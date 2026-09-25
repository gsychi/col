"""Explore richer near-end White supports; all results are finite discovery."""
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
import json


BASE = dict(D="obwbo", X="bowob")


class Evaluator:
    def __init__(self, width):
        self.width = width
        self.closed = []
        for r in range(5):
            for c in range(width):
                self.closed.append(sum(1 << (rr*width+cc) for rr,cc in
                                       [(r,c),(r-1,c),(r+1,c),(r,c-1),(r,c+1)]
                                       if 0<=rr<5 and 0<=cc<width))
        self.win = lru_cache(None)(self._win)

    def _win(self,a,b,q,star):
        moves=a
        while moves:
            bit=moves&-moves;moves-=bit
            if not self.win(b&~bit,a&~self.closed[bit.bit_length()-1],-q,star):return True
        left=q-F(1,q.denominator) if q.denominator>1 else q-1 if q>0 else None
        if left is not None and not self.win(b,a,-left,star):return True
        return bool(star and not self.win(b,a,-q,False))

    def masks(self,left,right):
        a=b=(1<<(5*self.width))-1
        for c,pattern in [(0,left),(self.width-1,right)]:
            for r,s in enumerate(pattern):
                if s not in 'ob':a&=~(1<<(r*self.width+c))
                if s not in 'ow':b&=~(1<<(r*self.width+c))
        return a,b

    def value(self,left,right):
        a,b=self.masks(left,right)
        for i in range(-16,25):
            q=F(i,4)
            for star in (False,True):
                if not self.win(a,b,-q,star) and not self.win(b,a,q,star):
                    return str(q),star
        return None


if __name__=='__main__':
    data=[]
    for width,far in [(1,'X'),(2,'D'),(3,'X')]:
        ev=Evaluator(width)
        for support in range(1,32,2):
            near='w'+''.join('o' if support>>r&1 else 'b' for r in range(1,5))
            value=ev.value(BASE[far],near)
            row=dict(width=width,far=far,near=near,support=support,value=value)
            data.append(row)
            print(row,'cache',ev.win.cache_info().currsize,flush=True)
    Path(__file__).with_suffix('.json').write_text(json.dumps(data,indent=2)+'\n')
