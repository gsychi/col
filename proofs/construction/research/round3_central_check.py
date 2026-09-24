#!/usr/bin/env python3
"""Replay central-cap counterstrategies on actual coordinate-set boards.

No controller search is imported. White is restricted to the stated policy;
failure of that policy is not a losing-game result for the empty rectangle.
"""
from collections import deque
import gzip
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def check(path, total_width, expected_height):
    data=json.loads(gzip.decompress(path.read_bytes()))
    h,k=data['height'],data['cap_width']
    assert (h,k) == (expected_height,3)
    assert h % 2 == k % 2 == total_width % 2 == 1 and total_width >= k+2
    lo=(total_width-k)//2
    cells=frozenset((r,c) for r in range(h) for c in range(total_width))
    cap=frozenset((r,c) for r in range(h) for c in range(lo,lo+k))
    outside=cells-cap
    tau=lambda v:(h-1-v[0],total_width-1-v[1])
    local=lambda v:(v[0]*k+v[1]-lo)
    actual=lambda v:(v//k,lo+v%k)
    near=lambda v:frozenset((rr,cc) for rr,cc in
                            (v,(v[0]-1,v[1]),(v[0]+1,v[1]),(v[0],v[1]-1),(v[0],v[1]+1)))
    def move(a,b,v,white=False):
        assert v in (b if white else a)
        return (a-{v},b-near(v)) if white else (a-near(v),b-{v})
    def safe(a,b):
        return {tau(v) for v in a} & outside <= b
    nodes=data['nodes']
    queue=deque([(data['root'],cells,cells,frozenset(),frozenset())])
    seen=set(); used_nodes=set(); transitions=0; leaves=0
    while queue:
        idx,a,b,bs,ws=queue.popleft()
        key=(idx,a,b,bs,ws)
        if key in seen:continue
        seen.add(key);used_nodes.add(idx)
        node=nodes[idx]
        aa=sum(1 << local(v) for v in a & cap)
        bb=sum(1 << local(v) for v in b & cap)
        ul=sum(1 << r for r,c in bs if c == lo-1)
        ur=sum(1 << (h-1-r) for r,c in bs if c == lo+k)
        bl=sum(1 << r for r,c in bs if c == lo)
        br=sum(1 << (h-1-r) for r,c in bs if c == lo+k-1)
        assert node['state'] == [aa,bb,ul,ur,bl,br]
        assert safe(a,b)
        fixed=(h//2,total_width//2)
        assert fixed in a or not {tau(v) for v in a} <= b
        children=[]
        if node['event']=='port':
            v=(node['row'],lo+k if node['side'] else lo-1)
            u=tau(v)
            mid=move(a,b,v);end=move(*mid,u,white=True)
            children.append((node['child'],*end,bs|{v},ws|{u}))
        else:
            assert node['event']=='blue'
            v=actual(node['vertex'])
            mid=move(a,b,v)
            permitted={u for u in mid[1] & cap if safe(*move(*mid,u,white=True))}
            assert {actual(u) for u,_ in node['white']} == permitted
            assert len(node['white']) == len(permitted)
            if not permitted:leaves+=1
            for u,child in node['white']:
                u=actual(u);end=move(*mid,u,white=True)
                children.append((child,*end,bs|{v},ws|{u}))
        for child in children:
            assert 0 <= child[0] < len(nodes)
            assert len(child[1] | child[2]) < len(a | b)
            assert safe(child[1],child[2])
            transitions+=1;queue.append(child)
    assert used_nodes == set(range(len(nodes)))
    return dict(height=h,board_width=total_width,cap_width=k,
                certificate_nodes=len(nodes),actual_states=len(seen),
                transitions=transitions,policy_failure_leaves=leaves)


if __name__=='__main__':
    for h in (3,5):
        path=HERE/f'round3_central_counter_{h}_3.json.gz'
        for n in (5,7,11):
            print('VERIFIED',check(path,n,h))
    print('Every legal in-cap White reply preserving the exterior mirror invariant is covered.')
    print('These certify failure of the specified policy, not the actual empty-board game.')
