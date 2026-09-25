#!/usr/bin/env python3
"""Independent finite certificates for reusable near-end marked-phase caps.

Default mode verifies stored response DAGs and coordinate geometry; --generate
rediscovers certificates and updates the manifest.
"""
from pathlib import Path
from fractions import Fraction as F
import argparse,gzip,json
from number_certificates import generate,verify
from wf_white_first_check import endpoint_masks,white_move
from round2_wf_check import blue_move,embed
from round4_wf_caps_probe import PAT,PAR,interface,cap,restrict
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'round4_wf_certificates'
# Bind imported discovery labels to the mathematical endpoint definitions.
assert PAT=={'D':'obwbo','U':'wbobo','V':'bwbob','X':'bowob','R':'wobob','J':'owobo'}
assert PAR=={'D':1,'U':1,'J':1,'V':0,'X':0,'R':0}

def contracts():
    out=[]
    def add(family,w,q,p,t,r,bound,reply=None):
        s,pattern=interface(PAR[q]^(w%2),r)
        state=cap(w,q,p,t,r)
        if state is None:return
        if p==0:assert pattern[t] not in 'ow'
        a,b=restrict(w,*state,pattern)
        if reply is not None:
            rr,cc=reply
            assert cc!=0 or pattern[rr] not in 'ow'
            a,b=white_move(w,a,b,rr,cc)
        name=f'{family}_{q.lower()}{w}_p{p}_t{t}_r{r}'
        out.append(dict(name=name,family=family,w=w,Q=q,p=p,t=t,r=r,S=s,pattern=pattern,a=a,b=b,bound=str(bound),reply=reply))
    # D is vertically symmetric, so r>2 is obtained by reflecting both moves.
    for w in (2,3,4):
        cpar=1^(w%2)
        for p in range(w):
            for t in ([2] if (cpar+p)%2==0 else [1,3]):
                for r in range(3):
                    if not endpoint_masks(w,'ooooo',PAT['D'])[1]>>(t*w+p)&1:continue
                    s,_=interface(cpar,r)
                    bound={'U':F(0),'J':F(1,4),'D':F(0),'R':F(0),'V':-F(1),'X':F(0)}[s]
                    add('dend',w,'D',p,t,r,bound)
    # Endpoint-marked U and J are asymmetric: explicitly certify all five rows.
    for q in ('U','J'):
        for w in (2,3):
            for r in range(5):
                s,_=interface(1^(w%2),r)
                bound={'U':F(0),'J':F(1,4),'D':F(0),'R':F(0),'V':-F(1),'X':F(0)}[s]
                add('endmark',w,q,w-1,2,r,bound)
    add('xsame',2,'X',0,2,0,F(1,8))
    add('xsame',2,'X',0,2,1,-F(1))
    add('reply',3,'U',1,1,2,F(0),(4,0))
    add('reply',3,'J',1,1,0,F(1,4),(0,2))
    add('reply',2,'R',1,1,2,F(0),(0,0))
    return out

def geometry(cs):
    count=0
    for x in cs:
        w,q,p,t,r,s=x['w'],x['Q'],x['p'],x['t'],x['r'],x['S']
        # All examples are in the exact reachable phase domain and have a
        # strictly smaller ordinary width where its original target applies.
        for left in range(2,23):
            if left%2 != PAR[q]^(w%2):continue
            n=left+w;mark=left+p
            hi=2*mark-(2 if q=='X' else 1 if PAR[q] else 0)
            if not(mark>=2 and mark+1<=n<=hi):continue
            if left%2:assert left>=3
            a,b=endpoint_masks(n,PAT['D'],PAT[q])
            a,b=white_move(n,a,b,t,mark)
            a,b=blue_move(n,a,b,r,left)
            if x['reply'] is not None:
                rr,cc=x['reply'];a,b=white_move(n,a,b,rr,left+cc)
            la,lb=endpoint_masks(left,PAT['D'],x['pattern'])
            va,vb=embed(n,la,lb,0,left)
            aa,bb=embed(n,x['a'],x['b'],left,w);va|=aa;vb|=bb
            assert not a&~va and not vb&~b,(x['name'],left,'permissions')
            for rr in range(5):assert not (vb>>(rr*n+left-1)&1 and vb>>(rr*n+left)&1)
            assert 0<left<n
            count+=1
    return count

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--generate',action='store_true');args=ap.parse_args()
    cs=contracts();summary=[];totaln=totale=0
    for x in cs:
        name=x['name'];q=-F(x['bound']);path=OUT/(name+'.json.gz')
        if args.generate:
            OUT.mkdir(exist_ok=True)
            doc=generate(5,x['w'],x['a'],x['b'],q)
            path.write_bytes(gzip.compress(json.dumps(doc,separators=(',',':')).encode(),mtime=0))
        doc=json.loads(gzip.decompress(path.read_bytes()))
        assert (doc['height'],doc['width'],doc['root'])==(5,x['w'],[x['a'],x['b'],q.numerator,q.denominator]),name
        n,e=verify(doc);totaln+=n;totale+=e
        summary.append({**x,'root':doc['root'],'checkpoints':n,'edges':e})
        print('VERIFIED',name,n,e,flush=True)
    embeds=geometry(cs)
    if args.generate:(OUT/'manifest.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(f'VERIFIED {len(cs)} certificates, {totaln} checkpoints, {totale} response edges')
    print(f'REGRESSION: {embeds} reachable cap embeddings, all decreasing width')
if __name__=='__main__':main()
