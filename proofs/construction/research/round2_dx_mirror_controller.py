"""Finite search for mirror-unless-blocked White controllers.

The strategy restriction is explicit: after every Blue move with a legal
reflected White reply, that reply is mandatory. Otherwise White chooses a
reply in the prescribed end caps. A failed search is only a failure of this
restricted policy at that finite root. No arbitrary-width conclusion follows.
"""
from functools import lru_cache
from pathlib import Path
import argparse
import gzip
import json

PATTERNS=dict(D='obwbo',X='bowob',U='wbobo',V='bwbob',R='wobob',J='owobo')


def run(width,pair,cap_width,half_turn,budget,repairs=0):
    size=5*width;full=(1<<size)-1
    closed=[];mate=[]
    for r in range(5):
        for c in range(width):
            closed.append(sum(1<<(rr*width+cc) for rr,cc in
                              [(r,c),(r-1,c),(r+1,c),(r,c-1),(r,c+1)]
                              if 0<=rr<5 and 0<=cc<width))
            mate.append((4-r if half_turn else r)*width+width-1-c)
    assert all(mate[v]!=v and mate[mate[v]]==v for v in range(size))
    a=b=full
    for c,name in [(0,pair[0]),(width-1,pair[1])]:
        for r,s in enumerate(PATTERNS[name]):
            if s not in 'ob':a&=~(1<<(r*width+c))
            if s not in 'ow':b&=~(1<<(r*width+c))
    allowed=sum(1<<(r*width+c) for r in range(5) for c in range(width)
                if c<cap_width or c>=width-cap_width)
    counters=dict(states=0,ordinary_moves=0,defect_moves=0,terminal_mirror=0)
    witness={}

    @lru_cache(None)
    def reflected(mask):
        return sum(1<<mate[v] for v in range(size) if mask>>v&1)

    @lru_cache(None)
    def white_wins(a,b,remaining):
        counters['states']+=1
        if counters['states']>budget:raise RuntimeError('budget exhausted')
        defects=reflected(a)&~b
        if not defects:
            counters['terminal_mirror']+=1
            return True
        blue_options=[v for v in range(size) if a>>v&1]
        blue_options.sort(key=lambda v:bool(b>>mate[v]&1))
        replies=[]
        for v in blue_options:
            aa=a&~closed[v];bb=b&~(1<<v)
            if bb>>mate[v]&1:
                counters['ordinary_moves']+=1
                options=[(mate[v],remaining)]
                if remaining:
                    options.extend((u,remaining-1) for u in range(size)
                                   if u!=mate[v] and (bb&allowed)&(1<<u))
            else:
                counters['defect_moves']+=1
                options=[(u,remaining) for u in range(size) if (bb & allowed) & (1<<u)]
                options.sort(key=lambda item:((reflected(aa&~(1<<item[0]))&~(bb&~closed[item[0]])).bit_count(),item[0]))
            chosen=None
            for u,next_remaining in options:
                if white_wins(aa&~(1<<u),bb&~closed[u],next_remaining):
                    chosen=u;break
            if chosen is None:
                witness[(a,b,remaining)]=dict(blue=v,white_options=options)
                return False
            replies.append((v,chosen))
        witness[(a,b,remaining)]=dict(replies=replies)
        return True

    try:answer=white_wins(a,b,repairs)
    except RuntimeError:answer='Unknown'
    root_witness=witness.get((a,b,repairs))
    result=dict(pair=pair,width=width,cap_width=cap_width,half_turn=half_turn,repairs=repairs,
                white_wins_restricted_policy=answer,counters=counters,root_witness=root_witness)
    if answer is False:
        root=(a,b,repairs);states=[root];seen={root};records=[]
        for aa,bb,remaining in states:
            record=witness[(aa,bb,remaining)];v=record['blue']
            records.append(dict(a=aa,b=bb,remaining=remaining,blue=v))
            for u,next_remaining in record['white_options']:
                child=(aa&~closed[v]&~(1<<u),bb&~(1<<v)&~closed[u],next_remaining)
                if child not in seen:seen.add(child);states.append(child)
        certificate=dict(kind='blue_counterstrategy',pair=pair,width=width,cap_width=cap_width,half_turn=half_turn,
                         repairs=repairs,root=list(root),nodes=records)
        name=f'round2_dx_mirror_counter_{pair}_{width}_{cap_width}_{int(half_turn)}_{repairs}.json.gz'
        Path(__file__).with_name(name).write_bytes(gzip.compress(json.dumps(certificate,separators=(',',':')).encode(),mtime=0))
        result['counterstrategy']=dict(file=name,nodes=len(records))
    elif answer is True:
        root=(a,b,repairs);states=[root];seen={root};records=[]
        for aa,bb,remaining in states:
            if not (reflected(aa)&~bb):
                records.append(dict(a=aa,b=bb,remaining=remaining,mirror_terminal=True))
                continue
            responses=witness[(aa,bb,remaining)]['replies']
            records.append(dict(a=aa,b=bb,remaining=remaining,replies=responses))
            for v,u in responses:
                forced_legal=(bb&~(1<<v))>>mate[v]&1
                next_remaining=remaining-int(bool(forced_legal and u!=mate[v]))
                child=(aa&~closed[v]&~(1<<u),bb&~(1<<v)&~closed[u],next_remaining)
                if child not in seen:seen.add(child);states.append(child)
        certificate=dict(kind='white_strategy',pair=pair,width=width,cap_width=cap_width,half_turn=half_turn,
                         repairs=repairs,root=list(root),nodes=records)
        name=f'round2_dx_mirror_strategy_{pair}_{width}_{cap_width}_{int(half_turn)}_{repairs}.json.gz'
        Path(__file__).with_name(name).write_bytes(gzip.compress(json.dumps(certificate,separators=(',',':')).encode(),mtime=0))
        result['strategy']=dict(file=name,nodes=len(records))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('width',type=int);p.add_argument('--pair',default='DX')
    p.add_argument('--caps',type=int,default=1);p.add_argument('--half-turn',action='store_true')
    p.add_argument('--repairs',type=int,default=0)
    p.add_argument('--budget',type=int,default=1000000);args=p.parse_args()
    result=run(args.width,args.pair,args.caps,args.half_turn,args.budget,args.repairs)
    output=Path(__file__).with_name(f'round2_dx_mirror_{args.pair}_{args.width}_{args.caps}_{int(args.half_turn)}_{args.repairs}.json')
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
