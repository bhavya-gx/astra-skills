from __future__ import annotations
import copy
import json
import math
from pathlib import Path
import re
import shutil
import time
from .media import ROOT, ffmpeg, inspect, run, validate
from .timeline import make_edl, pause_intervals, map_captions, read_srt, write_srt
from .graphics import write_overlay, sound_effects


def load_template(name):
    if name not in ("founder-story","product-breakdown","playful-explainer"):
        raise ValueError("Choose one of the three supplied templates.")
    return json.loads((ROOT/"templates"/f"{name}.json").read_text(encoding="utf-8"))


def check_config(config):
    load_template(config.get("template"))
    for field,limit in (("hook",100),("subhead",130),("cta",100)):
        if not isinstance(config.get(field),str) or len(config[field])>limit:
            raise ValueError(f"{field} must be text, at most {limit} characters.")
    if not isinstance(config.get("beats"),list) or len(config["beats"])!=3:
        raise ValueError("Provide exactly three beats.")
    for beat in config["beats"]:
        if not isinstance(beat,dict):raise ValueError("Each beat needs a title and text.")
        for key,limit in (("title",70),("text",140)):
            if not isinstance(beat.get(key),str) or len(beat[key])>limit:raise ValueError(f"Beat {key}: maximum {limit} characters.")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}",config.get("accent","")):
        raise ValueError("Accent must be a six-digit hex colour.")
    for key,low,high in [("warmth",0,1),("tint",-1,1),("title_y",.05,.40),("caption_y",.58,.84),("minimum_pause",.3,2),("threshold_db",-55,-20)]:
        v=config.get(key)
        if not isinstance(v,(int,float)) or not math.isfinite(v) or not low<=v<=high:raise ValueError(f"{key} must be between {low} and {high}.")


def transcribe(path, directory, progress):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError("Automatic captions are not installed. Run python bootstrap.py --captions, or supply an SRT file.")
    import numpy as np
    import wave
    # Decode through the tested FFmpeg build rather than PyAV's changing file API.
    audio_path=Path(directory)/"transcription-audio.wav"
    run([ffmpeg(),"-v","error","-y","-i",path,"-map","0:a:0","-ac","1","-ar","16000","-c:a","pcm_s16le",audio_path])
    with wave.open(str(audio_path),"rb") as audio_file:
        audio=np.frombuffer(audio_file.readframes(audio_file.getnframes()),dtype="<i2").astype(np.float32)/32768.0
    progress("Loading speech model · the first run downloads the model")
    try:
        model=WhisperModel("base",device="cpu",compute_type="int8",cpu_threads=4,download_root=str(ROOT/".cache/speech"))
    except Exception as e:
        raise RuntimeError("The speech model could not load. The first use needs internet access to Hugging Face. Retry online, provide an SRT, or turn off automatic captions.") from e
    segments,info=model.transcribe(audio,word_timestamps=True,vad_filter=True,beam_size=3)
    cues=[]; transcript=[]
    for segment in segments:
        transcript.append(dict(start=segment.start,end=segment.end,text=segment.text))
        words=list(segment.words or [])
        # Small phrase captions are easier to scan than one flickering word.
        for offset in range(0,len(words),4):
            group=words[offset:offset+4]
            cues.append(dict(start=group[0].start,end=group[-1].end,text="".join(w.word for w in group).strip(),
                             words=[dict(start=w.start,end=w.end,text=w.word) for w in group]))
        progress(f"Transcribing · {round(segment.end)} seconds processed")
    Path(directory,"transcript.json").write_text(json.dumps(dict(language=info.language,segments=transcript,cues=cues),indent=2),encoding="utf-8")
    return cues


def render(config, directory, draft=True, progress=print):
    config=copy.deepcopy(config);check_config(config)
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=True)
    work=directory/"work";work.mkdir(exist_ok=True)
    source=Path(config["source"]).resolve();info=inspect(source)
    if info["duration"]>600:raise ValueError("The starter supports clips up to 10 minutes. Trim a longer source first.")
    if info["duration"]<.25:raise ValueError("The source is too short.")
    if any(x in info["video_stream"] for x in ["smpte2084","arib-std-b67"]):
        raise ValueError("This starter expects SDR footage. Export an SDR/Rec.709 copy of this HDR video first.")
    width,height=(540,960) if draft else (1080,1920)
    (directory/"project.json").write_text(json.dumps(config,indent=2),encoding="utf-8")
    (work/"source-info.json").write_text(json.dumps(info,indent=2),encoding="utf-8")
    progress("Inspecting footage and planning the cut")
    cues=read_srt(config["captions_srt"]) if config.get("captions_srt") else []
    if config.get("auto_captions") and not cues and info["has_audio"]:
        cues=transcribe(source,work,progress)
    removed=[]
    if config.get("keep_ranges") is not None:
        intervals=config["keep_ranges"]
    elif config.get("tighten_pauses") and info["has_audio"]:
        wav=work/"analysis.wav"
        run([ffmpeg(),"-v","error","-y","-i",source,"-map","0:a:0","-ac","1","-ar","16000","-c:a","pcm_s16le",wav])
        intervals,removed=pause_intervals(wav,info["duration"],config["threshold_db"],config["minimum_pause"])
        # Speech timestamps protect quiet syllables when available.
        if cues:
            protected=[w for c in cues for w in c.get("words",[c])]
            removed=[(a,b) for a,b in removed if not any(a<c["end"]+.06 and b>c["start"]-.06 for c in protected)]
            intervals=[];last=0
            for a,b in removed:
                if a-last>=.08:intervals.append((last,a))
                last=b
            if info["duration"]-last>=.08:intervals.append((last,info["duration"]))
    else:intervals=[(0,info["duration"])]
    edl=make_edl(intervals,info["duration"]);duration=edl[-1]["output_end"]
    (directory/"edit-decisions.json").write_text(json.dumps(edl,indent=2),encoding="utf-8")
    cues=map_captions(cues,edl)
    pending_captions=work/"candidate-captions.srt"
    if cues:write_srt(cues,pending_captions)
    expression="+".join(f"between(n,{round(e['source_start']*30)},{round(e['source_end']*30)-1})" for e in edl)
    warmth=config["warmth"];tint=config["tint"]
    grade=f"colorbalance=rm={.028*warmth+.028*tint:.5f}:gm={.004*warmth-.018*tint:.5f}:bm={-.030*warmth+.008*tint:.5f}:rh={.018*warmth:.5f}:bh={-.018*warmth:.5f},eq=saturation={1+.045*warmth:.5f}:contrast=1.01"
    graph=[f"[0:v:0]fps=30,select='{expression}',setpts=N/(30*TB),setsar=1,{grade},split[fg][bg]",
           f"[bg]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},gblur=sigma=24[back]",
           f"[fg]scale={width}:{height}:force_original_aspect_ratio=decrease[front]",
           "[back][front]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]"]
    if info["has_audio"]:
        handles=[]
        for i,e in enumerate(edl):
            left=.01 if i else 0;right=.01 if i<len(edl)-1 else 0
            a=max(0,e["source_start"]-left);b=min(info["duration"],e["source_end"]+right)
            graph.append(f"[0:a:0]atrim=start={a:.8f}:end={b:.8f},asetpts=PTS-STARTPTS,aresample=48000,apad,atrim=duration={e['source_end']-e['source_start']+left+right:.8f}[a{i}]")
        previous="a0"
        for i in range(1,len(edl)):
            graph.append(f"[{previous}][a{i}]acrossfade=d=0.02:c1=tri:c2=tri[j{i}]");previous=f"j{i}"
        noise="highpass=f=70,afftdn=nr=7:nf=-45:tn=1," if config.get("noise_reduction") else ""
        graph.append(f"[{previous}]{noise}loudnorm=I=-16:TP=-1.8:LRA=9,aresample=48000,apad,atrim=duration={duration:.8f}[a]")
    else:graph.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={duration:.8f}[a]")
    graph_path=work/"assembly.ffgraph";graph_path.write_text(";\n".join(graph),encoding="utf-8")
    assembly=work/"assembly.mov"
    cmd=[ffmpeg(),"-v","warning","-y","-filter_complex_threads","2","-i",source,"-filter_complex_script",graph_path,"-map","[v]","-map","[a]","-c:v","libx264","-threads","4","-preset","fast","-crf","17","-pix_fmt","yuv420p","-c:a","pcm_s16le","-ar","48000","-t",str(duration),assembly]
    (work/"assembly-command.json").write_text(json.dumps([str(x) for x in cmd],indent=2),encoding="utf-8")
    progress(f"Assembling {len(edl)} retained sections · {duration:.1f} seconds")
    run(cmd,work/"assembly.log")
    overlay=work/"overlay.mov"
    progress("Drawing titles, cards, icons, and captions")
    events=write_overlay(config,cues,duration,width,height,overlay,progress)
    effects=work/"effects.wav";sound_effects(events if config.get("sound_effects") else [],duration,effects)
    inputs=["-i",assembly,"-i",overlay,"-i",effects]
    graph=[];base="0:v";input_count=3
    if config.get("portrait_blur"):
        from .portrait import build_matte
        matte=build_matte(assembly,work,duration,progress)
        inputs += ["-i",matte]; input_count+=1
        graph += ["[0:v]split[sharp][blur]",f"[blur]gblur=sigma={22*width/1080}[soft]",f"[3:v]scale={width}:{height},format=gray[matte]","[soft][sharp][matte]maskedmerge[portrait]"]
        base="portrait"
    insert=config.get("insert")
    if insert:
        insert_path=Path(insert["source"]).resolve()
        a,b=float(insert["start"]),float(insert["end"])
        if not (0<=a<b<=duration):raise ValueError("Insert start/end must fit the edited output timeline.")
        is_image=insert_path.suffix.lower() in [".jpg",".jpeg",".png",".webp"]
        inputs += (["-loop","1"] if is_image else ["-stream_loop","-1"])+["-i",insert_path]
        graph.append(f"[{input_count}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x16131a,setsar=1,setpts=PTS-STARTPTS+{a}/TB[insert]")
        graph.append(f"[{base}][insert]overlay=enable='between(t,{a},{b})':eof_action=pass[withinsert]");base="withinsert"
    graph += [f"[{base}][1:v]overlay=shortest=1,format=yuv420p[v]","[0:a][2:a]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.84:level=false:latency=1,aresample=48000[a]"]
    final_graph=work/"final.ffgraph";final_graph.write_text(";\n".join(graph),encoding="utf-8")
    candidate=directory/"candidate.mp4"
    cmd=[ffmpeg(),"-v","warning","-y","-filter_complex_threads","2",*inputs,"-filter_complex_script",final_graph,"-map","[v]","-map","[a]","-c:v","libx264","-threads","4","-preset","fast","-crf","20" if draft else "18","-pix_fmt","yuv420p","-r","30","-c:a","aac","-b:a","192k","-ar","48000","-t",str(duration),"-movflags","+faststart",candidate]
    (work/"render-command.json").write_text(json.dumps([str(x) for x in cmd],indent=2),encoding="utf-8")
    progress("Rendering your preview" if draft else "Rendering your 1080p master")
    run(cmd,work/"render.log")
    progress("Checking the full export")
    report=validate(candidate,width,height,duration,directory)
    destination=directory/("preview.mp4" if draft else "reel.mp4")
    if destination.exists():destination.rename(directory/f"previous-{time.time_ns()}.mp4")
    candidate.rename(destination)
    old_captions=directory/"captions.srt"
    if old_captions.exists():old_captions.rename(directory/f"previous-{time.time_ns()}-captions.srt")
    if cues:pending_captions.replace(old_captions)
    summary=dict(template=config["template"],source_duration=info["duration"],duration=duration,removed_seconds=round(info["duration"]-duration,3),cuts=len(edl)-1,captions=len(cues),output=destination.name,validation=report)
    (directory/"result.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    progress("Ready to review")
    return summary
