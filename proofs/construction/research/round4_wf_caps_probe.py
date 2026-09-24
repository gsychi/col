#!/usr/bin/env python3
"""Bounded discovery of suffix caps; all successful finite claims need certificates."""
from functools import lru_cache
from fractions import Fraction as F
from pathlib import Path
import json
from wf_white_first_check import endpoint_masks,white_move
from round2_wf_check import blue_move
from number_certificates import board_neighbors,left_number
PAT={'D':'obwbo','U':'wbobo','V':'bwbob','X':'bowob','R':'wobob','J':'owobo'}
PAR={'D':1,'U':1,'J':1,'V':0,'X':0,'R':0}
ROOT=Path(__file__).resolve().parent

def solver(w):
    nb=[sum(1<<v for v in ns) for ns in board_neighbors(5,w)]
    @lru_cache(None)
    def win(a,b,q):
        bits=a
        while bits:
            bit=bits&-bits;bits-=bit;v=bit.bit_length()-1
            if not win(b&~bit,a&~(bit|nb[v]),-q):return True
        left=left_number(q)
        return left is not None and not win(b,a,-left)
    return win

def interface(par,row):
    label=(('R','V','X') if par==0 else ('U','J','D'))[min(row,4-row)]
    return label,PAT[label][::(-1 if row>2 else 1)]

def restrict(w,a,b,s):
    for r,x in enumerate(s):
        if x in 'ow':b&=~(1<<(r*w))
    return a,b

def cap(w,q,p,t,row):
    a,b=endpoint_masks(w,'ooooo',PAT[q]);a,b=white_move(w,a,b,t,p)
    if not(a>>(row*w)&1):return None
    return blue_move(w,a,b,row,0)

def main():
    out=[]
    for w in range(1,5):
        win=solver(w)
        for q in PAT:
            cpar=PAR[q]^(w%2);target=F(q=='V')
            for p in range(w):
                for t in ([2] if (cpar+p)%2==0 else [1,3]):
                    # All cap marks are legal actual initial White moves.
                    aa,bb=endpoint_masks(w,'ooooo',PAT[q])
                    if not(bb>>(t*w+p)&1):continue
                    for row in range(5):
                        s,pattern=interface(cpar,row)
                        if p==0 and pattern[t] in 'ow':continue
                        state=cap(w,q,p,t,row)
                        if state is None:continue
                        a,b=state;a,b=restrict(w,a,b,pattern)
                        # Scalar debt bounds sufficient using original ordinary bounds.
                        margin=target+({'R':F(1,4),'V':-F(1,2),'J':F(1,4)}.get(s,F(0)))
                        tight=s in ('R','V')
                        # If only <= is known for left at its limit, cap must be strictly less.
                        immediate=(not win(a,b,-margin)) and (not tight or win(b,a,margin))
                        replies=[]
                        if not immediate:
                            for v in range(5*w):
                                if not(b>>v&1):continue
                                rr,cc=divmod(v,w)
                                if cc==0 and pattern[rr] in 'ow':continue
                                ra,rb=white_move(w,a,b,rr,cc)
                                if not win(ra,rb,-margin):replies.append([rr,cc])
                        entry={'width':w,'Q':q,'mark':[t,p],'blue_row':row,'S':s,'pattern':pattern,'cap':[a,b],'margin':str(margin),'immediate':immediate,'replies':replies}
                        out.append(entry)
            print('DONE',w,q,win.cache_info(),flush=True)
        win.cache_clear()
    (ROOT/'round4_wf_caps_probe.json').write_text(json.dumps(out,indent=2)+'\n')
    for q in PAT:
        rows=[x for x in out if x['Q']==q]
        print('SUMMARY',q,len(rows),sum(x['immediate'] or bool(x['replies']) for x in rows))
if __name__=='__main__':main()
