#!/usr/bin/env python3
"""Execute the certified White strategy, without search.

Example: python3 strategy.py --blue-moves 0 14
Cells are zero-based and row-major. Supply Blue's moves only; the script
inserts White's certified replies. Coordinates are also printed.
"""
from __future__ import annotations
import argparse
import gzip
import json
from pathlib import Path
from verify import InvalidCertificate, neighborhood, vertices, masks, require

ROOT=Path(__file__).resolve().parent

class CertifiedWhite:
    def __init__(self, directory: Path = ROOT):
        self.manifest=json.loads((directory/'manifest.json').read_text())
        self.by_opening={entry['blue_opening']:entry for entry in self.manifest['openings']}
        self.tiles={}
        for entry in self.manifest['certificates']:
            doc=json.loads(gzip.decompress((directory/entry['file']).read_bytes()))
            self.tiles[entry['file']]={
                'width':doc['width'], 'root':tuple(doc['root']),
                'nodes':{(a,b):rr for a,b,rr in doc['nodes']},
                'neighbors':neighborhood(3,doc['width'])}
        self.nb=neighborhood(3,15)
        self.a=self.b=frozenset(range(45))
        self.entry=None
        self.row_flip=self.col_flip=False
        self.local_states=[]
        self.history=[]

    def transform(self, v: int) -> int:
        r,c=divmod(v,15)
        return (2-r if self.row_flip else r)*15+(14-c if self.col_flip else c)

    def reply(self, blue: int) -> int:
        require(blue in self.a, f'Illegal Blue move {blue}; legal moves: {sorted(self.a)}')
        self.a=self.a-{blue}-self.nb[blue]
        self.b=self.b-{blue}
        if self.entry is None:
            r,c=divmod(blue,15)
            self.row_flip=r>1
            self.col_flip=c>7
            representative=self.transform(blue)
            self.entry=self.by_opening[representative]
            white=self.transform(self.entry['white_response'])
            self.local_states=[self.tiles[b['certificate']]['root'] for b in self.entry['blocks']]
        else:
            canonical=self.transform(blue)
            r,c=divmod(canonical,15)
            selected=None
            for i,block in enumerate(self.entry['blocks']):
                s,w=block['start_column'],block['width']
                if s<=c<s+w:
                    selected=(i,block,r*w+c-s)
                    break
            require(selected is not None,'Actual Blue move fell outside all virtual blocks')
            i,block,v=selected
            tile=self.tiles[block['certificate']]
            a,b=self.local_states[i]
            aset,bset=vertices(a,3*block['width']),vertices(b,3*block['width'])
            ordered=sorted(aset)
            require(v in aset,'Actual move not available in virtual tile')
            white_local=tile['nodes'][(a,b)][ordered.index(v)]
            a1=aset-{v}-tile['neighbors'][v]
            b1=bset-{v}
            require(white_local in b1,'Invalid local response')
            a2=a1-{white_local}
            b2=b1-{white_local}-tile['neighbors'][white_local]
            self.local_states[i]=masks(a2,b2)
            wr,wc=divmod(white_local,block['width'])
            white=self.transform(wr*15+block['start_column']+wc)
        require(white in self.b,'Certified White response is not legal on actual board')
        self.a=self.a-{white}
        self.b=self.b-{white}-self.nb[white]
        self.history.append((blue,white))
        return white

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blue-moves', type=int, nargs='+', required=True)
    args=parser.parse_args()
    game=CertifiedWhite()
    try:
        for blue in args.blue_moves:
            white=game.reply(blue)
            print(f'Blue {blue:2d} {divmod(blue,15)} -> White {white:2d} {divmod(white,15)}')
        print('White wins: Blue has no legal move.' if not game.a else f'Next legal Blue moves: {sorted(game.a)}')
    except InvalidCertificate as error:
        raise SystemExit(str(error))
