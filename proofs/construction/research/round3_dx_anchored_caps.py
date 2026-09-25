"""Discover exact 5x3 caps anchored at D, with an opening in the far column."""
from fractions import Fraction as F
from pathlib import Path
import json
from round2_dx_local_search import Evaluator

PATTERNS=dict(D='obwbo',U='wbobo',V='bwbob',X='bowob',R='wobob',J='owobo')


def scan():
    ev=Evaluator(3);base_a=base_b=(1<<15)-1
    for r,s in enumerate(PATTERNS['D']):
        if s not in 'ob':base_a&=~(1<<(3*r))
        if s not in 'ow':base_b&=~(1<<(3*r))
    rows=[]
    for r,names in [(0,'UR'),(1,'VJ'),(2,'DX')]:
        for name in names:
            a=base_a&~ev.closed[3*r+2];b=base_b&~(1<<(3*r+2))
            for rr,s in enumerate(PATTERNS[name]):
                if s in 'ow':b&=~(1<<(3*rr+2))
            value=None
            for i in range(-16,17):
                q=F(i,4)
                for star in (False,True):
                    if not ev.win(a,b,-q,star) and not ev.win(b,a,q,star):
                        value=dict(number=str(q),star=star);break
                if value is not None:break
            row=dict(blue=[r,2],interface=name,a=a,b=b,value=value)
            rows.append(row);print(row,flush=True)
    return rows


if __name__=='__main__':
    Path(__file__).with_suffix('.json').write_text(json.dumps(scan(),indent=2)+'\n')
