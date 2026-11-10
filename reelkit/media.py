from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def ffmpeg():
    override = os.environ.get("REELKIT_FFMPEG")
    if override:
        return override
    import imageio_ffmpeg
    # Use the same bundled build on a fresh installation and in verification.
    return imageio_ffmpeg.get_ffmpeg_exe()


def run(args, log=None):
    result = subprocess.run([str(x) for x in args], capture_output=True, text=True)
    if log:
        Path(log).write_text(result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"Media processing failed:\n{result.stderr[-3500:]}")
    return result


def inspect(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError(f"Video not found: {path}")
    result = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(path)], capture_output=True, text=True)
    info = result.stderr
    duration = re.search(r"Duration:\s+(\d+):(\d+):(\d+(?:\.\d+)?)", info)
    video = re.search(r"Stream[^\n]*Video:[^\n]+", info)
    if not duration or not video:
        raise ValueError("Use a video file with a readable duration (MP4, MOV, or WebM).")
    dims = re.search(r"(?:, |\s)(\d{2,6})x(\d{2,6})(?:[,\s\[])", video.group())
    if not dims:
        raise ValueError("Could not read video dimensions.")
    h, m, s = map(float, duration.groups())
    audio = re.search(r"Stream[^\n]*Audio:[^\n]+", info)
    sample_rate = re.search(r"(\d+) Hz", audio.group()) if audio else None
    return dict(duration=h*3600+m*60+s, width=int(dims[1]), height=int(dims[2]),
                has_audio=bool(audio), audio_rate=int(sample_rate[1]) if sample_rate else None,
                video_stream=video.group(), raw=info)


def validate(path, width, height, duration, directory):
    info = inspect(path)
    if (info["width"], info["height"]) != (width, height):
        raise RuntimeError("Export dimensions do not match the project.")
    if abs(info["duration"]-duration) > .16:
        raise RuntimeError("Export duration does not match the edit decision list.")
    if not info["has_audio"] or info["audio_rate"] != 48000:
        raise RuntimeError("Export audio is missing or has the wrong sample rate.")
    decoded=run([ffmpeg(), "-v", "error", "-xerror", "-i", path, "-f", "null", "-"], Path(directory)/"decode.log")
    if decoded.stderr.strip():
        raise RuntimeError("The export reported decoding errors. See decode.log.")
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    report = dict(status="passed", width=width, height=height, duration=info["duration"],
                  audio_rate=info["audio_rate"], full_decode=True, sha256=digest)
    Path(directory, "validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
