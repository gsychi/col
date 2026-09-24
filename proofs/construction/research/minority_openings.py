#!/usr/bin/env python3
"""Finite assembly tests for the parameterized minority-opening construction.
The unbounded conclusion follows from the repeated-tile argument in RESEARCH.md,
not from the finite range tested here. Local value certificates are checked by
number_certificates.py.
"""
from fractions import Fraction as F
from number_certificates import board_neighbors

def reflect(x,n):
 return sum(1<<(r*n+n-1-c) for r in range(3) for c in range(n) if x>>(r*n+c)&1)

def witness(n,r,c):
 assert n%2==1 and n>=1 and 0<=r<3 and 0<=c<n and (r+c)%2==1
 if n in (1,3):return None,F(-2)
 full=(1<<(3*n))-1
 mirrored=n%4==3 and c>=n-3
 cc=n-1-c if mirrored else c
 widths=[4]*(n//4)+[n%4]
 roots=[(4,4095,2023)]*(n//4)+([(1,7,5)] if n%4==1 else [(3,511,503)])
 va=vb=0;owner={};offset=0;score=F(0)
 for i,(w,a,b) in enumerate(roots):
  value=F(0) if w in (1,4) else F(1,4)
  if offset<=cc<offset+w:
   local=r*w+cc-offset
   nb=board_neighbors(3,w)
   a &= ~(1<<local | sum(1<<v for v in nb[local]));b &= ~(1<<local)
   if w==4:
    assert local in (1,3,4,6,9,11)
    value=F(-1)
   elif w==1:
    assert local==1;value=F(-2)
   else:raise AssertionError('Opening fell in the positive cap')
  for rr in range(3):
   for col in range(w):
    gv=rr*n+offset+col;lv=rr*w+col
    owner[gv]=i
    if a>>lv&1:va|=1<<gv
    if b>>lv&1:vb|=1<<gv
  score+=value;offset+=w
 assert offset==n
 if mirrored:
  va=reflect(va,n);vb=reflect(vb,n)
  owner={(v//n)*n+n-1-v%n:i for v,i in owner.items()}
 nb=board_neighbors(3,n);v=r*n+c
 aa=full&~(1<<v | sum(1<<u for u in nb[v]));bb=full&~(1<<v)
 assert aa&~va==0 and vb&~bb==0
 for u,nei in enumerate(nb):
  for v in nei:
   if owner[u]!=owner[v]:assert not (vb>>u&1 and vb>>v&1)
 assert score<0
 return (va,vb),score

if __name__=='__main__':
 count=0
 for n in range(1,102,2):
  for r in range(3):
   for c in range(n):
    if (r+c)%2:
     witness(n,r,c);count+=1
 print(f'PASS: {count} minority-color opening assemblies, all odd widths 1 through 101.')
