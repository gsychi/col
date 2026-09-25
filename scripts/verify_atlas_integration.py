#!/usr/bin/env python3
"""Check imported sources with Rust, known strip strategies, and the L exclusions."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'python'))
from col.adaptive_tiling import AdaptiveSearch, IndexedLibrary, extract_checkpoint
from col.atlas import Atlas
from col.tiling import Library, check_tile, mask, neighbors
from adaptive_tiling_research import root_after_opening, save_proof
from benchmark_atlas_priority import report, verify_rust, write


def main():
    out=ROOT/'reports/atlas-priority/validation';out.mkdir(parents=True,exist_ok=True)
    atlas=Atlas(ROOT/'proofs/atlas',ROOT/'proofs/atlas-review')
    all_sources=[dict(id=rel,source_sha256=s.sha256,doc=s.doc) for rel,s in atlas.sources.items()]
    grid_rust=verify_rust(report(all_sources,[]))
    library=atlas.library(3,Library.load(ROOT/'reports/adaptive-tiling/final/library'))
    index=IndexedLibrary(library);controls=[]
    for label,n,opening in [('3x13-empty',13,None),('3x19-opening26',19,26),('3x101-empty',101,None)]:
        a,b=root_after_opening(3,n,opening) if opening is not None else ((1<<(3*n))-1,)*2
        turn=1 if opening is not None else 0
        search=AdaptiveSearch(index,n,seconds=10,focus=opening,two_direction=True,zero_promotion=True)
        result=search.run(a,b,turn,max_white_turns=2)
        assert result['status']=='certified'
        result['verification']=save_proof(search,a,b,turn,out/(label+'.json'),replays=20)
        result.pop('failures');controls.append(dict(case=label,**result))
        print(label,result['seconds'],flush=True)
    # Independently verify the geometric embedding before treating the bent
    # remainder as a path. Then Rust verifies both path roots as ordinary DAGs.
    spec=importlib.util.spec_from_file_location('l_checker',ROOT/'proofs/atlas-review/verify_l_shapes.py')
    checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
    remainders=[]
    for path in sorted((ROOT/'proofs/atlas-review').glob('L_*.json.gz')):
        doc=json.loads(gzip.decompress(path.read_bytes()));states,edges=checker.verify(doc)
        docs=[];nb=[mask(s) for s in neighbors(1,13)];table={(a,b):rs for a,b,rs in doc['nodes']}
        for root in doc['roots']:
            pending=[tuple(root)];seen=set(pending);nodes=[]
            for a,b in pending:
                replies=table[a,b];nodes.append([a,b,replies])
                for v,r in zip([v for v in range(13) if a>>v&1],replies):
                    child=a&~((1<<v)|nb[v]|(1<<r)),b&~((1<<v)|(1<<r)|nb[r])
                    if child not in seen:seen.add(child);pending.append(child)
            tile=dict(height=1,width=13,root=root,nodes=nodes);check_tile(tile)
            raw=gzip.compress(json.dumps(tile,separators=(',',':')).encode(),mtime=0)
            docs.append(dict(id=f'{path.name}-root{len(docs)}',source_sha256=hashlib.sha256(raw).hexdigest(),doc=tile,
                             derived_from=dict(file=path.name,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())))
        rust=verify_rust(report(docs,[]))
        remainders.append(dict(case=path.name,states=states,edges=edges,rust=rust,
            conclusion='Only the specified unopened zero bulk plus independently safe unopened L is rejected; no physical board outcome inferred.'))
    result=dict(format='col-atlas-integration-validation-v1',atlas=atlas.verification,
                rust_all_grid_sources=grid_rust,known_strips=controls,l_remainders=remainders)
    write(out/'summary.json',result)


if __name__=='__main__':main()
