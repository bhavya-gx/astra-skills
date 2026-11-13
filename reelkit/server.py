"""Loopback-only editor. Uploaded media stays in the local project folder."""
from __future__ import annotations
import importlib.util
import json
import mimetypes
from pathlib import Path
import re
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse,parse_qs,unquote
import webbrowser
from .media import ROOT
from .render import load_template,render,check_config


def make_server(port=0,local=None):
    local=Path(local or ROOT/".local").resolve();(local/"uploads").mkdir(parents=True,exist_ok=True)
    token=secrets.token_urlsafe(32);jobs={};lock=threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def reply(self,obj,status=200):
            data=json.dumps(obj).encode();self.send_response(status);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(data)));self.send_header("Cache-Control","no-store");self.end_headers();self.wfile.write(data)
        def trusted(self):
            host=self.headers.get("Host","")
            expected=f"127.0.0.1:{self.server.server_port}"
            return host==expected and self.headers.get("Origin",f"http://{expected}")==f"http://{expected}"
        def do_GET(self):
            if not self.trusted():self.reply({"error":"Use the local editor address."},403);return
            parsed=urlparse(self.path);path=unquote(parsed.path)
            if path=="/":
                data=(ROOT/"reelkit/web/index.html").read_text(encoding="utf-8").replace("__SESSION_TOKEN__",token).encode()
                self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Content-Length",str(len(data)));self.send_header("Cache-Control","no-store");self.end_headers();self.wfile.write(data);return
            if path=="/api/templates":
                self.reply([load_template(n) for n in ["founder-story","product-breakdown","playful-explainer"]]);return
            if path=="/api/capabilities":
                self.reply(dict(captions=bool(importlib.util.find_spec("faster_whisper")),portrait=bool(importlib.util.find_spec("onnxruntime"))));return
            if path.startswith("/api/jobs/"):
                if self.headers.get("X-Reel-Token")!=token:self.reply({"error":"Session expired. Reload the page."},403);return
                with lock:job=dict(jobs.get(path.rsplit("/",1)[-1],{}))
                self.reply(job or {"error":"Job not found"},200 if job else 404);return
            if path.startswith("/files/"):
                if parse_qs(parsed.query).get("token",[""])[0]!=token:self.reply({"error":"Session expired"},403);return
                root=local;relative=path[len("/files/"):]
            elif path.startswith("/assets/") or path.startswith("/scripts/"):
                folder="assets" if path.startswith("/assets/") else "scripts"
                root=ROOT/folder;relative=path[len(folder)+2:]
            else:self.reply({"error":"Not found"},404);return
            target=(root/relative).resolve()
            if not target.is_relative_to(root) or not target.is_file():self.reply({"error":"Not found"},404);return
            size=target.stat().st_size;start=0;end=size-1;status=200
            requested=self.headers.get("Range")
            if requested:
                m=re.fullmatch(r"bytes=(\d+)-(\d*)",requested)
                if not m:self.reply({"error":"Unsupported range"},416);return
                start=int(m[1]);end=min(end,int(m[2])) if m[2] else end;status=206
                if start>end:self.reply({"error":"Range outside file"},416);return
            self.send_response(status);self.send_header("Content-Type",mimetypes.guess_type(str(target))[0] or "application/octet-stream");self.send_header("Content-Length",str(end-start+1));self.send_header("Accept-Ranges","bytes")
            if status==206:self.send_header("Content-Range",f"bytes {start}-{end}/{size}")
            self.send_header("X-Content-Type-Options","nosniff");self.end_headers()
            try:
                with target.open("rb") as f:
                    f.seek(start);left=end-start+1
                    while left:
                        chunk=f.read(min(left,1024*1024));self.wfile.write(chunk);left-=len(chunk)
            except (BrokenPipeError,ConnectionResetError):pass
        def do_POST(self):
            if not self.trusted() or self.headers.get("X-Reel-Token")!=token:self.reply({"error":"Session expired. Reload the editor."},403);return
            try:
                length=int(self.headers.get("Content-Length","0"))
                if length<=0:raise ValueError("The request is empty.")
                if self.path=="/api/upload":
                    if length>600*1024*1024:raise ValueError("Choose a video smaller than 600 MB.")
                    extension=Path(unquote(self.headers.get("X-Filename",""))).suffix.lower()
                    if extension not in [".mp4",".mov",".webm",".mkv",".srt",".png",".jpg",".jpeg",".webp"]:raise ValueError("Use MP4, MOV, WebM, MKV, SRT, PNG, JPG, or WebP.")
                    name=secrets.token_hex(10)+extension;target=local/"uploads"/name
                    try:
                        with target.open("wb") as f:
                            remaining=length
                            while remaining:
                                chunk=self.rfile.read(min(1024*1024,remaining))
                                if not chunk:raise ValueError("The upload was interrupted.")
                                f.write(chunk);remaining-=len(chunk)
                    except BaseException:target.unlink(missing_ok=True);raise
                    self.reply({"path":"uploads/"+name});return
                if length>100_000:raise ValueError("The project is too large.")
                data=json.loads(self.rfile.read(length))
                if self.path!="/api/render":self.reply({"error":"Not found"},404);return
                config=data["config"];check_config(config)
                for key in ["source","captions_srt"]:
                    if config.get(key):
                        p=(local/config[key]).resolve()
                        if not p.is_relative_to(local/"uploads") or not p.is_file():raise ValueError("Add your file again.")
                        config[key]=str(p)
                if data.get("demo"):
                    config["source"]=str(ROOT/"examples/demo-source.mp4");config.update(tighten_pauses=False,auto_captions=False,portrait_blur=False,captions_srt="")
                if config.get("insert"):
                    p=(local/config["insert"]["source"]).resolve()
                    if not p.is_relative_to(local/"uploads") or not p.is_file():raise ValueError("Add the insert file again.")
                    config["insert"]["source"]=str(p)
                with lock:
                    if any(j["state"]=="running" for j in jobs.values()):self.reply({"error":"An export is already running. Let it finish first."},409);return
                    job_id=time.strftime("%Y%m%d-%H%M%S")+"-"+secrets.token_hex(3);jobs[job_id]=dict(state="running",message="Starting your edit")
                directory=local/"jobs"/job_id
                def progress(message):
                    with lock:jobs[job_id]["message"]=message
                def execute():
                    try:
                        result=render(config,directory,bool(data.get("draft",True)),progress)
                        base=f"/files/jobs/{job_id}/"
                        links={"video":base+result["output"]+"?token="+token,"project":base+"project.json?token="+token,"cuts":base+"edit-decisions.json?token="+token}
                        if (directory/"captions.srt").exists():links["captions"]=base+"captions.srt?token="+token
                        with lock:jobs[job_id].update(state="done",result=result,links=links)
                    except Exception as e:
                        with lock:jobs[job_id].update(state="error",message=str(e))
                threading.Thread(target=execute,daemon=True).start();self.reply({"id":job_id})
            except (ValueError,KeyError,TypeError) as e:self.reply({"error":str(e)},400)
    server=ThreadingHTTPServer(("127.0.0.1",port),Handler);server.session_token=token
    return server


def serve(port=0,open_browser=True):
    server=make_server(port);url=f"http://127.0.0.1:{server.server_port}"
    print(f"Video Skills · {url}\nLeave this window open while editing. Press Ctrl+C to stop.",flush=True)
    if open_browser:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
