#!/usr/bin/env python3
"""Finite, search-free regressions for the symbolic reflection obstruction.

No minimax, sampled game values, or inference from a tested maximum width.
The quantified proofs are in round2_height_reflection_obstruction.md.
"""
from itertools import product


def grid(m, n):
    cells = {(r, c) for r in range(m) for c in range(n)}
    closed = {}
    for r, c in cells:
        closed[r, c] = cells & {(r, c), (r - 1, c), (r + 1, c),
                               (r, c - 1), (r, c + 1)}
    return cells, closed


def permissions(cells, closed, blue_stones, white_stones):
    assert not blue_stones & white_stones
    a = cells - white_stones
    b = cells - blue_stones
    for v in blue_stones:
        a -= closed[v]
    for v in white_stones:
        b -= closed[v]
    return a, b


def eligible_axis(m, n, a, b):
    k = n // 2
    return {(r, k) for r in range(m)
            if (r, k) in b and (r, k - 1) not in a and (r, k + 1) not in a}


def opening_reply_checks():
    pairs = 0
    intersections = 0
    positive_axis = 0
    for m in (3, 5, 7, 9, 11):
        for n in (3, 5, 7):
            cells, closed = grid(m, n)
            k = n // 2
            axis = {(r, k) for r in range(m)}
            for r in range(m):
                assert closed[r, k - 1] & closed[r, k + 1] == {(r, k)}
                intersections += 1
            for blue in cells:
                for white in cells - {blue}:
                    a, b = permissions(cells, closed, {blue}, {white})
                    assert not eligible_axis(m, n, a, b)
                    assert len(axis - a) <= 4
                    if m >= 5:
                        assert axis & a
                        positive_axis += 1
                    pairs += 1
    print(f"VERIFIED {intersections} neighborhood intersections and {pairs} "
          f"opening/reply support checks; {positive_axis} positive-axis obligations")


def support_budget_checks():
    m = n = 3
    cells, closed = grid(m, n)
    ordered = sorted(cells)
    axis = {(r, 1) for r in range(m)}
    count = 0
    # Includes unreachable same-color-adjacent assignments. The support
    # inequalities hold even in this larger class, hence also for legal play.
    for assignment in product(range(3), repeat=9):
        blue = {v for v, color in zip(ordered, assignment) if color == 1}
        white = {v for v, color in zip(ordered, assignment) if color == 2}
        a, b = permissions(cells, closed, blue, white)
        eligible = eligible_axis(m, n, a, b)
        left = {v for v in blue if v[1] < 1}
        right = {v for v in blue if v[1] > 1}
        assert len(eligible) <= 3 * min(len(left), len(right))
        assert 2 * len(eligible) <= 3 * len(blue)
        assert len(axis - a) <= 3 * len(blue) + len(white)
        if len(blue) == 1:
            assert not eligible
        count += 1
    print(f"VERIFIED support budgets on all {count} disjoint 3x3 assignments")


if __name__ == "__main__":
    opening_reply_checks()
    support_budget_checks()
    print("REGRESSION ONLY: all-width conclusions use the symbolic proof.")
