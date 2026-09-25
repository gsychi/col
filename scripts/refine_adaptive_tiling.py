#!/usr/bin/env python3
"""Repeat the concrete counterexample/local-tile loop with fixed research limits."""
import json
from pathlib import Path
import sys
import time
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'python'));sys.path.insert(0,str(ROOT/'scripts'))
from col.adaptive_tiling import *
from adaptive_tiling_research import root_after_opening,save_proof

out=ROOT/'reports/adaptive-tiling/final';out.mkdir(parents=True,exist_ok=True)
source=ROOT/'reports/weighted-tiling/checkpoint-library';library=Library.load(source)
n,v=23,34;a,b=root_after_opening(3,n,v);resolved=set();rounds=[];admitted=[]
for round_number in range(3):
    index=IndexedLibrary(library);search=AdaptiveSearch(index,n,seconds=15,max_states=150000,focus=v)
    result=search.run(a,b,max_white_turns=3)
    if result['status']=='certified':
        save_proof(search,a,b,1,out/'3x23-center.json');rounds.append(dict(search=result));break
    failures=[r for r in result['failures'] if len(r['path'])==2][:23]
    positions=[dict(a=a,b=b,path=[])]+[dict(a=int(r['a'],16),b=int(r['b'],16),path=r['path']) for r in failures]
    discovery=discover_contracts(index,n,positions,seconds=20,max_candidates=4000,tile_seconds=1,max_states=500000,focus=v,excluded=resolved)
    resolved.update((r['height'],r['width'],int(r['a'],16),int(r['b'],16)) for r in discovery['attempts'] if r['status']!='unknown')
    admitted.extend(r for r in discovery['attempts'] if r['status']=='certified')
    rounds.append(dict(search=result,discovery=discovery))
    print(dict(round=round_number,search_seconds=result['seconds'],new_tiles=len(discovery['added']),
        contracts=discovery['unique_contracts'],statuses=dict(Counter(r['status'] for r in discovery['attempts']))),flush=True)
    if not discovery['added']:break
library.save(out/'library');index=IndexedLibrary(library)
# Check that each mined contract actually solves its stated whole-board leaf.
verifications=[]
for i,entry in enumerate(admitted):
    aa,bb=a,b;actor=1
    search=AdaptiveSearch(index,n,seconds=10,max_states=150000,focus=v)
    for move_id in entry['context']['path']+[entry['context']['response']]:
        assert (aa if actor==0 else bb)>>move_id&1
        aa,bb,actor=search.child(aa,bb,actor,move_id)
    assert actor==0
    result=search.run(aa,bb,turn=0,max_white_turns=1)
    assert result['status']=='certified'
    verification=save_proof(search,aa,bb,0,out/f'contract-{i}.json',replays=5)
    verifications.append(dict(tile=entry['tile'],**verification))
search=AdaptiveSearch(index,n,seconds=30,max_states=150000,focus=v)
final=search.run(a,b,max_white_turns=4)
if final['status']=='certified':save_proof(search,a,b,1,out/'3x23-center.json')
summary=dict(format='col-adaptive-refinement-v1',source_library=str(source),rounds=rounds,admitted=admitted,
    verifications=verifications,final=final,variants=index.variant_count,
    scope='Up to three refinement rounds on the 3x23 center, tiles <=21 cells; completed three-White-turn searches and a bounded fourth-turn search. No production default changes.')
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(dict(new_tiles=len(admitted),verified_contexts=len(verifications),final_status=final['status'],
    completed_depths=final['metrics']['depths_completed'],seconds=final['seconds']),flush=True)
