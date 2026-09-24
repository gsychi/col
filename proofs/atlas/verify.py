#!/usr/bin/env python3
"""Independent search-free strategy checker and exhaustive 5x4 lattice check.
Uses coordinate sets, not the generator's bitwise recurrence. No minimax.
"""
from pathlib import Path
import argparse,gzip,json,time
ROOT=Path(__file__).resolve().parent

def require(p,msg):
    if not p: raise ValueError(msg)

def verify_strategy(path,h,w,root):
    raw=path.read_bytes()
    d=json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)
    require((d['height'],d['width'])==(h,w),'dimensions')
    require(d['root']==list(root),'root')
    n=h*w;full=(1<<n)-1
    nb=[frozenset(rr*w+cc for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)) if 0<=rr<h and 0<=cc<w) for r in range(h) for c in range(w)]
    def verts(m):
        require(type(m)is int and 0<=m<=full,'mask')
        return frozenset(v for v in range(n) if m>>v&1)
    def mask(s):return sum(1<<v for v in s)
    records={}
    for a,b,responses in d['nodes']:
        require((a,b) not in records,'duplicate state')
        records[a,b]=(verts(a),verts(b),responses)
    require(tuple(root) in records,'missing root')
    children={};edges=0
    for key,(A,B,rs) in records.items():
        require(len(rs)==len(A),'first-player coverage')
        children[key]=[]
        for v,r in zip(sorted(A),rs):
            A1,B1=A-{v}-nb[v],B-{v}
            require(type(r)is int and r in B1,'illegal response')
            A2,B2=A1-{r},B1-{r}-nb[r]
            ch=mask(A2),mask(B2)
            require(ch in records,'missing successor')
            require(len(A2|B2)<=len(A|B)-2,'no descent')
            children[key].append(ch);edges+=1
    seen={tuple(root)};stack=list(seen)
    while stack:
        for ch in children[stack.pop()]:
            if ch not in seen:seen.add(ch);stack.append(ch)
    require(len(seen)==len(records),'unreachable checkpoints')
    return len(records),edges

def verify_frontier(h,w):
    root=ROOT/'certificates'/f'{h}x{w}'
    m=json.loads((root/'manifest.json').read_text())
    require((m['height'],m['width'])==(h,w),'shape')
    n=h*w;full=(1<<n)-1;safe=[];bad=[];nodes=edges=0
    for rec in m['records']:
        b=rec['white'];v=rec['blue_winning_move']
        require(0<=b<=full,'white mask')
        if rec['blue_first_loses']:
            require(v==-1,'safe move field');r=(full,b);safe.append(b)
        else:
            require(0<=v<n,'winning opening');rr,cc=divmod(v,w)
            nb={r2*w+c2 for r2,c2 in ((rr-1,cc),(rr+1,cc),(rr,cc-1),(rr,cc+1)) if 0<=r2<h and 0<=c2<w}
            r=(b&~(1<<v),full&~sum(1<<x for x in nb|{v}));bad.append(b)
        p=root/rec['file']
        if not p.exists():p=p.with_suffix('.json.gz')
        N,E=verify_strategy(p,h,w,r);nodes+=N;edges+=E
    require(len(safe)==len(set(safe)) and len(bad)==len(set(bad)),'duplicate frontier')
    cover=bytearray(1<<n)
    for b in safe:
        rem=full^b;s=rem
        while True:
            require(cover[b|s]!=2,'conflicting certificates');cover[b|s]=1
            if not s:break
            s=(s-1)&rem
    for b in bad:
        s=b
        while True:
            require(cover[s]!=1,'conflicting certificates');cover[s]=2
            if not s:break
            s=(s-1)&b
    require(0 not in cover,'incomplete lattice coverage')
    actual_safe={i for i,x in enumerate(cover) if x==1}
    data=json.loads((ROOT/'data'/f'full{h}x{w}_frontier.json').read_text())
    require(actual_safe==set(data['safe_white_masks']),'atlas disagreement')
    require(set(safe)==set(data['minimal_safe_white_masks']),'safe frontier mismatch')
    require(set(bad)==set(data['maximal_unsafe_white_masks']),'unsafe frontier mismatch')
    # Independently check that these really are the two irredundant frontiers.
    require(all(not any(c!=b and c&b==c for c in safe) for b in safe),'nonminimal safe root')
    require(all(not any(c!=b and c|b==c for c in bad) for b in bad),'nonmaximal unsafe root')
    def ports(b):
        return (sum(((b>>(r*w))&1)<<r for r in range(h)),sum(((b>>(r*w+w-1))&1)<<r for r in range(h)),b&((1<<w)-1),(b>>(w*(h-1)))&((1<<w)-1))
    ps=[ports(b) for b in actual_safe]
    horizontal=sum(not(a[1]&b[0]) for a in ps for b in ps)
    vertical=sum(not(a[3]&b[2]) for a in ps for b in ps)
    if (h,w)==(5,4):require(horizontal==0 and vertical==0,'5x4 seam assertion')
    return {'height':h,'width':w,'masks':1<<n,'safe_masks':len(actual_safe),'unsafe_masks':len(cover)-len(actual_safe),'minimal_safe':len(safe),'maximal_unsafe':len(bad),'certificates':len(m['records']),'checkpoints':nodes,'response_edges':edges,'horizontal_safe_joins':horizontal,'vertical_safe_joins':vertical}

def main():
    start=time.monotonic();summaries=[]
    for path in sorted((ROOT/'data').glob('full*x*_frontier.json')):
        d=json.loads(path.read_text());result=verify_frontier(d['height'],d['width']);summaries.append(result)
        print(f"VERIFIED {result['height']}x{result['width']}: {result['safe_masks']}/{result['masks']} safe; {result['minimal_safe']} minimal supports")
    summary={'shapes':len(summaries),'classified_masks':sum(x['masks'] for x in summaries),'safe_masks':sum(x['safe_masks'] for x in summaries),'minimal_safe':sum(x['minimal_safe'] for x in summaries),'certificates':sum(x['certificates'] for x in summaries),'checkpoints':sum(x['checkpoints'] for x in summaries),'response_edges':sum(x['response_edges'] for x in summaries),'seconds':time.monotonic()-start,'by_shape':summaries}
    print(json.dumps(summary,indent=2))
    (ROOT/'logs/verification_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('VERIFIED: complete full-Blue White-permission classifications on every listed shape.')

if __name__=='__main__':main()
