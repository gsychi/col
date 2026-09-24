#!/usr/bin/env python3
"""Independently check six width-three paired boundary base inequalities.

Default verification reads supplied response DAGs; --generate is discovery.
The starred roots include one isolated shared vertex behind a dead column.
"""
from pathlib import Path
from fractions import Fraction as F
import argparse
import gzip
import json
from number_certificates import generate,verify

ROOT=Path(__file__).resolve().parent
PATTERNS={'R':'wobob','V':'bwbob','X':'bowob'}
TARGETS={'R':F(1),'V':F(2),'X':F(1)}


def root(left,star):
    width=5 if star else 3
    a={(r,c) for r in range(5) for c in range(3)};b=set(a)
    for c,p in [(0,PATTERNS[left]),(2,PATTERNS['X'])]:
        for r,s in enumerate(p):
            if s not in 'ob':a.discard((r,c))
            if s not in 'ow':b.discard((r,c))
    if star:
        a.add((0,4));b.add((0,4))
        assert all(c!=3 for r,c in a|b)
        assert all(abs(r)+abs(c-4)>1 for r,c in (a|b)-{(0,4)})
    return width,sum(1<<(r*width+c) for r,c in a),sum(1<<(r*width+c) for r,c in b)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--generate',action='store_true')
    build=parser.parse_args().generate
    directory=ROOT/'round4_pair_base_certificates'
    if build:directory.mkdir(exist_ok=True)
    manifest=[];nodes=edges=0
    for left in ('R','V','X'):
        for star in (False,True):
            width,a,b=root(left,star);q=-TARGETS[left]
            name=f'{left.lower()}x3_{"starred" if star else "ordinary"}_upper.json.gz'
            path=directory/name
            if build:
                doc=generate(5,width,a,b,q)
                path.write_bytes(gzip.compress(json.dumps(doc,separators=(',',':')).encode(),mtime=0))
            doc=json.loads(gzip.decompress(path.read_bytes()))
            assert (doc['height'],doc['width'],doc['root'])==(5,width,[a,b,q.numerator,q.denominator])
            nn,ee=verify(doc);nodes+=nn;edges+=ee
            manifest.append(dict(file=name,family=left+'X',board_width=3,star=star,
                                 target=str(TARGETS[left]),ambient_width=width,root=doc['root'],
                                 checkpoints=nn,response_edges=ee))
    if build:(directory/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    assert json.loads((directory/'manifest.json').read_text())==manifest
    print(f'Verified {len(manifest)} paired-base DAGs: {nodes} checkpoints, {edges} response edges.')
    print('Proved T1(RX3), T2(VX3), T1(XX3), including each starred inequality directly.')


if __name__=='__main__':main()
