from pathlib import Path
from functools import lru_cache
import json

def board_nb(h,w):
 nb=[]
 for v in range(h*w):
  r,c=divmod(v,w);nb.append(sum(1<<(rr*w+cc) for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)) if 0<=rr<h and 0<=cc<w))
 return nb

def outcome(h,w,a,b,integer=0,half=0,star=0):
 nb=board_nb(h,w);n=h*w
 if integer:
  for _ in range(abs(integer)):
   v=len(nb);nb.append(0)
   if integer>0:a|=1<<v
   else:b|=1<<v
 if half:
  v=len(nb);nb.extend([1<<(v+1),1<<v])
  if half>0:a|=3<<v;b|=1<<(v+1)
  else:b|=3<<v;a|=1<<(v+1)
 if star:v=len(nb);nb.append(0);a|=1<<v;b|=1<<v
 @lru_cache(None)
 def win(a,b):
  x=a
  while x:
   p=x&-x;x-=p;v=p.bit_length()-1
   if not win(b&~p,a&~(p|nb[v])):return True
  return False
 bl=win(a,b);wh=win(b,a)
 return ('N' if wh else 'L') if bl else ('R' if wh else 'P')

if __name__=='__main__':
 res=[]
 for h,w,a,b in [(3,3,511,503),(3,3,511,495),(3,4,4095,2023),(3,4,4095,1959),(3,1,7,5)]:
  row={'h':h,'w':w,'a':a,'b':b,'tests':{}}
  for q in range(-2,3):row['tests'][str(q)]=outcome(h,w,a,b,integer=q)
  row['tests']['-1/2']=outcome(h,w,a,b,half=-1)
  row['tests']['1/2']=outcome(h,w,a,b,half=1)
  print(row,flush=True);res.append(row)
 json.dump(res,open(f'{Path(__file__).resolve().parent}/small_values.json','w'),indent=2)
