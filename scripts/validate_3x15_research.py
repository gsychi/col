"""Independent plain recurrence checks for the separator-bound implication.

No symmetry, CGT, tablebases, or production evaluator are used here.
"""
from functools import lru_cache
import json
from pathlib import Path
import random
import subprocess

def adjacency(n):
    result=[]
    for x in range(3*n):
        r,c=divmod(x,n)
        result.append(sum(1<<(rr*n+cc) for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)) if 0<=rr<3 and 0<=cc<n))
    return result

adj=adjacency(2)
@lru_cache(maxsize=None)
def win(a,b,t):
    moves=a if t==0 else b
    while moves:
        bit=moves&-moves;moves^=bit
        blocked=bit|adj[bit.bit_length()-1]
        aa,bb=(a&~blocked,b&~bit) if t==0 else (a&~bit,b&~blocked)
        if not win(aa,bb,1-t):return True
    return False

checks=0
for a in range(64):
    for b in range(64):
        for t in range(2):
            original=win(a,b,t)
            for col in range(2):
                cut=sum(1<<(r*2+col) for r in range(3))
                for restricted in range(2):
                    aa,bb=(a&~cut,b) if restricted==0 else (a,b&~cut)
                    simplified=win(aa,bb,t)
                    if simplified==(restricted==t):assert original==simplified
                    checks+=1

# The hybrid DFPN must agree with completed DFS on both winning and losing
# legal positions, including early 3x7 positions that exceed its 128-state probes.
rng=random.Random(315)
binary="/private/tmp/col-3x15-fragment/target/release/research"
cases=0
outcomes={True:0,False:0}
for n in (3,5,7):
    adj=adjacency(n)
    for depth in (0,1,2,3,4,5,6,7):
        stones=[set(),set()];legal=[(1<<(3*n))-1]*2;t=0
        for _ in range(depth):
            choices=[i for i in range(3*n) if legal[t]>>i&1]
            if not choices:break
            x=rng.choice(choices);stones[t].add(x)
            legal[t]&=~((1<<x)|adj[x]);legal[1-t]&=~(1<<x);t=1-t
        pos="/".join("".join("B" if r*n+c in stones[0] else "W" if r*n+c in stones[1] else "." for c in range(n)) for r in range(3))
        values=[]
        for mode in ("dfs","dfpn","separator","fragment-20"):
            cp=subprocess.run([binary,str(n),"10000000","16","0",pos,str(t),"heuristic","-","0",mode],capture_output=True,text=True,timeout=30,check=True)
            row=json.loads(cp.stdout)
            assert row["actor_wins"] is not None,(n,pos,mode)
            values.append(row["actor_wins"])
        assert len(set(values))==1,(n,pos,values)
        cases+=1;outcomes[values[0]]+=1
result={"independent_monotonicity_checks":checks,"four_mode_agreement_positions":cases,"winning_cases":outcomes[True],"losing_cases":outcomes[False]}
Path("reports/3x15-investigation/validation.json").write_text(json.dumps(result,indent=2))
print(json.dumps(result))
