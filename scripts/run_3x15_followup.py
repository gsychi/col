"""Follow-up separator and search-order screens, using the second isolated build."""
import json
from pathlib import Path
import subprocess
import time

out=Path("reports/3x15-investigation")
binary="/private/tmp/col-3x15-fragment/target/release/research"
rows=[]
def run(name,n,pos,t,mode,limit=15_000_000,timeout=90):
    cmd=[binary,str(n),str(limit),"24","0",pos,str(t),"legacy","-","0",mode]
    started=time.monotonic()
    try:
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
        row=json.loads(p.stdout) if p.returncode==0 else {"error":p.stderr}
        row["stderr"]=p.stderr
    except subprocess.TimeoutExpired:row={"actor_wins":None,"external_timeout":True}
    row.update(name=name,command=cmd,wall_seconds=time.monotonic()-started)
    rows.append(row);(out/"followup.json").write_text(json.dumps(rows,indent=2));print(json.dumps(row),flush=True)
for mode in ("dfs","fragment-20","fragment-26","separator"):
    run(f"3x13-{mode}",13,"empty",0,mode)
demon="B.............B/.............../..............W"
for mode in ("dfs","fragment-20","fragment-26","separator"):
    run(f"demon-{mode}",15,demon,1,mode)
run("demon-dfpn-long",15,demon,1,"dfpn",120_000_000,180)
