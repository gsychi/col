"""Finite adversarial-port discovery for a uniform two-end mirror controller.

The two caps are disjoint 5 x k rectangles. External mirrored play may delete
A(v), B(tau(v)) at any inward port v. Nonmirror White replies are restricted
away from inward ports, so they create no new exterior mirror defect.
A positive result is only discovery until a supplied strategy is independently
checked against the symbolic interface lemma. A negative result is confined
to this adversarial abstraction, not to the actual DX game.
"""
from functools import lru_cache
from pathlib import Path
import argparse
import json


def run(k,half_turn,budget,legal_ports=False):
    width=2*k;size=5*width;full=(1<<size)-1
    closed=[];mate=[]
    for r in range(5):
        for c in range(width):
            side=c//k
            closed.append(sum(1<<(rr*width+cc) for rr,cc in
                              [(r,c),(r-1,c),(r+1,c),(r,c-1),(r,c+1)]
                              if 0<=rr<5 and 0<=cc<width and cc//k==side))
            mate.append((4-r if half_turn else r)*width+width-1-c)
    ports=[r*width+c for r in range(5) for c in (k-1,k)]
    special=sum(1<<v for v in range(size) if v not in ports)
    a=b=full
    for c,pattern in [(0,'obwbo'),(width-1,'bowob')]:
        for r,s in enumerate(pattern):
            if s not in 'ob':a&=~(1<<(r*width+c))
            if s not in 'ow':b&=~(1<<(r*width+c))
    counts=dict(states=0,port_events=0,cap_openings=0,mirror_terminals=0)
    records={}

    @lru_cache(None)
    def reflect(mask):return sum(1<<mate[v] for v in range(size) if mask>>v&1)

    @lru_cache(None)
    def white_wins(a,b,left_used=0,right_used=0):
        counts['states']+=1
        if counts['states']>budget:raise RuntimeError('budget exhausted')
        defects=reflect(a)&~b
        if not defects:
            counts['mirror_terminals']+=1
            return True
        for v in ports:
            row=v//width;side=int(v%width==k)
            pair_row=4-row if half_turn and side else row
            marker=1<<pair_row
            if legal_ports:
                if (left_used|right_used)&marker:continue
                own=right_used if side else left_used
                if own&((marker<<1)|(marker>>1)):continue
            child=(a&~(1<<v),b&~(1<<mate[v]))
            if child==(a,b) and not legal_ports:continue
            next_left=left_used|(marker if not side else 0) if legal_ports else 0
            next_right=right_used|(marker if side else 0) if legal_ports else 0
            counts['port_events']+=1
            if not white_wins(*child,next_left,next_right):
                records[(a,b,left_used,right_used)]=dict(event='port',vertex=v,next_left=next_left,next_right=next_right)
                return False
        blue=[v for v in range(size) if a>>v&1]
        blue.sort(key=lambda v:bool(b>>mate[v]&1))
        responses=[]
        available_special=special
        if legal_ports:
            for port in ports:
                pr=port//width;pside=int(port%width==k)
                paired=4-pr if half_turn and pside else pr
                if (left_used|right_used)&(1<<paired):available_special|=1<<port
        for v in blue:
            counts['cap_openings']+=1
            aa=a&~closed[v];bb=b&~(1<<v)
            options=[u for u in range(size) if bb&available_special&(1<<u)]
            if bb>>mate[v]&1:
                options=[mate[v]]+[u for u in options if u!=mate[v]]
            chosen=None
            for u in options:
                if white_wins(aa&~(1<<u),bb&~closed[u],left_used,right_used):
                    chosen=u;break
            if chosen is None:
                records[(a,b,left_used,right_used)]=dict(event='blue',vertex=v,white_options=options)
                return False
            responses.append([v,chosen])
        records[(a,b,left_used,right_used)]=dict(replies=responses)
        return True

    try:answer=white_wins(a,b)
    except RuntimeError:answer='Unknown'
    prefix=[];state=(a,b,0,0)
    while state in records and records[state].get('event')=='port':
        v=records[state]['vertex'];prefix.append([v//width,v%width])
        state=(state[0]&~(1<<v),state[1]&~(1<<mate[v]),records[state]['next_left'],records[state]['next_right'])
    return dict(cap_width=k,half_turn=half_turn,legal_ports=legal_ports,white_wins_abstract_controller=answer,
                counts=counts,initial_losing_port_prefix=prefix,first_nonport_witness=records.get(state))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('cap_width',type=int)
    p.add_argument('--half-turn',action='store_true');p.add_argument('--budget',type=int,default=1000000)
    p.add_argument('--legal-ports',action='store_true')
    args=p.parse_args();result=run(args.cap_width,args.half_turn,args.budget,args.legal_ports)
    Path(__file__).with_name(f'round2_dx_caps_{args.cap_width}_{int(args.half_turn)}_{int(args.legal_ports)}.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
