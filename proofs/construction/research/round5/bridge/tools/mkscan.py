import subprocess, sys, os
sys.path.insert(0,'/tmp/5x9/w')
from pos import play
H,W=5,9
def refl(g,v):
    r,c=divmod(v,W)
    if g&1: r=H-1-r
    if g&2: c=W-1-c
    return r*W+c
done=set(f.split('.')[0] for d in ('jobs','running','done') for f in os.listdir('/tmp/5x9/q/'+d))
for o in [0,2,4,10,18,20]:
    syms=[g for g in range(4) if refl(g,o)==o]
    seen=set()
    for u in range(45):
        r,c=divmod(u,W)
        if u==o or (r+c)%2: continue
        # White cannot play adjacent... opening is Blue: any cell except o is White-legal
        key=min(refl(g,u) for g in syms)
        if key in seen: continue
        seen.add(key)
        name=f'scan_o{o}_u{u}'
        if name+'.job' in done or name in done: continue
        A,B=play([o,u])
        subprocess.run(['python3','/tmp/5x9/sub.py','/tmp/5x9/q',name,'5400','HYW=5','HYLOG=24','--','/tmp/bridge/b2/hy2','scan','5','9',str(A),str(B),'0'])
        print(name)
