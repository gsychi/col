"""Exact Col search on 3 x w permission positions, used only to *generate*
certificates. Lean re-checks every certificate; nothing here is trusted.

A position is a pair (A, B) of bitmasks over cells r*w + c (A: Blue-legal,
B: White-legal). `blue_loses` decides whether Blue, moving first, loses.
"""

from __future__ import annotations

import sys
from functools import lru_cache

sys.setrecursionlimit(100000)

ROWS = 3


def closed_nbhd(w: int, i: int) -> int:
    r, c = divmod(i, w)
    m = 1 << i
    if c > 0:
        m |= 1 << (i - 1)
    if c + 1 < w:
        m |= 1 << (i + 1)
    if r > 0:
        m |= 1 << (i - w)
    if r + 1 < ROWS:
        m |= 1 << (i + w)
    return m


def bits(x: int):
    while x:
        low = x & -x
        yield low.bit_length() - 1
        x ^= low


class Solver:
    def __init__(self, w: int):
        self.w = w
        self.nb = [closed_nbhd(w, i) for i in range(ROWS * w)]
        self.memo: dict[tuple[int, int], int | None] = {}

    def blue_move(self, a: int, b: int, v: int):
        return a & ~self.nb[v], b & ~(1 << v)

    def white_move(self, a: int, b: int, u: int):
        return a & ~(1 << u), b & ~self.nb[u]

    def reply(self, a: int, b: int, v: int):
        """A White reply to Blue's v after which Blue (to move) loses, or None."""
        a1, b1 = self.blue_move(a, b, v)
        for u in bits(b1):
            a2, b2 = self.white_move(a1, b1, u)
            if self.blue_loses(a2, b2):
                return u
        return None

    def blue_loses(self, a: int, b: int) -> bool:
        key = (a, b)
        if key in self.memo:
            return self.memo[key]
        result = all(self.reply(a, b, v) is not None for v in bits(a))
        self.memo[key] = result
        return result

    def certificate(self, a: int, b: int) -> list[int]:
        """Closed set of Blue-to-move positions reachable under chosen replies."""
        assert self.blue_loses(a, b), "root is not a Blue-first loss"
        seen: set[tuple[int, int]] = set()
        stack = [(a, b)]
        while stack:
            p = stack.pop()
            if p in seen:
                continue
            seen.add(p)
            pa, pb = p
            for v in bits(pa):
                u = self.reply(pa, pb, v)
                a1, b1 = self.blue_move(pa, pb, v)
                stack.append(self.white_move(a1, b1, u))
        size = ROWS * self.w
        return sorted((pa << size) | pb for pa, pb in seen)
