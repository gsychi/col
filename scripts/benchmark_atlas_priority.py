#!/usr/bin/env python3
"""Reproduce matched 3x23 atlas ablations and independently check every cutoff."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'python'))
from col.adaptive_tiling import (AdaptiveSearch, IndexedLibrary, extract_checkpoint,
                                 resolve_contract)
from col.atlas import Atlas, LocalBound
from col.certificate_types import ConstructionRejected, Unknown
from col.tiling import Library, check_report, mask, neighbors, to_columns
from adaptive_tiling_research import root_after_opening, save_proof


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n')


def cases(out):
    path=ROOT/'reports/adaptive-tiling/final/summary.json';history=json.loads(path.read_text())
    a,b=root_after_opening(3,23,34)
    positions=[dict(id='center-depth3',a=hex(a),b=hex(b),turn=1,path=[],white_turns=3,seconds=30),
               dict(id='center-depth4-budget',a=hex(a),b=hex(b),turn=1,path=[],white_turns=4,seconds=10)]
    seen={(a,b)}
    sources=[r['search']['failures'] for r in history['rounds']]+[history['final']['failures']]
    for batch,rows in enumerate(sources):
        added=0
        for i,row in enumerate(rows):
            key=int(row['a'],16),int(row['b'],16)
            if key in seen:continue
            seen.add(key);added+=1
            positions.append(dict(id=f'recorded-{batch}-{i}',a=row['a'],b=row['b'],turn=row['turn'],path=row['path'],
                                  white_turns=row['white_turns'],seconds=10))
            if added==4:break
    # Check recorded positions really follow the specified alternating path.
    nb=[mask(s) for s in neighbors(3,23)]
    for row in positions:
        aa,bb=a,b;turn=1
        for v in row['path']:
            actual=[aa,bb];assert actual[turn]>>v&1
            actual[turn]&=~((1<<v)|nb[v]);actual[1-turn]&=~(1<<v)
            aa,bb=actual;turn=1-turn
        assert (aa,bb,turn)==(int(row['a'],16),int(row['b'],16),row['turn'])
    contracts=[];seen=set()
    for batch in history['rounds']:
        for row in batch['discovery']['attempts']:
            key=row['height'],row['width'],row['a'],row['b']
            if key in seen:continue
            seen.add(key);contracts.append({k:row[k] for k in ('height','width','a','b','context','status')})
    result=dict(format='col-atlas-benchmark-cases-v1',source=str(path.relative_to(ROOT)),
        source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),positions=positions,contracts=contracts,
        selection='Center at depth 3 and bounded depth 4; first four distinct failed positions from each of three recorded rounds and final search.',
        cache_policy='Fresh adaptive memo and empty 100000-entry local match LRU per case and repetition; no outcome cache reused.',
        max_states=150000)
    write(out/'cases.json',result);return result


def report(library,cutoffs):
    return dict(format='col-tiling-proof-v1',height=3,width=23,columns=[[0,0] for _ in range(23)],turn=0,
        outcome='unknown',witness=None,response=None,openings=[],uncovered=[],library=library,cutoffs=cutoffs,
        metrics=dict(queries=0,matching_tiles=0,successful_covers=len(cutoffs),dfs_cutoffs=0,query_seconds=0))


def verify_rust(value):
    with tempfile.TemporaryDirectory(prefix='col-atlas-check-') as directory:
        path=Path(directory)/'proof.json';path.write_text(json.dumps(value,separators=(',',':')))
        run=subprocess.run([str(ROOT/'solver/target/release/col-cert'),'verify',str(path)],check=True,capture_output=True,text=True,timeout=120)
    return run.stdout.strip()


def checked_leaves(search):
    """Check ALL accepted tiling cutoffs, including genuine counterproof leaves."""
    library=Library([]);converted={};leaves=[]
    for store in (search.nodes,search.refutations):
        for (a,b,actor),node in store.items():
            if node['kind']!='tiling':continue
            blocks=[]
            for p in node['cover']['blocks']:
                key=p['source'],tuple(p['checkpoint'])
                if key not in converted:
                    doc=extract_checkpoint(search.index.library,*key)
                    converted[key]=library.add(doc)[0]
                blocks.append(dict(start_column=p['start_column'],tile=converted[key],row_flip=p['row_flip'],column_flip=p['column_flip']))
            sets=[{v for v in range(69) if m>>v&1} for m in (a,b)]
            leaves.append(dict(columns=to_columns(3,23,*sets),turn=actor,response=None,witness=dict(blocks=blocks)))
    value=report(list(library.tiles.values()),leaves);check_report(value)
    rust=verify_rust(value)
    return dict(leaves=len(leaves),source_checkpoints=len(converted),rust=rust)


def worker(args):
    out=args.out;manifest=json.loads((out/'cases.json').read_text());arm=args.worker
    started=time.perf_counter();base=Library.load(ROOT/'reports/adaptive-tiling/final/library');atlas=None
    if arm!='baseline':atlas=Atlas(ROOT/'proofs/atlas',ROOT/'proofs/atlas-review')
    library=atlas.library(3,base) if atlas else base
    source_seconds=time.perf_counter()-started
    t=time.perf_counter();index=IndexedLibrary(library);index_seconds=time.perf_counter()-t
    print(f'{arm}: {len(library.tiles)} DAGs, {index.variant_count} variants; prepare {source_seconds+index_seconds:.2f}s',flush=True)
    result=dict(arm=arm,source_seconds=source_seconds,index_seconds=index_seconds,
        atlas_verification=atlas.verification if atlas else None,variants=index.variant_count,
        two_direction=arm=='atlas-dual',zero_promotion=arm=='atlas-dual',runs=[])
    arm_dir=out/arm;arm_dir.mkdir(parents=True,exist_ok=True)
    # Independent Rust checker sees EVERY grid source, even those of other heights.
    if atlas and arm=='atlas-dual':
        all_sources=[dict(id=rel,source_sha256=s.sha256,doc=s.doc) for rel,s in atlas.sources.items()]
        result['rust_all_grid_sources']=verify_rust(report(all_sources,[]))
        write(arm_dir/'provenance.json',dict(format='col-atlas-import-provenance-v1',
            verification=atlas.verification,tiles=[{k:v for k,v in t.items() if k!='doc'} for t in library.tiles.values()]))
    for repeat in range(args.repeats):
        for row in manifest['positions']:
            index.matches_cache.clear()
            for k in index.metrics:index.metrics[k]=0
            a,b=int(row['a'],16),int(row['b'],16);turn=row['turn']
            search=AdaptiveSearch(index,23,seconds=row['seconds'],max_states=manifest['max_states'],focus=34,
                                  two_direction=arm=='atlas-dual',zero_promotion=arm=='atlas-dual')
            record=search.run(a,b,turn,max_white_turns=row['white_turns'])
            record.pop('failures');record.update(case=row['id'],repeat=repeat)
            # A completed prefix can prove either player; inspect every recorded
            # outcome, then Rust independently checks every accepted leaf once.
            if repeat==0:
                record['cutoff_verification']=checked_leaves(search)
                if record['status']!='unknown':
                    record['verification']=save_proof(search,a,b,turn,arm_dir/(row['id']+'.json'),replays=20)
                if arm=='atlas-dual':
                    # Replay one propagated/direct actual counterstrategy even
                    # when the search's requested root itself stays Unknown.
                    candidate=next((key for key,node in search.refutations.items() if node['kind']=='choice'),None)
                    if candidate is None:candidate=next(iter(search.refutations),None)
                    if candidate:
                        record['counterstrategy_verification']=save_proof(search,*candidate,
                            arm_dir/(row['id']+'-counterstrategy.json'),replays=10)
            result['runs'].append(record)
            print(f"{arm} {repeat} {row['id']}: {record['status']} {record['seconds']:.4f}s visits={record['metrics']['states']} refutation_cutoffs={record['metrics']['actual_refutation_cutoffs']}",flush=True)
            write(arm_dir/'summary.json',result)
    if atlas:
        t=time.perf_counter();counts=Counter();eligible=0;avoided=0
        for row in manifest['contracts']:
            h,w=row['height'],row['width'];a,b=int(row['a'],16),int(row['b'],16)
            eligible+=int(a==(1<<(h*w))-1)
            answer=atlas.classify(h,w,a,b)
            counts[type(answer).__name__]+=1
            avoided+=int(not isinstance(answer,Unknown))
        result['recorded_contract_classification']=dict(queries=len(manifest['contracts']),full_first_eligible=eligible,
            answers=dict(counts),minimax_calls_avoidable=avoided,seconds=time.perf_counter()-t,
            unsafe_witness_scans=atlas.metrics['unsafe_witness_scans'])
    # Identical bounded minimax obligations: first 64 recorded local contracts.
    local=[]
    for row in manifest['contracts'][:64]:
        doc,stats=resolve_contract(row['height'],row['width'],int(row['a'],16),int(row['b'],16),
                                  atlas=atlas,state_limit=25000,seconds=.05)
        local.append(dict(height=row['height'],width=row['width'],a=row['a'],b=row['b'],**stats))
    result['local_minimax_probe']=dict(limits=dict(seconds=.05,states=25000,cases=64),records=local)
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result['peak_process_mib']=rss/(1024*1024 if sys.platform=='darwin' else 1024)
    result['memory_scope']='Whole isolated worker including atlas verification, indexes, search and independent Python proof checking; Rust child excluded.'
    write(arm_dir/'summary.json',result)


def main(args):
    args.out.mkdir(parents=True,exist_ok=True);cases(args.out)
    for arm in ('baseline','atlas-one-direction','atlas-dual'):
        subprocess.run([sys.executable,__file__,'--out',str(args.out),'--worker',arm,'--repeats',str(args.repeats)],check=True)
    results=[json.loads((args.out/arm/'summary.json').read_text()) for arm in ('baseline','atlas-one-direction','atlas-dual')]
    write(args.out/'summary.json',dict(format='col-atlas-priority-benchmark-v1',repeats=args.repeats,arms=results,
        limitation='Fixed-budget deeper runs measure coverage/throughput, not a reduction in a completed search DAG. Unknown is never a game outcome. Local construction rejection is never a board refutation.'))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'reports/atlas-priority')
    parser.add_argument('--repeats',type=int,default=3)
    parser.add_argument('--worker',choices=['baseline','atlas-one-direction','atlas-dual'])
    args=parser.parse_args()
    worker(args) if args.worker else main(args)
