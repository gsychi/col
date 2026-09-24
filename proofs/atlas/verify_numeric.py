#!/usr/bin/env python3
from pathlib import Path
from fractions import Fraction
import gzip,json
from verify_numeric_base import verify,board_neighbors
ROOT=Path(__file__).resolve().parent

def load(name):
 p=ROOT/'certificates'/'numeric'/name
 if not p.exists():p=p.with_suffix('.json.gz')
 return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())

def main():
 total_nodes=total_edges=0
 for rec in json.loads((ROOT/'data/numeric_manifest.json').read_text()):
  h,w=rec['height'],rec['width'];a,b=rec['blue'],rec['white'];v=rec['opening']
  assert (h,w)==(5,4)
  base_a=(1<<20)-1;base_b=518119
  if v is not None:
   nb=sum(1<<x for x in board_neighbors(5,4)[v])
   assert (a,b)==(base_a&~(nb|1<<v),base_b&~(1<<v))
  else:assert (a,b)==(base_a,base_b)
  if rec['kind']=='exact_number':
   q=Fraction(*rec['value'])
   for name,(aa,bb,qq) in zip(rec['files'],[(a,b,-q),(b,a,q)]):
    doc=load(name);assert (doc['height'],doc['width'],doc['root'])==(h,w,[aa,bb,qq.numerator,qq.denominator]);nn,ee=verify(doc);total_nodes+=nn;total_edges+=ee
   print('VERIFIED',rec['name'],'=',str(q))
  elif rec['kind']=='outcome_N':
   assert {x['actor'] for x in rec['proofs']}=={0,1}
   for proof in rec['proofs']:
    aa,bb=(a,b) if proof['actor']==0 else (b,a);mv=proof['move'];assert aa>>mv&1;nb=sum(1<<x for x in board_neighbors(h,w)[mv]);doc=load(proof['file']);assert (doc['height'],doc['width'],doc['root'])==(h,w,[bb&~(1<<mv),aa&~((1<<mv)|nb),0,1]);nn,ee=verify(doc);total_nodes+=nn;total_edges+=ee
   print('VERIFIED',rec['name'],'has outcome N; no numerical value asserted')
  else:raise ValueError('unknown claim')
 print('NUMERIC/FUZZY CHECKPOINTS',total_nodes,'RESPONSE EDGES',total_edges)

if __name__=='__main__':main()
