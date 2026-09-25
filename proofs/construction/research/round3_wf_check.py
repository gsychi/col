#!/usr/bin/env python3
"""Search-free certificates for a reachable F-phase separator obstruction.

--generate discovers response DAGs; default mode independently verifies them.
"""
from fractions import Fraction as F
from pathlib import Path
import argparse,gzip,json
from number_certificates import generate,verify
from wf_white_first_check import endpoint_masks,white_move
from round2_wf_check import blue_move,embed

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'round3_wf_certificates'
D='obwbo';X='bowob';K='wbwob'
# support, separator lower bound, left lower bound, marked-right lower bound
CASES=[(0,'2','-1','1'),(1,'3/4','-1','1'),(2,'1','0','3/2'),
       (3,'1/2','1/2','3/2'),(8,'1','0','3/2'),(9,'-1/4','0','3/2'),
       (10,'0','1','2'),(11,'-1/2','3/2','2'),(16,'3/4','-1','1'),
       (17,'0','-1','1'),(18,'-1/4','0','3/2'),(19,'-3/4','1/2','3/2'),
       (24,'1/2','1/2','3/2'),(25,'-3/4','1/2','3/2'),
       (26,'-1/2','3/2','2'),(27,'-1','2','2')]


def components(support):
    q=''.join('w' if r==2 else ('b' if support>>r&1 else 'o') for r in range(5))
    left=endpoint_masks(2,D,q)
    right=endpoint_masks(3,q,X);right=white_move(3,*right,2,1)
    return q,[(1,17,support),(2,*left),(3,*right)]


def end_caps():
    result=[]
    for row,name,pattern,value in [(0,'R','wobob',F(0)),(1,'V','bwbob',-F(1)),(2,'X',X,F(0))]:
        a,b=endpoint_masks(4,'ooooo',X)
        a,b=white_move(4,a,b,2,2);a,b=blue_move(4,a,b,row,0)
        for r,ch in enumerate(pattern):
            if ch in 'ow':b&=~(1<<(r*4))
        result.append((row,name,pattern,a,b,value))
    return result


def roots():
    result=[]
    for support,*bounds in CASES:
        q,parts=components(support)
        for label,(w,a,b),bound in zip(('separator','left','right'),parts,bounds):
            # A loss for -G+bound proves G>=bound.
            result.append((f's{support}_{label}_lower',w,b,a,F(bound)))
            if support==17:
                result.append((f's{support}_{label}_upper',w,a,b,-F(bound)))
    for row,name,pattern,a,b,value in end_caps():
        result.extend([(f'cap4_{name.lower()}_upper',4,a,b,-value),(f'cap4_{name.lower()}_lower',4,b,a,value)])
    a,b=endpoint_masks(3,D,K)
    result.extend([('dk3_upper',3,a,b,F(0)),('dk3_lower',3,b,a,F(0))])
    return result


def check_geometry():
    expected={s for s in range(32) if not s&4}
    assert {x[0] for x in CASES}==expected and len(CASES)==16
    actual=endpoint_masks(6,D,X)
    actual=white_move(6,*actual,2,4)
    actual=blue_move(6,*actual,2,2)
    for support,*bounds in CASES:
        q,parts=components(support)
        va=vb=0
        for offset,(w,a,b) in zip((2,0,3),parts):
            aa,bb=embed(6,a,b,offset,w);va|=aa;vb|=bb
        assert not actual[0]&~va and not vb&~actual[1]
        for seam in (1,2):
            for row in range(5):
                assert not ((vb>>(row*6+seam)&1) and (vb>>(row*6+seam+1)&1))
        assert sum(map(F,bounds))>=0
        if support!=17:assert sum(map(F,bounds))>0
    # Exact dead-column continuation on DD7: W1, B2, W4, B0 in column 3.
    a,b=endpoint_masks(7,D,D)
    a,b=white_move(7,a,b,1,3);a,b=blue_move(7,a,b,2,3)
    a,b=white_move(7,a,b,4,3);a,b=blue_move(7,a,b,0,3)
    central=sum(1<<(r*7+3) for r in range(5))
    assert not central&(a|b)
    la,lb=endpoint_masks(3,D,K);ra,rb=endpoint_masks(3,K,D)
    va,vb=embed(7,la,lb,0,3);aa,bb=embed(7,ra,rb,4,3)
    assert (a,b)==(va|aa,vb|bb), 'Continuation must be an exact disjoint sum'
    cap_count=0
    for k in range(6,31,2):
        for row,name,pattern,ca,cb,value in end_caps():
            a,b=endpoint_masks(k,D,X)
            a,b=white_move(k,a,b,2,k-2)
            a,b=blue_move(k,a,b,row,k-4)
            la,lb=endpoint_masks(k-4,D,pattern)
            va,vb=embed(k,la,lb,0,k-4)
            aa,bb=embed(k,ca,cb,k-4,4);va|=aa;vb|=bb
            assert not a&~va and not vb&~b,(k,row,'cap comparison')
            for r in range(5):
                assert not ((vb>>(r*k+k-5)&1) and (vb>>(r*k+k-4)&1))
            assert 0<k-4<k
            cap_count+=1
    return 16,cap_count


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--generate',action='store_true')
    args=parser.parse_args();summary=[];total_n=total_e=0
    for name,w,a,b,q in roots():
        path=OUT/(name+'.json.gz')
        if args.generate:
            OUT.mkdir(exist_ok=True)
            doc=generate(5,w,a,b,q)
            path.write_bytes(gzip.compress(json.dumps(doc,separators=(',',':')).encode(),mtime=0))
        doc=json.loads(gzip.decompress(path.read_bytes()))
        expected=(5,w,[a,b,q.numerator,q.denominator])
        assert (doc['height'],doc['width'],doc['root'])==expected,name
        n,e=verify(doc);total_n+=n;total_e+=e
        summary.append({'name':name,'root':expected,'checkpoints':n,'edges':e})
        print('VERIFIED',name,n,e,flush=True)
    geometries,cap_count=check_geometry()
    if args.generate:(OUT/'manifest.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(f'VERIFIED {len(summary)} certificates, {total_n} checkpoints, {total_e} response edges')
    print(f'VERIFIED {geometries} exhaustive separator contracts and the exact DD7 continuation')
    print(f'REGRESSION: {cap_count} four-column cap embeddings, all decreasing width')

if __name__=='__main__':main()
