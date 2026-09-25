"""Independent set-based checker for bounded proactive-repair mirror DAGs.

No strategy search, minimax, or import of the discovery controller is used.
"""
from pathlib import Path
import gzip
import json

ROOT=Path(__file__).resolve().parent


def verify(path,half_turn,repairs,kind):
    data=json.loads(gzip.decompress(path.read_bytes()))
    assert (data['pair'],data['width'],data['cap_width'],data['half_turn'],data['repairs'],data['kind'])==('DX',4,2,half_turn,repairs,kind)
    width=4;vertices=frozenset(range(20))
    neighbors={v:frozenset(rr*width+cc for rr,cc in
                         [(v//width,v%width),(v//width-1,v%width),(v//width+1,v%width),
                          (v//width,v%width-1),(v//width,v%width+1)]
                         if 0<=rr<5 and 0<=cc<width) for v in vertices}
    def tau(v):return ((4-v//width) if half_turn else (v//width))*width+width-1-v%width
    assert all(tau(tau(v))==v and tau(v)!=v for v in vertices)
    assert all(frozenset(tau(u) for u in neighbors[v])==neighbors[tau(v)] for v in vertices)
    def verts(mask):
        assert type(mask) is int and 0<=mask<(1<<20)
        return frozenset(v for v in vertices if mask>>v&1)
    def state(a,b,remaining):
        assert type(remaining) is int and 0<=remaining<=repairs
        return verts(a),verts(b),remaining
    a=b=set(vertices)
    for column,pattern in [(0,'obwbo'),(3,'bowob')]:
        a=a-{r*width+column for r,s in enumerate(pattern) if s not in 'ob'}
        b=b-{r*width+column for r,s in enumerate(pattern) if s not in 'ow'}
    root=(frozenset(a),frozenset(b),repairs)
    assert state(*data['root'])==root
    nodes={}
    for record in data['nodes']:
        key=state(record['a'],record['b'],record['remaining'])
        assert key not in nodes
        nodes[key]=record
    assert root in nodes
    edges=0;terminals=0;adj={}
    for key,record in nodes.items():
        blue,white,remaining=key
        defects=frozenset(tau(v) for v in blue)-white
        if record.get('mirror_terminal'):
            assert kind=='white_strategy' and record['mirror_terminal'] is True and not defects
            assert set(record)=={'a','b','remaining','mirror_terminal'}
            adj[key]=[];terminals+=1;continue
        assert defects
        if kind=='white_strategy':
            assert set(record)=={'a','b','remaining','replies'}
            replies=record['replies']
            assert len(replies)==len(blue) and {r[0] for r in replies}==blue
            moves=replies
        else:
            assert set(record)=={'a','b','remaining','blue'}
            assert record['blue'] in blue
            moves=[(record['blue'],None)]
        adj[key]=[]
        for v,supplied_u in moves:
            middle_blue=blue-neighbors[v];middle_white=white-{v}
            legal_mirror=tau(v) in middle_white
            allowed={}
            if legal_mirror:
                allowed[tau(v)]=remaining
                if remaining:
                    allowed.update({u:remaining-1 for u in middle_white if u!=tau(v)})
            else:
                allowed={u:remaining for u in middle_white}
            if kind=='white_strategy':
                assert supplied_u in allowed
                selected=[(supplied_u,allowed[supplied_u])]
            else:
                selected=list(allowed.items())
            for u,next_remaining in selected:
                child=(middle_blue-{u},middle_white-neighbors[u],next_remaining)
                assert child in nodes
                assert len(child[0]|child[1])<len(blue|white)
                if u==tau(v):
                    child_defects=frozenset(tau(x) for x in child[0])-child[1]
                    assert child_defects==defects-(neighbors[tau(v)]|{v})
                adj[key].append(child);edges+=1
    seen={root};stack=[root]
    while stack:
        for child in adj[stack.pop()]:
            if child not in seen:seen.add(child);stack.append(child)
    assert seen==set(nodes)
    return len(nodes),edges,terminals


if __name__=='__main__':
    totals=[0,0,0]
    for half_turn,repairs,kind in [(False,0,'blue_counterstrategy'),(False,1,'blue_counterstrategy'),
                                   (True,0,'blue_counterstrategy'),(True,1,'blue_counterstrategy'),
                                   (False,2,'white_strategy')]:
        prefix='strategy' if kind=='white_strategy' else 'counter'
        name=f'round2_dx_mirror_{prefix}_DX_4_2_{int(half_turn)}_{repairs}.json.gz'
        result=verify(ROOT/name,half_turn,repairs,kind)
        totals=[a+b for a,b in zip(totals,result)]
        print(name,result)
    print(f'Verified five mirror-policy DAGs: {totals[0]} states, {totals[1]} transitions, {totals[2]} terminal mirror invariants.')
