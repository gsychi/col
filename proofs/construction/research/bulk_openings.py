from pathlib import Path
from fractions import Fraction as F
from functools import lru_cache
import json

def evaluate(h,w,a,b,q):
 nb=[]
 for v in range(h*w):
  r,c=divmod(v,w);nb.append(sum(1<<(rr*w+cc) for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)) if 0<=rr<h and 0<=cc<w))
 @lru_cache(None)
 def win(a,b,q):
  z=a
  while z:
   p=z&-z;z-=p;v=p.bit_length()-1
   if not win(b&~p,a&~(p|nb[v]),-q):return True
  if q.denominator>1:left=q-F(1,q.denominator)
  elif q>0:left=q-1
  else:return False
  return not win(b,a,-left)
 out=[]
 for v in range(h*w):
  if not(a>>v&1):continue
  aa=a&~((1<<v)|nb[v]);bb=b&~(1<<v)
  x=win(aa,bb,q);y=win(bb,aa,-q)
  cls=('N' if y else 'L') if x else ('R' if y else 'P')
  out.append({'cell':v,'row':v//w,'col':v%w,'blue_next_wins':x,'white_next_wins':y,'class':cls})
 return out
if __name__=='__main__':
 results=[]
 for b in [2023,1959,3710,3951]:
  out=evaluate(3,4,4095,b,F(1,4));results.append({'white':b,'add':'1/4','options':out})
  print(b,[(x['row'],x['col'],x['class']) for x in out],flush=True)
 json.dump(results,open(f'{Path(__file__).resolve().parent}/bulk_openings_results.json','w'),indent=2)
