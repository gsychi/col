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

def generate(h,w,a,b,q):
 nb=[sum(1<<x for x in s) for s in board_neighbors(h,w)]
 @lru_cache(None)
 def moves(a,b,q):
  result=[]
  bits=a
  while bits:
   bit=bits&-bits;bits-=bit;v=bit.bit_length()-1
   result.append((v,b&~bit,a&~(bit|nb[v]),-q))
  x=left_number(q)
  if x is not None:result.append((-1,b,a,-x))
  return tuple(result)
 @lru_cache(None)
 def win(a,b,q):
  return any(not win(aa,bb,qq) for mv,aa,bb,qq in moves(a,b,q))
 if win(a,b,q):raise ValueError('Requested root is not a loss')
 states=[(a,b,q)];seen={states[0]};records=[];edges=0
 for aa,bb,qq in states:
  replies=[]
  for mv,ab,ba,qb in moves(aa,bb,qq):
   response=next((m2,a2,b2,q2) for m2,a2,b2,q2 in moves(ab,ba,qb) if not win(a2,b2,q2))
   m2,a2,b2,q2=response;replies.append([mv,m2]);edges+=1
   state=(a2,b2,q2)
   if state not in seen:seen.add(state);states.append(state)
  records.append([aa,bb,qq.numerator,qq.denominator,replies])
 return {'height':h,'width':w,'root':[a,b,q.numerator,q.denominator],'nodes':records,'edges':edges}

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

def build():
 out=[]
 # Equality F3=1/4 is checked as two losses for F3-1/4 and its conjugate.
 for name,h,w,a,b,q in [
  ('cap_minus_quarter_blue',3,3,511,503,-F(1,4)),
  ('cap_minus_quarter_white',3,3,503,511,F(1,4)),
  ('economical_bulk_blue',3,4,4095,1959,F(0)),
  ('economical_bulk_white',3,4,1959,4095,F(0)),
  ('phase_connector_blue',3,4,4095,3951,F(0)),
  ('phase_connector_white',3,4,3951,4095,F(0)),
  ('original_bulk_blue',3,4,4095,2023,F(0)),
  ('original_bulk_white',3,4,2023,4095,F(0)),
  ('opened_bulk_plus_one_blue',3,4,4056,2021,F(1)),
  ('opened_bulk_plus_one_white',3,4,2021,4056,-F(1)),
  ('opened_bulk_c3_plus_one_blue',3,4,3955,2023,F(1)),
  ('opened_bulk_c3_plus_one_white',3,4,2023,3955,-F(1)),
  ('opened_bulk_middle0_plus_one_blue',3,4,3790,2023,F(1)),
  ('opened_bulk_middle0_plus_one_white',3,4,2023,3790,-F(1)),
  ('opened_bulk_middle2_plus_one_blue',3,4,2843,1959,F(1)),
  ('opened_bulk_middle2_plus_one_white',3,4,1959,2843,-F(1)),
  ('three_by_three_edge_plus_two_blue',3,3,488,509,F(2)),
  ('three_by_three_edge_plus_two_white',3,3,509,488,-F(2)),
 ]:
  d=generate(h,w,a,b,q);sizes=verify(d)
  (ROOT/'new_certificates').mkdir(exist_ok=True)
  p=ROOT/'new_certificates'/f'{name}.json.gz';p.write_bytes(gzip.compress(json.dumps(d,separators=(',',':')).encode(),mtime=0))
  out.append({'name':name,'checkpoints':sizes[0],'edges':sizes[1]})
  print(name,sizes,flush=True)
 # A positive root is certified by a Blue move followed by a White-first loss.
 h,w=5,4;full=(1<<20)-1;white=518119;v=8
 aa=full & ~(1<<v | sum(1<<x for x in board_neighbors(h,w)[v]))
 bb=white & ~(1<<v)
 d=generate(h,w,bb,aa,F(0));sizes=verify(d)
 d['claim']={'type':'blue_wins_root_by_one_move','original_blue':full,'original_white':white,'blue_move':v}
 (ROOT/'new_certificates'/'five_row_extrusion_refutation.json.gz').write_bytes(gzip.compress(json.dumps(d,separators=(',',':')).encode(),mtime=0))
 out.append({'name':'five_row_extrusion_refutation','checkpoints':sizes[0],'edges':sizes[1]})
 print('five_row_extrusion_refutation',sizes)
 json.dump(out,open(ROOT/'new_certificate_summary.json','w'),indent=2)

def check_all():
 expected={
  'cap_minus_quarter_blue':(3,3,[511,503,-1,4]),
  'cap_minus_quarter_white':(3,3,[503,511,1,4]),
  'economical_bulk_blue':(3,4,[4095,1959,0,1]),
  'economical_bulk_white':(3,4,[1959,4095,0,1]),
  'phase_connector_blue':(3,4,[4095,3951,0,1]),
  'phase_connector_white':(3,4,[3951,4095,0,1]),
  'original_bulk_blue':(3,4,[4095,2023,0,1]),
  'original_bulk_white':(3,4,[2023,4095,0,1]),
  'opened_bulk_plus_one_blue':(3,4,[4056,2021,1,1]),
  'opened_bulk_plus_one_white':(3,4,[2021,4056,-1,1]),
  'opened_bulk_c3_plus_one_blue':(3,4,[3955,2023,1,1]),
  'opened_bulk_c3_plus_one_white':(3,4,[2023,3955,-1,1]),
  'opened_bulk_middle0_plus_one_blue':(3,4,[3790,2023,1,1]),
  'opened_bulk_middle0_plus_one_white':(3,4,[2023,3790,-1,1]),
  'opened_bulk_middle2_plus_one_blue':(3,4,[2843,1959,1,1]),
  'opened_bulk_middle2_plus_one_white':(3,4,[1959,2843,-1,1]),
  'three_by_three_edge_plus_two_blue':(3,3,[488,509,2,1]),
  'three_by_three_edge_plus_two_white':(3,3,[509,488,-2,1]),
 }
 for name,(h,w,root) in expected.items():
  p=ROOT/'new_certificates'/f'{name}.json.gz'
  d=json.loads(gzip.decompress(p.read_bytes()))
  if (d['height'],d['width'],d['root'])!=(h,w,root):raise ValueError('Wrong claimed root')
  print('VERIFIED',p.name,verify(d))
 p=ROOT/'new_certificates'/'five_row_extrusion_refutation.json.gz'
 d=json.loads(gzip.decompress(p.read_bytes()));claim=d['claim']
 if claim!={'type':'blue_wins_root_by_one_move','original_blue':1048575,'original_white':518119,'blue_move':8}:raise ValueError('Wrong extrusion claim')
 aa=frozenset(range(20))-{8}-board_neighbors(5,4)[8]
 bb=frozenset(v for v in range(20) if 518119>>v&1)-{8}
 if (d['height'],d['width'],d['root'])!=(5,4,[sum(1<<v for v in bb),sum(1<<v for v in aa),0,1]):raise ValueError('Wrong extrusion child')
 print('VERIFIED',p.name,verify(d))
 print('VERIFIED: C3=1/4, E4=0, E4_restricted=0, J4=0, opened_E4=-1; five-row alternating extrusion is Blue-first winning.')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--generate',action='store_true');args=p.parse_args()
 if args.generate:build()
 else:check_all()
