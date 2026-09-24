#!/usr/bin/env python3
"""Independent certificates for delayed White-first DD boundary reductions.

Default mode checks saved response DAGs without minimax. --generate rebuilds.
"""
from fractions import Fraction as F
import argparse
import gzip
import json
from pathlib import Path

from number_certificates import board_neighbors, generate, verify
from wf_white_first_check import endpoint_masks, white_move

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'round2_wf_certificates'
D='obwbo'
Q_BY_ROW={0:'wbobo',1:'owobo',2:D,3:'owobo'[::-1],4:'wbobo'[::-1]}


def blue_move(w,a,b,r,c):
    v=r*w+c;bit=1<<v
    if not a&bit:raise ValueError('Illegal Blue move')
    return a&~(bit|sum(1<<u for u in board_neighbors(5,w)[v])),b&~bit


def cap_roots():
    result=[]
    for row,q,value in [(1,'bwbob',-F(1,2)),(3,'bwbob'[::-1],-F(1)),(4,'wobob'[::-1],F(0))]:
        a,b=endpoint_masks(1,D,D);a,b=white_move(1,a,b,0,0)
        a,b=blue_move(1,a,b,row,0)
        result.append((f'left_column0_row{row}',1,a,b,value,0,q))
    for row,q in Q_BY_ROW.items():
        a,b=endpoint_masks(2,D,'ooooo');a,b=white_move(2,a,b,0,0)
        a,b=blue_move(2,a,b,row,1)
        for r,p in enumerate(q):
            if p in 'ow':b&=~(1<<(2*r+1))
        value=-F(1) if row==1 else F(0)
        star=1<<8 if row==3 else 0
        result.append((f'left_column1_row{row}',2,a,b,value,star,q))
    # Vertical reflection supplies rows three and four.
    for row in (0,1,2):
        q=Q_BY_ROW[row]
        a,b=endpoint_masks(2,'ooooo',D);a,b=blue_move(2,a,b,row,0)
        for r,p in enumerate(q):
            if p in 'ow':b&=~(1<<(2*r))
        star=1<<1 if row==1 else 0
        result.append((f'right_penultimate_row{row}',2,a,b,-F(1),star,q))
    return result


def central_roots():
    result=[]
    for t,r,q,value in [(2,0,'wobob',F(1,2)),(2,1,'bwbob',-F(1,2)),
                        (1,0,'wbobo',F(1)),(1,2,D,F(1)),
                        (1,3,'owobo'[::-1],F(1)),(1,4,'wbobo'[::-1],F(1))]:
        a,b=endpoint_masks(1,'ooooo','ooooo')
        a,b=white_move(1,a,b,t,0);a,b=blue_move(1,a,b,r,0)
        for row,permission in enumerate(q):
            if permission in 'ow':b&=~(1<<row)
        result.append((f'central_white{t}_blue{r}',1,a,b,value,0,q))
    return result


def numeric_roots():
    result=[]
    for name,w,a,b,value,star,q in cap_roots()+central_roots():
        if star:
            assert star&(star-1)==0 and a&star and b&star
            vertex=star.bit_length()-1
            neighborhood=sum(1<<u for u in board_neighbors(5,w)[vertex])
            assert not neighborhood&(a|b), 'Claimed star is not an isolated shared cell'
            a&=~star;b&=~star
        result.extend([(name+'_upper',w,a,b,-value),
                       (name+'_lower',w,b,a,value)])
    # Exact local right options of the V separator.
    a,b=endpoint_masks(1,'w.wbo','w.wbo')
    for row,value in [(0,-F(1,2)),(2,-F(1,2)),(4,-F(1))]:
        aa,bb=white_move(1,a,b,row,0)
        result.extend([(f'v_reply{row}_upper',1,aa,bb,-value),
                       (f'v_reply{row}_lower',1,bb,aa,value)])
    # Counterexample to the proposed preplayed-phase bound E_X(even)<=0.
    a,b=endpoint_masks(4,D,'bowob');a,b=white_move(4,a,b,0,0)
    result.extend([('corner_phase_x4_upper',4,a,b,-F(1,2)),
                   ('corner_phase_x4_lower',4,b,a,F(1,2))])
    for width,column,rows,patterns in [(3,2,(2,),('D','U','J')),
                                          (4,2,(2,),('R','V')),
                                          (4,3,(1,3),('R','V','X'))]:
        letters={'D':D,'U':'wbobo','J':'owobo','R':'wobob','V':'bwbob','X':'bowob'}
        for row in rows:
            for symbol in patterns:
                assert column+1<=width<=2*column
                assert (row==2) if column%2==0 else (row in (1,3))
                a,b=endpoint_masks(width,D,letters[symbol])
                a,b=white_move(width,a,b,row,column)
                q=-F(1) if symbol=='V' else F(0)
                result.append((f'phase_{symbol.lower()}{width}_p{column}_r{row}_upper',width,a,b,q))
    return result


def embed(w,a,b,start,local_w):
    aa=bb=0
    for r in range(5):
        for c in range(local_w):
            aa|=((a>>(r*local_w+c))&1)<<(r*w+start+c)
            bb|=((b>>(r*local_w+c))&1)<<(r*w+start+c)
    return aa,bb


def check_geometry():
    checks=0
    for n in (5,7,9):
        for name,w,ca,cb,value,star,q in cap_roots():
            a,b=endpoint_masks(n,D,D);a,b=white_move(n,a,b,0,0)
            row=int(name[-1])
            if name.startswith('right_'):
                column=n-2
                a,b=blue_move(n,a,b,row,column)
                ta,tb=endpoint_masks(n-2,D,q)
                ta,tb=white_move(n-2,ta,tb,0,0)
                va,vb=embed(n,ta,tb,0,n-2)
                aa,bb=embed(n,ca,cb,n-2,2)
                va|=aa;vb|=bb;seam=n-3
            else:
                column=0 if w==1 else 1
                a,b=blue_move(n,a,b,row,column)
                ta,tb=endpoint_masks(n-w,q,D)
                va,vb=embed(n,ca,cb,0,w)
                aa,bb=embed(n,ta,tb,w,n-w)
                va|=aa;vb|=bb;seam=w-1
            assert not a&~va,(n,name,'Blue inclusion')
            assert not vb&~b,(n,name,'White inclusion')
            for r in range(5):
                assert not ((vb>>(r*n+seam)&1) and (vb>>(r*n+seam+1)&1)),(n,name,'White seam')
            assert 0<n-w<n
            checks+=1
    for n in (7,9,11,13):
        m=n//2
        for name,w,ca,cb,value,star,q in central_roots():
            t=int(name[13]);r=int(name[-1])
            if (m%2==0 and t!=2) or (m%2!=0 and t!=1):continue
            a,b=endpoint_masks(n,D,D);a,b=white_move(n,a,b,t,m)
            a,b=blue_move(n,a,b,r,m)
            la,lb=endpoint_masks(m,D,q);ra,rb=endpoint_masks(m,q,D)
            va,vb=embed(n,la,lb,0,m)
            aa,bb=embed(n,ca,cb,m,1);va|=aa;vb|=bb
            aa,bb=embed(n,ra,rb,m+1,m);va|=aa;vb|=bb
            assert not a&~va,(n,name,'central Blue inclusion')
            assert not vb&~b,(n,name,'central White inclusion')
            for seam in (m-1,m):
                for row in range(5):
                    assert not ((vb>>(row*n+seam)&1) and (vb>>(row*n+seam+1)&1))
            assert m<n
            checks+=1
    return checks


def check_phase_transfer():
    from dd_reduction_check import rectangle, board_play, permissions, CONTRACTS
    count=0
    for n in range(5,18,2):
        p=n//2
        for t in ((2,) if p%2==0 else (1,3)):
            for r in range(3):
                for c in range(p):
                    aa,bb=rectangle(n)
                    aa,bb=board_play(aa,bb,1,(t,p))
                    if (r,c) not in aa:continue
                    aa,bb=board_play(aa,bb,0,(r,c))
                    va=set();vb=set();regions={}
                    def add_region(a,b,offset,width,region):
                        va.update((rr,cc+offset) for rr,cc in a)
                        vb.update((rr,cc+offset) for rr,cc in b)
                        regions.update({(rr,cc+offset):region for rr in range(5) for cc in range(width)})
                    if c==1:
                        _,cw,ca,cb,_,_,qp=next(x for x in cap_roots() if x[0]==f'right_penultimate_row{r}')
                        q={0:'U',1:'J',2:'D'}[r]
                        cap_a={(rr,1-cc) for rr in range(5) for cc in range(2) if ca>>(2*rr+cc)&1}
                        cap_b={(rr,1-cc) for rr in range(5) for cc in range(2) if cb>>(2*rr+cc)&1}
                        add_region(cap_a,cap_b,0,2,0)
                        k=n-2
                        ra,rb=rectangle(k,q,'D');ra,rb=board_play(ra,rb,1,(t,p-2))
                        add_region(ra,rb,2,k,1)
                    else:
                        if r==0:q='R' if c%2==0 else 'U'
                        elif r==1:q='V' if c%2==0 else 'J'
                        else:q='X' if c%2==0 else 'D'
                        label='corner' if c==0 and r==0 else q
                        _,_,reply,_,sep,_=next(x for x in CONTRACTS if x[0]==label)
                        if reply is not None:aa,bb=board_play(aa,bb,1,(reply,c))
                        if c:
                            la,lb=rectangle(c,'D',q);add_region(la,lb,0,c,0)
                        sa,sb=permissions(sep)
                        add_region({(rr,0) for rr in sa},{(rr,0) for rr in sb},c,1,1)
                        k=n-c-1
                        ra,rb=rectangle(k,q,'D');ra,rb=board_play(ra,rb,1,(t,p-c-1))
                        add_region(ra,rb,c+1,k,2)
                    assert p+1<=k<n
                    if q=='X':assert k%2==0 and k<=2*p-2
                    elif q in ('R','V'):assert k%2==0 and k<=2*p
                    else:assert k%2==1 and k<=2*p-1
                    assert aa<=va and vb<=bb,(n,t,r,c,q,'phase comparison')
                    for rr,cc in vb:
                        for other in ((rr+1,cc),(rr,cc+1)):
                            assert other not in vb or regions[rr,cc]==regions[other],(n,t,r,c,q,'phase seam')
                    count+=1
    return count


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate',action='store_true')
    args=parser.parse_args();summary=[];nodes_total=edges_total=0
    for name,w,a,b,q in numeric_roots():
        path=OUT/(name+'.json.gz')
        if args.generate:
            OUT.mkdir(exist_ok=True)
            doc=generate(5,w,a,b,q)
            path.write_bytes(gzip.compress(json.dumps(doc,separators=(',',':')).encode(),mtime=0))
        doc=json.loads(gzip.decompress(path.read_bytes()))
        expected=(5,w,[a,b,q.numerator,q.denominator])
        assert (doc['height'],doc['width'],doc['root'])==expected, name
        nodes,edges=verify(doc);nodes_total+=nodes;edges_total+=edges
        summary.append({'name':name,'root':expected,'nodes':nodes,'edges':edges})
        print('VERIFIED',name,nodes,edges,flush=True)
    count=check_geometry()
    phase_count=check_phase_transfer()
    if args.generate:
        (OUT/'manifest.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(f'VERIFIED {len(summary)} certificates, {nodes_total} checkpoints, {edges_total} response edges')
    print(f'GEOMETRY REGRESSIONS: {count} caps and {phase_count} phase transfers; infinite scope is proved in round2_wf_delayed_phase.md')

if __name__=='__main__':main()
