"""Edit checks on synthetic media; nothing personal is rendered."""
import os
from pathlib import Path
import tempfile
import unittest
from reelkit.check import check, find_repeats, format_report


def cue(start, end, text):
    return dict(start=start, end=end, text=text)


class RepeatTests(unittest.TestCase):
    def test_phrase_said_twice_fails_single_word_is_review_only(self):
        cues = [cue(0, 1.5, 'start with targeting'), cue(1.6, 3, 'start with targeting today'), cue(3.2, 4.5, 'what targeting means')]
        bad, review = find_repeats(cues)
        self.assertEqual(bad[0]['phrase'], 'start with')
        self.assertTrue(all(r['word'] != 'start' for r in review))
        bad, review = find_repeats([cue(0, 1, 'what targeting means'), cue(1.2, 2.2, 'targeting is a list')])
        self.assertEqual(bad, []); self.assertEqual(review[0]['word'], 'targeting')

    def test_stopwords_and_distant_repeats_are_ignored(self):
        bad, review = find_repeats([cue(0, 1, 'and so it is'), cue(1.1, 2, 'and so it goes')])
        self.assertEqual((bad, review), ([], []))
        bad, _ = find_repeats([cue(0, 1, 'ship the reel'), cue(8, 9, 'ship the reel')])
        self.assertEqual(bad, [])

    def test_joins_limit_the_scan_to_the_cuts(self):
        cues = [cue(0, 1, 'ship the reel'), cue(1.2, 2.2, 'ship the reel')]
        self.assertEqual(find_repeats(cues, joins=[1.1])[0][0]['phrase'], 'ship the')
        self.assertEqual(find_repeats(cues, joins=[5])[0], [])


@unittest.skipUnless(os.environ.get('REELKIT_INTEGRATION') == '1', 'Set REELKIT_INTEGRATION=1 for FFmpeg analysis')
class MediaCheckTests(unittest.TestCase):
    def make(self, folder, name, video, audio, extra=()):
        from reelkit.media import ffmpeg, run
        out = Path(folder) / name
        run([ffmpeg(), '-v', 'error', '-y', '-f', 'lavfi', '-i', video, '-f', 'lavfi', '-i', audio, *extra, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', out])
        return out

    def test_pause_freeze_and_quiet_audio_fail(self):
        with tempfile.TemporaryDirectory() as d:
            # Still picture for 4 s, a tone with a 1.2 s hole in the middle, at a quiet level.
            p = self.make(d, 'still.mp4', 'color=c=gray:s=160x284:r=30:d=4', 'sine=frequency=400:sample_rate=48000:duration=4', ['-af', "volume=enable='between(t,1.4,2.6)':volume=0"])
            report = check(p)
            by = {r['name']: r for r in report['checks']}
            self.assertFalse(report['ok'])
            self.assertFalse(by['pauses']['ok']); self.assertIn('1.4', by['pauses']['items'][0])
            self.assertFalse(by['freezes']['ok'])
            self.assertFalse(by['loudness']['ok'])
            self.assertIn('skipped', by['repeats']['detail'])
            self.assertIn('FAIL  pauses', format_report(report))
            self.assertTrue(check(p, max_pause=1.5)['checks'][1]['ok'])

    def test_moving_picture_with_captions_passes_and_flags_uncaptioned_sound(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.make(d, 'moving.mp4', 'testsrc=s=160x284:r=30:d=3', 'sine=frequency=300:sample_rate=48000:duration=3', ['-af', 'volume=4dB'])
            srt = Path(d) / 'captions.srt'
            srt.write_text('1\n00:00:00,000 --> 00:00:01,900\nthe first idea\n\n2\n00:00:02,000 --> 00:00:02,900\nthe second idea\n', encoding='utf-8')
            report = check(p, max_pause=5, tolerance=40, max_peak=5)
            by = {r['name']: r for r in report['checks']}
            self.assertTrue(by['freezes']['ok']); self.assertTrue(by['repeats']['ok'])
            self.assertEqual(by['uncaptioned sound']['items'], [])
            srt.write_text('1\n00:00:00,000 --> 00:00:00,900\nthe first idea\n', encoding='utf-8')
            report = check(p, max_pause=5, tolerance=40, max_peak=5)
            self.assertTrue({r['name']: r for r in report['checks']}['uncaptioned sound']['items'])

    def test_video_without_audio_fails_the_export_check(self):
        from reelkit.media import ffmpeg, run
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'mute.mp4'
            run([ffmpeg(), '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=gray:s=160x284:r=30:d=1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', p])
            report = check(p)
            self.assertFalse(report['ok']); self.assertEqual(len(report['checks']), 1)


if __name__ == '__main__':
    unittest.main()
