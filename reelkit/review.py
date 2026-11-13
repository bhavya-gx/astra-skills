"""Timestamped review notes for a render, saved next to it as <render>.review.json.

Open a render in the browser, click the waveform for a moment or drag for a range, type a note. The assistant reads the
notes, fixes each one, writes a short "reply" and sets "done": true. Nothing leaves this computer.
"""
from __future__ import annotations
from array import array
import json
import math
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
from urllib.parse import parse_qs, unquote, urlparse
import webbrowser
from .media import ROOT, ffmpeg
from .timeline import read_srt

VIDEO_SUFFIXES = (".mp4", ".mov", ".webm", ".mkv")
MAX_NOTES_BYTES = 256 * 1024
PEAK_COUNT = 1600


def notes_path(render):
    return Path(render).with_suffix(".review.json")


def read_notes(render):
    p = notes_path(render)
    if not p.exists():
        return []
    notes = json.loads(p.read_text(encoding="utf-8"))
    return notes if isinstance(notes, list) else []


def clean_notes(notes):
    """Keep only the fields the page and the assistant use, sorted by start time."""
    if not isinstance(notes, list):
        raise ValueError("Notes must be a list.")
    result = []
    for n in notes:
        if not isinstance(n, dict) or not isinstance(n.get("note"), str):
            raise ValueError("Each note needs text.")
        start = float(n.get("start", 0)); end = float(n.get("end", start))
        if not (math.isfinite(start) and math.isfinite(end)) or start < 0 or end < start:
            raise ValueError("Note times must be ordered and finite.")
        item = dict(start=round(start, 2), end=round(end, 2), note=n["note"][:2000], words=str(n.get("words", ""))[:500], done=bool(n.get("done")))
        if n.get("reply"):
            item["reply"] = str(n["reply"])[:2000]
        result.append(item)
    return sorted(result, key=lambda x: (x["start"], x["end"]))


def write_notes(render, notes):
    notes = clean_notes(notes)
    notes_path(render).write_text(json.dumps(notes, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return notes


def captions_for(render):
    """Edited-time captions beside the render: <stem>.srt first, then the render folder's captions.srt."""
    render = Path(render)
    for candidate in (render.with_suffix(".srt"), render.parent / "captions.srt"):
        if candidate.is_file():
            try:
                return read_srt(candidate)
            except ValueError:
                return []
    return []


def words_in(cues, start, end):
    return " ".join(c["text"] for c in cues if c["end"] > start - .3 and c["start"] < end + .3)


def stamp(seconds):
    return f"{int(seconds // 60)}:{seconds % 60:04.1f}"


def format_notes(render, include_done=False):
    """Plain text for the assistant: one line per note, open notes first unless include_done."""
    notes = read_notes(render)
    cues = captions_for(render)
    lines = []
    for i, n in enumerate(notes, 1):
        if n.get("done") and not include_done:
            continue
        when = stamp(n["start"]) + (f" to {stamp(n['end'])}" if n["end"] > n["start"] + .2 else "")
        words = n.get("words") or words_in(cues, n["start"], n["end"])
        state = "done" if n.get("done") else ("in progress" if n.get("reply") else "open")
        lines.append(f"{i}. [{state}] {when}  {n['note']}" + (f'  ("{words}")' if words else "") + (f"\n   reply: {n['reply']}" if n.get("reply") else ""))
    if not lines:
        return "No open notes." if notes else "No notes yet."
    return "\n".join(lines)


def peaks_for(render):
    """Waveform peaks for the page, decoded through the bundled FFmpeg. Silent or video-only files give an empty list."""
    rate = 8000
    result = subprocess.run([ffmpeg(), "-v", "error", "-i", str(render), "-map", "0:a:0?", "-vn", "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"], capture_output=True)
    raw = result.stdout
    if result.returncode or len(raw) < 4:
        return dict(duration=0, peaks=[])
    samples = array("h"); samples.frombytes(raw[: len(raw) // 2 * 2])
    if sys.byteorder != "little":
        samples.byteswap()
    bucket = max(1, len(samples) // PEAK_COUNT)
    peaks = []
    for i in range(0, len(samples) - len(samples) % bucket, bucket):
        chunk = samples[i:i + bucket]
        peaks.append(round(max(abs(max(chunk)), abs(min(chunk))) / 32768.0, 3))
    return dict(duration=len(samples) / rate, peaks=peaks)


def renders_under(root):
    """Finished renders under a folder, newest first. Work files and unpromoted candidates are skipped."""
    found = []
    for p in sorted(Path(root).rglob("*")):
        if p.suffix.lower() not in VIDEO_SUFFIXES or not p.is_file():
            continue
        if "work" in p.relative_to(root).parts or p.name == "candidate.mp4" or p.name.startswith("transcription-"):
            continue
        found.append(p)
    return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)


def ago(t):
    s = time.time() - t
    if s < 60:
        return "just now"
    if s < 3600:
        return f"{int(s // 60)} min ago"
    if s < 86400:
        return f"{int(s // 3600)} h ago"
    return time.strftime("%b %d", time.localtime(t))


def inline_json(value):
    return json.dumps(value).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def make_review_server(target, port=0):
    target = Path(target).resolve()
    if target.is_file():
        root, single = target.parent, target
    elif target.is_dir():
        root, single = target, None
    else:
        raise ValueError(f"Render or folder not found: {target}")
    token = secrets.token_urlsafe(32)
    page = (ROOT / "reelkit/web/review.html").read_text(encoding="utf-8")
    peak_cache = {}

    def info_for(p):
        notes = read_notes(p)
        saved = notes_path(p).stat().st_mtime if notes_path(p).exists() else None
        open_count = sum(not n.get("done") for n in notes)
        return dict(file=p.relative_to(root).as_posix(), name=p.name, folder=p.parent.relative_to(root).as_posix() if p.parent != root else "",
                    rendered=ago(p.stat().st_mtime), saved=ago(saved) if saved else None, open=open_count, done=len(notes) - open_count)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, obj, status=200, kind="application/json"):
            data = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
            self.send_response(status); self.send_header("Content-Type", kind); self.send_header("Content-Length", str(len(data))); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(data)

        def trusted(self):
            host = self.headers.get("Host", ""); port = self.server.server_port
            return host in (f"127.0.0.1:{port}", f"localhost:{port}") and self.headers.get("Origin", f"http://{host}") == f"http://{host}"

        def target_file(self):
            rel = parse_qs(urlparse(self.path).query).get("file", [""])[0]
            p = (root / rel).resolve()
            if not rel or not p.is_relative_to(root) or not p.is_file() or p.suffix.lower() not in VIDEO_SUFFIXES:
                return None
            return p

        def do_GET(self):
            if not self.trusted():
                self.reply({"error": "Use the local review address."}, 403); return
            route = urlparse(self.path).path
            if route == "/":
                if single:
                    self.send_response(302); self.send_header("Location", "/review?file=" + single.name); self.end_headers(); return
                data = page.replace("__INFO__", inline_json({"library": [info_for(p) for p in renders_under(root)], "root": root.name})).replace("__TOKEN__", token).replace("__TITLE__", "Reviews")
                self.reply(data.encode(), kind="text/html; charset=utf-8"); return
            if route.startswith("/assets/"):
                asset = (ROOT / "assets" / unquote(route[len("/assets/"):])).resolve()
                if not asset.is_relative_to(ROOT / "assets") or not asset.is_file():
                    self.reply({"error": "Not found"}, 404); return
                self.reply(asset.read_bytes(), kind=mimetypes.guess_type(str(asset))[0] or "application/octet-stream"); return
            p = self.target_file()
            if not p:
                self.reply({"error": "Not found"}, 404); return
            if route == "/review":
                info = info_for(p); info["library"] = None
                data = page.replace("__INFO__", inline_json(info)).replace("__TOKEN__", token).replace("__TITLE__", "Review " + p.name)
                self.reply(data.encode(), kind="text/html; charset=utf-8"); return
            if route == "/notes":
                self.reply(read_notes(p)); return
            if route == "/captions":
                self.reply(captions_for(p)); return
            if route == "/peaks":
                key = (str(p), p.stat().st_mtime_ns)
                if key not in peak_cache:
                    peak_cache.clear(); peak_cache[key] = peaks_for(p)
                self.reply(peak_cache[key]); return
            if route == "/video":
                self.send_video(p); return
            self.reply({"error": "Not found"}, 404)

        def do_POST(self):
            if not self.trusted() or self.headers.get("X-Reel-Token") != token:
                self.reply({"error": "Session expired. Reload the page."}, 403); return
            p = self.target_file()
            if urlparse(self.path).path != "/notes" or not p:
                self.reply({"error": "Not found"}, 404); return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_NOTES_BYTES:
                    raise ValueError("Notes are empty or too large.")
                notes = write_notes(p, json.loads(self.rfile.read(length)))
                self.reply({"saved": ago(time.time()), "notes": notes})
            except (ValueError, TypeError) as e:
                self.reply({"error": str(e)}, 400)

        def send_video(self, target):
            size = target.stat().st_size; start = 0; end = size - 1; status = 200
            requested = self.headers.get("Range")
            if requested:
                m = re.fullmatch(r"bytes=(\d+)-(\d*)", requested)
                if not m:
                    self.reply({"error": "Unsupported range"}, 416); return
                start = int(m[1]); end = min(end, int(m[2])) if m[2] else end; status = 206
                if start > end:
                    self.reply({"error": "Range outside file"}, 416); return
            self.send_response(status); self.send_header("Content-Type", "video/mp4" if target.suffix.lower() == ".mp4" else "application/octet-stream"); self.send_header("Content-Length", str(end - start + 1)); self.send_header("Accept-Ranges", "bytes")
            if status == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("X-Content-Type-Options", "nosniff"); self.end_headers()
            try:
                with target.open("rb") as f:
                    f.seek(start); left = end - start + 1
                    while left:
                        chunk = f.read(min(left, 1024 * 1024)); self.wfile.write(chunk); left -= len(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.session_token = token; server.root = root
    return server


def serve_review(target, port=0, open_browser=True):
    server = make_review_server(target, port)
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"Astra Skills review · {url}\nNotes save next to each render as <render>.review.json. Press Ctrl+C to stop.", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
