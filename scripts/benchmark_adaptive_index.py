#!/usr/bin/env python3
"""Compare identical safe-checkpoint palettes on fixed whole-board tile queries."""
import json
from pathlib import Path
import statistics
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'python'))
from col.adaptive_tiling import Library,IndexedLibrary,AdaptiveSearch,mask,neighbors
from col.weighted_tiling import Sources,WeightedSearch,check_cover

sources=Sources.load();library=Library.load(ROOT/'reports/weighted-tiling/checkpoint-library')
t=time.perf_counter();slow=WeightedSearch(sources,'original',original_checkpoints=True);slow_index=time.perf_counter()-t
t=time.perf_counter();fast=IndexedLibrary(library);fast_index=time.perf_counter()-t
assert {(v.width,v.a,v.b) for v in slow.variants}=={(v.width,v.a,v.b) for group in fast.groups.values() for v in group}
positions=[]
for n in (13,19,23):
    full=(1<<(3*n))-1
    if n==13:positions.append((n,full,full));continue
    opening=26 if n==19 else 34
    a=full&~((1<<opening)|mask(neighbors(3,n)[opening]));b=full&~(1<<opening)
    search=AdaptiveSearch(fast,n,seconds=10)
    replies=[8] if n==19 else search.representative_white_moves(a,b)
    positions.extend((n,*search.child(a,b,1,v)[:2]) for v in replies)
results=[];timings={'linear':[],'indexed':[]}
for repeat in range(3):
    order=('linear','indexed') if repeat%2==0 else ('indexed','linear')
    for mode in order:
        answers=[];elapsed=0
        for n,a,b in positions:
            t=time.perf_counter();cover=slow.bound(3,n,a,b) if mode=='linear' else fast.plan(n,a,b)
            elapsed+=time.perf_counter()-t;answers.append(cover is not None)
            if repeat==0 and mode=='linear' and cover is not None:check_cover(sources,3,n,a,b,cover)
        timings[mode].append(elapsed)
        if not results:results=answers
        else:assert answers==results
summary=dict(format='col-adaptive-index-benchmark-v1',queries=len(positions),matched=sum(results),variants=fast.variant_count,
    index_seconds=dict(linear=slow_index,indexed=fast_index),wall_seconds=timings,
    median_seconds={mode:statistics.median(values) for mode,values in timings.items()},
    measurements='Identical original checkpoint sets, same 25 whole-board tile queries, three runs with alternating order. Includes empty 3x13, successful 3x19 response, and all 23 symmetry-distinct responses to the 3x23 center. Timings exclude source verification and index construction.',
    positions=[dict(width=n,a=hex(a),b=hex(b),cover=answer) for (n,a,b),answer in zip(positions,results)])
summary['query_speedup']=summary['median_seconds']['linear']/summary['median_seconds']['indexed']
out=ROOT/'reports/adaptive-tiling';out.mkdir(exist_ok=True);(out/'index-benchmark.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='positions'},indent=2))
