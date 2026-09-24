"""Check finite pair-algebra obstruction and moving-cap repairs independently.

The default consumes supplied response DAGs and uses a separate coordinate-set
checker. --generate discovers those DAGs before checking them.
"""
from pathlib import Path
from fractions import Fraction as F
import argparse
import gzip
import json
from number_certificates import generate,verify
from dx_verify_interface_contracts import path_game,permissions,number,add,STAR,leq

ROOT=Path(__file__).resolve().parent
X='bowob';D='obwbo'
SIDES={0:'1/2',1:'1/2',2:'1',3:'1',8:'1',9:'1',10:'1',11:'3/2',
       16:'1/2',17:'1/2',18:'1',19:'1',24:'1',25:'1',26:'3/2',27:'3/2'}
CAPS={0:('2',False),1:('1',True),2:('1',False),3:('1/2',False),
      8:('1',False),9:('0',True),10:('0',False),11:('-1/2',False),
      16:('1',True),17:('0',False),18:('0',True),19:('-1/2',True),
      24:('1/2',False),25:('-1/2',True),26:('-1/2',False),27:('-1',False)}


def position(width,left,right='ooooo'):
    a={(r,c) for r in range(5) for c in range(width)};b=set(a)
    for c,p in [(0,left),(width-1,right)]:
        for r,s in enumerate(p):
            if s not in 'ob':a.discard((r,c))
            if s not in 'ow':b.discard((r,c))
    return a,b


def closed(v):
    r,c=v;return {v,(r-1,c),(r+1,c),(r,c-1),(r,c+1)}


def mask(width,vertices):return sum(1<<(r*width+c) for r,c in vertices)


def anchored(width,near):
    a,b=position(width,X);v=(2,width-1)
    assert v in a;a-=closed(v);b.discard(v)
    b-={(r,width-1) for r,s in enumerate(near) if s in 'ow'}
    return a,b


def check(build):
    directory=ROOT/'round4_dx_certificates'
    if build:directory.mkdir(exist_ok=True)
    manifest=[];nodes=edges=0
    def certificate(label,width,a,b,q):
        nonlocal nodes,edges
        am,bm=mask(width,a),mask(width,b)
        path=directory/f'{label}.json.gz'
        if build:
            data=generate(5,width,am,bm,q)
            path.write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0))
        data=json.loads(gzip.decompress(path.read_bytes()))
        assert (data['height'],data['width'],data['root'])==(5,width,[am,bm,q.numerator,q.denominator])
        nn,ee=verify(data);nodes+=nn;edges+=ee
        manifest.append(dict(file=path.name,root=data['root'],nodes=nn,edges=ee))
    for support,qtext in SIDES.items():
        near=''.join('w' if r==2 else 'b' if support>>r&1 else 'o' for r in range(5))
        a,b=position(3,X,near);q=F(qtext)
        actual_a,actual_b=position(7,X,X)
        actual_a-=closed((2,3));actual_b.discard((2,3))
        right_a,right_b=position(3,near,X)
        assert right_a=={(r,2-c) for r,c in a}
        assert right_b=={(r,2-c) for r,c in b}
        right_a={(r,c+4) for r,c in right_a};right_b={(r,c+4) for r,c in right_b}
        virtual_a=a|{(0,3),(4,3)}|right_a
        virtual_b=b|{(r,3) for r in range(5) if support>>r&1}|right_b
        assert actual_a==virtual_a and virtual_b<=actual_b
        for seam in (2,3):
            assert all(not ((r,seam) in virtual_b and (r,seam+1) in virtual_b) for r in range(5))
        certificate(f's{support}_side_lower',3,b,a,q)
        if support==17:certificate('s17_side_upper',3,a,b,-q)
        cap=path_game(frozenset([0,4]),frozenset(r for r in range(5) if support>>r&1))
        cn,cs=CAPS[support];target=number(F(cn))
        if cs:target=add(target,STAR)
        assert leq(cap,target) and leq(target,cap)
        total=add(number(2*q),cap)
        assert leq(number(F(1)),total)
        if support!=17:assert not leq(total,number(F(1)))
    contracts=[(2,X,F(0),False),(3,D,F(-1),False),(4,X,F(0),True)]
    embeddings=0
    for width,near,value,star in contracts:
        a,b=anchored(width,near)
        label=f'cap{width}_{"D" if near==D else "X"}'
        # A detached shared vertex cancels star. The dead intervening column
        # preserves the original cap's graph, and the ambient board has <=30 cells.
        ambient=width+2 if star else width
        aa=set(a);bb=set(b)
        if star:aa.add((0,width+1));bb.add((0,width+1))
        certificate(label+'_upper',ambient,aa,bb,-value)
        certificate(label+'_lower',ambient,bb,aa,value)
        for far in (X,'wobob','bwbob'):
            for n in range(2*width+1,2*width+24,2):
                actual_a,actual_b=position(n,X,far);v=(2,width-1)
                actual_a-=closed(v);actual_b.discard(v)
                side_a,side_b=position(n-width,near,far)
                side_a={(r,c+width) for r,c in side_a};side_b={(r,c+width) for r,c in side_b}
                assert actual_a<=a|side_a and b|side_b<=actual_b
                assert all(not ((r,width-1) in b and (r,width) in side_b) for r in range(5))
                assert n-width<n
                embeddings+=1
            # Smallest domain members are not all reached by the symmetric sweep.
            n={2:5,3:5,4:7}[width]
            actual_a,actual_b=position(n,X,far);v=(2,width-1)
            actual_a-=closed(v);actual_b.discard(v)
            side_a,side_b=position(n-width,near,far)
            side_a={(r,c+width) for r,c in side_a};side_b={(r,c+width) for r,c in side_b}
            assert actual_a<=a|side_a and b|side_b<=actual_b
            assert all(not ((r,width-1) in b and (r,width) in side_b) for r in range(5))
            embeddings+=1
    assert leq(add(STAR,STAR),number(F(0))) and leq(number(F(0)),add(STAR,STAR))
    assert leq(add(number(F(1,2)),STAR),number(F(1)))
    assert not leq(number(F(1)),add(number(F(1,2)),STAR))
    if build:(directory/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    assert json.loads((directory/'manifest.json').read_text())==manifest
    print(f'Verified {len(manifest)} bound DAGs: {nodes} checkpoints, {edges} response edges.')
    print(f'Checked 16 exhaustive support bounds, three exact cap identities, {embeddings} embeddings (regression).')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--generate',action='store_true')
    check(parser.parse_args().generate)
