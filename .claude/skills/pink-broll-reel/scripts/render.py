"""Render the approved pink title and reference soundtrack over ordered local B-roll."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import uuid

import imageio_ffmpeg
from PIL import Image

SKILL = Path(__file__).resolve().parents[1]


def run(args):
    result = subprocess.run([str(x) for x in args], capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace')[-4000:])
    return result


def video_info(path):
    reader = imageio_ffmpeg.read_frames(str(path))
    try:
        return next(reader)
    finally:
        reader.close()


def audio_duration(path, ffmpeg):
    # Measure decoded samples, avoiding container priming and duration metadata.
    data = run([ffmpeg, '-v', 'error', '-i', path, '-map', '0:a:0',
                '-ac', '1', '-ar', '44100', '-f', 's16le', '-']).stdout
    return len(data) / (44100 * 2)


def shot_values(shot):
    start = float(shot['start'])
    frames = shot['frames']
    zoom, x, luma = (float(shot[k]) for k in ('zoom', 'crop_x', 'luma'))
    if (not isinstance(frames, int) or isinstance(frames, bool) or frames < 1
            or not all(math.isfinite(v) for v in (start, zoom, x, luma))
            or start < 0 or zoom < 1 or not 0 < luma <= 1):
        raise ValueError('Shot needs a nonnegative start, positive integer frames, zoom >= 1 and luma in (0, 1].')
    y = 1 - 1 / zoom if shot['crop_y'] == 'bottom' else float(shot['crop_y'])
    if not math.isfinite(y) or min(x, y) < 0 or max(x, y) + 1 / zoom > 1 + 1e-9:
        raise ValueError('Crop extends outside the source.')
    return start, frames, zoom, x, y, luma


def render(sources, output, assets=None, *, settings=None, draft=False):
    sources = [Path(p).resolve() for p in sources]
    output = Path(output).resolve()
    assets = Path(assets or SKILL / 'assets').resolve()
    settings = Path(settings or SKILL / 'assets/style.json').resolve()
    shots = json.loads(settings.read_text(encoding='utf-8'))['shots']
    if not shots or len(shots) != len(sources):
        raise ValueError('Provide one source for each shot in the settings.')
    values = [shot_values(s) for s in shots]
    title, audio = assets / 'title.png', assets / 'audio.m4a'
    for path in [*sources, title, audio]:
        if not path.is_file():
            raise ValueError(f'Missing local input: {path}; supply original title.png/audio.m4a assets.')
    sidecar = output.with_suffix('.project.json')
    if output.exists() or sidecar.exists():
        raise ValueError('Output or project already exists; choose a new filename.')
    if output.suffix.lower() != '.mp4':
        raise ValueError('Output must have an .mp4 extension.')
    with Image.open(title) as im:
        if im.size != (1080, 1920) or im.mode != 'RGBA' or im.getchannel('A').getextrema() != (0, 255):
            raise ValueError('title.png must be 1080x1920 RGBA with transparent background and opaque lettering.')
    for source, (start, frames, *_rest) in zip(sources, values):
        info = video_info(source)
        width, height = info['size']  # Decoded geometry after display rotation.
        if abs(width / height - 9 / 16) > .003:
            raise ValueError(f'Use portrait 9:16 footage: {source}')
        if start + frames / 30 > info['duration'] + .01:
            raise ValueError(f'Source is too short for its shot: {source}')
    total_frames = sum(s[1] for s in values)
    duration = total_frames / 30
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    if audio_duration(audio, ffmpeg) + .001 < duration:
        raise ValueError('Reference audio is shorter than the edited picture.')
    width, height = (540, 960) if draft else (1080, 1920)
    graph, mapping, cursor = [], [], 0
    for i, (source, (start, frames, zoom, x, y, luma)) in enumerate(zip(sources, values)):
        graph.append(
            f'[{i}:v:0]trim=start={start}:duration={frames/30+.1},setpts=PTS-STARTPTS,'
            f'fps=30,trim=end_frame={frames},setpts=N/(30*TB),'
            f'crop=iw/{zoom}:ih/{zoom}:iw*{x}:ih*{y},'
            f'scale={width}:{height}:flags=lanczos:in_range=auto:out_range=tv,setsar=1,'
            f"format=yuv420p,lutyuv=y='(val-16)*{luma}+16'[s{i}]")
        mapping.append({'source': str(source), 'source_range': [start, start + frames/30],
                        'output_frames': [cursor, cursor+frames],
                        'output_range': [cursor/30, (cursor+frames)/30],
                        'crop': {'zoom': zoom, 'x': x, 'y': y}, 'luma': luma})
        cursor += frames
    n = len(sources)
    graph += [''.join(f'[s{i}]' for i in range(n)) + f'concat=n={n}:v=1:a=0[picture]',
              f'[{n}:v:0]scale={width}:{height}:flags=lanczos,format=rgba[title]',
              '[picture][title]overlay=0:0:format=auto:eof_action=repeat,format=yuv420p[v]',
              f'[{n+1}:a:0]atrim=end={duration},asetpts=PTS-STARTPTS,aresample=44100[a]']
    graph = ';\n'.join(graph)
    output.parent.mkdir(parents=True, exist_ok=True)
    candidate = output.with_name(f'.{output.stem}-{uuid.uuid4().hex}.mp4')
    encoded = candidate.with_name(candidate.stem + '.encoded.mp4')
    lock = output.with_name(f'.{output.name}.lock')
    command = [ffmpeg, '-hide_banner', '-y']
    for path in [*sources, title, audio]:
        command += ['-i', path]
    command += ['-filter_complex_threads', '2', '-filter_complex', graph,
                '-map', '[v]', '-map', '[a]', '-map_metadata', '-1',
                '-metadata:s:v:0', 'rotate=0', '-c:v', 'libx264',
                '-crf', '20' if draft else '17', '-preset', 'fast' if draft else 'slow',
                '-threads', '4', '-pix_fmt', 'yuv420p', '-r', '30',
                '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
                '-color_range', 'tv', '-c:a', 'aac', '-b:a', '192k', '-ar', '44100',
                '-movflags', '+faststart', encoded]
    with lock.open('x', encoding='utf-8') as f:
        f.write(str(candidate))
    try:
        run(command)
        # FFmpeg 7 can retain input display matrices through a complex graph.
        # Pixels are already autorotated; clear only the container transform.
        remux = [ffmpeg, '-v', 'error', '-y', '-display_rotation:v:0', '0',
                 '-i', encoded, '-map', '0:v:0', '-map', '0:a:0', '-c', 'copy',
                 '-map_metadata', '-1', '-movflags', '+faststart', candidate]
        run(remux)
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
        sound_length = audio_duration(candidate, ffmpeg)
        if (tuple(exported['size']) != (width, height) or count != total_frames
                or abs(exported['fps'] - 30) > .01 or abs(sound_length-duration) > .04):
            raise RuntimeError('Rendered dimensions, timing, frame count or audio failed validation.')
        report = {'passed': True, 'width': width, 'height': height, 'frames': count,
                  'fps': 30, 'duration': duration, 'audio_rate': 44100,
                  'decoded_audio_duration': sound_length, 'full_decode': True,
                  'sha256': hashlib.sha256(candidate.read_bytes()).hexdigest()}
        remux[-1] = output
        project = {'shots': mapping, 'assets': str(assets),
                   'asset_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (title, audio)},
                   'filtergraph': graph, 'commands': [[str(x) for x in c] for c in (command, remux)],
                   'validation': report}
        if output.exists() or sidecar.exists():
            raise ValueError('Output appeared during rendering; choose a new filename.')
        candidate.rename(output)
        sidecar.write_text(json.dumps(project, indent=2), encoding='utf-8')
        return report
    finally:
        candidate.unlink(missing_ok=True)
        encoded.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sources', required=True, nargs='+', type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--assets', type=Path)
    p.add_argument('--settings', type=Path)
    p.add_argument('--draft', action='store_true')
    try:
        print(json.dumps(render(**vars(p.parse_args())), indent=2))
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
        p.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
