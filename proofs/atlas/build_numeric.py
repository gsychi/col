#!/usr/bin/env python3
"""Rebuild selected numerical and fuzzy-game certificates with the C++ generator."""
import csv,json,subprocess,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
exe=ROOT/'number_scan';out=ROOT/'certificates'/'numeric';out.mkdir(parents=True,exist_ok=True)
h,w=5,4;A=(1<<20)-1;B=518119
queries=json.loads((ROOT/'data/5x4_openings_numeric_query_manifest.json').read_text());answers=list(csv.DictReader((ROOT/'data/5x4_openings_numeric.csv').open()))
D={(q['opening'],q['value_scaled'],q['orientation']):d for q,d in zip(queries,answers)}
def nb(v):
 r,c=divmod(v,w)
 return sum(1<<(rr*w+cc) for rr,cc in [(r-1,c),(r+1,c),(r,c-1),(r,c+1)] if 0<=rr<h and 0<=cc<w)
def emit(name,a,b,q):
 path=out/(name+'.json')
 if not path.exists() or os.environ.get("REGENERATE")=="1":subprocess.run([str(exe),str(h),str(w),'50000000',str(a),str(b),str(q),str(path)],check=True)
 return path.name
manifest=[]
# A numerical identity is checked by two losses of G-value, one for each actor.
for name,a,b,q,v in [('alternating_5x4',A,B,48,None)]+[(f'opening_{v}',A&~((1<<v)|nb(v)),B&~(1<<v),(-64 if v!=8 else 32),v) for v in [1,3,4,6,9,11,8]]:
 paths=[emit(name+'_blue',a,b,-q),emit(name+'_white',b,a,q)]
 from fractions import Fraction
 val=Fraction(q,64)
 manifest.append({'name':name,'kind':'exact_number','height':h,'width':w,'blue':a,'white':b,'value':[val.numerator,val.denominator],'opening':v,'files':paths})
# Outcome N is certified by a winning opening for each actor; no numerical value asserted.
for v in [0,2,5,7,10]:
 a=A&~((1<<v)|nb(v));b=B&~(1<<v);ps=[]
 for actor in [0,1]:
  aa,bb=(a,b) if actor==0 else (b,a);d=D[v,0,actor];assert d['result']=='1';move=int(d['winning_move']);assert move>=0
  ps.append({'actor':actor,'move':move,'file':emit(f'fuzzy_opening{v}_actor{actor}',bb&~(1<<move),aa&~((1<<move)|nb(move)),0)})
 manifest.append({'name':f'opening_{v}','kind':'outcome_N','height':h,'width':w,'blue':a,'white':b,'opening':v,'proofs':ps})
(ROOT/'data/numeric_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
