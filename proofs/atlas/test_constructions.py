#!/usr/bin/env python3
"""Check concrete embeddings of the written parametric constructions.
The unbounded claims follow from THEOREMS.md, not from these finite tests.
"""
from fractions import Fraction
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
A=json.loads((ROOT/'atlas.json').read_text())

def zero(h,w,white):
 for p in A['primitive_zero_tiles']:
  if (p['height'],p['width'])==(h,w) and p['white']&white==p['white']:return True
  if (p['height'],p['width'])==(w,h):
   b=sum(1<<((v%h)*w+v//h) for v in range(h*w) if p['white']>>v&1)
   if b&white==b:return True
 return False

def mask(h,w,rows):return sum(1<<(r*w+c) for r in range(h) for c in range(w) if rows[r][c]=='o')
def embed(h,W,col,w,m):return sum(1<<(r*W+col+c) for r in range(h) for c in range(w) if m>>(r*w+c)&1)
def adjacency(h,w,v):
 r,c=divmod(v,w)
 return {rr*w+cc for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)) if 0<=rr<h and 0<=cc<w}

def valid_cover(h,W,actual_a,actual_b,tiles):
 # tiles: (start_column,width,blue,white,upper_bound)
 aa=bb=occupied=0;owner={};cost=Fraction()
 for tid,(col,w,a,b,value) in enumerate(tiles):
  box=embed(h,W,col,w,(1<<(h*w))-1);assert not occupied&box;occupied|=box
  aa|=embed(h,W,col,w,a);bb|=embed(h,W,col,w,b);cost+=value
  for v in range(h*W):
   if box>>v&1:owner[v]=tid
 assert actual_a&~aa==0 and bb&~actual_b==0
 for v in range(h*W):
  if bb>>v&1:
   for u in adjacency(h,W,v):
    if bb>>u&1:assert owner[u]==owner[v]
 return cost

def main():
 E=2023;J4=3951;J2=51;F=5
 assert zero(3,4,E) and zero(3,4,J4) and zero(3,2,J2) and zero(3,1,F)
 count=0
 for k in range(1,26):
  n=4*k;full=(1<<(3*n))-1;white=full&~(1<<n)&~(1<<(n-1))&~(1<<(3*n-1))
  ts=[(4*i,4,4095,E,Fraction()) for i in range(k)];assert valid_cover(3,n,full,white,ts)==0;count+=1
 for n in range(1,101):
  if n%4==3:continue
  base=1 if n%4==1 else 2 if n%4==2 else 4;k=(n-base)//4;b={1:F,2:J2,4:J4}[base]
  ts=[(4*i,4,4095,E,Fraction()) for i in range(k)]+[(4*k,base,(1<<(3*base))-1,b,Fraction())]
  full=(1<<(3*n))-1;white=full&~(1<<n)&~(1<<(2*n-1));assert valid_cover(3,n,full,white,ts)==0;count+=1
 assert zero(2,2,9) and zero(2,2,6)
 # The parity argument proves arbitrary even-by-even dimensions. Test finite examples.
 for h in range(2,13,2):
  for w in range(2,13,2):
   for parity in [0,1]:
    cells={r*w+c for r in range(h) for c in range(w) if (r+c)%2==parity}
    assert all(not(adjacency(h,w,v)&cells) for v in cells)
   count+=1
 # After any one Blue opening on 5x8, choose a reflection making r+c odd.
 for v0 in range(40):
  r,c=divmod(v0,8);c=c if (r+c)%2 else 7-c;v=r*8+c;j=c//4;local=r*4+c%4
  assert (r+c)%2==1
  representative=(4-r)*4+c%4 if r>2 else local
  manifest=json.loads((ROOT/'data/numeric_manifest.json').read_text())
  assert any(x['opening']==representative and x['kind']=='exact_number' and x['value']==[-1,1] for x in manifest)
  ts=[]
  for i in range(2):
   a=(1<<20)-1;b=518119;q=Fraction(3,4)
   if i==j:
    a&=~sum(1<<x for x in adjacency(5,4,local)|{local});b&=~(1<<local);q=Fraction(-1)
   ts.append((4*i,4,a,b,q))
  full=(1<<40)-1;actual_a=full&~sum(1<<x for x in adjacency(5,8,v)|{v});actual_b=full&~(1<<v)
  assert valid_cover(5,8,actual_a,actual_b,ts)==Fraction(-1,4);count+=1
 print(f'VERIFIED {count} finite construction embeddings, including all 40 one-Blue-stone 5x8 positions.')

if __name__=='__main__':main()
