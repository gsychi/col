#!/usr/bin/env python3
"""Search-free checker for Blue-first-losing response DAGs with an auxiliary
dyadic number and star (format col-bridge-dag-v1).

A node [A, B, pnum, pden, star, replies] is a Blue-to-move position of the sum
    (Col permission game (A,B) on the h x w grid) + pnum/pden + (star ? * : 0).
Blue's options are: every cell of A; the Left option of the number, when it
exists; the star, when present.  `replies` must list, for EACH of those
options exactly once, a White answer: a cell of the post-move White set, -1
(the number's Right option) or -2 (the star).  The answer must reach another
listed node, and the rank |A u B| + birthday(number) + star must fall strictly
on each ply.  A valid DAG proves by induction on the rank that every node is a
Blue-first loss, i.e. (Col game) + number + star <= 0.

Python 3.10+, standard library only; coordinate sets, not the generator's bit
arithmetic.  Nothing here performs game-tree search.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from fractions import Fraction
from pathlib import Path


class InvalidCertificate(ValueError):
    pass


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise InvalidCertificate(msg)


def grid_neighbours(h: int, w: int) -> tuple[frozenset[int], ...]:
    out = []
    for v in range(h * w):
        r, c = divmod(v, w)
        cand = ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
        out.append(frozenset(rr * w + cc for rr, cc in cand if 0 <= rr < h and 0 <= cc < w))
    return tuple(out)


def cells(mask: int, n: int) -> frozenset[int]:
    require(type(mask) is int and 0 <= mask < (1 << n), "bad cell mask")
    return frozenset(v for v in range(n) if mask >> v & 1)


def dyadic(num: int, den: int) -> Fraction:
    require(type(num) is int and type(den) is int, "non-integer number field")
    require(den >= 1 and den & (den - 1) == 0, "denominator is not a power of two")
    return Fraction(num, den)


def left_option(q: Fraction):
    """Left option of the canonical form of the dyadic number q, or None."""
    if q.denominator > 1:
        return q - Fraction(1, q.denominator)
    return q - 1 if q > 0 else None


def right_option(q: Fraction):
    if q.denominator > 1:
        return q + Fraction(1, q.denominator)
    return q + 1 if q < 0 else None


def birthday(q: Fraction) -> int:
    if q.denominator == 1:
        return abs(q.numerator)
    k = q.denominator.bit_length() - 1
    return -(-abs(q.numerator) // q.denominator) + k


def load(path: Path, sha256: str | None = None) -> dict:
    raw = path.read_bytes()
    if sha256 is not None:
        require(hashlib.sha256(raw).hexdigest() == sha256, f"checksum mismatch: {path.name}")
    data = gzip.decompress(raw) if path.suffix == ".gz" else raw
    return json.loads(data)


def verify_dag(doc: dict) -> tuple[int, int]:
    """Check a col-bridge-dag-v1 document; return (checkpoints, edges)."""
    require(doc.get("format") == "col-bridge-dag-v1", "unknown DAG format")
    h, w = doc["height"], doc["width"]
    require(type(h) is int and type(w) is int and 1 <= h <= 12 and 1 <= w <= 12, "dimensions")
    n = h * w
    nb = grid_neighbours(h, w)

    def state(a, b, pn, pd, s):
        require(s in (0, 1), "star flag")
        return (cells(a, n), cells(b, n), dyadic(pn, pd), s)

    def rank(st) -> int:
        a, b, q, s = st
        return len(a | b) + birthday(q) + s

    nodes = {}
    for rec in doc["nodes"]:
        require(isinstance(rec, list) and len(rec) == 6, "malformed node")
        st = state(*rec[:5])
        require(st not in nodes, "duplicate node")
        require(isinstance(rec[5], list), "replies must be a list")
        nodes[st] = rec[5]
    root = state(*doc["root"])
    require(root in nodes, "root missing")
    children: dict = {}
    edges = 0
    for st, replies in nodes.items():
        a, b, q, s = st
        options = {}
        for v in a:
            options[v] = (a - {v} - nb[v], b - {v}, q, s)
        ql = left_option(q)
        if ql is not None:
            options[-1] = (a, b, ql, s)
        if s:
            options[-2] = (a, b, q, 0)
        seen_moves = set()
        kids = []
        for pair in replies:
            require(isinstance(pair, list) and len(pair) == 2, "malformed reply pair")
            mv, rep = pair
            require(type(mv) is int and type(rep) is int, "non-integer move")
            require(mv in options and mv not in seen_moves, "unknown or repeated Blue option")
            seen_moves.add(mv)
            mid = options[mv]
            ma, mb, mq, ms = mid
            if rep >= 0:
                require(rep in mb, "illegal White reply")
                child = (ma - {rep}, mb - {rep} - nb[rep], mq, ms)
            elif rep == -1:
                qr = right_option(mq)
                require(qr is not None, "number has no Right option")
                child = (ma, mb, qr, ms)
            elif rep == -2:
                require(ms == 1, "no star to take")
                child = (ma, mb, mq, 0)
            else:
                raise InvalidCertificate("bad reply code")
            require(child in nodes, "missing successor node")
            require(rank(child) < rank(mid) < rank(st), "rank does not decrease")
            kids.append(child)
            edges += 1
        require(seen_moves == set(options), "not every Blue option is answered")
        children[st] = kids
    reach = {root}
    stack = [root]
    while stack:
        for c in children[stack.pop()]:
            if c not in reach:
                reach.add(c)
                stack.append(c)
    require(len(reach) == len(nodes), "unreachable nodes")
    require(doc.get("edges") == edges, "edge count mismatch")
    return len(nodes), edges


def claim_of(doc: dict) -> tuple[int, int, int, int, Fraction, int]:
    """(h, w, A, B, q, s) with the certified claim  T(A,B) <= q + s*."""
    a, b, pn, pd, s = doc["root"]
    return doc["height"], doc["width"], a, b, -dyadic(pn, pd), s


if __name__ == "__main__":
    import sys

    for name in sys.argv[1:]:
        d = load(Path(name))
        print(name, verify_dag(d), claim_of(d))
