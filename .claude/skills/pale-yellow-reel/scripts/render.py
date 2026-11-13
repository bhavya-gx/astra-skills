"""Render the approved static-title style with explicitly supplied local assets."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import uuid

import imageio_ffmpeg
from PIL import Image

SKILL = Path(__file__).resolve().parents[1]


def run(args):
    result = subprocess.run([str(x) for x in args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-4000:])
    return result


def video_info(path):
    reader = imageio_ffmpeg.read_frames(str(path))
    try:
        return next(reader)
    finally:
        reader.close()


def audio_info(path, ffmpeg):
    # Input-only probing exits nonzero because no output was requested.
    result = subprocess.run([ffmpeg, '-hide_banner', '-i', str(path)],
                            capture_output=True, text=True)
    audio = re.search(r'Stream[^\n]*Audio:[^\n]+', result.stderr)
    duration = re.search(r'Duration:\s+(\d+):(\d+):(\d+(?:\.\d+)?)', result.stderr)
    rate = re.search(r'(\d+) Hz', audio.group()) if audio else None
    if not audio or not duration or not rate:
        raise ValueError(f'No readable audio track: {path}')
    h, m, s = map(float, duration.groups())
    return h * 3600 + m * 60 + s, int(rate[1])


def geometry(zoom, crop_x, crop_y):
    if not all(math.isfinite(x) for x in (zoom, crop_x)) or zoom < 1:
        raise ValueError('Zoom must be finite and at least 1.')
    crop_y = 1 - 1 / zoom if crop_y is None else crop_y
    if not math.isfinite(crop_y) or min(crop_x, crop_y) < 0:
        raise ValueError('Crop positions must be finite and nonnegative.')
    if max(crop_x, crop_y) + 1 / zoom > 1 + 1e-9:
        raise ValueError('Crop extends outside the source; adjust zoom or position.')
    return crop_y


def render(source, output, assets=None, *, start=.2, duration=4.,
           zoom=1.28, crop_x=.07, crop_y=None, draft=False):
    source, output = Path(source).resolve(), Path(output).resolve()
    assets = Path(assets or SKILL / 'assets').resolve()
    title, audio = assets / 'title.png', assets / 'audio.m4a'
    for path in (source, title, audio):
        if not path.is_file():
            raise ValueError(f'Missing local input: {path}. Supply --assets with title.png/audio.m4a.')
    sidecar = output.with_suffix('.project.json')
    if output.exists() or sidecar.exists():
        raise ValueError('Output or project already exists; choose a new filename.')
    if output.suffix.lower() != '.mp4':
        raise ValueError('Output must have an .mp4 extension.')
    if not math.isfinite(start) or start < 0 or not math.isfinite(duration) or duration <= 0:
        raise ValueError('Start must be nonnegative and duration positive, in seconds.')
    frames = round(duration * 30)
    if frames < 1 or abs(frames / 30 - duration) > 1e-6:
        raise ValueError('Duration must be a whole number of 30 fps frames.')
    crop_y = geometry(zoom, crop_x, crop_y)
    with Image.open(title) as im:
        if im.size != (1080, 1920) or im.mode != 'RGBA':
            raise ValueError('title.png must be a 1080x1920 RGBA overlay.')
        if im.getchannel('A').getextrema() != (0, 255):
            raise ValueError('Title needs transparent background and opaque lettering.')
    info = video_info(source)
    # read_frames reports the decoded output geometry after display rotation.
    w, h = info['size']
    if abs(w / h - 9 / 16) > .003:
        raise ValueError('Use portrait 9:16 footage; reframe other aspect ratios first.')
    if start + duration > info['duration'] + .01:
        raise ValueError('Source is too short for the requested start and duration.')
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    if audio_info(audio, ffmpeg)[0] + .01 < duration:
        raise ValueError('Reference audio is shorter than the requested duration.')
    width, height = (540, 960) if draft else (1080, 1920)
    graph = (
        f'[0:v:0]trim=start={start}:duration={duration+.1},setpts=PTS-STARTPTS,'
        f'crop=iw/{zoom}:ih/{zoom}:iw*{crop_x}:ih*{crop_y},'
        f'scale={width}:{height}:flags=lanczos:in_range=auto:out_range=tv,setsar=1,'
        f'fps=30,trim=end_frame={frames},setpts=N/(30*TB),format=yuv420p,'
        "lutyuv=y='(val-16)*0.93+16'[picture];"
        f'[1:v:0]scale={width}:{height}:flags=lanczos,format=rgba[title];'
        '[picture][title]overlay=0:0:format=auto:eof_action=repeat,format=yuv420p[v];'
        f'[2:a:0]atrim=start=0:end={duration},asetpts=PTS-STARTPTS,aresample=44100[a]'
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    candidate = output.with_name(f'.{output.stem}-{uuid.uuid4().hex}.mp4')
    lock = output.with_name(f'.{output.name}.lock')
    command = [ffmpeg, '-hide_banner', '-y', '-i', source, '-i', title, '-i', audio,
               '-filter_complex_threads', '2', '-filter_complex', graph,
               '-map', '[v]', '-map', '[a]', '-map_metadata', '-1',
               '-c:v', 'libx264', '-crf', '20' if draft else '17',
               '-preset', 'fast' if draft else 'slow', '-threads', '4',
               '-pix_fmt', 'yuv420p', '-r', '30', '-color_primaries', 'bt709',
               '-color_trc', 'bt709', '-colorspace', 'bt709', '-color_range', 'tv',
               '-c:a', 'aac', '-b:a', '192k', '-ar', '44100', '-movflags', '+faststart', candidate]
    with lock.open('x', encoding='utf-8') as f:
        f.write(str(candidate))
    try:
        run(command)
        decoded = run([ffmpeg, '-v', 'error', '-xerror', '-i', candidate,
                       '-map', '0:v:0', '-map', '0:a:0', '-f', 'null', '-'])
        if decoded.stderr.strip():
            raise RuntimeError('Full decode reported errors.')
        reader = imageio_ffmpeg.read_frames(str(candidate))
        try:
            exported = next(reader)
            count = sum(1 for _ in reader)
        finally:
            reader.close()
        audio_duration, rate = audio_info(candidate, ffmpeg)
        if (tuple(exported['size']) != (width, height) or count != frames
                or abs(exported['fps'] - 30) > .01 or rate != 44100
                or abs(audio_duration - duration) > .04):
            raise RuntimeError('Rendered geometry, timing, frame count or audio failed validation.')
        report = {'passed': True, 'width': width, 'height': height, 'frames': count,
                  'fps': 30, 'duration': frames / 30, 'audio_rate': rate, 'full_decode': True,
                  'sha256': hashlib.sha256(candidate.read_bytes()).hexdigest()}
        # The stored command is directly reusable with a caller-chosen output path.
        command[-1] = output
        project = {'source': str(source), 'source_range': [start, start + duration],
                   'output_range': [0, duration], 'assets': str(assets),
                   'crop': {'zoom': zoom, 'x': crop_x, 'y': crop_y},
                   'filtergraph': graph, 'command': [str(x) for x in command],
                   'validation': report}
        if output.exists() or sidecar.exists():
            raise ValueError('Output appeared during rendering; choose another filename.')
        candidate.rename(output)
        sidecar.write_text(json.dumps(project, indent=2), encoding='utf-8')
        return report
    finally:
        candidate.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def main():
    defaults = json.loads((SKILL / 'assets/style.json').read_text(encoding='utf-8'))
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--assets', type=Path)
    p.add_argument('--start', type=float, default=defaults['source_start'])
    p.add_argument('--duration', type=float, default=defaults['duration'])
    p.add_argument('--zoom', type=float, default=defaults['zoom'])
    p.add_argument('--crop-x', type=float, default=defaults['crop_x'])
    p.add_argument('--crop-y', type=float)
    p.add_argument('--draft', action='store_true')
    args = p.parse_args()
    try:
        print(json.dumps(render(**vars(args)), indent=2))
    except (ValueError, RuntimeError, OSError) as error:
        p.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
