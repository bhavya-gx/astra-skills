import argparse
import importlib.util
import json
from pathlib import Path
from .media import ROOT,ffmpeg


def main():
    parser=argparse.ArgumentParser(description="Local talking-head reel templates")
    commands=parser.add_subparsers(dest="command",required=True)
    server=commands.add_parser("serve",help="Open the local editor")
    server.add_argument("--port",type=int,default=0);server.add_argument("--no-browser",action="store_true")
    commands.add_parser("doctor",help="Check the installed tools")
    new=commands.add_parser("new",help="Create an editable project")
    new.add_argument("--template",default="founder-story");new.add_argument("--source",required=True);new.add_argument("--out",required=True)
    render=commands.add_parser("render",help="Render a project JSON file")
    render.add_argument("project");render.add_argument("--draft",action="store_true");render.add_argument("--out")
    review=commands.add_parser("review",help="Open a render in the browser and leave timestamped notes")
    review.add_argument("target",help="A rendered video, or a folder of renders");review.add_argument("--port",type=int,default=0);review.add_argument("--no-browser",action="store_true")
    review.add_argument("--print",action="store_true",dest="print_notes",help="Print the open notes as text and exit");review.add_argument("--all",action="store_true",help="With --print, include notes marked done")
    demo=commands.add_parser("demo",help="Render illustrated previews without your own footage")
    demo.add_argument("--template",default="all");demo.add_argument("--out",default=str(ROOT/".local/demos"))
    args=parser.parse_args()
    if args.command=="serve":
        from .server import serve
        serve(args.port,not args.no_browser)
    elif args.command=="review":
        from .review import format_notes,serve_review
        if args.print_notes:print(format_notes(args.target,args.all))
        else:serve_review(args.target,args.port,not args.no_browser)
    elif args.command=="doctor":
        print(json.dumps(dict(ffmpeg=ffmpeg(),captions=bool(importlib.util.find_spec("faster_whisper")),portrait=bool(importlib.util.find_spec("onnxruntime"))),indent=2))
    else:
        from .render import load_template,render
        if args.command=="new":
            p=Path(args.out).resolve();p.parent.mkdir(parents=True,exist_ok=True)
            if p.exists():parser.error("The project already exists. Choose a new path.")
            config=load_template(args.template);config["source"]=str(Path(args.source).resolve())
            p.write_text(json.dumps(config,indent=2),encoding="utf-8");print(p)
        elif args.command=="render":
            p=Path(args.project).resolve();config=json.loads(p.read_text(encoding="utf-8"))
            for key in ["source","captions_srt"]:
                if config.get(key) and not Path(config[key]).is_absolute():config[key]=str((p.parent/config[key]).resolve())
            if config.get("insert") and not Path(config["insert"]["source"]).is_absolute():config["insert"]["source"]=str((p.parent/config["insert"]["source"]).resolve())
            print(json.dumps(render(config,args.out or p.parent/"renders",args.draft),indent=2))
        else:
            from .demo import create_source
            source=ROOT/"examples/demo-source.mp4"
            if not source.exists():source=create_source()
            names=["founder-story","product-breakdown","playful-explainer"] if args.template=="all" else [args.template]
            for name in names:
                config=load_template(name);config.update(source=str(source),tighten_pauses=False,auto_captions=False)
                render(config,Path(args.out)/name,True)


if __name__=="__main__":
    try:main()
    except (ValueError,RuntimeError) as e:raise SystemExit(str(e))
