#!/usr/bin/env python3
"""Explicit permission masks for the five-row boundary families.

Conventions (see DEFINITIONS.md): rows 0..4 top to bottom, columns 0..n-1,
row-major bit r*n+c, bit 0 top-left. Endpoint letters are read top->bottom:
  D=obwbo U=wbobo V=bwbob X=bowob R=wobob J=owobo
  o = both players legal, b = Blue only, w = White only, . = neither.
PQ_n puts P on column 0 and Q on column n-1 (both read top->bottom, no
vertical flip); at n=1 the two letters are intersected. A one-ended family
P_n puts P on column 0 and leaves every other column neutral (o).
M_n (odd n) is the empty 5 x n board after Blue (2,(n-1)/2), White (0,0).
"""
import sys

H = 5
LETTERS = dict(D="obwbo", U="wbobo", V="bwbob", X="bowob", R="wobob", J="owobo",
               T="bobob")


def empty(n, h=H):
    full = (1 << (h * n)) - 1
    return full, full


def apply_column(a, b, n, col, pattern):
    for r, s in enumerate(pattern):
        bit = 1 << (r * n + col)
        if s not in "ob":
            a &= ~bit
        if s not in "ow":
            b &= ~bit
    return a, b


def two_ended(p, q, n):
    """P on the left end, Q on the right end; intersect at n = 1."""
    a, b = empty(n)
    a, b = apply_column(a, b, n, 0, LETTERS[p])
    a, b = apply_column(a, b, n, n - 1, LETTERS[q])
    return a, b


def one_ended(p, n):
    a, b = empty(n)
    return apply_column(a, b, n, 0, LETTERS[p])


def closed_nbhd(r, c, n, h=H):
    cells = [(r, c), (r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
    return sum(1 << (rr * n + cc) for rr, cc in cells if 0 <= rr < h and 0 <= cc < n)


def blue_move(a, b, r, c, n):
    bit = 1 << (r * n + c)
    assert a & bit, "illegal Blue move"
    return a & ~closed_nbhd(r, c, n), b & ~bit


def white_move(a, b, r, c, n):
    bit = 1 << (r * n + c)
    assert b & bit, "illegal White move"
    return a & ~bit, b & ~closed_nbhd(r, c, n)


def m_family(n):
    assert n % 2 == 1
    a, b = empty(n)
    a, b = blue_move(a, b, 2, (n - 1) // 2, n)
    a, b = white_move(a, b, 0, 0, n)
    return a, b


def diagram(a, b, n, h=H):
    rows = []
    for r in range(h):
        s = ""
        for c in range(n):
            bit = 1 << (r * n + c)
            s += "o" if a & bit and b & bit else "b" if a & bit else "w" if b & bit else "."
        rows.append(s)
    return rows


def family(name, n):
    """Return (a, b) for a family name such as 'DX', 'D', 'M', 'XU'."""
    if name == "M":
        return m_family(n)
    if name == "E":
        return empty(n)
    if len(name) == 1:
        return one_ended(name, n)
    if len(name) == 2:
        return two_ended(name[0], name[1], n)
    raise ValueError(name)


if __name__ == "__main__":
    # Usage: families.py NAME WIDTH [WIDTH...]  -> "5 n A B NAME_n" lines
    name = sys.argv[1]
    for n in map(int, sys.argv[2:]):
        a, b = family(name, n)
        print(H, n, a, b, f"{name}_{n}")
