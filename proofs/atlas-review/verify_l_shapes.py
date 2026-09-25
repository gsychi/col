#!/usr/bin/env python3
"""Independent search-free verifier. Uses coordinate sets, not minimax.
Checks the actual bulk/L interface before checking every response-DAG edge.
"""
from pathlib import Path
import gzip,json
ROOT=Path(__file__).resolve().parent

def require(ok,msg):
    if not ok:raise ValueError(msg)

def verify(doc):
    h,w=doc['height'],doc['width'];p=doc['bulk_checkerboard_phase']
    require((h,w) in [(5,9),(7,7)] and p in [0,1],'scope')
    vs=[tuple(v) for v in doc['path_cells']];ids={v:i for i,v in enumerate(vs)}
    actual={(r,c) for r in range(h) for c in range(w)}
    bulk={(r,c) for r in range(h-1) for c in range(w-1)}
    require(len(vs)==13 and len(set(vs))==13 and set(vs)==actual-bulk,'remainder')
    def neighbors(v):
        r,c=v;return {(r-1,c),(r+1,c),(r,c-1),(r,c+1)}
    nb={v:neighbors(v)&set(vs) for v in vs}
    for i,v in enumerate(vs):require(nb[v]==set(vs[max(0,i-1):i]+vs[i+1:i+2]),'path order')
    bw={v for v in bulk if sum(v)%2==p}
    allowed={v for v in vs if not(neighbors(v)&bw)}
    def verts(mask):
        require(type(mask)is int and 0<=mask<(1<<13),'mask')
        return frozenset(v for i,v in enumerate(vs) if (mask>>i)&1)
    require(verts(doc['blue'])==set(vs),'Blue full')
    require(verts(doc['white'])==allowed,'maximal White support / crossing edges')
    require(doc['losing_actor']=='White','role')
    opening=doc['blue_first_winning_move'];require(type(opening)is int and 0<=opening<13,'opening')
    v=vs[opening]
    roots=[(frozenset(allowed),frozenset(vs)),(frozenset(allowed-{v}),frozenset(set(vs)-{v}-nb[v]))]
    actual_roots=[(verts(a),verts(b)) for a,b in doc['roots']]
    require(actual_roots==roots,'root correspondence')
    nodes={}
    for a,b,rs in doc['nodes']:
        key=(verts(a),verts(b));require(key not in nodes,'duplicate');nodes[key]=rs
    children={};edges=0
    for (A,B),rs in nodes.items():
        require(type(rs)is list and len(rs)==len(A),'universal White coverage')
        cs=[]
        for first,j in zip(sorted(A,key=ids.get),rs):
            require(type(j)is int and 0<=j<13,'response index')
            response=vs[j];A1=A-{first}-nb[first];B1=B-{first}
            require(response in B1,'illegal Blue reply')
            child=(frozenset(A1-{response}),frozenset(B1-{response}-nb[response]))
            require(child in nodes,'missing successor')
            require(len(child[0]|child[1])<=len(A|B)-2,'descent')
            cs.append(child);edges+=1
        children[A,B]=cs
    require(all(r in nodes for r in roots),'missing root')
    seen=set(roots);stack=list(roots)
    while stack:
        for child in children[stack.pop()]:
            if child not in seen:seen.add(child);stack.append(child)
    require(seen==set(nodes),'unreachable node')
    return len(nodes),edges

if __name__=='__main__':
    for path in sorted(ROOT.glob('L_*.json.gz')):
        with gzip.open(path,'rt') as f:d=json.load(f)
        n,e=verify(d)
        print(f'VERIFIED {path.name}: Blue wins with either starting player; {n} checkpoints, {e} responses')
        bad=json.loads(json.dumps(d));bad['white']^=1
        try:verify(bad)
        except ValueError:pass
        else:raise AssertionError('corrupted interface accepted')
        bad=json.loads(json.dumps(d));node=next(x for x in bad['nodes'] if x[2]);node[2].pop()
        try:verify(bad)
        except ValueError:pass
        else:raise AssertionError('missing move accepted')
    print('VERIFIED: corruption checks. This rejects only the bare independent-safe L construction.')
