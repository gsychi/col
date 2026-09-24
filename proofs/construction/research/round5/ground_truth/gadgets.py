#!/usr/bin/env python3
"""Number/star gadgets placed in spare columns of an ambient board.

A gadget is a permission pattern on a 5-cell vertical path (one column).
Its exact value is computed by the independent short-game evaluator in
gadget_value() (plain recursive Conway order on all options, no Col theorem)
and cross-checked against colval. Used to realise G - q with the Rust
outcome solver: ambient width n+2, column n dead, column n+1 = gadget.
"""
from fractions import Fraction as F
from functools import lru_cache
import itertools

# ---------------------------------------------------------------- short games
# A game is a pair (frozenset of Left options, frozenset of Right options);
# canonical-form arithmetic is avoided: we only need <= and equality tests.


@lru_cache(None)
def path_game(a, b, n):
    """Col on a path of n cells with legal sets a (Blue) and b (White)."""
    lefts, rights = [], []
    for v in range(n):
        bit = 1 << v
        nb = bit | (bit << 1 & ((1 << n) - 1)) | (bit >> 1)
        if a & bit:
            lefts.append(path_game(a & ~nb, b & ~bit, n))
        if b & bit:
            rights.append(path_game(a & ~bit, b & ~nb, n))
    return (tuple(sorted(set(lefts), key=repr)), tuple(sorted(set(rights), key=repr)))


def neg(g):
    return (tuple(neg(x) for x in g[1]), tuple(neg(x) for x in g[0]))


@lru_cache(None)
def le(g, h):
    """g <= h  iff no g^L >= h and no h^R <= g."""
    return not any(le(h, gl) for gl in g[0]) and not any(le(hr, g) for hr in h[1])


@lru_cache(None)
def number_game(q):
    q = F(q)
    if q.denominator == 1:
        k = q.numerator
        if k == 0:
            return ((), ())
        if k > 0:
            return ((number_game(k - 1),), ())
        return ((), (number_game(k + 1),))
    d = F(1, q.denominator)
    return ((number_game(q - d),), (number_game(q + d),))


STAR = ((((), ()),), (((), ()),))


def add(g, h):
    return (tuple([add(gl, h) for gl in g[0]] + [add(g, hl) for hl in h[0]]),
            tuple([add(gr, h) for gr in g[1]] + [add(g, hr) for hr in h[1]]))


def equals(g, h):
    return le(g, h) and le(h, g)


def pattern_masks(pat):
    a = sum(1 << r for r, s in enumerate(pat) if s in "ob")
    b = sum(1 << r for r, s in enumerate(pat) if s in "ow")
    return a, b


def gadget_value(pat):
    """Exact value (q, star) of the vertical path pattern, by Conway order."""
    a, b = pattern_masks(pat)
    g = path_game(a, b, len(pat))
    for den in (1, 2, 4, 8, 16):
        for num in range(-6 * den, 6 * den + 1):
            q = F(num, den)
            if q.denominator != den and den > 1:
                continue
            ng = number_game(q)
            if equals(g, ng):
                return q, False
            if equals(g, add(ng, STAR)):
                return q, True
    return None


def table():
    out = {}
    for pat in itertools.product("obw.", repeat=5):
        pat = "".join(pat)
        v = gadget_value(pat)
        if v is None:
            continue
        # prefer patterns with fewer live cells (smaller searches)
        live = sum(s != "." for s in pat)
        if v not in out or live < out[v][0]:
            out[v] = (live, pat)
    return {k: p for k, (_, p) in out.items()}


if __name__ == "__main__":
    t = table()
    for (q, s), pat in sorted(t.items()):
        print(f"{q}{'+*' if s else ''}\t{pat}")
