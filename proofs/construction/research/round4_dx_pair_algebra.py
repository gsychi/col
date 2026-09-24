"""Discover every one-column support at a diagnostic XX opening.

After Blue (2,3) in XX_7, cut columns0..2 | column3 | columns4..6.
Each strongest safe support S has exactly two identical (X,Q(S))_3 sides.
This finite test diagnoses the proposed XX_odd<1 inductive target.
"""
from fractions import Fraction as F
from pathlib import Path
import json
from round2_dx_local_search import Evaluator
from dx_interface_contracts import exact_value


def scan():
    ev=Evaluator(3);out=[]
    for support in range(32):
        if support&4:continue
        near=''.join('w' if r==2 else 'b' if support>>r&1 else 'o' for r in range(5))
        a,b=ev.masks('bowob',near)
        cap=exact_value(17,support)
        side=ev.value('bowob',near)
        row=dict(support=support,near=near,a=a,b=b,cap=cap,side=side)
        if side is not None:
            row['sum']=str(2*F(side[0])+F(cap['number']))
            row['sum_star']=cap['star']
        out.append(row);print(row,flush=True)
    return out


if __name__=='__main__':
    Path(__file__).with_suffix('.json').write_text(json.dumps(scan(),indent=2)+'\n')
