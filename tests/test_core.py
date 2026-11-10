import json
from pathlib import Path
import tempfile
import unittest
from array import array
import wave
import sys
from reelkit.timeline import make_edl,map_captions,pause_intervals,read_srt,write_srt
from reelkit.render import load_template,check_config
from reelkit.graphics import stages


class TimelineTests(unittest.TestCase):
    def test_frame_exact_mapping_across_a_removed_pause(self):
        edl=make_edl([(0,2),(4,6)],6)
        self.assertEqual(edl[-1]['output_end'],4)
        cues=map_captions([dict(start=4.5,end=5,text='The next idea')],edl)
        self.assertEqual(cues,[dict(start=2.5,end=3,text='The next idea')])
    def test_repeated_source_ranges_are_rejected(self):
        with self.assertRaises(ValueError):make_edl([(0,3),(2,4)],5)
    def test_caption_straddling_cut_is_clipped(self):
        edl=make_edl([(0,1),(2,3)],3)
        cues=map_captions([dict(start=.8,end=2.2,text='hello')],edl)
        self.assertEqual(len(cues),2)
        self.assertAlmostEqual(cues[-1]['end'],1.2)
    def test_deleted_words_do_not_survive_in_auto_captions(self):
        edl=make_edl([(0,1),(2,3)],3)
        words=[dict(start=.2,end=.5,text=' Keep'),dict(start=1.2,end=1.5,text=' remove'),dict(start=2.2,end=2.5,text=' this')]
        cues=map_captions([dict(start=.2,end=2.5,text='Keep remove this',words=words)],edl)
        self.assertEqual([c['text'] for c in cues],['Keep','this'])
    def test_srt_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'speech.srt';c=[dict(start=.04,end=1.2,text='Real speech timing')]
            write_srt(c,p);self.assertEqual(read_srt(p),c)
    def test_silence_is_cut_with_speech_guards(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'audio.wav';a=array('h',[8000]*16000+[0]*16000+[8000]*16000)
            if sys.byteorder!='little':a.byteswap()
            with wave.open(str(p),'wb') as f:f.setparams((1,2,16000,0,'NONE',''));f.writeframes(a.tobytes())
            kept,removed=pause_intervals(p,3)
            self.assertAlmostEqual(removed[0][0],1.12);self.assertAlmostEqual(removed[0][1],1.88)
            self.assertEqual(len(kept),2)
    def test_silent_video_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'audio.wav'
            with wave.open(str(p),'wb') as f:f.setparams((1,2,16000,0,'NONE',''));f.writeframes(bytes(64000))
            self.assertEqual(pause_intervals(p,2),([(0,2)],[]))


class TemplateTests(unittest.TestCase):
    def test_all_defaults_are_valid(self):
        for name in ['founder-story','product-breakdown','playful-explainer']:check_config(load_template(name))
    def test_colour_cannot_inject_a_filter(self):
        c=load_template('founder-story');c['accent']='white;movie=secret'
        with self.assertRaises(ValueError):check_config(c)
    def test_custom_card_timing(self):
        c=load_template('founder-story');c['stage_starts']=[0,1,4,5,9]
        self.assertEqual([s['end'] for s in stages(c,10)],[1,4,5,9,10])
    def test_custom_card_timing_rejects_out_of_bounds(self):
        c=load_template('founder-story');c['stage_starts']=[0,1,4,5,10]
        with self.assertRaises(ValueError):stages(c,10)


if __name__=='__main__':unittest.main()
