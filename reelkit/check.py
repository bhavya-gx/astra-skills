"""Check a finished reel for the faults a reviewer keeps catching, and print PASS or FAIL per check.

Only FFmpeg is needed. Checks: a readable export with audio, pauses left in the cut, frozen picture, loudness
and true peak, a phrase repeated across a cut (needs the captions), and loud stretches with no caption (needs the captions).
"""
from __future__ import annotations
from array import array
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from .media import ffmpeg, inspect
from .timeline import read_srt

STOP = set("a an the and to of i im is it in on for you your we were with that this so are be or my me uh um".split())
RATE = 16000


def normalise(word):
    return re.sub(r"[^a-z0-9%]", "", word.lower().replace("'", ""))


def cue_words(cues):
    """(word, time) pairs spread evenly across each cue."""
    words = []
    for c in cues:
        parts = [normalise(w) for w in c["text"].split()]
        parts = [w for w in parts if w]
        step = (c["end"] - c["start"]) / max(1, len(parts))
        words += [(w, c["start"] + i * step) for i, w in enumerate(parts)]
    return words


def find_repeats(cues, joins=None, window=4.0):
    """A two-word phrase said twice within the window is a probable retake: FAIL. One repeated content word is listed for review.
    With joins (output seconds), only repeats that straddle a join count."""
    words = cue_words(cues)
    pairs = [((words[i][0], words[i + 1][0]), words[i][1]) for i in range(len(words) - 1)]
    bad, review = [], []
    def straddles(t1, t2):
        return joins is None or any(t1 < j <= t2 + .6 for j in joins)
    seen = set()
    for i, (pair, t) in enumerate(pairs):
        if set(pair) <= STOP:
            continue
        for pair2, t2 in pairs[i + 2:]:
            if t2 - t > window:
                break
            if pair2 == pair and straddles(t, t2) and (pair, round(t, 1)) not in seen:
                seen.add((pair, round(t, 1))); bad.append(dict(phrase=" ".join(pair), first=round(t, 2), second=round(t2, 2)))
    for i, (w, t) in enumerate(words):
        if w in STOP or len(w) < 3:
            continue
        for w2, t2 in words[i + 1:]:
            if t2 - t > 2.5:
                break
            if w2 == w and straddles(t, t2) and not any(w in b["phrase"].split() and abs(b["first"] - t) < 1 for b in bad):
                review.append(dict(word=w, first=round(t, 2), second=round(t2, 2))); break
    return bad, review


def silence_runs(path, noise_db=-35, minimum=.35):
    log = subprocess.run([ffmpeg(), "-nostdin", "-v", "info", "-i", str(path), "-vn", "-af", f"silencedetect=noise={noise_db}dB:d={minimum}", "-f", "null", "-"], capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: (-?[0-9.]+)", log)]
    ends = [(float(a), float(b)) for a, b in re.findall(r"silence_end: ([0-9.]+) \| silence_duration: ([0-9.]+)", log)]
    runs = [(s, e) for s, (e, d) in zip(starts, ends)]
    if len(starts) > len(ends):
        runs.append((starts[-1], None))
    return runs


def freezes(path, duration):
    """(start, length) of still stretches. A freeze that lasts to the end logs no duration, so it runs to the end."""
    log = subprocess.run([ffmpeg(), "-nostdin", "-v", "info", "-i", str(path), "-an", "-vf", "freezedetect=n=0.001:d=0.5", "-f", "null", "-"], capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"freeze_start: ([0-9.]+)", log)]
    durations = [float(x) for x in re.findall(r"freeze_duration: ([0-9.]+)", log)]
    if len(starts) > len(durations):
        durations.append(max(0, duration - starts[-1]))
    return list(zip(starts, durations))


def loudness(path):
    log = subprocess.run([ffmpeg(), "-nostdin", "-v", "info", "-i", str(path), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    integrated = re.search(r"Integrated loudness:\s*I:\s*(-?(?:inf|[0-9.]+)) LUFS", log)
    peak = re.search(r"True peak:\s*Peak:\s*(-?(?:inf|[0-9.]+)) dBFS", log)
    return (float(integrated[1]) if integrated else None, float(peak[1]) if peak else None)


def loud_frames(path, level_db=-30):
    """50 ms windows above level_db, as (hop seconds, list of bools). Standard library only."""
    rate = 4000; hop = rate // 20
    raw = subprocess.run([ffmpeg(), "-v", "error", "-i", str(path), "-map", "0:a:0?", "-vn", "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"], capture_output=True).stdout
    samples = array("h"); samples.frombytes(raw[: len(raw) // 2 * 2])
    if sys.byteorder != "little":
        samples.byteswap()
    floor = 32768.0 * 10 ** (level_db / 20)
    mask = []
    for i in range(0, len(samples) - len(samples) % hop, hop):
        chunk = samples[i:i + hop]
        mask.append(math.sqrt(sum(v * v for v in chunk) / hop) > floor)
    return hop / rate, mask


def stretches(mask, step, minimum):
    """Stretches of True in mask lasting at least minimum seconds, as (start, end) seconds."""
    found, start = [], None
    for i, on in enumerate(list(mask) + [False]):
        if on and start is None:
            start = i
        elif not on and start is not None:
            if (i - start) * step >= minimum:
                found.append((start * step, i * step))
            start = None
    return found


def check(path, captions=None, edl=None, max_pause=.5, target_lufs=-16, tolerance=2, max_peak=-1):
    path = Path(path).resolve()
    if captions is None and (path.parent / "captions.srt").is_file():
        captions = path.parent / "captions.srt"
    if edl is None and (path.parent / "edit-decisions.json").is_file():
        edl = path.parent / "edit-decisions.json"
    info = inspect(path)
    duration = info["duration"]
    results = []
    def add(name, ok, detail, items=()):
        results.append(dict(name=name, ok=bool(ok), detail=detail, items=list(items)))
    add("export", info["has_audio"], f"{info['width']}x{info['height']}, {duration:.2f} s, " + ("audio present" if info["has_audio"] else "no audio track"))
    if not info["has_audio"]:
        return dict(file=path.name, duration=duration, ok=False, checks=results)
    runs = silence_runs(path)
    inner = [(a, b) for a, b in runs if b is not None and a > .05 and b < duration - .1 and b - a > max_pause]
    add("pauses", not inner, f"longest inner pause {max((b - a for a, b in inner), default=0):.2f} s (limit {max_pause} s)", [f"{a:.2f} to {b:.2f} s" for a, b in inner])
    stuck = freezes(path, duration)
    long_ = [(s, d) for s, d in stuck if d >= 3]
    add("freezes", not long_, f"{len(long_)} frozen for 3 s or more" + (f", {len(stuck) - len(long_)} shorter still stretches to review" if len(stuck) > len(long_) else ""), [f"{s:.2f} s for {d:.2f} s" for s, d in long_])
    lufs, peak = loudness(path)
    loud_ok = lufs is not None and abs(lufs - target_lufs) <= tolerance and (peak is None or peak <= max_peak)
    add("loudness", loud_ok, f"integrated {lufs} LUFS (target {target_lufs} ±{tolerance}), true peak {peak} dBTP (limit {max_peak})")
    if captions:
        cues = read_srt(captions)
        joins = None
        if edl:
            segments = json.loads(Path(edl).read_text(encoding="utf-8"))
            joins = [s["output_start"] for s in segments[1:]]
        bad, review = find_repeats(cues, joins)
        add("repeats", not bad, f"{len(cues)} captions scanned" + (" at the cuts" if joins else "") + (f", {len(review)} single repeated words to review" if review else ""),
            [f"'{b['phrase']}' at {b['first']:.1f} and {b['second']:.1f} s" for b in bad] + [f"review: '{r['word']}' at {r['first']:.1f} and {r['second']:.1f} s" for r in review])
        step, loud = loud_frames(path)
        covered = [False] * len(loud)
        for c in cues:
            for i in range(max(0, int(c["start"] / step)), min(len(loud), int(c["end"] / step) + 1)):
                covered[i] = True
        uncaptioned = stretches([a and not b for a, b in zip(loud, covered)], step, .35)
        add("uncaptioned sound", True, f"{len(uncaptioned)} loud stretches with no caption (review: speech that was cut from the captions, or music and effects)", [f"{a:.2f} to {b:.2f} s" for a, b in uncaptioned])
    else:
        add("repeats", True, "skipped: no captions.srt beside the render and none given with --captions")
    return dict(file=path.name, duration=duration, ok=all(r["ok"] for r in results), checks=results)


def format_report(report):
    lines = [f"{report['file']} ({report['duration']:.1f} s)"]
    for r in report["checks"]:
        lines.append(f"  {'PASS' if r['ok'] else 'FAIL'}  {r['name']}: {r['detail']}")
        lines += [f"        {item}" for item in r["items"]]
    return "\n".join(lines)
