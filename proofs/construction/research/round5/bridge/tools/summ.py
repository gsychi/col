import os,re,glob
res={}
for f in sorted(glob.glob('/tmp/5x9/q/logs/scan_o*_u*.out')):
    m=re.search(r'scan_o(\d+)_u(\d+)',f); o,u=int(m[1]),int(m[2])
    lines=[l.split() for l in open(f) if l.startswith('SCAN')]
    fails=[(l[3],float(l[7])) for l in lines if l[5]=='-1']
    done=os.path.exists(f'/tmp/5x9/q/done/scan_o{o}_u{u}.job')
    res.setdefault(o,[]).append((len(fails),u,len(lines),done,fails))
for o in sorted(res):
    print(f'opening {divmod(o,9)}')
    for nf,u,n,d,fails in sorted(res[o]):
        print(f'  reply {divmod(u,9)} fails {nf}/{n} {"done" if d else "running"} ', ' '.join(f'{a}:{b:g}' for a,b in fails))
