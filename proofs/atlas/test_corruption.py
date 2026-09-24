#!/usr/bin/env python3
import copy,gzip,json,tempfile
from pathlib import Path
from verify import verify_strategy
from verify_numeric_base import verify as verify_number
ROOT=Path(__file__).resolve().parent

def read(path):
 if not path.exists():path=path.with_suffix('.json.gz')
 return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes())

def main():
 m=json.loads((ROOT/'certificates/2x2/manifest.json').read_text());r=next(r for r in m['records'] if r['blue_first_loses']);d=read(ROOT/'certificates/2x2'/r['file']);tests=0
 with tempfile.TemporaryDirectory() as td:
  path=Path(td)/'certificate.json';path.write_text(json.dumps(d));verify_strategy(path,2,2,(15,r['white']))
  variants=[]
  bad=copy.deepcopy(d);next(row for row in bad['nodes'] if row[2])[2].pop();variants.append(bad)
  bad=copy.deepcopy(d);next(row for row in bad['nodes'] if row[2])[2][0]=99;variants.append(bad)
  bad=copy.deepcopy(d);bad['root'][0]^=1;variants.append(bad)
  for bad in variants:
   path.write_text(json.dumps(bad))
   try:verify_strategy(path,2,2,(15,r['white']))
   except ValueError:tests+=1
   else:raise AssertionError('corruption accepted')
 d=read(ROOT/'certificates/numeric/alternating_5x4_blue.json')
 bad=copy.deepcopy(d);next(row for row in bad['nodes'] if row[4])[4].pop()
 try:verify_number(bad)
 except ValueError:tests+=1
 else:raise AssertionError('incomplete numeric coverage accepted')
 print(f'PASS: {tests} malformed-certificate rejection tests; ordinary and numerical verification paths exercised.')

if __name__=='__main__':main()
