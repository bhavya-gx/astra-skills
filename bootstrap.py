"""One-command setup; dependencies stay inside this project's .venv."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser();p.add_argument("--captions",action="store_true");p.add_argument("--portrait",action="store_true");p.add_argument("--check",action="store_true",help="Install/check only; do not launch the browser");p.add_argument("--lite",action="store_true",help="Install only the template renderer, without speech or portrait tools")
    args=p.parse_args()
    if sys.version_info<(3,10):raise SystemExit("Install Python 3.12 or newer from python.org, then open the launcher again.")
    env=ROOT/".venv";python=env/("Scripts/python.exe" if os.name=="nt" else "bin/python")
    if not python.exists():
        print("Creating your local editing environment…",flush=True);venv.create(env,with_pip=True)
    files=["requirements.txt"]+(["requirements-captions.txt"] if args.captions or not args.lite else [])+(["requirements-portrait.txt"] if args.portrait or not args.lite else [])
    for filename in files:
        requirement=ROOT/filename;digest=hashlib.sha256(requirement.read_bytes()).hexdigest();stamp=env/(filename+".sha256")
        if not stamp.exists() or stamp.read_text()!=digest:
            print(f"Installing {filename}… The first setup needs internet access.",flush=True)
            subprocess.run([str(python),"-m","pip","install","--disable-pip-version-check","-r",str(requirement)],check=True)
            stamp.write_text(digest)
    command="doctor" if args.check else "serve"
    return subprocess.call([str(python),"-m","reelkit",command],cwd=ROOT)


if __name__=="__main__":
    try:raise SystemExit(main())
    except subprocess.CalledProcessError:
        raise SystemExit("Setup did not finish. Check your internet connection and read docs/troubleshooting.md; then run the launcher again.")
