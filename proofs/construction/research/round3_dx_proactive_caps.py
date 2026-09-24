"""Discovery: proactive White replies to the first move of the mirror trap.

Keep the first three columns, with D at the left, Blue at (0,2), and an
arbitrary legal local White reply. Search the U/R interface on the remaining
right strip. All values are finite and require separate certificate checks.
"""
from fractions import Fraction as F
from pathlib import Path
import json
from round2_dx_local_search import Evaluator


PATTERNS=dict(U='wbobo',R='wobob')


def scan():
    ev=Evaluator(3);a=b=(1<<15)-1
    for r,s in enumerate('obwbo'):
        if s not in 'ob':a&=~(1<<(3*r))
        if s not in 'ow':b&=~(1<<(3*r))
    a&=~ev.closed[2];b&=~(1<<2)
    rows=[]
    for name,pattern in PATTERNS.items():
        white_support={r for r,s in enumerate(pattern) if s in 'ow'}
        for u in range(15):
            if not b>>u&1:continue
            r,c=divmod(u,3)
            if c==2 and r in white_support:continue
            aa=a&~(1<<u);bb=b&~ev.closed[u]
            for rr in white_support:bb&=~(1<<(3*rr+2))
            found=None
            for j in range(-12,13):
                q=F(j,4)
                for star in (False,True):
                    if not ev.win(aa,bb,-q,star) and not ev.win(bb,aa,q,star):
                        found=dict(number=str(q),star=star);break
                if found is not None:break
            record=dict(interface=name,blue=[0,2],white=[r,c],a=aa,b=bb,value=found)
            rows.append(record);print(record,flush=True)
    return rows


if __name__=='__main__':
    Path(__file__).with_suffix('.json').write_text(json.dumps(scan(),indent=2)+'\n')
