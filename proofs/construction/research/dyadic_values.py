from functools import lru_cache
from fractions import Fraction as F
from small_values import board_nb
import json

def tests(h,w,a,b):
 nb=board_nb(h,w)
 @lru_cache(None)
 def win(a,b,q):
  x=a
  while x:
   bit=x&-x;x-=bit;v=bit.bit_length()-1
   if not win(b&~bit,a&~(bit|nb[v]),-q):return True
  if q.denominator>1:
   left=q-F(1,q.denominator)
  elif q>0:left=q-1
  else:return False
  return not win(b,a,-left)
 res={}
 for q in [F(0),-F(1,2),-F(1,4),-F(1,8),-F(1,16),-F(3,8),-F(3,16),-F(5,16)]:
  x=win(a,b,q);y=win(b,a,-q)
  res[str(q)]=('N' if y else 'L') if x else ('R' if y else 'P')
 return res
if __name__=='__main__':
 print('F3',tests(3,3,511,503))
