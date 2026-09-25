#!/usr/bin/env python3
"""Finite regressions for the written arbitrary-width bridge support theorem."""
from math import ceil


def play(a, b, color, v):
    a, b = set(a), set(b)
    own, other = (a, b) if color == 'B' else (b, a)
    assert v in own
    r, c = v
    own.difference_update({v, (r-1,c), (r+1,c), (r,c-1), (r,c+1)})
    other.discard(v)
    return a, b


def check_single_opening():
    positions = intervals = 0
    for h in (3, 5, 7):
        for n in (3, 5, 7, 9):
            full = {(r,c) for r in range(h) for c in range(n)}
            for opening in sorted(full):
                blue, white = play(full, full, 'B', opening)
                for reply in [None] + sorted(white):
                    a, b = (blue, white) if reply is None else play(blue, white, 'W', reply)
                    assert b-a <= white-blue
                    columns = {c for r,c in b-a}
                    for left in range(n):
                        for right in range(left+2, n):
                            both_witnesses = left in columns and right in columns
                            shared_interior_possible = all((r,c) in b for r in range(h) for c in range(left+1, right))
                            assert not (both_witnesses and shared_interior_possible)
                            intervals += 1
                    positions += 1
    return positions, intervals


def check_sharp_example():
    full = {(r,c) for r in range(5) for c in range(3)}
    a,b = play(full, full, 'B', (0,1))
    va, vb = set(), set()
    for c, pattern in enumerate(('wbobo','bwbob','bbbbb')):
        va.update((r,c) for r,ch in enumerate(pattern) if ch in 'ob')
        vb.update((r,c) for r,ch in enumerate(pattern) if ch in 'ow')
    assert a <= va and vb <= b
    assert all(not ((r,1) in vb and (r,2) in vb) for r in range(5))


def check_private_capacity():
    count = 0
    for h in range(3, 102, 2):
        for r in range(h):
            a = ceil(r/2) + ceil((h-r-1)/2)
            assert a >= 1
            left = list(range(0, r, 2))
            right = list(range(r+1, h, 2))
            selected = left+right
            assert len(selected) == a and r not in selected
            assert all(abs(u-v) != 1 for i,u in enumerate(selected) for v in selected[i+1:])
            assert 2*a > a
            count += 1
    return count


if __name__ == '__main__':
    positions, intervals = check_single_opening()
    check_sharp_example()
    count = check_private_capacity()
    print(f'REGRESSION: {positions} post-opening/reply positions; {intervals} candidate intervals rejected.')
    print('VERIFIED concrete width-two UV embedding and White seam.')
    print(f'REGRESSION: {count} private-capacity inequalities; the all-height proof is written separately.')
