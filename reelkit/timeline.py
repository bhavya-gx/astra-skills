"""Keep source and output time explicit; never infer subtitles from a script."""
from __future__ import annotations
from array import array
import math
from pathlib import Path
import re
import sys
import wave

FPS = 30


def make_edl(intervals, duration):
    total = int(math.floor(duration*FPS+1e-6))
    result, cursor, previous = [], 0, -1
    for start, end in intervals:
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end > duration+.034 or end <= start:
            raise ValueError("Each keep range must have 0 <= start < end <= source duration.")
        a, b = max(0, round(start*FPS)), min(total, round(end*FPS))
        if a < previous:
            raise ValueError("Keep ranges must be ordered and must not overlap.")
        previous = b
        if b-a < 2:
            continue
        result.append(dict(source_start=a/FPS, source_end=b/FPS, output_start=cursor/FPS,
                           output_end=(cursor+b-a)/FPS, frames=b-a))
        cursor += b-a
    if not result:
        raise ValueError("The edit contains no retained video.")
    if len(result)>100:
        raise ValueError("More than 100 cuts: use a shorter source or a less aggressive silence threshold.")
    return result


def pause_intervals(wav_path, duration, threshold_db=-38, minimum_pause=.50, guard=.12):
    with wave.open(str(wav_path), "rb") as f:
        rate = f.getframerate()
        if f.getnchannels()!=1 or f.getsampwidth()!=2:
            raise ValueError("Pause analysis needs mono PCM16 audio.")
        samples = array("h", f.readframes(f.getnframes()))
    if sys.byteorder != "little":
        samples.byteswap()
    hop = round(rate*.02)
    quiet, starts, begin = [], [], None
    threshold = 32768*10**(threshold_db/20)
    for offset in range(0, len(samples), hop):
        chunk = samples[offset:offset+hop]
        rms = math.sqrt(sum(x*x for x in chunk)/max(1, len(chunk)))
        if rms < threshold and begin is None:
            begin = offset/rate
        if rms >= threshold and begin is not None:
            quiet.append((begin, offset/rate)); begin = None
    if begin is not None:
        quiet.append((begin, min(duration, len(samples)/rate)))
    # An entirely silent recording is still useful for text-led reels.
    if sum(b-a for a,b in quiet) > duration*.98:
        return [(0, duration)], []
    removed = [(a+guard, b-guard) for a,b in quiet if b-a >= minimum_pause and b-a > 2*guard]
    keep, last = [], 0.0
    for a,b in removed:
        if a-last >= .08:
            keep.append((last,a))
        last=b
    if duration-last >= .08:
        keep.append((last,duration))
    return keep or [(0,duration)], removed


def map_captions(cues, edl):
    mapped = []
    for cue in cues:
        for cut in edl:
            if cue.get("words"):
                words=[w for w in cue["words"] if cut["source_start"] <= (w["start"]+w["end"])/2 < cut["source_end"]]
                if not words:continue
                a=max(words[0]["start"],cut["source_start"]);b=min(words[-1]["end"],cut["source_end"])
                if b>a:
                    mapped.append(dict(start=cut["output_start"]+a-cut["source_start"],end=cut["output_start"]+b-cut["source_start"],text="".join(w["text"] for w in words).strip()))
                continue
            a=max(cue["start"],cut["source_start"])
            b=min(cue["end"],cut["source_end"])
            if b-a >= .035:
                mapped.append(dict(start=cut["output_start"]+a-cut["source_start"],
                                   end=cut["output_start"]+b-cut["source_start"],text=cue["text"]))
    return sorted(mapped,key=lambda x:x["start"])


def read_srt(path):
    raw=Path(path).read_text(encoding="utf-8-sig").replace("\r\n","\n")
    def seconds(s):
        h,m,v=s.replace(",",".").split(":")
        return int(h)*3600+int(m)*60+float(v)
    cues=[]
    pattern=r"(\d+:\d+:\d+[,.]\d+)\s*-->\s*(\d+:\d+:\d+[,.]\d+)[^\n]*\n(.*?)(?=\n\s*\n|\Z)"
    for match in re.finditer(pattern,raw,re.S):
        a,b=seconds(match[1]),seconds(match[2])
        text=re.sub(r"<[^>]*>","",match[3]).strip().replace("\n"," ")
        if b>a and text:
            cues.append(dict(start=a,end=b,text=text))
    if not cues:
        raise ValueError("No timed captions found in the SRT file.")
    return cues


def write_srt(cues,path):
    def stamp(t):
        ms=round(t*1000); sec,ms=divmod(ms,1000); minute,sec=divmod(sec,60); hour,minute=divmod(minute,60)
        return f"{hour:02}:{minute:02}:{sec:02},{ms:03}"
    Path(path).write_text("\n\n".join(f"{i+1}\n{stamp(c['start'])} --> {stamp(c['end'])}\n{c['text']}" for i,c in enumerate(cues))+"\n",encoding="utf-8")
