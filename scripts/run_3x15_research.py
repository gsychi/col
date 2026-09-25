"""Reproducible bounded screens; null outcome always means unresolved."""
import argparse
import json
from pathlib import Path
import platform
import subprocess
import time

parser=argparse.ArgumentParser()
parser.add_argument("--binary",default="/private/tmp/col-3x15-research/target/release/research")
parser.add_argument("--out",default="reports/3x15-investigation")
args=parser.parse_args()
out=Path(args.out).resolve(); out.mkdir(parents=True,exist_ok=True)
results=[]
def run(name,n,limit,bits,admission,pos,turn,order="legacy",profile=False,min_live=0,mode="dfs"):
    command=[args.binary,str(n),str(limit),str(bits),str(int(admission)),pos,str(turn),order,
             str(out/f"{name}.tsv") if profile else "-",str(min_live),mode]
    start=time.monotonic()
    try:
        cp=subprocess.run(command,capture_output=True,text=True,timeout=100)
        row=json.loads(cp.stdout) if cp.returncode==0 else {"error":cp.stderr,"returncode":cp.returncode}
        row.update(stderr=cp.stderr)
    except subprocess.TimeoutExpired:
        row={"actor_wins":None,"external_timeout":True}
    row.update(name=name,command=command,wall_seconds=time.monotonic()-start,mode=mode,order=order,position=pos,turn=turn)
    results.append(row)
    (out/"screens.json").write_text(json.dumps({"platform":platform.platform(),"results":results},indent=2))
    print(json.dumps(row),flush=True)

for n in (7,9,11,13):
    for mode in ("dfs","dfpn"):
        run(f"empty-{n}-{mode}",n,30_000_000,20,False,"empty",0,"heuristic",mode=mode)
for admission in (False,True):
    run(f"empty-13-admission-{admission}",13,30_000_000,20,admission,"empty",0,"heuristic")
demon="B.............B/.............../..............W"
run("demon-profile",15,5_000_000,24,False,demon,1,profile=True)
for mode in ("dfs","dfpn","native"):
    run(f"demon-{mode}",15,30_000_000,24,False,demon,1,mode=mode)
for min_live in (8,12):
    run(f"demon-min-live-{min_live}",15,30_000_000,24,False,demon,1,min_live=min_live)
run("q15-dfs",15,120_000_000,24,False,"B.............B/.............../W.............W",0)
run("q15-dfpn",15,120_000_000,24,False,"B.............B/.............../W.............W",0,mode="dfpn")
