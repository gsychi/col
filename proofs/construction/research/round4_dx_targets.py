"""Bounded discovery for the three anchored-cap auxiliary targets.

The raw solver is a discovery aid, not a supplied independent certificate.
Negative integer offsets use isolated White-only vertices behind a dead column.
"""
from pathlib import Path
import json
import subprocess

RAW='/tmp/col-round2-raw/target/release/raw_research'
PATTERNS={'R':'wobob','V':'bwbob','X':'bowob'}


def root(left,width,offset):
    ambient=width+2;a=b=0
    for r in range(5):
        for c in range(width):a|=1<<(r*ambient+c);b|=1<<(r*ambient+c)
    for c,p in [(0,PATTERNS[left]),(width-1,PATTERNS['X'])]:
        for r,s in enumerate(p):
            if s not in 'ob':a&=~(1<<(r*ambient+c))
            if s not in 'ow':b&=~(1<<(r*ambient+c))
    for i in range(offset):b|=1<<((2*i)*ambient+width+1)
    return ambient,a,b


if __name__=='__main__':
    out=[]
    for width in (3,5):
        for left,offset in [('R',1),('V',2),('X',1)]:
            ambient,a,b=root(left,width,offset)
            for turn in (0,1):
                raw=subprocess.check_output([RAW,'5',str(ambient),str(a),str(b),str(turn),'2000000'],text=True)
                result=json.loads(raw);result['label']=f'{left}X_{width}-{offset}'
                result['status']='Unknown' if result['states']>=result['budget'] else 'Completed'
                out.append(result);print(json.dumps(result),flush=True)
    Path(__file__).with_suffix('.json').write_text(json.dumps(out,indent=2)+'\n')
