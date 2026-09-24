"""Bind and check selected round-two roots, local caps, and reflection maps.

Default mode verifies supplied response DAGs without minimax. --generate
regenerates the DAGs and then runs the independent set-based verifier.
"""
from fractions import Fraction as F
from pathlib import Path
import argparse
import gzip
import json
from number_certificates import generate, verify
from dx_verify_interface_contracts import path_game, permissions, number, add, STAR, leq

ROOT=Path(__file__).resolve().parent
PATTERNS=dict(D='obwbo',U='wbobo',V='bwbob',X='bowob',R='wobob',J='owobo',C='wbwbw',K='bwbwb')
CASES=[('UX',2,'-1/4'),('UX',3,'1'),('VX',1,'1/2'),('VX',2,'2'),('VX',3,'0'),
       ('XX',1,'1'),('XX',2,'1'),('XX',3,'1/2'),('XR',3,'1/2'),
       ('DD',2,'1'),('DV',1,'2'),('DV',3,'1'),('DX',1,'1'),('DX',2,'-1'),
       ('DC',2,'0'),('KX',2,'2')]


def endpoint_masks(pair,width):
    a=b=(1<<(5*width))-1
    for c,name in [(0,pair[0]),(width-1,pair[1])]:
        for r,s in enumerate(PATTERNS[name]):
            if s not in 'ob':a&=~(1<<(r*width+c))
            if s not in 'ow':b&=~(1<<(r*width+c))
    return a,b


def check(build):
    directory=ROOT/'round2_dx_certificates'
    if build:directory.mkdir(exist_ok=True)
    total_nodes=total_edges=0
    for pair,width,value in CASES:
        a,b=endpoint_masks(pair,width)
        q=F(value)
        for side,aa,bb,aux in [('le',a,b,-q),('ge',b,a,q)]:
            name=f'{pair}_{width}_{side}.json.gz'
            path=directory/name
            if build:
                data=generate(5,width,aa,bb,aux)
                path.write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0))
            data=json.loads(gzip.decompress(path.read_bytes()))
            assert (data['height'],data['width'],data['root'])==(5,width,[aa,bb,aux.numerator,aux.denominator])
            nodes,edges=verify(data)
            total_nodes+=nodes;total_edges+=edges
    for pattern,value in [('.w.ob',F(-1,2)),('..wbb',F(0)),('...bb',F(1)),
                          ('..wbo',F(-1,2)),('w.wbo',F(-3,2)),('...ob',F(1,2))]:
        g=path_game(*permissions(pattern));target=number(value)
        assert leq(g,target) and leq(target,g)
    # Width-one intersection XR is a number-plus-star, not a dyadic number.
    a,b=endpoint_masks('XR',1)
    g=path_game(frozenset(i for i in range(5) if a>>i&1),frozenset(i for i in range(5) if b>>i&1))
    target=add(number(F(1,2)),STAR)
    assert leq(g,target) and leq(target,g)
    # Check the symbolic identities behind the all-even mirror theorem.
    conjugate=lambda p:''.join({'o':'o','b':'w','w':'b','.':'.'}[x] for x in p)
    assert conjugate(PATTERNS['J'])==PATTERNS['J'][::-1]
    assert conjugate(PATTERNS['C'])==PATTERNS['K']
    assert len(PATTERNS['J'])==5
    for width in range(2,18,2):
        for right,half_turn in [(PATTERNS['J'],True),(PATTERNS['J'][::-1],False)]:
            a={(r,c) for r in range(5) for c in range(width)};b=set(a)
            for c,p in [(0,PATTERNS['J']),(width-1,right)]:
                aa,bb=permissions(p)
                a-={(r,c) for r in range(5) if r not in aa}
                b-={(r,c) for r in range(5) if r not in bb}
            transform=lambda v:(4-v[0],width-1-v[1]) if half_turn else (v[0],width-1-v[1])
            assert {transform(v) for v in a}==b
            assert all(transform((r,c))!=(r,c) for r in range(5) for c in range(width))
    trap_branches=0
    for width in range(6,32,2):
        universe={(r,c) for r in range(5) for c in range(width)}
        a=set(universe);b=set(universe)
        for c,p in [(0,PATTERNS['D']),(width-1,PATTERNS['X'])]:
            aa,bb=permissions(p)
            a-={(r,c) for r in range(5) if r not in aa}
            b-={(r,c) for r in range(5) if r not in bb}
        frontier=[(a,b)]
        for r in range(5):
            c=2 if r%2==0 else width-3;v=(r,c);next_frontier=[]
            near=lambda x:{x,(x[0]-1,x[1]),(x[0]+1,x[1]),(x[0],x[1]-1),(x[0],x[1]+1)}
            for aa,bb in frontier:
                assert v in aa
                mid_a=aa-near(v);mid_b=bb-{v}
                replies={(r,width-1-c),(4-r,width-1-c)}&mid_b
                assert replies
                for u in replies:next_frontier.append((mid_a-{u},mid_b-near(u)))
            frontier=next_frontier
        expected_a=set();expected_b=set()
        blocks=[(0,2,'D','C'),(width-2,2,'K','X')]
        if width>6:blocks.append((3,width-6,'C','K'))
        for offset,length,left,right in blocks:
            aa,bb=endpoint_masks(left+right,length)
            expected_a|={(r,offset+c) for r in range(5) for c in range(length) if aa>>(r*length+c)&1}
            expected_b|={(r,offset+c) for r in range(5) for c in range(length) if bb>>(r*length+c)&1}
        assert all(aa==expected_a and bb==expected_b for aa,bb in frontier)
        trap_branches+=len(frontier)
    print(f'Verified {2*len(CASES)} bound DAGs: {total_nodes} checkpoints, {total_edges} checked response edges.')
    print('Verified six local caps and XR_1 = 1/2+star by independent short-game order.')
    print('Verified J conjugacy identity; all-even pairing maps proved symbolically in round2_dx_progress.md.')
    print(f'Verified {trap_branches} assembly branches of the all-even mirror trap (finite regression of symbolic proof).')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--generate',action='store_true')
    check(parser.parse_args().generate)
