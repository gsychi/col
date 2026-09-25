#!/usr/bin/env python3
"""Regenerate every local strategy by plain minimax and recheck the full proof.

Requires a C++17 compiler and Python 3.10+. No third-party packages.
Usage: python3 regenerate.py --output /tmp/col-proof-regenerated
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
from verify import verify

ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
out=args.output.resolve()
if out==ROOT:raise SystemExit('Choose a different directory to preserve the supplied proof.')
out.mkdir(parents=True,exist_ok=True)
(out/'certificates').mkdir(exist_ok=True)
manifest=json.loads((ROOT/'manifest.json').read_text())
with tempfile.TemporaryDirectory(prefix='col-proof-build-') as td:
    binary=Path(td)/'generate'
    cmd=shlex.split(os.environ.get('CXX','c++'))+['-O2','-std=c++17',str(ROOT/'generate.cpp'),'-o',str(binary)]
    subprocess.run(cmd,check=True)
    for item in manifest['certificates']:
        raw_path=Path(td)/'tile.json'
        result=subprocess.run([str(binary),str(item['height']),str(item['width']),
            str(item['root'][0]),str(item['root'][1]),str(raw_path)],check=True,capture_output=True,text=True)
        raw=raw_path.read_bytes();doc=json.loads(raw)
        packed=gzip.compress(raw,mtime=0)
        (out/item['file']).write_bytes(packed)
        item['nodes']=len(doc['nodes'])
        item['edges']=sum(len(n[2]) for n in doc['nodes'])
        item['sha256']=hashlib.sha256(packed).hexdigest()
        print(item['file'],result.stdout.strip())
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
shutil.copy2(ROOT/'verify.py',out/'verify.py')
result=verify(out)
(out/'verification_output.json').write_text(json.dumps(result,indent=2)+'\n')
