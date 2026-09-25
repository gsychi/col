"""Independently verify anchored-D caps and their width-independent interfaces.

Default checks supplied response DAGs. --generate regenerates them first.
Root geometry and every numerical claim are reconstructed here explicitly.
"""
from pathlib import Path
from fractions import Fraction as F
import argparse
import gzip
import json
from number_certificates import generate,verify

ROOT=Path(__file__).resolve().parent
PATTERNS=dict(D='obwbo',U='wbobo',V='bwbob',X='bowob',R='wobob',J='owobo')
CASES=[(0,'U',None,F(0)),(0,'R',None,F(-1)),(1,'V',None,F(-2)),
       (1,'J',None,F(1,2)),(2,'D',None,F(0)),(2,'X',None,F(-1)),
       (0,'R',(0,0),F(-1,2)),(0,'R',(2,2),F(-1,2)),(0,'R',(4,2),F(-1,2))]
CHECKER_CAPS=[('D_C','obwbo','wbwbw',F(-1)),
              ('Cbar_X','bwbwb','bowob',F(0)),
              ('D_Cbar','obwbo','bwbwb',F(1)),
              ('C_X','wbwbw','bowob',F(1))]


def permitted(pattern):
    return ({r for r,s in enumerate(pattern) if s in 'ob'},
            {r for r,s in enumerate(pattern) if s in 'ow'})


def position(width,left,right=None):
    a={(r,c) for r in range(5) for c in range(width)};b=set(a)
    ends=[(0,left)]+([(width-1,right)] if right is not None else [])
    for c,p in ends:
        aa,bb=permitted(p)
        a-={(r,c) for r in range(5) if r not in aa}
        b-={(r,c) for r in range(5) if r not in bb}
    return a,b


def closed(v):
    r,c=v;return {v,(r-1,c),(r+1,c),(r,c-1),(r,c+1)}


def cap(opening,interface,reply):
    a,b=position(3,PATTERNS['D']);v=(opening,2)
    assert v in a;a-=closed(v);b.discard(v)
    if reply is not None:
        assert reply in b;a.discard(reply);b-=closed(reply)
    support=permitted(PATTERNS[interface])[1]
    b-={(r,2) for r in support}
    return a,b


def name(opening,interface,reply):
    response='none' if reply is None else f'{reply[0]}_{reply[1]}'
    return f'row{opening}_{interface}_reply_{response}'


def check(build):
    directory=ROOT/'round3_dx_certificates'
    if build:directory.mkdir(exist_ok=True)
    nodes=edges=0;manifest=[];assemblies=0
    for opening,interface,reply,value in CASES:
        a,b=cap(opening,interface,reply)
        am=sum(1<<(r*3+c) for r,c in a);bm=sum(1<<(r*3+c) for r,c in b)
        label=name(opening,interface,reply)
        for direction,aa,bb,q in [('le',am,bm,-value),('ge',bm,am,value)]:
            path=directory/f'{label}_{direction}.json.gz'
            if build:
                data=generate(5,3,aa,bb,q)
                path.write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0))
            data=json.loads(gzip.decompress(path.read_bytes()))
            assert (data['height'],data['width'],data['root'])==(5,3,[aa,bb,q.numerator,q.denominator])
            nn,ee=verify(data);nodes+=nn;edges+=ee
            manifest.append(dict(file=path.name,root=data['root'],nodes=nn,edges=ee))
        for width in range(4,22):
            for far in PATTERNS.values():
                actual_a,actual_b=position(width,PATTERNS['D'],far)
                v=(opening,2);assert v in actual_a
                actual_a-=closed(v);actual_b.discard(v)
                if reply is not None:
                    assert reply in actual_b
                    actual_a.discard(reply);actual_b-=closed(reply)
                side_a,side_b=position(width-3,PATTERNS[interface],far)
                side_a={(r,c+3) for r,c in side_a};side_b={(r,c+3) for r,c in side_b}
                virtual_a=a|side_a;virtual_b=b|side_b
                assert actual_a<=virtual_a and virtual_b<=actual_b
                assert all(not ((r,2) in b and (r,3) in side_b) for r in range(5))
                assert width-3<width
                assemblies+=1
    for label,left,right,value in CHECKER_CAPS:
        a,b=position(3,left,right)
        am=sum(1<<(r*3+c) for r,c in a);bm=sum(1<<(r*3+c) for r,c in b)
        for direction,aa,bb,q in [('le',am,bm,-value),('ge',bm,am,value)]:
            path=directory/f'checker_{label}_{direction}.json.gz'
            if build:
                data=generate(5,3,aa,bb,q)
                path.write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0))
            data=json.loads(gzip.decompress(path.read_bytes()))
            assert (data['height'],data['width'],data['root'])==(5,3,[aa,bb,q.numerator,q.denominator])
            nn,ee=verify(data);nodes+=nn;edges+=ee
            manifest.append(dict(file=path.name,root=data['root'],nodes=nn,edges=ee))
    trap_branches=0
    for width in range(8,34,2):
        a,b=position(width,PATTERNS['D'],PATTERNS['X'])
        frontier=[(a,b)]
        for r in range(5):
            c=width-4 if r%2==0 else 3;v=(r,c);next_frontier=[]
            for aa,bb in frontier:
                assert v in aa
                mid_a=aa-closed(v);mid_b=bb-{v}
                replies={(r,width-1-c),(4-r,width-1-c)}&mid_b
                assert replies
                for u in replies:next_frontier.append((mid_a-{u},mid_b-closed(u)))
            frontier=next_frontier
        expected_a=set();expected_b=set()
        blocks=[(0,3,'obwbo','bwbwb'),(width-3,3,'wbwbw','bowob')]
        if width>8:blocks.append((4,width-8,'bwbwb','wbwbw'))
        for offset,length,left,right in blocks:
            aa,bb=position(length,left,right)
            expected_a|={(r,c+offset) for r,c in aa}
            expected_b|={(r,c+offset) for r,c in bb}
        assert all(aa==expected_a and bb==expected_b for aa,bb in frontier)
        trap_branches+=len(frontier)
    if build:(directory/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    assert json.loads((directory/'manifest.json').read_text())==manifest
    print(f'Verified {len(manifest)} exact-bound DAGs: {nodes} checkpoints, {edges} response edges.')
    print(f'Checked {assemblies} cap assemblies, including width-one endpoint intersections (regression only).')
    print(f'Checked {trap_branches} branches of the width-three mirror trap (regression only).')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--generate',action='store_true')
    check(parser.parse_args().generate)
