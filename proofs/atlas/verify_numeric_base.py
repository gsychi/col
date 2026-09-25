#!/usr/bin/env python3
"""Generate/check exact Col + canonical-dyadic second-player certificates.
The checker uses coordinate sets, validates every possible first-player move,
and does not call the minimax routine used for generation.
"""
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
import gzip,json,argparse
ROOT=Path(__file__).resolve().parent

def board_neighbors(h,w):
 return tuple(frozenset(rr*w+cc for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)) if 0<=rr<h and 0<=cc<w) for r in range(h) for c in range(w))
def left_number(q):
 if q.denominator>1:return q-F(1,q.denominator)
 return q-1 if q>0 else None

def verify(doc):
 h,w=doc['height'],doc['width'];n=h*w
 if not(1<=n<=30):raise ValueError('Dimensions')
 neighbors=board_neighbors(h,w)
 def verts(x):
  if type(x) is not int or not 0<=x<1<<n:raise ValueError('Mask')
  return frozenset(v for v in range(n) if x>>v&1)
 def number(qnum,qden):
  if type(qnum)is not int or type(qden)is not int or qden<=0 or qden&(qden-1):raise ValueError('Not dyadic')
  return F(qnum,qden)
 # Independent option arithmetic and coordinate-set updates.
 def transitions(a,b,q):
  t={v:(b-{v},a-{v}-neighbors[v],-q) for v in a}
  if q.denominator!=1:
   l=F(q.numerator-1,q.denominator);t[-1]=(b,a,-l)
  elif q.numerator>0:t[-1]=(b,a,-(q-1))
  return t
 def rank(a,b,q):
  if q.denominator==1:day=abs(q.numerator)
  else:day=abs(q.numerator)//q.denominator+1+(q.denominator.bit_length()-1)
  return len(a|b)+day
 nodes={}
 for am,bm,qn,qd,replies in doc['nodes']:
  key=(verts(am),verts(bm),number(qn,qd))
  if key in nodes:raise ValueError('Duplicate state')
  nodes[key]=replies
 am,bm,qn,qd=doc['root'];root=(verts(am),verts(bm),number(qn,qd))
 if root not in nodes:raise ValueError('Root missing')
 children={};edges=0
 for key,replies in nodes.items():
  options=transitions(*key)
  if len(replies)!=len(options) or {r[0] for r in replies}!=set(options):raise ValueError('Incomplete first-player coverage')
  children[key]=[]
  for first,reply in replies:
   mid=options[first];responses=transitions(*mid)
   if reply not in responses:raise ValueError('Illegal reply')
   child=responses[reply]
   if child not in nodes:raise ValueError('Successor missing')
   if not rank(*child)<rank(*mid)<rank(*key):raise ValueError('No descent')
   children[key].append(child);edges+=1
 seen={root};stack=[root]
 while stack:
  for c in children[stack.pop()]:
   if c not in seen:seen.add(c);stack.append(c)
 if len(seen)!=len(nodes) or edges!=doc['edges']:raise ValueError('Metadata/reachability')
 return len(nodes),edges

