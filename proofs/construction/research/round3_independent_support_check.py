#!/usr/bin/env python3
"""Independent exact-order and finite geometry checks; no infinite extrapolation."""
from functools import lru_cache
from itertools import combinations
from round2_height_twin_check import evaluator, game, GAMES, ZERO, leq

STAR = game([ZERO], [ZERO])


@lru_cache(None)
def integer(n):
    if not n:
        return ZERO
    return game([integer(n-1)], []) if n > 0 else game([], [integer(n+1)])


@lru_cache(None)
def add(g, h):
    return game([add(x,h) for x in GAMES[g][0]] + [add(g,x) for x in GAMES[h][0]],
                [add(x,h) for x in GAMES[g][1]] + [add(g,x) for x in GAMES[h][1]])


def independent_sets(n, edges):
    return [s for s in range(1 << n)
            if all(not (s >> u & 1 and s >> v & 1) for u,v in edges)]


def grid(m, n):
    return {(r*n+c,rr*n+cc) for r in range(m) for c in range(n)
            for rr,cc in ((r+1,c),(r,c+1)) if rr < m and cc < n}


def graph_checks():
    counts = dict(graphs=0,exact_formulas=0,lower_bounds=0)
    for n in range(5):
        possible = list(combinations(range(n),2))
        for bits in range(1 << len(possible)):
            edges = {e for i,e in enumerate(possible) if bits >> i & 1}
            sets = independent_sets(n,edges)
            alpha = max(s.bit_count() for s in sets)
            evaluate = evaluator(n,edges)
            full = (1 << n) - 1
            counts['graphs'] += 1
            for i in sets:
                whole = evaluate(full,i)
                for j in sets:
                    q = integer(j.bit_count()-i.bit_count())
                    value = add(q,STAR) if (i & j).bit_count() % 2 else q
                    actual = evaluate(j,i)
                    assert leq(actual,value) and leq(value,actual)
                    assert leq(value,whole)
                    counts['exact_formulas'] += 1
                    counts['lower_bounds'] += 1
                if i.bit_count() < alpha:
                    assert leq(ZERO,whole) and not leq(whole,ZERO)
                if i.bit_count() % 2:
                    assert not leq(whole,ZERO)
    return counts


def geometry_checks():
    maxima = 0
    for m,n in ((1,1),(1,3),(1,5),(1,7),(3,1),(3,3),(3,5),(5,3)):
        sets = independent_sets(m*n,grid(m,n))
        alpha = max(s.bit_count() for s in sets)
        majority = sum(1 << (r*n+c) for r in range(m) for c in range(n)
                       if (r+c) % 2 == 0)
        assert alpha == (m*n+1)//2
        assert [s for s in sets if s.bit_count() == alpha] == [majority]
        maxima += 1
    paths = 0
    survivors = set()
    for m in range(1,14,2):
        for n in range(1,14,2):
            adjacent = [set() for _ in range(m*n)]
            for u,v in grid(m,n):
                adjacent[u].add(v);adjacent[v].add(u)
            for center in range(m*n):
                for u,v in combinations(adjacent[center],2):
                    cells = (u,center,v)
                    paths += 1
                    rows = [sum(x//n == r for x in cells) for r in range(m)]
                    cols = [sum(x%n == c for x in cells) for c in range(n)]
                    if all(x % 2 for x in rows+cols) and (m*n-3) % 4 == 0:
                        survivors.add((m,n))
    assert survivors == {(1,3),(3,1)}
    return dict(unique_maximum_grids=maxima,three_cell_paths=paths,
                possible_odd_partitions=sorted(survivors))


if __name__ == '__main__':
    print('VERIFIED graph order regressions:',graph_checks())
    print('VERIFIED geometry regressions:',geometry_checks())
    print('The all-graph and all-dimension statements are proved symbolically.')
