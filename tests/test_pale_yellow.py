"""Behavior checks for the standalone style; fixtures contain no personal media."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

import imageio_ffmpeg
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'pale_yellow_renderer', ROOT / '.agents/skills/pale-yellow-reel/scripts/render.py')
STYLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STYLE)


class GeometryTests(unittest.TestCase):
    def test_approved_crop_and_head_placement(self):
        y = STYLE.geometry(1.28, .07, None)
        self.assertAlmostEqual(y + 1 / 1.28, 1)
        # A point 43.8% down the source should land near the approved 28% line.
        self.assertAlmostEqual((.438 - y) * 1.28, .28, delta=.005)

    def test_invalid_crop_rejected(self):
        for values in [(0, .07, None), (1.28, .3, None), (1.28, .07, -.1),
                       (float('nan'), .07, None), (1.28, .07, float('inf'))]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                STYLE.geometry(*values)

    def test_missing_assets_never_use_substitute(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            (p / 'source.mp4').touch()
            with self.assertRaisesRegex(ValueError, 'Missing local input'):
                STYLE.render(p / 'source.mp4', p / 'out.mp4', p)
            self.assertFalse((p / 'out.mp4').exists())


@unittest.skipUnless(os.environ.get('REELKIT_INTEGRATION') == '1', 'Enable real renders')
class StyleRenderTests(unittest.TestCase):
    def test_timing_overlay_preview_master_and_preserved_output(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            STYLE.run([ffmpeg, '-v', 'error', '-y', '-f', 'lavfi', '-i',
                       'color=red:s=360x640:r=30:d=1', '-f', 'lavfi', '-i',
                       'color=blue:s=360x640:r=30:d=3.5', '-filter_complex',
                       '[0:v][1:v]concat=n=2:v=1:a=0[v]', '-map', '[v]',
                       '-c:v', 'libx264', '-pix_fmt', 'yuv420p', p / 'source.mp4'])
            STYLE.run([ffmpeg, '-v', 'error', '-y', '-f', 'lavfi', '-i',
                       'sine=frequency=440:sample_rate=44100:duration=4.5',
                       '-c:a', 'aac', p / 'audio.m4a'])
            title = Image.new('RGBA', (1080, 1920))
            ImageDraw.Draw(title).rectangle((300, 700, 780, 900), fill=(249, 247, 190, 255))
            title.save(p / 'title.png')
            report = STYLE.render(p / 'source.mp4', p / 'draft.mp4', p, draft=True)
            self.assertEqual((report['frames'], report['width'], report['height']), (120, 540, 960))
            frames = imageio_ffmpeg.read_frames(str(p / 'draft.mp4'))
            next(frames)
            selected = {}
            for i, data in enumerate(frames):
                if i in (0, 30):
                    selected[i] = Image.frombytes('RGB', (540, 960), data)
            # A source cut at 1 s maps to output 0.8 s after the 0.2 s trim.
            self.assertGreater(selected[0].getpixel((10, 10))[0], 180)
            self.assertGreater(selected[30].getpixel((10, 10))[2], 180)
            for im in selected.values():
                pixel = im.getpixel((270, 400))
                self.assertLess(max(abs(a-b) for a, b in zip(pixel, (249, 247, 190))), 10)
            project = json.loads((p / 'draft.project.json').read_text())
            self.assertEqual(project['source_range'], [.2, 4.2])
            self.assertEqual(project['output_range'], [0, 4.])
            before = (p / 'draft.mp4').read_bytes()
            with self.assertRaisesRegex(ValueError, 'already exists'):
                STYLE.render(p / 'source.mp4', p / 'draft.mp4', p, draft=True)
            self.assertEqual(before, (p / 'draft.mp4').read_bytes())
            with self.assertRaisesRegex(ValueError, 'Source is too short'):
                STYLE.render(p / 'source.mp4', p / 'too-long.mp4', p, duration=5)
            master = STYLE.render(p / 'source.mp4', p / 'master.mp4', p, duration=.6)
            self.assertEqual((master['frames'], master['width'], master['height']), (18, 1080, 1920))
            STYLE.run([ffmpeg, '-v', 'error', '-y', '-f', 'lavfi', '-i',
                       'sine=duration=0.2:sample_rate=44100', '-c:a', 'aac', p / 'audio.m4a'])
            with self.assertRaisesRegex(ValueError, 'audio is shorter'):
                STYLE.render(p / 'source.mp4', p / 'short-audio.mp4', p)


if __name__ == '__main__':
    unittest.main()
