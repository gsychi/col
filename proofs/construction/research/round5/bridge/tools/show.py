import gzip, json, sys
from fractions import Fraction
d = json.loads(gzip.decompress(open(sys.argv[1],'rb').read()))
N = d['nodes']; r = d['roots']['pos']
def pic(h,w,a,b):
    rows=[]
    for i in range(h):
        s=''
        for j in range(w):
            v=i*w+j; A=a>>v&1; B=b>>v&1
            s+= 'o' if A and B else 'b' if A else 'w' if B else '.'
        rows.append(s)
    return '/'.join(rows)
def desc(i, depth, maxd):
    n=N[i]; h,w,a,b,qn,qd,s,k=n[:8]
    ind='  '*depth
    if k=='C':
        kids=[]
        for c in n[9]:
            m=N[c[0]]; kids.append(f"{m[0]}x{m[1]} q={m[4]}/{m[5]}{'*' if m[6] else ''} {m[7]}")
        print(ind+f"C {h}x{w} {pic(h,w,a,b)} ret={n[8]} kids: "+'; '.join(kids))
    elif k=='E':
        print(ind+f"E {h}x{w} {pic(h,w,a,b)} q={qn}/{qd}")
        if depth<maxd:
            for e in n[8]:
                print(ind+f" Blue {divmod(e[0],w)} White {divmod(e[1],w)} ->")
                desc(e[2], depth+1, maxd)
    else: print(ind+'A')
desc(r,0,int(sys.argv[2]) if len(sys.argv)>2 else 1)
