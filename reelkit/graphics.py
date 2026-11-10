from __future__ import annotations
from array import array
import math
from pathlib import Path
import random
import subprocess
import sys
import wave
from PIL import Image, ImageDraw, ImageFont
from .media import ROOT, ffmpeg

W,H=1080,1920


def font(size,serif=False):
    f=ImageFont.truetype(str(ROOT/"assets/fonts"/("InstrumentSerif.ttf" if serif else "InterTight.ttf")),round(size))
    if not serif:
        try: f.set_variation_by_axes([700])
        except (AttributeError,OSError): pass
    return f


def label(im,text,box,size=66,serif=False,color="white",align="center",shadow=True):
    x,y,w,h=box; draw=ImageDraw.Draw(im)
    def wrap(f):
        lines=[]; line=""
        for word in text.split():
            trial=f"{line} {word}".strip()
            if line and draw.textlength(trial,font=f)>w:
                lines.append(line);line=word
            else: line=trial
        if line: lines.append(line)
        return lines
    for s in range(round(size),19,-2):
        f=font(s,serif);lines=wrap(f)
        if len(lines)*s*1.22<=h and all(draw.textlength(line,font=f)<=w for line in lines): break
    for line in lines:
        tx=x+(w-draw.textlength(line,font=f))/2 if align=="center" else x
        draw.text((tx,y),line,font=f,fill=color,stroke_width=2 if shadow else 0,stroke_fill="#171a20",anchor="lt")
        y+=s*1.22


def icon(im,kind,box,color="#ffc65c"):
    x,y,s=box; d=ImageDraw.Draw(im); ink="#252331"; u=s/100
    def b(a,b,c,e): return (x+a*u,y+b*u,x+c*u,y+e*u)
    if kind=="game":
        d.rounded_rectangle(b(4,24,96,84),radius=18*u,fill=color,outline=ink,width=round(3*u))
        d.line([x+19*u,y+54*u,x+43*u,y+54*u],fill=ink,width=round(7*u))
        d.line([x+31*u,y+42*u,x+31*u,y+66*u],fill=ink,width=round(7*u))
        for a,c in [(69,47),(82,61)]:d.ellipse(b(a-5,c-5,a+5,c+5),fill=ink)
    elif kind=="robot":
        d.line((x+50*u,y+8*u,x+50*u,y+27*u),fill=color,width=round(5*u))
        d.ellipse(b(44,1,56,13),fill=color)
        d.rounded_rectangle(b(8,25,92,87),radius=14*u,fill=color,outline=ink,width=round(3*u))
        for a in [31,69]:d.ellipse(b(a-6,42,a+6,54),fill=ink)
        d.rounded_rectangle(b(31,66,69,73),radius=3*u,fill=ink)
    else:
        d.ellipse(b(20,2,80,62),fill=color,outline=ink,width=round(3*u))
        d.rounded_rectangle(b(35,57,65,80),radius=5*u,fill=color)
        d.line((x+36*u,y+88*u,x+64*u,y+88*u),fill=ink,width=round(5*u))
        for angle in [-45,0,45,180]:
            a=math.radians(angle);cx=x+50*u;cy=y+32*u
            d.line((cx+39*u*math.cos(a),cy+39*u*math.sin(a),cx+48*u*math.cos(a),cy+48*u*math.sin(a)),fill=color,width=round(4*u))


def stages(config,duration):
    result=[dict(start=0,end=duration*.20,title=config["hook"],body=config["subhead"],kind="hook")]+[
        dict(start=duration*(.20+i*.20),end=duration*(.40+i*.20),title=b["title"],body=b["text"],kind="beat",index=i)
        for i,b in enumerate(config["beats"])]+[dict(start=duration*.80,end=duration,title=config["cta"],body="",kind="cta")]
    starts=config.get("stage_starts")
    if starts is not None:
        if len(starts)!=5 or starts[0]!=0 or any(not isinstance(t,(int,float)) or not math.isfinite(t) for t in starts) or any(a>=b for a,b in zip(starts,starts[1:])) or starts[-1]>=duration:
            raise ValueError("stage_starts needs five increasing output times, starting at 0 and ending before the video ends.")
        for i,event in enumerate(result):event.update(start=starts[i],end=starts[i+1] if i<4 else duration)
    return result


def stage_image(config,stage):
    im=Image.new("RGBA",(W,H)); d=ImageDraw.Draw(im)
    style=config["template"]; accent=config["accent"]; y=round(config.get("title_y",.13)*H)
    title,body=stage["title"],stage["body"]
    if style=="founder-story":
        d.rounded_rectangle((444,y-34,636,y-26),radius=4,fill=accent)
        label(im,title,(90,y,900,235),size=100,serif=True)
        if body:
            d.rounded_rectangle((142,y+246,938,y+381),radius=18,fill="#faf3e8ee")
            label(im,body,(170,y+267,740,95),size=39,color="#34302d",shadow=False)
    elif style=="product-breakdown":
        d.rounded_rectangle((95,y,985,y+320),radius=32,fill="#fff9f2f5")
        d.rounded_rectangle((127,y+32,206,y+99),radius=15,fill=accent)
        number=f"{stage.get('index',-1)+1:02}" if stage["kind"]=="beat" else "AI"
        label(im,number,(131,y+45,71,45),size=35,color="#29252a",shadow=False)
        label(im,title,(235,y+32,690,130),size=68,color="#26232a",align="left",shadow=False)
        label(im,body,(137,y+187,800,100),size=40,color="#625966",align="left",shadow=False)
    else:
        d.rounded_rectangle((115,y-10,965,y+300),radius=38,fill="#242033df",outline=accent,width=3)
        label(im,title,(150,y+20,780,140),size=77,color=accent)
        if body: label(im,body,(150,y+180,780,96),size=38)
        icon(im,["game","robot","bulb"][stage.get("index",0)%3],(492,y+326,96),accent)
    return im


def caption_image(text,y):
    im=Image.new("RGBA",(W,H))
    label(im,text,(85,round(y*H),910,210),size=62)
    return im


def write_overlay(config,cues,duration,width,height,path,progress=lambda x:None):
    events=stages(config,duration); cache={}; captions={}; frame_count=round(duration*30)
    cmd=[ffmpeg(),"-v","error","-y","-f","rawvideo","-pixel_format","rgba","-video_size",f"{width}x{height}","-framerate","30","-i","pipe:0","-an","-c:v","qtrle","-pix_fmt","argb",str(path)]
    with Path(path).with_suffix(".log").open("wb") as log:
        process=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=log)
        last_key=None; raw=None
        try:
            for n in range(frame_count):
                t=n/30
                idx=next((i for i,e in enumerate(events) if e["start"]<=t<e["end"]),len(events)-1)
                cue=next((c["text"] for c in cues if c["start"]<=t<c["end"]),"")
                age=max(0,t-events[idx]["start"]); step=min(7,int(age*30))
                key=(idx,cue,step)
                if key!=last_key:
                    if idx not in cache: cache[idx]=stage_image(config,events[idx]).resize((width,height),Image.Resampling.LANCZOS)
                    out=Image.new("RGBA",(width,height)); layer=cache[idx]
                    # A short slide/fade introduces a new idea without changing the speaker's geometry.
                    if step<7:
                        layer=layer.copy();layer.putalpha(layer.getchannel("A").point(lambda a:round(a*(step+1)/8)))
                    offset=round(-18*height/H*(1-min(1,age/.23))**2)
                    out.alpha_composite(layer,(0,offset))
                    if cue:
                        if cue not in captions:
                            captions.clear()
                            captions[cue]=caption_image(cue,config.get("caption_y",.78)).resize((width,height),Image.Resampling.LANCZOS)
                        out.alpha_composite(captions[cue])
                    raw=out.tobytes();last_key=key
                process.stdin.write(raw)
                if n and n%300==0: progress(f"Drawing graphics · {round(n/frame_count*100)}%")
        except BaseException:
            process.kill();process.wait();raise
        finally:
            process.stdin.close()
        if process.wait():raise RuntimeError("Graphics encoding failed. See overlay.log.")
    return events


def sound_effects(events,duration,path):
    rate=48000; samples=array("h",[0])*round(duration*rate);rng=random.Random(6)
    for event in events[1:]:
        start=round(event["start"]*rate)
        for i in range(round(.16*rate)):
            at=start+i
            if at>=len(samples): break
            t=i/rate; envelope=math.sin(math.pi*min(1,t/.16))*math.exp(-t*22)
            v=(math.sin(2*math.pi*(900*t-1600*t*t))*.8+rng.uniform(-1,1)*.15)*envelope*.055
            samples[at]=max(-32767,min(32767,samples[at]+round(v*32767)))
    if sys.byteorder!="little":samples.byteswap()
    with wave.open(str(path),"wb") as w:
        w.setparams((1,2,rate,0,"NONE","not compressed"));w.writeframes(samples.tobytes())
