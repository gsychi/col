#!/usr/bin/env python3
"""Check that the derived atlas entries point to their certified checkpoints.
Run verify.py as well to validate the source response graphs themselves.
"""
from pathlib import Path
import gzip,json
from build_atlas import ports
ROOT=Path(__file__).resolve().parent

def main():
 atlas=json.loads((ROOT/'atlas.json').read_text());cache={}
 def doc(rel):
  if rel not in cache:
   p=ROOT/rel;cache[rel]=json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
  return cache[rel]
 for tile in atlas['primitive_zero_tiles']:
  d=doc(tile['certificate']);assert (d['height'],d['width'],d['root'])==(tile['height'],tile['width'],[tile['blue'],tile['white']]);assert tile['blue']==(1<<(tile['height']*tile['width']))-1;assert tile['value']==[0,1];assert tile['white_ports']==ports(tile['height'],tile['width'],tile['white'])
 count=0;seen=set()
 with gzip.open(ROOT/atlas['partial_tile_file'],'rt') as f:
  for line in f:
   x=json.loads(line);d=doc(x['certificate']);node=d['nodes'][x['node_index']];key=(x['height'],x['width'],x['blue'],x['white']);assert key not in seen;seen.add(key);assert (d['height'],d['width'],node[0],node[1])==key;assert x['value_kind']=='upper_bound' and x['bound']==[0,1];assert x['white_ports']==ports(x['height'],x['width'],x['white']);count+=1
 assert count==atlas['partial_tile_upper_bound_count']
 print(f'VERIFIED INDEX: {len(atlas["primitive_zero_tiles"])} exact-zero primitives and {count} unique upper-bound-zero checkpoints.')

if __name__=='__main__':main()
