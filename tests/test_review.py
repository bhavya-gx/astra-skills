"""Review notes: saved next to the render, served only from the review folder, readable as text by the assistant."""
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from reelkit.review import clean_notes, format_notes, make_review_server, peaks_for, read_notes, renders_under, write_notes


class NotesTests(unittest.TestCase):
    def test_notes_are_sorted_cleaned_and_printed(self):
        with tempfile.TemporaryDirectory() as d:
            render = Path(d) / 'preview.mp4'; render.write_bytes(b'0')
            (Path(d) / 'captions.srt').write_text('1\n00:00:01,000 --> 00:00:02,000\nthe second phrase\n', encoding='utf-8')
            notes = write_notes(render, [dict(start=4, end=4, note='cut the breath', extra='dropped'), dict(start=1.2, end=1.9, note='repeated take', done=False)])
            self.assertEqual([n['start'] for n in notes], [1.2, 4])
            self.assertNotIn('extra', notes[0])
            self.assertEqual(read_notes(render), notes)
            text = format_notes(render)
            self.assertIn('0:01.2 to 0:01.9  repeated take  ("the second phrase")', text)
            self.assertIn('0:04.0  cut the breath', text)
            notes[0].update(done=True, reply='Kept the second take.'); write_notes(render, notes)
            self.assertNotIn('repeated take', format_notes(render))
            self.assertIn('reply: Kept the second take.', format_notes(render, include_done=True))

    def test_bad_notes_are_rejected(self):
        for bad in [[dict(note=1)], [dict(start=-1, note='x')], [dict(start=3, end=1, note='x')], [dict(start=float('nan'), note='x')], 'text']:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                clean_notes(bad)

    def test_library_skips_work_files_and_candidates(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            for name in ['a/preview.mp4', 'a/candidate.mp4', 'a/work/assembly.mov', 'b/reel.mp4', 'notes.txt']:
                (p / name).parent.mkdir(parents=True, exist_ok=True); (p / name).write_bytes(b'0')
            self.assertEqual(sorted(x.relative_to(p).as_posix() for x in renders_under(p)), ['a/preview.mp4', 'b/reel.mp4'])


class ReviewServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        (self.root / 'preview.mp4').write_bytes(b'0123456789'); (self.root / 'secret.txt').write_text('private')
        self.server = make_review_server(self.root)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(); self.tmp.cleanup()

    def get(self, path, **headers):
        with urllib.request.urlopen(urllib.request.Request(self.base + path, headers=headers)) as f:
            return f.status, f.read()

    def test_library_and_review_pages(self):
        status, body = self.get('/')
        self.assertEqual(status, 200); self.assertIn(b'preview.mp4', body); self.assertNotIn(b'secret.txt', body)
        status, body = self.get('/review?file=preview.mp4')
        self.assertIn(b'Review preview.mp4', body); self.assertIn(self.server.session_token.encode(), body)
        status, body = self.get('/assets/fonts/InterTight.ttf')
        self.assertEqual(status, 200); self.assertGreater(len(body), 1000)

    def test_only_videos_inside_the_folder_are_served(self):
        for path in ['/video?file=secret.txt', '/video?file=../README.md', '/video?file=%2e%2e/LICENSE', '/notes?file=', '/assets/%2e%2e/README.md']:
            with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as e:
                self.get(path)
            self.assertEqual(e.exception.code, 404)
        status, body = self.get('/video?file=preview.mp4', Range='bytes=2-5')
        self.assertEqual((status, body), (206, b'2345'))

    def test_untrusted_origin_cannot_read(self):
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.get('/notes?file=preview.mp4', Origin='https://unrelated.example')
        self.assertEqual(e.exception.code, 403)

    def test_notes_need_the_session_token_and_land_next_to_the_render(self):
        body = json.dumps([dict(start=2, end=2.5, note='clipped word')]).encode()
        req = urllib.request.Request(self.base + '/notes?file=preview.mp4', data=body, headers={'Content-Type': 'application/json'})
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req)
        self.assertEqual(e.exception.code, 403)
        req.add_header('X-Reel-Token', self.server.session_token)
        with urllib.request.urlopen(req) as f:
            answer = json.load(f)
        self.assertEqual(answer['notes'][0]['note'], 'clipped word')
        self.assertEqual(json.loads((self.root / 'preview.review.json').read_text(encoding='utf-8'))[0]['start'], 2)
        status, body = self.get('/notes?file=preview.mp4')
        self.assertEqual(json.loads(body)[0]['end'], 2.5)


@unittest.skipUnless(os.environ.get('REELKIT_INTEGRATION') == '1', 'Set REELKIT_INTEGRATION=1 for FFmpeg decoding')
class PeaksTests(unittest.TestCase):
    def test_peaks_follow_the_audio(self):
        from reelkit.media import ffmpeg, run
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'tone.mp4'
            run([ffmpeg(), '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=black:s=64x64:r=30:d=2', '-f', 'lavfi', '-i', 'sine=frequency=400:sample_rate=48000:duration=2', '-af', 'volume=enable=lt(t\\,1):volume=0', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', p])
            wave = peaks_for(p)
            self.assertAlmostEqual(wave['duration'], 2, delta=.15)
            half = len(wave['peaks']) // 2
            self.assertLess(max(wave['peaks'][: half - 20]), .02); self.assertGreater(max(wave['peaks'][half + 20:]), .08)
            silent = Path(d) / 'silent.mp4'
            run([ffmpeg(), '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=black:s=64x64:r=30:d=1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', silent])
            self.assertEqual(peaks_for(silent)['peaks'], [])


if __name__ == '__main__':
    unittest.main()
