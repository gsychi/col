#!/usr/bin/env python3
"""Finite discovery of White-first endpoint caps; no infinite claim."""
from functools import lru_cache
from fractions import Fraction as F
from wf_white_first_check import endpoint_masks, white_move
from number_certificates import board_neighbors, left_number
import json


def numerical_solver(width):
    nb=[sum(1<<v for v in ns) for ns in board_neighbors(5,width)]
    @lru_cache(None)
    def win(a,b,q):
        bits=a
        while bits:
            bit=bits&-bits;bits-=bit;v=bit.bit_length()-1
            if not win(b&~bit,a&~(bit|nb[v]),-q):return True
        left=left_number(q)
        return left is not None and not win(b,a,-left)
    def bounds(a,b):
        for denominator in (1,2,4,8,16):
            for numerator in range(-2*denominator, 3*denominator+1):
                q=F(numerator,denominator)
                blue,white=win(a,b,-q),win(b,a,q)
                if not blue and not white:return q,False
                if blue and white:return q,True
        return None,None
    return bounds


def main():
    solvers={w:numerical_solver(w) for w in (1,2,3)}
    results=[]
    for cap_width in (2,3):
        for row in (0,2):
            a,b=endpoint_masks(cap_width,'obwbo','ooooo')
            a,b=white_move(cap_width,a,b,row,0)
            allowed=sum(1<<r for r in range(5) if b>>(r*cap_width+cap_width-1)&1)
            for support in range(32):
                if support&~allowed:continue
                bb=b
                for r in range(5):
                    if not (support>>r&1):bb&=~(1<<(r*cap_width+cap_width-1))
                cap,capstar=solvers[cap_width](a,bb)
                endpoint=''.join('b' if support>>r&1 else 'o' for r in range(5))
                tail=[]
                for width in ((1,3) if cap_width==2 else (2,)):
                    aa,bb=endpoint_masks(width,'obwbo',endpoint)
                    q,star=solvers[width](aa,bb)
                    tail.append((width,str(q),star))
                entry={'cap_width':cap_width,'white_row':row,'support':support,'cap':str(cap),'capstar':capstar,'tail_endpoint':endpoint,'tail':tail}
                results.append(entry)
                if cap is not None and tail[-1][1] != 'None' and (F(tail[-1][1])+cap<0 or (F(tail[-1][1])+cap==0 and tail[-1][2]==capstar)):
                    print('CANDIDATE',entry,flush=True)
            print('DONE',cap_width,row,flush=True)
    with open(__file__.replace('.py','.json'),'w') as handle:json.dump(results,handle,indent=2)

if __name__=='__main__':main()
