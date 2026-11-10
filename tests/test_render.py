"""Small end-to-end checks; set REELKIT_INTEGRATION=1 to enable."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from reelkit.media import ROOT,ffmpeg,run,validate,inspect
from reelkit.render import load_template,render


@unittest.skipUnless(os.environ.get('REELKIT_INTEGRATION')=='1','Set REELKIT_INTEGRATION=1 for real FFmpeg renders')
class RenderTests(unittest.TestCase):
    def test_cut_caption_sync_and_clean_rerender(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);source=p/'source.mp4'
            run([ffmpeg(),'-v','error','-y','-f','lavfi','-i','color=c=0x908080:s=160x284:r=30:d=3','-f','lavfi','-i','sine=frequency=400:sample_rate=48000:duration=3','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',source])
            srt=p/'source.srt';srt.write_text('1\n00:00:02,000 --> 00:00:02,900\nThe second phrase\n',encoding='utf-8')
            c=load_template('founder-story');c.update(source=str(source),auto_captions=False,captions_srt=str(srt),keep_ranges=[[0,1],[2,3]],tighten_pauses=False)
            first=render(c,p/'result',True,lambda _:None)
            self.assertEqual(first['duration'],2)
            self.assertIn('00:00:01,000 --> 00:00:01,900',(p/'result/captions.srt').read_text())
            c.update(captions_srt='')
            second=render(c,p/'result',True,lambda _:None)
            self.assertEqual(second['captions'],0);self.assertFalse((p/'result/captions.srt').exists())
            self.assertTrue(list((p/'result').glob('previous-*-captions.srt')))
    def test_truncated_video_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);source=p/'broken.mp4'
            raw=(ROOT/'assets/previews/founder-story.mp4').read_bytes()
            source.write_bytes(raw[:len(raw)//2])
            with self.assertRaises((ValueError,RuntimeError)):
                validate(source,540,960,10,p)


if __name__=='__main__':unittest.main()
