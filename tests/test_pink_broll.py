"""Behavior checks use synthetic pictures and tones, never personal media."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

import imageio_ffmpeg
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('pink_renderer', ROOT / '.agents/skills/pink-broll-reel/scripts/render.py')
STYLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STYLE)


class PinkStyleTests(unittest.TestCase):
    def test_approved_mapping_and_removed_fourth_shot(self):
        shots = json.loads((STYLE.SKILL / 'assets/style.json').read_text())['shots']
        self.assertEqual(len(shots), 3)
        cursor, boundaries = 0, []
        for shot in shots:
            start, frames, zoom, x, y, luma = STYLE.shot_values(shot)
            cursor += frames
            boundaries.append(cursor)
            self.assertAlmostEqual(y + 1 / zoom, 1)
        self.assertEqual(boundaries, [157, 281, 378])
        self.assertEqual(cursor / 30, 12.6)

    def test_invalid_timing_and_crops(self):
        valid = {'start': .2, 'frames': 12, 'zoom': 1.2, 'crop_x': .05, 'crop_y': 'bottom', 'luma': .92}
        for patch in [{'frames': 0}, {'frames': 1.5}, {'frames': True}, {'start': -1},
                      {'start': float('nan')}, {'zoom': .9}, {'crop_x': .7},
                      {'crop_y': -.1}, {'crop_y': float('inf')}, {'luma': 0}]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                STYLE.shot_values(dict(valid, **patch))

    def test_package_mirrors_and_private_assets_absent(self):
        for rel in ['SKILL.md', 'agents/openai.yaml', 'assets/style.json', 'scripts/render.py']:
            self.assertEqual((STYLE.SKILL / rel).read_bytes(), (ROOT / '.claude/skills/pink-broll-reel' / rel).read_bytes())
        for parent in ['.agents', '.claude']:
            assets = ROOT / parent / 'skills/pink-broll-reel/assets'
            self.assertEqual(sorted(p.name for p in assets.iterdir()), ['style.json'])

    def test_source_count_and_missing_assets_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            with self.assertRaisesRegex(ValueError, 'one source'):
                STYLE.render([p / 'a.mp4'], p / 'out.mp4', p)
            with self.assertRaisesRegex(ValueError, 'Missing local input'):
                STYLE.render([p / 'a.mp4'] * 3, p / 'out.mp4', p)
            self.assertFalse((p / 'out.mp4').exists())


@unittest.skipUnless(os.environ.get('REELKIT_INTEGRATION') == '1', 'Enable real renders')
class PinkRenderTests(unittest.TestCase):
    def test_three_shot_cuts_overlay_audio_and_master(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder);ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            sources = []
            for i, color in enumerate(['red', 'blue', 'lime']):
                source = p / f'{i}.mp4';sources.append(source)
                STYLE.run([ffmpeg, '-v', 'error', '-y', '-f', 'lavfi', '-i',
                           'color=black:s=360x640:r=30:d=0.2', '-f', 'lavfi', '-i',
                           f'color={color}:s=360x640:r=30:d=1.3', '-filter_complex',
                           '[0:v][1:v]concat=n=2:v=1:a=0[v]', '-map', '[v]',
                           '-c:v', 'libx264', '-pix_fmt', 'yuv420p', source])
            # iPhone-style rotation must be consumed once, not retained on export.
            STYLE.run([ffmpeg, '-v', 'error', '-y', '-i', sources[0], '-vf', 'transpose=1',
                       '-c:v', 'libx264', p / 'landscape.mp4'])
            STYLE.run([ffmpeg, '-v', 'error', '-y', '-display_rotation:v:0', '-90',
                       '-i', p / 'landscape.mp4', '-c', 'copy', p / 'rotated.mp4'])
            sources[0] = p / 'rotated.mp4'
            self.assertEqual(tuple(STYLE.video_info(sources[0])['size']), (360, 640))
            STYLE.run([ffmpeg, '-v', 'error', '-y', '-f', 'lavfi', '-i',
                       'sine=frequency=440:sample_rate=44100:duration=2', '-c:a', 'aac', p / 'audio.m4a'])
            title = Image.new('RGBA', (1080, 1920))
            ImageDraw.Draw(title).rectangle((350, 790, 730, 1140), fill=(237, 208, 222, 255))
            title.save(p / 'title.png')
            settings = {'shots': [{'start': .2, 'frames': frames, 'zoom': 1., 'crop_x': 0.,
                                    'crop_y': 'bottom', 'luma': 1.} for frames in [12, 15, 9]]}
            (p / 'settings.json').write_text(json.dumps(settings))
            report = STYLE.render(sources, p / 'draft.mp4', p, settings=p / 'settings.json', draft=True)
            self.assertEqual((report['frames'], report['width'], report['height']), (36, 540, 960))
            self.assertAlmostEqual(report['decoded_audio_duration'], 1.2, delta=.04)
            reader = imageio_ffmpeg.read_frames(str(p / 'draft.mp4'));next(reader)
            for i, data in enumerate(reader):
                if i in [0, 11, 12, 26, 27, 35]:
                    im = Image.frombytes('RGB', (540, 960), data)
                    expected_channel = 0 if i < 12 else (2 if i < 27 else 1)
                    pixel = im.getpixel((10, 10))
                    self.assertGreater(pixel[expected_channel], 220)
                    self.assertLess(sum(pixel)-pixel[expected_channel], 30)
                    self.assertLess(max(abs(a-b) for a, b in zip(im.getpixel((270, 470)), (237, 208, 222))), 12)
            project = json.loads((p / 'draft.project.json').read_text())
            self.assertEqual([s['output_frames'] for s in project['shots']], [[0, 12], [12, 27], [27, 36]])
            self.assertAlmostEqual(project['shots'][0]['source_range'][0], .2)
            self.assertAlmostEqual(project['shots'][0]['source_range'][1], .6)
            before = (p / 'draft.mp4').read_bytes()
            with self.assertRaisesRegex(ValueError, 'already exists'):
                STYLE.render(sources, p / 'draft.mp4', p, settings=p / 'settings.json', draft=True)
            self.assertEqual(before, (p / 'draft.mp4').read_bytes())
            master = STYLE.render(sources, p / 'master.mp4', p, settings=p / 'settings.json')
            self.assertEqual((master['width'], master['height'], master['frames']), (1080, 1920, 36))
            settings['shots'][0]['frames'] = 50
            (p / 'too-long.json').write_text(json.dumps(settings))
            with self.assertRaisesRegex(ValueError, 'Source is too short'):
                STYLE.render(sources, p / 'invalid.mp4', p, settings=p / 'too-long.json')
            STYLE.run([ffmpeg, '-v', 'error', '-y', '-f', 'lavfi', '-i',
                       'sine=duration=0.2:sample_rate=44100', '-c:a', 'aac', p / 'audio.m4a'])
            with self.assertRaisesRegex(ValueError, 'audio is shorter'):
                STYLE.render(sources, p / 'short-audio.mp4', p, settings=p / 'settings.json')


if __name__ == '__main__':
    unittest.main()
