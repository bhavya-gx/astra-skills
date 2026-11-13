"""Build a public archive from an explicit set of source directories."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parents[1]
ROOT_FILES={'README.md','SECURITY.md','START-HERE.html','LICENSE','THIRD_PARTY_NOTICES.md','AGENTS.md','CLAUDE.md','CONTRIBUTING.md','.gitignore','.gitattributes','bootstrap.py','Start-Mac.command','Start-Windows.bat','start-linux.sh','requirements.txt','requirements-captions.txt','requirements-portrait.txt'}
FOLDERS={'reelkit','.claude','assets','templates','scripts','docs','prompts','.agents','.github','tests','examples','release','voice'}
EXCLUDED={'__pycache__','.venv','.cache','.local','.git','dist'}
TEXT={'.py','.md','.html','.json','.txt','.sh','.command','.bat','.yml','.yaml'}


def collect():
    found=[]
    for p in sorted(ROOT.rglob('*')):
        relative=p.relative_to(ROOT)
        if any(part in EXCLUDED for part in relative.parts):continue
        if p.is_symlink():raise ValueError(f'Symlinks are not release files: {relative}')
        if not p.is_file() or p.name in ['.DS_Store','MANIFEST.json'] or p.suffix in ['.pyc','.log']:continue
        if relative.parts[0] not in FOLDERS and str(relative) not in ROOT_FILES:continue
        if p.suffix in TEXT:
            text=p.read_text(encoding='utf-8')
            patterns=[r'/Users/[A-Za-z0-9_.-]+/',r'/home/[A-Za-z0-9_.-]+/',r'sk-[A-Za-z0-9_-]{30,}',r'AKIA[A-Z0-9]{16}',r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----']
            if any(re.search(pattern,text) for pattern in patterns):raise ValueError(f'Personal path or secret-like content in {relative}')
        found.append(p)
    for name in ROOT_FILES:
        if not (ROOT/name).is_file():raise ValueError(f'Missing release file: {name}')
    return found


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/'dist/video-skills-v0.2.0.zip');args=parser.parse_args()
    files=collect()
    manifest={'version':'0.2.0','files':[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
    manifest_path=ROOT/'release/MANIFEST.json';manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files+[manifest_path]:
            name='video-skills/'+str(p.relative_to(ROOT)).replace('\\','/')
            info=zipfile.ZipInfo.from_file(p,name);info.create_system=3
            info.external_attr=((0o100755 if p.suffix in ['.command','.sh'] else 0o100644)<<16)
            z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
    with zipfile.ZipFile(args.out) as z:
        bad=z.testzip()
        if bad:raise RuntimeError(f'Archive CRC error: {bad}')
    digest=hashlib.sha256(args.out.read_bytes()).hexdigest()
    args.out.with_suffix('.zip.sha256').write_text(f'{digest}  {args.out.name}\n',encoding='utf-8')
    print(json.dumps({'archive':str(args.out),'files':len(files)+1,'bytes':args.out.stat().st_size,'sha256':digest},indent=2))


if __name__=='__main__':main()
