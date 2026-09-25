#!/usr/bin/env python3
"""Check/replay proof artifacts and search only missing, bounded local games."""
import argparse
import json
import resource
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
from col.tiling import (Library, Strategy, check_report, check_witness, generate_tile,
                        mask, neighbors, to_columns, InvalidCertificate)


def opening_states(h,n,opening):
    full=(1<<(h*n))-1;nb=[mask(s) for s in neighbors(h,n)]
    a=full&~((1<<opening)|nb[opening]);b=full&~(1<<opening)
    for response in range(h*n):
        if b>>response&1:
            yield response,a&~(1<<response),b&~((1<<response)|nb[response])


def coverage(lib,h,n):
    full=(1<<(h*n))-1
    direct=lib.plan(h,n,full,full)
    if direct is not None:
        check_witness(h,to_columns(h,n,set(range(h*n)),set(range(h*n))),0,direct,lib.tiles)
        return dict(board=f'{h}x{n}',direct=True,covered_representatives=(h+1)//2*((n+1)//2),uncovered=[])
    missing=[];covered=0
    for r in range((h+1)//2):
        for c in range((n+1)//2):
            for response,a,b in opening_states(h,n,r*n+c):
                w=lib.plan(h,n,a,b)
                if w is not None:
                    check_witness(h,to_columns(h,n,{v for v in range(h*n) if a>>v&1},{v for v in range(h*n) if b>>v&1}),0,w,lib.tiles)
                    covered+=1;break
            else:missing.append([r,c])
    return dict(board=f'{h}x{n}',direct=False,covered_representatives=covered,uncovered=missing)


def bridge_candidates(lib,h,n,opening,max_cells,deadline):
    """Insert one missing tile between certified prefixes and suffixes.

    Its Blue mask is the exact local permission set. Its White permissions
    exclude boundary rows that conflict with either certified neighbor.
    """
    for response,a,b in opening_states(h,n,opening):
        if time.monotonic()>=deadline:return
        dp,suffix=lib.boundaries(h,n,a,b)
        for w in range(min(n,max_cells//h),0,-1):
            for c in range(n-w+1):
                if not dp[c] or not suffix[c+w]:continue
                aa,bb=lib.extract(h,n,c,w,a,b)
                for left in sorted(dp[c]):
                    for right in sorted(suffix[c+w]):
                        forbidden=sum((1<<(r*w) if left>>r&1 else 0) | (1<<(r*w+w-1) if right>>r&1 else 0) for r in range(h))
                        yield (h,w,aa,bb&~forbidden),dict(opening=opening,response=response,start_column=c,left=left,right=right)


def seed_candidates(h,max_cells,deadline):
    # Full Blue permissions are useful repeated blocks; enumerate only White
    # endpoint restrictions, never all 4^(h*w) arbitrary tinted positions.
    for w in range(1,max_cells//h+1):
        full=(1<<(h*w))-1
        for left in range(1<<h):
            for right in range(1<<h):
                if time.monotonic()>=deadline:return
                forbidden=0
                for r in range(h):
                    if left>>r&1:forbidden|=1<<(r*w)
                    if right>>r&1:forbidden|=1<<(r*w+w-1)
                yield (h,w,full,full&~forbidden),dict(seed=True,left=left,right=right)


def discover(args):
    started=time.monotonic();lib=Library.load(args.library)
    output=Path(args.out).resolve()
    source=Path(args.library).resolve()
    if output==source or source.is_relative_to(output) or output.is_relative_to(source):
        raise ValueError('discovery output must be separate from the source library')
    records=[];boards=[];seen=set();attempts=0
    # Each board gets its own bounded discovery budget so a hard strip cannot
    # prevent the taller-board pilot from running.
    for label in args.boards:
        h,n=map(int,label.lower().split('x'));h,n=sorted((h,n))
        if not (1<=h<=7 and n>0):raise ValueError('height must be 1..7')
        before=coverage(lib,h,n);deadline=time.monotonic()+args.seconds
        board_attempts=0;added=0;current=before
        while time.monotonic()<deadline and board_attempts<args.max_candidates:
            gaps=current['uncovered']
            if not gaps:break
            candidates=[bridge_candidates(lib,h,n,r*n+c,args.max_tile_cells,deadline) for r,c in gaps]
            if h != 3:
                candidates.append(seed_candidates(h,args.max_tile_cells,deadline))
            admitted=False
            for group in candidates:
                for key,context in group:
                    if key in seen:continue
                    if time.monotonic()>=deadline or board_attempts>=args.max_candidates:break
                    seen.add(key);hh,w,a,b=key
                    if any(v[:4]==(hh,w,a,b) for v in lib.variants):continue
                    doc,metrics=generate_tile(hh,w,a,b,args.max_states,min(args.tile_seconds,max(0.001,deadline-time.monotonic())))
                    board_attempts+=1;attempts+=1
                    entry=dict(board=label,height=hh,width=w,blue_mask=a,white_mask=b,context=context,**metrics)
                    if doc is not None:
                        name,_,_=lib.add(doc);entry['tile']=name;added+=1;admitted=True
                    records.append(entry)
                    if admitted:break
                if admitted or time.monotonic()>=deadline or board_attempts>=args.max_candidates:break
            if not admitted:break
            current=coverage(lib,h,n)
        after=current
        boards.append(dict(before=before,after=after,attempts=board_attempts,admitted_tiles=added))
        print(json.dumps(boards[-1]),flush=True)
    lib.save(output/'library')
    result=dict(format='col-tiling-discovery-v1',boards=boards,attempts=records,
                limits=dict(seconds_per_board=args.seconds,tile_seconds=args.tile_seconds,max_states=args.max_states,max_candidates_per_board=args.max_candidates,max_tile_cells=args.max_tile_cells),
                elapsed_seconds=time.monotonic()-started,peak_rss_native=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                peak_rss_units='bytes' if sys.platform=='darwin' else 'KiB',
                claim='Finite checked tiles and covers only; unresolved cases remain unknown.')
    (output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f"Saved {output/'report.json'} and verified tile library")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    v=sub.add_parser('verify-python');v.add_argument('proof',type=Path)
    p=sub.add_parser('replay');p.add_argument('proof',type=Path);p.add_argument('--moves',type=int,nargs='*',default=[])
    d=sub.add_parser('discover')
    d.add_argument('--library',type=Path,default=ROOT/'proofs/3x15')
    d.add_argument('--out',type=Path,required=True)
    d.add_argument('--boards',nargs='+',default=['3x19','3x23','3x27','3x31','5x9','7x7'])
    d.add_argument('--seconds',type=float,default=30)
    d.add_argument('--tile-seconds',type=float,default=1)
    d.add_argument('--max-states',type=int,default=100000)
    d.add_argument('--max-candidates',type=int,default=200)
    d.add_argument('--max-tile-cells',type=int,default=21)
    args=parser.parse_args()
    if args.command=='discover':
        if min(args.seconds,args.tile_seconds,args.max_states,args.max_candidates,args.max_tile_cells)<=0 or args.max_tile_cells>63:
            parser.error('budgets must be positive; max tile cells must be <=63')
        discover(args);return
    report=json.loads(args.proof.read_text())
    if args.command=='verify-python':
        check_report(report)
        print(f"VERIFIED: {report['height']}x{report['width']} {report['outcome']} (side to move)")
    else:
        strategy=Strategy(report)
        if strategy.initial_response is not None:
            print(f'Initial P{strategy.winner+1} move: {strategy.initial_response}')
        for v in args.moves:
            print(f'Opponent {v} -> P{strategy.winner+1} {strategy.reply(v)}')
        print(json.dumps(dict(winner=strategy.winner+1,finished=not strategy.legal_opponent_moves,legal_opponent_moves=strategy.legal_opponent_moves)))

if __name__=='__main__':
    try:main()
    except (InvalidCertificate,ValueError,KeyError,TypeError,OSError) as error:
        raise SystemExit(f'INVALID: {error}')
