#!/usr/bin/env python3
"""Try short adaptive strategies and mine only concrete missing tile contracts."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import random
import resource
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'python'))
from col.adaptive_tiling import (Library,IndexedLibrary,AdaptiveSearch,AdaptivePlayer,
    check_adaptive,discover_contracts,mask,neighbors,to_columns)
from col.tiling import check_report


def root_after_opening(h,n,v):
    full=(1<<(h*n))-1
    return full&~((1<<v)|mask(neighbors(h,n)[v])),full&~(1<<v)


def leaf_report(proof):
    h,n=proof['height'],proof['width'];root=proof['root']
    def columns(a,b):
        return to_columns(h,n,*({v for v in range(h*n) if int(m,16)>>v&1} for m in (a,b)))
    leaves=[dict(columns=columns(row['a'],row['b']),turn=row['turn'],response=None,witness=row['witness'])
            for row in proof['nodes'] if row['kind']=='tiling']
    return dict(format='col-tiling-proof-v1',height=h,width=n,columns=columns(*root[:2]),turn=root[2],
        outcome='unknown',witness=None,response=None,openings=[],uncovered=[],library=proof['library'],cutoffs=leaves,
        metrics=dict(queries=0,matching_tiles=0,successful_covers=len(leaves),dfs_cutoffs=0,query_seconds=0))


def save_proof(search,a,b,turn,path,replays=100):
    proof=search.artifact(a,b,turn);checked=check_adaptive(proof)
    path.write_text(json.dumps(proof,separators=(',',':'))+'\n')
    # Cross-check all local DAGs and leaf assemblies with production Rust.
    leaves=leaf_report(proof);check_report(leaves);leaf_path=path.with_name(path.stem+'-leaves.json')
    leaf_path.write_text(json.dumps(leaves,separators=(',',':'))+'\n')
    result=subprocess.run([str(ROOT/'solver/target/release/col-cert'),'verify',str(leaf_path)],capture_output=True,text=True,check=True,timeout=30)
    rng=random.Random(230019);games=0;moves=0
    for swapped in (False,True):
        current=copy.deepcopy(proof)
        if swapped:
            current['winner']=1-current['winner'];x,y,t=current['root'];current['root']=[y,x,1-t]
            for row in current['nodes']:row['a'],row['b'],row['turn']=row['b'],row['a'],1-row['turn']
        check_adaptive(current)
        for trial in range(replays):
            game=AdaptivePlayer(current,checked=True)
            if game.turn==game.winner:game.response()
            while game.legal_moves:game.opponent(rng.choice(game.legal_moves))
            if game.turn==game.winner:raise AssertionError('Winner ran out of moves')
            games+=1;moves+=len(game.history)
    return dict(**checked,replay_games=games,replay_moves=moves,rust_leaf_verifier=result.stdout.strip())


def run(args):
    out=args.out;out.mkdir(parents=True,exist_ok=True)
    t=time.perf_counter();library=Library.load(args.library);source_seconds=time.perf_counter()-t
    atlas=None
    if args.atlas:
        from col.atlas import Atlas
        atlas=Atlas(args.atlas,args.atlas_review);library=atlas.library(3,library)
    t=time.perf_counter();index=IndexedLibrary(library);index_seconds=time.perf_counter()-t
    proof_options=dict(two_direction=bool(atlas or args.two_direction),zero_promotion=bool(atlas or args.two_direction))
    print(f'Checked {len(library.tiles)} source DAGs; indexed {index.variant_count} checkpoint variants.',flush=True)
    controls=[]
    for label,n,opening in [('3x13-empty',13,None),('3x19-opening26',19,26)]:
        a,b=root_after_opening(3,n,opening) if opening is not None else ((1<<(3*n))-1,)*2
        turn=1 if opening is not None else 0
        search=AdaptiveSearch(index,n,seconds=10,focus=opening,**proof_options)
        record=search.run(a,b,turn,max_white_turns=2);record['case']=label
        if record['status']!='certified':raise AssertionError('Known control failed: '+label)
        record['verification']=save_proof(search,a,b,turn,out/(label+'.json'),replays=20)
        controls.append(record);print(f'{label}: certified in {record["seconds"]:.4f}s',flush=True)
    n,v=23,34;a,b=root_after_opening(3,n,v)
    before_index_metrics=dict(index.metrics)
    search=AdaptiveSearch(index,n,seconds=args.seconds,max_states=args.max_states,focus=v,**proof_options)
    before=search.run(a,b,max_white_turns=args.white_turns)
    before['oracle']={k:index.metrics[k]-before_index_metrics[k] for k in index.metrics}
    print(f'3x23 before discovery: {before["status"]}; {before["seconds"]:.3f}s; completed depths {before["metrics"]["depths_completed"]}',flush=True)
    (out/'before.json').write_text(json.dumps(before,indent=2)+'\n')
    discovery=None;after=None;verification=None
    if before['status'] in ('certified','refuted'):verification=save_proof(search,a,b,1,out/'3x23-center.json')
    else:
        positions=[dict(a=a,b=b,path=[])]+[dict(a=int(r['a'],16),b=int(r['b'],16),path=r['path']) for r in before['failures'][:12]]
        discovery=discover_contracts(index,n,positions,seconds=args.discovery_seconds,max_candidates=args.max_candidates,
            tile_seconds=args.tile_seconds,max_states=args.tile_states,focus=v,atlas=atlas)
        library.save(out/'library');(out/'discovery.json').write_text(json.dumps(discovery,indent=2)+'\n')
        print(f'Discovery: {len(discovery["added"])} checked tiles; '+str(dict(Counter(r['status'] for r in discovery['attempts']))),flush=True)
        if discovery['added']:
            t=time.perf_counter();index=IndexedLibrary(library);reindex_seconds=time.perf_counter()-t
            search=AdaptiveSearch(index,n,seconds=args.seconds,max_states=args.max_states,focus=v,**proof_options)
            after=search.run(a,b,max_white_turns=args.white_turns);after['index_seconds']=reindex_seconds
            if after['status'] in ('certified','refuted'):verification=save_proof(search,a,b,1,out/'3x23-center.json')
            print(f'3x23 after discovery: {after["status"]}; {after["seconds"]:.3f}s',flush=True)
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    summary=dict(format='col-adaptive-experiment-v1',source_library=str(args.library),
        source_seconds=source_seconds,index_seconds=index_seconds,checkpoint_variants=index.variant_count,
        controls=controls,before=before,discovery=discovery,after=after,verification=verification,
        atlas_verification=atlas.verification if atlas else None,
        peak_process_mib=rss/(1024*1024 if sys.platform=='darwin' else 1024),
        limits=dict(seconds_per_search=args.seconds,max_expanded_states=args.max_states,max_white_turns=args.white_turns),
        limitation='Bounded certificate search only. Unknown and rejected tile contracts are not whole-board outcomes. Rust verifies tile DAGs and leaf assemblies; Python verifies the full adaptive prefix.')
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--library',type=Path,default=ROOT/'reports/weighted-tiling/checkpoint-library')
    p.add_argument('--out',type=Path,default=ROOT/'reports/adaptive-tiling/reproducible')
    p.add_argument('--atlas',type=Path,help='Check and import a role-relative grid atlas before searching')
    p.add_argument('--atlas-review',type=Path,help='Optional checked exact-zero export package')
    p.add_argument('--two-direction',action='store_true',help='Also prove actual White losses and promote actual subset-zero matches; implied by --atlas')
    p.add_argument('--seconds',type=float,default=30)
    p.add_argument('--max-states',type=int,default=150000)
    p.add_argument('--white-turns',type=int,default=4)
    p.add_argument('--discovery-seconds',type=float,default=35)
    p.add_argument('--max-candidates',type=int,default=4000)
    p.add_argument('--tile-seconds',type=float,default=.6)
    p.add_argument('--tile-states',type=int,default=150000)
    p.add_argument('--verify',type=Path)
    args=p.parse_args()
    if args.verify:print(json.dumps(check_adaptive(json.loads(args.verify.read_text())),indent=2))
    else:run(args)
