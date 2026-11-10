from pathlib import Path
from PIL import Image,ImageDraw
from .media import ROOT,ffmpeg,run
from .graphics import font


def create_source(directory=None):
    directory=Path(directory or ROOT/"examples");directory.mkdir(parents=True,exist_ok=True)
    image=directory/"demo-source.png";video=directory/"demo-source.mp4"
    im=Image.new("RGB",(1080,1920),"#d5bc9e");d=ImageDraw.Draw(im)
    d.rectangle((0,0,1080,1120),fill="#bda58d")
    d.rounded_rectangle((650,140,1030,920),90,fill="#e0c7a4")
    d.rectangle((714,180,724,850),fill="#ad947a")
    d.rectangle((930,180,940,850),fill="#ad947a")
    d.rounded_rectangle((80,680,240,980),32,fill="#858361")
    d.ellipse((95,480,200,760),fill="#667457");d.ellipse((25,580,175,830),fill="#728164")
    d.rounded_rectangle((70,1130,1010,1790),100,fill="#ae7254")
    d.polygon([(210,1800),(260,1300),(390,1160),(690,1160),(820,1300),(885,1800)],fill="#353b46")
    d.rounded_rectangle((450,1050,630,1250),60,fill="#c88c6c")
    d.ellipse((344,665,740,1170),fill="#dfaa85")
    d.pieslice((315,630,770,1100),180,350,fill="#40332f")
    d.ellipse((385,865,425,887),fill="#332c2a");d.ellipse((645,865,685,887),fill="#332c2a")
    d.arc((470,960,610,1040),0,180,fill="#9d5c4e",width=8)
    d.text((72,86),"YOUR FOOTAGE GOES HERE",font=font(31),fill="#fff7ea")
    d.text((72,1835),"Original illustrated demo · no recorded speech",font=font(28),fill="#fff7ea")
    im.save(image)
    run([ffmpeg(),"-v","error","-y","-loop","1","-i",image,"-f","lavfi","-i","anullsrc=r=48000:cl=stereo","-vf","scale=540:960","-c:v","libx264","-preset","fast","-pix_fmt","yuv420p","-r","30","-c:a","aac","-t","10","-movflags","+faststart",video])
    return video
