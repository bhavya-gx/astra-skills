"""Optional real portrait matting; never blur an assumed oval around a face."""
import hashlib
from pathlib import Path
import subprocess
import urllib.request
from .media import ROOT, ffmpeg

MODEL_URL="https://huggingface.co/Xenova/modnet/resolve/main/onnx/model.onnx"
MODEL_SHA256="07c308cf0fc7e6e8b2065a12ed7fc07e1de8febb7dc7839d7b7f15dd66584df9"


def build_matte(source,work,duration,progress):
    try:
        import numpy as np
        import onnxruntime as ort
    except ImportError:
        raise RuntimeError("Portrait blur needs its optional tools. Run python bootstrap.py --portrait.")
    cache=ROOT/".cache/portrait";cache.mkdir(parents=True,exist_ok=True)
    model=cache/"modnet.onnx"
    if not model.exists():
        progress("Downloading portrait model · about 25 MB")
        pending=model.with_suffix(".download")
        urllib.request.urlretrieve(MODEL_URL,pending)
        if hashlib.sha256(pending.read_bytes()).hexdigest()!=MODEL_SHA256:
            pending.unlink();raise RuntimeError("Portrait model checksum changed. See docs/troubleshooting.md.")
        pending.replace(model)
    if hashlib.sha256(model.read_bytes()).hexdigest()!=MODEL_SHA256:
        raise RuntimeError("Portrait model checksum does not match the tested model.")
    options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
    session=ort.InferenceSession(str(model),sess_options=options,providers=["CPUExecutionProvider"])
    iw,ih=256,448;target=Path(work)/"matte.mkv";count=round(duration*30)
    progress("Separating the speaker from the background")
    with (Path(work)/"matte.log").open("wb") as log:
        decoder=subprocess.Popen([ffmpeg(),"-v","error","-i",str(source),"-vf",f"scale={iw}:{ih}","-pix_fmt","rgb24","-f","rawvideo","pipe:1"],stdout=subprocess.PIPE,stderr=log)
        encoder=subprocess.Popen([ffmpeg(),"-v","error","-y","-f","rawvideo","-pixel_format","gray","-video_size",f"{iw}x{ih}","-framerate","30","-i","pipe:0","-an","-c:v","ffv1",str(target)],stdin=subprocess.PIPE,stderr=log)
        try:
            for n in range(count):
                raw=decoder.stdout.read(iw*ih*3)
                if len(raw)!=iw*ih*3:raise RuntimeError("Portrait decoder ended early.")
                a=np.frombuffer(raw,dtype=np.uint8).reshape(ih,iw,3).astype(np.float32)/127.5-1
                matte=session.run(None,{session.get_inputs()[0].name:np.transpose(a,(2,0,1))[None]})[0].squeeze()
                encoder.stdin.write((np.clip(matte,0,1)*255).astype(np.uint8).tobytes())
                if n%150==0:progress(f"Background blur · {round(n/count*100)}%")
        except BaseException:
            decoder.kill();encoder.kill();decoder.wait();encoder.wait();raise
        finally:
            decoder.stdout.close();encoder.stdin.close()
        dc,ec=decoder.wait(),encoder.wait()
        if dc or ec:raise RuntimeError("Portrait processing failed. See matte.log.")
    return target
