#!/usr/bin/env python3
"""All-options exact-order checks for three finite graph counterexamples."""
from round2_height_twin_check import evaluator,game,leq,ZERO

STAR=game([ZERO],[ZERO])


def exact_star(name,n,edges,mask):
    evaluate=evaluator(n,edges)
    value=evaluate(mask,mask)
    assert leq(value,STAR) and leq(STAR,value)
    assert not leq(value,ZERO) and not leq(ZERO,value)
    print(f'VERIFIED {name} = star; {evaluate.cache_info().currsize} permission states')


def main():
    edges={(0,3),(0,4),(0,5),(1,4),(2,3)}
    matching={(0,5),(1,4),(2,3)}
    assert matching<=edges and {v for e in matching for v in e}==set(range(6))
    assert all(u<3<=v for u,v in edges)
    exact_star('perfect-matching tree',6,edges,63)

    edges={(v,v+1) for v in range(9)}|{(0,5),(3,8),(1,8)}
    assert all((v,v+1) in edges for v in range(9))
    assert all((u-v)%2 for u,v in edges)
    exact_star('even bipartite graph with a Hamiltonian path',10,edges,1023)

    cells={(r,c) for r in range(3) for c in range(5)}-{(r,c) for r in (0,2) for c in (0,4)}
    assert len(cells)==11
    assert {(2-r,c) for r,c in cells}==cells
    assert {(r,4-c) for r,c in cells}==cells
    for r in range(3):
        row=sorted(c for rr,c in cells if rr==r)
        assert row==list(range(row[0],row[-1]+1)) and len(row)%2
    for c in range(5):
        col=sorted(r for r,cc in cells if cc==c)
        assert col==list(range(col[0],col[-1]+1)) and len(col)%2
    reached={next(iter(cells))}
    while True:
        enlarged=reached|{v for v in cells if any(abs(v[0]-u[0])+abs(v[1]-u[1])==1 for u in reached)}
        if enlarged==reached:break
        reached=enlarged
    assert reached==cells
    edges={(r*5+c,rr*5+cc) for r,c in cells for rr,cc in ((r+1,c),(r,c+1)) if (rr,cc) in cells}
    mask=sum(1 << (r*5+c) for r,c in cells)
    assert mask==15342
    exact_star('clipped 3x5 grid',15,edges,mask)
    for n in (3,5):
        evaluate=evaluator(n,{(v,v+1) for v in range(n-1)})
        value=evaluate((1<<n)-1,(1<<n)-1)
        assert leq(value,ZERO) and leq(ZERO,value)
    print('VERIFIED both fixed paths = zero and all stated graph properties')


if __name__=='__main__':main()
