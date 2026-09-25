#!/usr/bin/env python3
"""Synthesize certified partitions; no game-tree search.

Uses the supplied verified tile library, not the manifest's opening table.
The interface state is the three White-legality bits at the right edge.

python3 tiling_search.py --demon
python3 tiling_search.py --root

--root independently finds a reply and a tiling for all 16 representative
openings, then checks every assembled state with the same relaxation checker.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from verify import check_tile, check_assembly, actual_after_opening, neighborhood, masks
ROOT=Path(__file__).resolve().parent

class TilingSearch:
    def __init__(self):
        self.manifest=json.loads((ROOT/'manifest.json').read_text())
        self.tiles={e['file']:check_tile(ROOT/e['file'],e) for e in self.manifest['certificates']}
        self.library=[]
        for filename,tile in self.tiles.items():
            w=tile['width'];a,b=masks(tile['a'],tile['b'])
            left=sum(1<<r for r in range(3) if r*w in tile['b'])
            right=sum(1<<r for r in range(3) if r*w+w-1 in tile['b'])
            self.library.append((w,a,b,left,right,filename))

    @staticmethod
    def extract(mask: int, n: int, start: int, width: int) -> int:
        rowmask=(1<<width)-1
        return sum(((mask>>(r*n+start))&rowmask)<<(r*width) for r in range(3))

    def plan(self, a: int, b: int, n: int=15):
        # dp[column][White-right-boundary-mask] = one certified prefix partition.
        dp=[{} for _ in range(n+1)]
        dp[0][0]=[]
        for col in range(n):
            if not dp[col]:continue
            compatible=[]
            extracts={}
            for w,ta,tb,left,right,filename in self.library:
                if col+w>n:continue
                if w not in extracts:
                    extracts[w]=(self.extract(a,n,col,w),self.extract(b,n,col,w))
                aa,bb=extracts[w]
                if aa&~ta==0 and tb&~bb==0:
                    compatible.append((w,left,right,filename))
            for incoming,path in list(dp[col].items()):
                # Retire an entire Blue-illegal column. It becomes a dead gap.
                if self.extract(a,n,col,1)==0 and 0 not in dp[col+1]:
                    dp[col+1][0]=path
                for w,left,right,filename in compatible:
                    if incoming&left==0 and right not in dp[col+w]:
                        dp[col+w][right]=path+[{'start_column':col,'width':w,'certificate':filename}]
        return next(iter(dp[n].values()),None)

    def attach_masks(self, entry):
        av,bv=set(),set()
        for block in entry['blocks']:
            tile=self.tiles[block['certificate']];w=block['width'];start=block['start_column']
            av |= {(v//w)*15+start+v%w for v in tile['a']}
            bv |= {(v//w)*15+start+v%w for v in tile['b']}
        entry['relaxed_masks']=list(masks(frozenset(av),frozenset(bv)))

    def prove_root(self):
        answers=[]
        for row in (0,1):
            for col in range(8):
                blue=row*15+col
                answer=None
                for white in range(45):
                    if white==blue:continue
                    a,b=actual_after_opening(blue,white)
                    plan=self.plan(*masks(a,b))
                    if plan is not None:
                        answer={'blue_opening':blue,'white_response':white,'blocks':plan}
                        self.attach_masks(answer)
                        check_assembly(answer,self.tiles)
                        break
                if answer is None:raise RuntimeError(f'No certificate found for opening {blue}')
                answers.append(answer)
                print(f'Opening {blue:2d}: White {answer["white_response"]:2d}, widths {[b["width"] for b in answer["blocks"]]}')
        print('SUCCESS: 16/16 representative openings certified using boundary DP, no game-tree search.')
        return answers

    def prove_demon(self):
        nb=neighborhood(3,15);occupied=frozenset({0,14,44})
        a=frozenset(range(45))-occupied-nb[0]-nb[14]
        b=frozenset(range(45))-occupied-nb[44]
        for white in sorted(b):
            aa=a-{white};bb=b-{white}-nb[white]
            plan=self.plan(*masks(aa,bb))
            if plan is not None:
                e={'white_response':white,'blocks':plan}
                self.attach_masks(e)
                check_assembly(e,self.tiles,(aa,bb))
                print(f'CERTIFIED DEMON WIN: White {white}; widths {[x["width"] for x in plan]}')
                return e
        raise RuntimeError('No certified White response found')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--root',action='store_true');group.add_argument('--demon',action='store_true')
    args=parser.parse_args();solver=TilingSearch()
    if args.root:solver.prove_root()
    else:solver.prove_demon()
