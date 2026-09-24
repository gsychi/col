#!/usr/bin/env python3
"""Reproducible experiment; does not modify production search or tablebases."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import random
import resource
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'python'))
from col.weighted_tiling import (Sources, WeightedSearch, check_result, plain_outcome,
                                neighbors, mask)

MODES = ('original', 'nonpositive', 'weighted')
KNOWN = ((3,3),(3,5),(3,7),(3,9),(3,11),(3,13),(3,15),(5,5),(5,7))


def case(h,n,a,b,turn,label,expected=None,group='opening'):
    return dict(height=h,width=n,a=hex(a),b=hex(b),turn=turn,label=label,
                expected=expected,group=group)


def arguments(c):
    return c['height'],c['width'],int(c['a'],16),int(c['b'],16),c['turn']


def opening_cases(h,n,known=True):
    full=(1<<(h*n))-1; nb=neighbors(h,n)
    return [case(h,n,full & ~((1<<v)|mask(nb[v])),full & ~(1<<v),1,
                 f'{h}x{n}/opening/{r},{c}','win' if known else None)
            for r in range((h+1)//2) for c in range((n+1)//2) for v in [r*n+c]]


def late_cases(h,n,rng,count=12):
    """Legal random playout prefixes, then independently solve both actors."""
    result=[]; seen=set(); nb=neighbors(h,n)
    for attempt in range(1000):
        a=b=(1<<(h*n))-1; turn=0
        while (a|b).bit_count()>10:
            current=a if turn==0 else b
            legal=[v for v in range(h*n) if current>>v&1]
            if not legal: break
            v=rng.choice(legal); bit=1<<v
            if turn==0: a &= ~(bit|mask(nb[v])); b &= ~bit
            else: b &= ~(bit|mask(nb[v])); a &= ~bit
            turn=1-turn
        if (a|b).bit_count()>10 or (a,b) in seen: continue
        # Small empty boards need a played position too.
        if a==b==(1<<(h*n))-1:
            v=rng.randrange(h*n); a &= ~((1<<v)|mask(nb[v])); b &= ~(1<<v)
        if (a,b) in seen: continue
        seen.add((a,b))
        for actor in (0,1):
            expected='win' if plain_outcome(h,n,a,b,actor) else 'loss'
            result.append(case(h,n,a,b,actor,f'{h}x{n}/late/{len(seen)}/{actor}',expected,'late'))
        if len(seen)==count: break
    return result


def verify_bundle(path):
    bundle=json.loads(gzip.decompress(Path(path).read_bytes()))
    if bundle['format']!='col-weighted-bound-experiment-v1': raise ValueError('Unknown format')
    sources=Sources(bundle['sources']); checked=0
    for c in bundle['cases']:
        for result in c['results'].values():
            check_result(sources,*arguments(c),result)
            if result['outcome']!='unknown':
                checked+=1
                if c['expected'] is not None and result['outcome']!=c['expected']:
                    raise ValueError('Outcome disagrees with reference: '+c['label'])
    return dict(sources=len(sources.documents),checked_results=checked,cases=len(bundle['cases']))


def run(output,repeats):
    output.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter(); sources=Sources.load(); source_seconds=time.perf_counter()-started
    engines={mode:WeightedSearch(sources,mode) for mode in MODES}
    rng=random.Random(20260905); cases=[]
    for h,n in KNOWN:
        full=(1<<(h*n))-1
        cases.append(case(h,n,full,full,0,f'{h}x{n}/empty','loss','empty'))
        cases.extend(opening_cases(h,n)); cases.extend(late_cases(h,n,rng))
    # All representative openings, not just the known missing one.
    cases.extend(opening_cases(3,19,known=False))
    for c in cases: c['results']={}
    timings={mode:[] for mode in MODES}; measurements={}; checking=0.0
    for repeat in range(repeats):
        # Rotate mode order. Certificate checking is outside query timing.
        order=MODES[repeat%3:]+MODES[:repeat%3]
        for mode in order:
            engine=engines[mode]; engine.reset_metrics(); elapsed=0
            for c in cases:
                t=time.perf_counter(); result=engine.query(*arguments(c)); elapsed+=time.perf_counter()-t
                if repeat==0:
                    t=time.perf_counter(); check_result(sources,*arguments(c),result); checking+=time.perf_counter()-t
                    if result['outcome']!='unknown' and c['expected'] is not None:
                        assert result['outcome']==c['expected'],c['label']
                    c['results'][mode]=result
                else: assert result==c['results'][mode],c['label']
            timings[mode].append(elapsed); measurements[mode]=dict(engine.metrics)
            print(f'{mode} repeat {repeat+1}: {elapsed:.3f}s, {engine.metrics["queries"]} bound queries',flush=True)
    # Checkpoint reuse is a separate experiment, so it cannot confound weights.
    t=time.perf_counter(); expanded=WeightedSearch(sources,'weighted',checkpoints=True)
    gap=next(c for c in cases if c['label']=='3x19/opening/1,7')
    result=expanded.query(*arguments(gap)); check_result(sources,*arguments(gap),result)
    gap['results']['weighted_checkpoints']=result
    expansion=dict(variants=len(expanded.variants),seconds=time.perf_counter()-t,
                   metrics=expanded.metrics,outcome=result['outcome'])
    rows=[]
    for h,n in KNOWN+((3,19),):
        selected=[c for c in cases if (c['height'],c['width'])==(h,n)]
        row=dict(board=f'{h}x{n}',modes={})
        for mode in MODES:
            bygroup={}
            for group in ('empty','opening','late'):
                groupcases=[c for c in selected if c['group']==group]
                bygroup[group]=dict(total=len(groupcases),accepted=sum(c['results'][mode]['outcome']!='unknown' for c in groupcases),
                    kinds=dict(Counter(c['results'][mode].get('kind','unknown') for c in groupcases)))
            row['modes'][mode]=bygroup
        rows.append(row)
    improvements=[c['label'] for c in cases if c['results']['weighted']['outcome']!='unknown' and c['results']['original']['outcome']=='unknown']
    compensation=[c['label'] for c in cases if c['results']['weighted']['outcome']!='unknown' and c['results']['nonpositive']['outcome']=='unknown']
    bundle=dict(format='col-weighted-bound-experiment-v1',sources=sources.documents,cases=cases,
        limitation='Numerical bound evidence only; the existing same-tile gameplay player cannot replay compensated sums.')
    artifact=output/'evidence.json.gz'
    artifact.write_bytes(gzip.compress(json.dumps(bundle,separators=(',',':')).encode(),mtime=0))
    verification=verify_bundle(artifact)
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    summary=dict(seed=20260905,repeats=repeats,source_check_seconds=source_seconds,assembly_check_seconds=checking,
        peak_process_mib=rss/(1024*1024 if sys.platform=='darwin' else 1024),
        modes={mode:dict(variants=len(engines[mode].variants),wall_seconds=timings[mode],
                        median_seconds=statistics.median(timings[mode]),metrics=measurements[mode]) for mode in MODES},
        boards=rows,new_vs_original=improvements,new_vs_nonpositive=compensation,
        missing_opening_checkpoint_probe=expansion,verification=verification,
        dfs_cutoffs=0,production_defaults_changed=False)
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    lines=['# Weighted tile experiment','',
        'This compares three palettes using the same experimental Python DP and move order. Production Rust search and its defaults are unchanged.',
        '', '`original` uses the 25 original safe roots. `nonpositive` adds signed certificates but excludes positive bounds. `weighted` permits positive tiles compensated elsewhere. All arithmetic is exact dyadic arithmetic.',
        '', '| Board | Opening probes | Original | Nonpositive | Weighted |', '|---|---:|---:|---:|---:|']
    for row in rows:
        m=row['modes']; total=m['original']['opening']['total']
        lines.append('| '+row['board']+' | '+str(total)+' | '+' | '.join(str(m[mode]['opening']['accepted']) for mode in MODES)+' |')
    lines += ['', 'Opening probes ask for a fresh proof after a representative first move. They do not restrict or invalidate an already verified empty-board strategy. The root-only palettes leave 3x19 unresolved; the other boards have known second-player results. Checkpoint reuse is tested separately below.', '',
        f'New accepted positions versus the original palette: **{len(improvements)}**. Positions requiring positive-tile compensation versus the nonpositive control: **{len(compensation)}**.', '',
        '| Mode | Variants | Bound queries | Median query wall time |', '|---|---:|---:|---:|']
    for mode in MODES:
        m=summary['modes'][mode]
        lines.append(f'| {mode} | {m["variants"]} | {m["metrics"]["queries"]} | {m["median_seconds"]:.3f}s |')
    late=[c for c in cases if c['group']=='late']
    lines += ['',f'Timings cover the same {len(cases)} positions, repeated {repeats} times, excluding source and assembly verification. They compare Python palettes, not Python against production Rust. Process peak memory was {summary["peak_process_mib"]:.1f} MiB including source checking, all modes, evidence, and checkpoint expansion; it is not a per-mode measurement.', '',
        f'Independent exact minimax checked both actors on {len(late)} late-position probes (at most 10 live cells). Every accepted result agrees. Accepted late probes: '+', '.join(f'{mode} {sum(c["results"][mode]["outcome"]!="unknown" for c in late)}/{len(late)}' for mode in MODES)+'.', '',
        f'The remaining 3x19 opening (row 1, column 7, zero-based) returns **{result["outcome"]}** for White after enabling {expansion["variants"]} reflected checked-checkpoint variants. That separate probe took {expansion["seconds"]:.3f}s.', '',
        f'The evidence recheck validates {verification["sources"]} source DAGs and {verification["checked_results"]} assembled results. Local checking took {source_seconds:.3f}s; first-pass assembly checking took {checking:.3f}s.', '',
        '**Limits:** No production DFS cutoffs were measured or enabled. This exports checkable numerical bounds, not an executable weighted game player. The old same-tile reply rule is insufficient for compensated sums. For the independently checked, executable 3x19 follow-up, see [checkpoint results](checkpoint-results.md). No all-odd-width theorem is claimed.', '',
        'Reproduce:', '', '```sh', 'python3 scripts/benchmark_weighted_tiling.py --repeats 3', 'python3 scripts/benchmark_weighted_tiling.py --verify reports/weighted-tiling/evidence.json.gz', '```', '']
    (output/'README.md').write_text('\n'.join(lines))
    print(json.dumps(dict(new_vs_original=len(improvements),new_vs_nonpositive=len(compensation),checkpoint_probe=expansion,verification=verification),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/weighted-tiling')
    parser.add_argument('--repeats',type=int,default=3)
    parser.add_argument('--verify',type=Path)
    args=parser.parse_args()
    if args.verify: print(json.dumps(verify_bundle(args.verify),indent=2))
    else:
        if args.repeats<1: parser.error('--repeats must be positive')
        run(args.output,args.repeats)
