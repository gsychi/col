#!/usr/bin/env python3
"""Discovery: a central cap with half-turn paired outside ports.

This searches a sufficient finite controller problem, not arbitrary Col play.
A positive answer needs an independent response certificate and symbolic lift.
"""
from functools import lru_cache
from pathlib import Path
import argparse
import gzip
import json


def run(height, width, budget, export=False):
    assert height % 2 == width % 2 == 1 and width >= 3
    size = height * width
    full = (1 << size) - 1
    center = 1 << (size // 2)
    closed = []
    for v in range(size):
        r, c = divmod(v, width)
        closed.append(sum(1 << (rr * width + cc) for rr, cc in
                          [(r,c),(r-1,c),(r+1,c),(r,c-1),(r,c+1)]
                          if 0 <= rr < height and 0 <= cc < width))
    interior = sum(1 << v for v in range(size) if 0 < v % width < width - 1)
    ports = [(r, side, r * width + (width - 1 if side else 0))
             for r in range(height) for side in (0,1)]
    counts = dict(states=0, mirror_terminals=0, port_events=0, cap_moves=0)
    records = {}

    @lru_cache(None)
    def reflect(mask):
        return sum(1 << (size - 1 - v) for v in range(size) if mask >> v & 1)

    @lru_cache(None)
    def win(a, b, used_l=0, used_r=0, blocked_l=0, blocked_r=0):
        counts['states'] += 1
        if counts['states'] > budget:
            raise RuntimeError('budget exhausted')
        state = (a,b,used_l,used_r,blocked_l,blocked_r)
        if not (a & center) and not (reflect(a) & ~b):
            counts['mirror_terminals'] += 1
            return True
        used = used_l | used_r
        for row, side, v in ports:
            paired = height - 1 - row if side else row
            bit = 1 << paired
            own = used_r if side else used_l
            blocked = blocked_r if side else blocked_l
            if used & bit or blocked & bit or own & ((bit << 1) | (bit >> 1)):
                continue
            counts['port_events'] += 1
            child = (a & ~(1 << v), b & ~(1 << (size-1-v)),
                     used_l | (bit if not side else 0),
                     used_r | (bit if side else 0), blocked_l, blocked_r)
            if not win(*child):
                records[state] = dict(event='port',row=row,side=side,child=child)
                return False
        special = interior
        for row, side, v in ports:
            paired = height - 1 - row if side else row
            bit = 1 << paired
            opposite_used = used_l if side else used_r
            opposite_blocked = blocked_l if side else blocked_r
            # A nonmirror reply is also safe when the reflected exterior
            # BLUE permission is already absent. It may remove an exterior
            # White permission, but cannot create a mirror defect there.
            if (used & bit or opposite_blocked & bit or
                    opposite_used & ((bit << 1) | (bit >> 1))):
                special |= 1 << v
        blue = [v for v in range(size) if a >> v & 1]
        blue.sort(key=lambda v: (v != size//2, bool(b >> (size-1-v) & 1)))
        responses = []
        for v in blue:
            counts['cap_moves'] += 1
            aa, bb = a & ~closed[v], b & ~(1 << v)
            bl, br = blocked_l, blocked_r
            row, col = divmod(v, width)
            if col == 0:
                bl |= 1 << row
            if col == width - 1:
                br |= 1 << (height-1-row)
            options = [u for u in range(size) if bb & special & (1 << u)]
            mate = size - 1 - v
            if bb >> mate & 1:
                options = [mate] + [u for u in options if u != mate]
            chosen = None
            for u in options:
                child = (aa & ~(1 << u), bb & ~closed[u], used_l,used_r,bl,br)
                if win(*child):
                    chosen = u
                    break
            if chosen is None:
                records[state] = dict(event='blue',vertex=v,white_options=options)
                return False
            responses.append([v,chosen])
        records[state] = dict(replies=responses)
        return True

    root = (full,full,0,0,0,0)
    try:
        answer = win(*root)
    except RuntimeError:
        answer = 'Unknown'
    state = root
    prefix = []
    while state in records and records[state].get('event') == 'port':
        rec = records[state]
        prefix.append([rec['row'],rec['side']])
        state = tuple(rec['child'])
    if export and answer is False:
        states = [root]
        indices = {root:0}
        nodes = []
        def intern(child):
            child = tuple(child)
            if child not in indices:
                indices[child] = len(states)
                states.append(child)
            return indices[child]
        for st in states:
            rec = records[st]
            node = dict(state=list(st),event=rec['event'])
            if rec['event'] == 'port':
                node.update(row=rec['row'],side=rec['side'],child=intern(rec['child']))
            else:
                v = rec['vertex']
                a,b,ul,ur,bl,br = st
                row,col=divmod(v,width)
                if col == 0:bl |= 1 << row
                if col == width-1:br |= 1 << (height-1-row)
                node.update(vertex=v,white=[])
                for u in rec['white_options']:
                    child=(a & ~closed[v] & ~(1 << u),b & ~(1 << v) & ~closed[u],ul,ur,bl,br)
                    node['white'].append([u,intern(child)])
            nodes.append(node)
        certificate=dict(height=height,cap_width=width,root=0,nodes=nodes,
                         claim='Blue defeats the stated central-cap safe-mirror controller')
        path=Path(__file__).with_name(f'round3_central_counter_{height}_{width}.json.gz')
        path.write_bytes(gzip.compress(json.dumps(certificate,separators=(',',':')).encode(),mtime=0))
    return dict(height=height,cap_width=width,budget=budget,
                white_wins_controller=answer,counts=counts,
                initial_port_prefix=prefix,first_nonport_witness=records.get(state))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('height',type=int)
    parser.add_argument('width',type=int)
    parser.add_argument('--budget',type=int,default=500000)
    parser.add_argument('--export',action='store_true')
    args=parser.parse_args()
    result=run(args.height,args.width,args.budget,args.export)
    dest=Path(__file__).with_name(f'round3_central_{args.height}_{args.width}.json')
    dest.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
