#!/usr/bin/env python3
"""Export exact-zero upgrades; source response DAGs must be checked by atlas verify.py.
The theorem applies on the induced live graph and never fills holes with new cells.
"""
from pathlib import Path
import argparse,gzip,json,hashlib

def main():
    p=argparse.ArgumentParser();p.add_argument('atlas',type=Path);args=p.parse_args()
    root=args.atlas.resolve();records=[];total=0;docs={}
    with gzip.open(root/'certified_partial_tiles.jsonl.gz','rt') as f:
        for line in f:
            x=json.loads(line);total+=1
            if x['white']&~x['blue']:continue
            assert x['value_kind']=='upper_bound' and x['bound']==[0,1]
            rel=x['certificate']
            if rel not in docs:
                raw=(root/rel).read_bytes()
                docs[rel]=(json.loads(gzip.decompress(raw) if rel.endswith('.gz') else raw),hashlib.sha256(raw).hexdigest())
            doc,digest=docs[rel];a,b,_=doc['nodes'][x['node_index']]
            assert (doc['height'],doc['width'],a,b)==(x['height'],x['width'],x['blue'],x['white'])
            records.append(dict(height=x['height'],width=x['width'],blue=a,white=b,
                  roles='positive=source first actor; negative=source responder',
                  value_kind='exact_number',value=[0,1],
                  rule='certified_nonpositive_plus_white_subset_blue',
                  certificate=rel,node_index=x['node_index'],certificate_sha256=digest))
    assert total==152473 and len(records)==772
    out=Path(__file__).resolve().parent/'zero_upgrades.jsonl.gz'
    with gzip.open(out,'wt') as f:
        for x in records:f.write(json.dumps(x,separators=(',',':'))+'\n')
    print(f'CHECKED {total} source entries; EXPORTED {len(records)} exact-zero upgrades to {out.name}.')
    print('Source DAG checks are a separate prerequisite: run atlas verify.py and verify_index.py.')
if __name__=='__main__':main()
