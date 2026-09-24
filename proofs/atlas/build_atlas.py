#!/usr/bin/env python3
"""Build the useful tile index from independently checkable local certificates."""
from pathlib import Path
import gzip,json
ROOT=Path(__file__).resolve().parent

def ports(h,w,b):
 return {'west':sum(((b>>(r*w))&1)<<r for r in range(h)),
         'east':sum(((b>>(r*w+w-1))&1)<<r for r in range(h)),
         'north':b&((1<<w)-1),'south':(b>>(w*(h-1)))&((1<<w)-1)}
def pattern(h,w,a,b):
 return [''.join('o' if a>>v&1 and b>>v&1 else 'b' if a>>v&1 else 'w' if b>>v&1 else '.' for v in range(r*w,(r+1)*w)) for r in range(h)]
def load(path):
 if not path.exists():path=path.with_suffix('.json.gz')
 return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes()),path

def main():
 summary=json.loads((ROOT/'logs/verification_summary.json').read_text())
 primitive=[];seen=set();partial_count=0
 with gzip.open(ROOT/'certified_partial_tiles.jsonl.gz','wt',encoding='utf-8') as out:
  for path in sorted((ROOT/'data').glob('full*x*_frontier.json')):
   d=json.loads(path.read_text());h,w=d['height'],d['width'];base=ROOT/'certificates'/f'{h}x{w}';m=json.loads((base/'manifest.json').read_text());files={r['white']:r['file'] for r in m['records']}
   for b in d['minimal_safe_white_masks']:
    _,fp=load(base/files[b]);primitive.append({'id':f'{h}x{w}-W{b}','height':h,'width':w,'blue':d['blue'],'white':b,'pattern':pattern(h,w,d['blue'],b),'white_ports':ports(h,w,b),'value_kind':'exact_number','value':[0,1],'certificate':str(fp.relative_to(ROOT)),'inclusion_rule':'actual_blue subset_of blue; white subset_of actual_white'})
   for rec in m['records']:
    doc,fp=load(base/rec['file'])
    for j,(a,b,replies) in enumerate(doc['nodes']):
     if not a or (a|b).bit_count()<4:continue
     key=h,w,a,b
     if key in seen:continue
     seen.add(key);partial_count+=1
     entry={'height':h,'width':w,'blue':a,'white':b,'white_ports':ports(h,w,b),'value_kind':'upper_bound','bound':[0,1],'certificate':str(fp.relative_to(ROOT)),'node_index':j}
     out.write(json.dumps(entry,separators=(',',':'))+'\n')
 atlas={'version':1,'rules':'normal-play Col; own-color orthogonal adjacency forbidden','scope':'Full Blue legality, arbitrary permanent White restriction; partial checkpoints separately bounded above by zero.','bit_order':'row-major; bit 0 of north/south is leftmost; bit 0 of west/east is topmost','summary':{k:v for k,v in summary.items() if k not in ['seconds','by_shape']},'partial_tile_upper_bound_count':partial_count,'primitive_zero_tiles':primitive,'by_shape':summary['by_shape'],'numeric_manifest':'data/numeric_manifest.json','partial_tile_file':'certified_partial_tiles.jsonl.gz'}
 (ROOT/'atlas.json').write_text(json.dumps(atlas,indent=2)+'\n')
 print('primitive_zero_tiles',len(primitive),'certified_partial_upper_bounds',partial_count)

if __name__=='__main__':main()
