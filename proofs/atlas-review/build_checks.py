#!/usr/bin/env python3
"""Generate exact counterstrategy DAGs for the four proposed bare L remainders.
No outcome is inferred from a time or node limit. No production solver is used.
"""
from functools import lru_cache
from pathlib import Path
import gzip,json
ROOT=Path(__file__).resolve().parent

def build(h,w,phase):
    cells=[(r,w-1) for r in range(h)]+[(h-1,c) for c in range(w-2,-1,-1)]
    def adj(u,v): return abs(u[0]-v[0])+abs(u[1]-v[1])==1
    nb=[sum(1<<j for j,v in enumerate(cells) if i==j or adj(u,v)) for i,u in enumerate(cells)]
    n=len(cells);full=(1<<n)-1
    bulk=[(r,c) for r in range(h-1) for c in range(w-1)]
    white_bulk=[v for v in bulk if sum(v)%2==phase]
    white=sum(1<<i for i,u in enumerate(cells) if not any(adj(u,v) for v in white_bulk))
    @lru_cache(None)
    def wins(a,b):
        x=a
        while x:
            v=x&-x;x^=v
            if not wins(b&~v,a&~nb[v.bit_length()-1]):return True
        return False
    assert wins(full,white) and not wins(white,full)
    opening=next(i for i in range(n) if not wins(white&~(1<<i),full&~nb[i]))
    roots=[(white,full),(white&~(1<<opening),full&~nb[opening])]
    records={}
    def visit(a,b):
        if (a,b) in records:return
        assert not wins(a,b)
        replies=[];records[a,b]=replies
        for i in range(n):
            if not (a>>i)&1:continue
            a1=a&~nb[i];b1=b&~(1<<i)
            j=next(j for j in range(n) if (b1>>j)&1 and not wins(a1&~(1<<j),b1&~nb[j]))
            replies.append(j);visit(a1&~(1<<j),b1&~nb[j])
    for root in roots:visit(*root)
    doc={'height':h,'width':w,'bulk_checkerboard_phase':phase,'path_cells':cells,
         'blue':full,'white':white,'blue_first_winning_move':opening,
         'losing_actor':'White','roots':roots,'nodes':[[a,b,rs] for (a,b),rs in records.items()]}
    file=ROOT/f'L_{h}x{w}_phase{phase}.json.gz'
    with gzip.open(file,'wt') as f:json.dump(doc,f,separators=(',',':'))
    return {'file':file.name,'target':[h,w],'bulk':[h-1,w-1],'phase':phase,
            'path':' '.join('o' if white>>i&1 else 'b' for i in range(n)),
            'outcome':'Blue wins with either starting player','checkpoints':len(records),
            'response_edges':sum(len(x) for x in records.values()),'search_states':wins.cache_info().currsize}

if __name__=='__main__':
    rows=[build(h,w,phase) for h,w in [(5,9),(7,7)] for phase in [0,1]]
    (ROOT/'l_shape_results.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps(rows,indent=2))
