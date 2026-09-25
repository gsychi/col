#!/usr/bin/env python3
"""Check the prescribed corner branch; no search for moves or strategies."""
from round2_height_twin_check import evaluator, game, leq, ZERO


PATTERNS = dict(O="ooooo", D="obwbo", U="wbobo", V="bwbob", X="bowob",
                R="wobob", J="owobo", Y="bowbb")


def grid(m, n):
    cells = {(r, c) for r in range(m) for c in range(n)}
    neighbors = {v: cells & {(v[0] - 1, v[1]), (v[0] + 1, v[1]),
                             (v[0], v[1] - 1), (v[0], v[1] + 1)} for v in cells}
    return cells, neighbors


def rectangle(n, left, right):
    a, neighbors = grid(5, n)
    b = set(a)
    for c, pattern in ((0, PATTERNS[left]), (n - 1, PATTERNS[right])):
        a -= {(r, c) for r, s in enumerate(pattern) if s not in "ob"}
        b -= {(r, c) for r, s in enumerate(pattern) if s not in "ow"}
    return a, b, neighbors


def play(a, b, neighbors, who, v):
    a, b = set(a), set(b)
    if who == "B":
        assert v in a
        return a - {v} - neighbors[v], b - {v}
    assert v in b
    return a - {v}, b - {v} - neighbors[v]


def check_cap():
    edges = {(r * 3 + c, rr * 3 + cc) for r in range(2) for c in range(3)
             for rr, cc in ((r + 1, c), (r, c + 1)) if rr < 2 and cc < 3}
    evaluate = evaluator(6, edges)
    star = game([ZERO], [ZERO])
    for b in (59, 58):  # wob / ooo, and the smaller support .ob / ooo
        cap = evaluate(62, b)
        assert leq(cap, star) and leq(star, cap)
        assert not leq(cap, ZERO) and not leq(ZERO, cap)
    print("VERIFIED 2x3 caps (A=62,B=59/58) both equal star; smaller support permits X")


def check_new_boundary_obstruction():
    a, b, neighbors = rectangle(2, "D", "Y")
    mask = lambda cells: sum(1 << (r * 2 + c) for r, c in cells)
    edges = {(r * 2 + c, rr * 2 + cc)
             for (r, c), adjacent in neighbors.items() for rr, cc in adjacent}
    evaluate = evaluator(10, edges)
    assert (mask(a), mask(b)) == (975, 313)
    root = evaluate(mask(a), mask(b))
    one = game([ZERO], [])
    half = game([ZERO], [one])
    assert leq(root, half) and leq(half, root)
    aa, bb = play(a, b, neighbors, "B", (0, 0))
    assert (mask(aa), mask(bb)) == (968, 312)
    child = evaluate(mask(aa), mask(bb))
    assert leq(ZERO, child)
    print("VERIFIED DY2=1/2 and its Blue (0,0) child >=0; uniform star-compensated leaf target fails")


def branch_checks():
    count = 0
    for n in range(4, 13):
        k = n - 3
        for left in "ODUVXRJ":
            for right in "OD":
                initial_a, initial_b, neighbors = rectangle(n, left, right)
                for z in sorted(v for v in initial_a if v[1] < k):
                    a, b = play(initial_a, initial_b, neighbors, "B", z)
                    a, b = play(a, b, neighbors, "W", (0, k))
                    if (2, k) not in a:
                        assert z == (2, k - 1)
                        continue
                    a, b = play(a, b, neighbors, "B", (2, k))
                    a, b = play(a, b, neighbors, "W", (2, k + 2))
                    reverse_a, reverse_b = play(initial_a, initial_b, neighbors, "B", (2, k))
                    reverse_a, reverse_b = play(reverse_a, reverse_b, neighbors, "W", (0, k))
                    reverse_a, reverse_b = play(reverse_a, reverse_b, neighbors, "B", z)
                    reverse_a, reverse_b = play(reverse_a, reverse_b, neighbors, "W", (2, k + 2))
                    assert (a, b) == (reverse_a, reverse_b)
                    twins = {(0, k + 2), (1, k + 1)}
                    common = {(0, k + 1), (1, k + 2)}
                    assert twins <= a & b
                    assert all(neighbors[v] & (a | b) == common for v in twins)
                    assert all(not (neighbors[v] & common) for v in common)
                    assert common <= a and not common & b
                    a -= twins | common
                    b -= twins | common
                    assert not (a | b) & {(r, c) for r in range(3) for c in range(k, n)}

                    for endpoint, cap_top in (("X", ".ob"), ("Y", "wob")):
                        va, vb, small_neighbors = rectangle(k, left, endpoint)
                        va, vb = play(va, vb, small_neighbors, "B", z)
                        owner = {v: 0 for v in small_neighbors}
                        for rr, pattern in enumerate((cap_top, "ooo"), start=3):
                            for cc, permission in enumerate(pattern, start=k):
                                owner[rr, cc] = 1
                                if permission in "ob":
                                    va.add((rr, cc))
                                if permission in "ow":
                                    vb.add((rr, cc))
                        assert a <= va and vb <= b, (n, left, right, z, endpoint)
                        for v in vb:
                            for w in neighbors[v] & vb:
                                assert owner[v] == owner[w]
                    assert k < n
                    count += 1
    print(f"VERIFIED {count} corner branches, both temporal orders, and both X/Y interfaces")


def no_twins_after_two_moves():
    count = 0
    for m in range(3, 7):
        for n in range(3, 8):
            cells, neighbors = grid(m, n)
            for blue in cells:
                a, b = play(cells, cells, neighbors, "B", blue)
                for white in b:
                    aa, bb = play(a, b, neighbors, "W", white)
                    live = aa | bb
                    seen = set()
                    for v in aa & bb:
                        key = frozenset(neighbors[v] & live)
                        assert key not in seen
                        seen.add(key)
                    count += 1
    print(f"REGRESSION: {count} two-move positions have no shared false twins")


if __name__ == "__main__":
    check_cap()
    check_new_boundary_obstruction()
    branch_checks()
    no_twins_after_two_moves()
