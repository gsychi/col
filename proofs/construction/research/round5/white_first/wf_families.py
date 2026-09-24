#!/usr/bin/env python3
"""Masks for the white_first stream: the ground-truth letters plus the K end.

Conventions as in ground_truth/DEFINITIONS.md: 5 rows, row-major bit r*n+c,
A = Blue-legal, B = White-legal. Letters are read top->bottom on BOTH ends
(no vertical flip on the right end); at width 1 the two end columns are
intersected.

New endpoint letter K ("D after White's private reserve move"):
  K_n := DD_n after White plays (2,0).
The White stone at (2,0) makes (2,0) dead and removes White permission at
(1,0), (3,0) (already Blue-only in D) and (2,1). So the K end is the column
pattern `ob.bo` on column 0 together with "no White permission at (2,1)".
KQ_a for a >= 2: column 0 = ob.bo, column a-1 = Q, and (2,1) White-removed
(when a = 2 this acts on the Q column). KQ_1 is the column ob.bo intersected
with Q (the (2,1) cell does not exist).
QK_a is the horizontal mirror of KQ_a (K on the right end).
"""
import sys
from pathlib import Path

H = 5
LETTERS = dict(D="obwbo", U="wbobo", V="bwbob", X="bowob", R="wobob", J="owobo",
               T="bobob", K="ob.bo", N="ooooo")


def empty(n):
    full = (1 << (H * n)) - 1
    return full, full


def apply_column(a, b, n, col, pattern):
    for r, s in enumerate(pattern):
        bit = 1 << (r * n + col)
        if s not in "ob":
            a &= ~bit
        if s not in "ow":
            b &= ~bit
    return a, b


def bit(r, c, n):
    return 1 << (r * n + c)


def two_ended(p, q, n):
    """Letter p on column 0, letter q on column n-1. K on either end also
    removes White at row 2 of the adjacent column."""
    a, b = empty(n)
    a, b = apply_column(a, b, n, 0, LETTERS[p])
    a, b = apply_column(a, b, n, n - 1, LETTERS[q])
    if p == "K" and n >= 2:
        b &= ~bit(2, 1, n)
    if q == "K" and n >= 2:
        b &= ~bit(2, n - 2, n)
    return a, b


def closed_nbhd(r, c, n):
    cells = [(r, c), (r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
    return sum(1 << (rr * n + cc) for rr, cc in cells if 0 <= rr < H and 0 <= cc < n)


def blue_move(a, b, r, c, n):
    m = bit(r, c, n)
    assert a & m, "illegal Blue move"
    return a & ~closed_nbhd(r, c, n), b & ~m


def white_move(a, b, r, c, n):
    m = bit(r, c, n)
    assert b & m, "illegal White move"
    return a & ~m, b & ~closed_nbhd(r, c, n)


# Stone letters. P* is the column of a Blue opening at row r, paired with the
# plain letter P = (row r White-only, White kept on rows T'): the stone column
# keeps White exactly on the rows outside T' (other than r); the inner
# neighbour of the stone column loses Blue at row r (effect of the move).
# These are the round-4 separators: U*=.wbob R*=..obo V*=w.wbo J*=...ob
# X*=o...o D*=bw.wb.
PLAIN = dict(U=(0, {2, 4}), R=(0, {1, 3}), V=(1, {3}), J=(1, {0, 2, 4}),
             X=(2, {1, 3}), D=(2, {0, 4}))


def stone_rows(p):
    r, keep = PLAIN[p]
    return r, {x for x in range(H) if x != r and x not in keep}


def stone_end(a, b, n, col, p):
    """Apply a stone letter p* on end column col: the actual Blue move at
    (r, col), then drop White on rows of col outside the kept set."""
    r, keep = stone_rows(p)
    a, b = blue_move(a, b, r, col, n)
    for x in range(H):
        if x not in keep:
            b &= ~bit(x, col, n)
    return a, b


def pair(left, right, n):
    """General two-ended strip. left/right are letters, 'P*' stone letters,
    or 'N' (neutral). Stone letters need n >= 2; a stone next to K acts on
    the K strip (the K effect at (2,1) is applied first)."""
    lp = left.rstrip("*")
    rp = right.rstrip("*")
    a, b = two_ended("N" if left.endswith("*") else lp, "N" if right.endswith("*") else rp, n)
    if left.endswith("*"):
        assert n >= 2
        a, b = stone_end(a, b, n, 0, lp)
    if right.endswith("*"):
        assert n >= 2
        a, b = stone_end(a, b, n, n - 1, rp)
    return a, b


def pair_with_k(right, n):
    """K on the left and `right` (plain or stone) on the right."""
    if not right.endswith("*"):
        return two_ended("K", right, n)
    a, b = two_ended("K", "N", n)
    return stone_end(a, b, n, n - 1, right[0])


def fam(name, n):
    """Names: 'KU', 'KU*', 'U*D', 'DU', 'KD', ..."""
    if name.startswith("K"):
        return pair_with_k(name[1:], n)
    if name[1] == "*":
        return pair(name[:2], name[2:], n)
    return pair(name[0], name[1:], n)


def family(name, n):
    if "*" in name or (name.startswith("K") and len(name) > 1):
        return fam(name, n)
    if len(name) == 2:
        return two_ended(name[0], name[1], n)
    if len(name) == 1:
        return two_ended(name, "N", n) if n >= 2 else apply_column(*empty(1), 1, 0, LETTERS[name])
    raise ValueError(name)


def diagram(a, b, n):
    rows = []
    for r in range(H):
        s = ""
        for c in range(n):
            m = bit(r, c, n)
            s += "o" if a & m and b & m else "b" if a & m else "w" if b & m else "."
        rows.append(s)
    return rows


def self_test():
    """K_n equals DD_n after White (2,0) for every n >= 1, and every
    non-K family agrees with ground_truth/families.py."""
    gt = Path(__file__).resolve().parent.parent / "ground_truth"
    sys.path.insert(0, str(gt))
    import families as F  # noqa: E402  (ground-truth reference, read-only)
    for n in range(1, 13):
        a, b = F.family("DD", n)
        assert white_move(a, b, 2, 0, n) == family("KD", n), n
        for p in "DUVXRJ":
            for q in "DUVXRJ":
                assert family(p + q, n) == F.family(p + q, n), (p, q, n)
    return True


if __name__ == "__main__":
    if sys.argv[1:] == ["--test"]:
        print("self-test", self_test())
        sys.exit(0)
    name = sys.argv[1]
    for n in map(int, sys.argv[2:]):
        a, b = family(name, n)
        print(H, n, a, b, f"{name}_{n}")
