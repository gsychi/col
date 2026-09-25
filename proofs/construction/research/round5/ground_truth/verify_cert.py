#!/usr/bin/env python3
"""Independent, search-free checker for Col response-DAG certificates.

Accepts two schemas (both state the *player to move loses* at the root):
  * canonical-dyadic-response-dag-v1 (the number_certificates.py format):
      root [a,b,qn,qd]; nodes [[a,b,qn,qd,[[first,reply],...]], ...]
  * dyadic-star-response-dag-v1 (same plus a star flag s in {0,1}):
      root [a,b,qn,qd,s]; nodes [[a,b,qn,qd,s,[[first,reply],...]], ...]
States are in the mover's frame: a = cells legal for the player to move,
b = cells legal for the other player, q = dyadic number (mover's view),
s = a star summand is present. Move codes: v >= 0 a cell, -1 the canonical
Left move in the number, -2 taking the star.

Checks, using coordinate sets only (no minimax, no component values):
every option of the player to move at every checkpoint has exactly one
listed reply; each reply is a legal option of the other player; the reply
leads to a listed checkpoint; a finite rank strictly decreases on every ply;
every checkpoint is reachable from the root; the edge count matches.
A valid DAG proves: the player to move at the root loses (G + q + s* is
<= 0 from the mover's side), by induction on the rank.

Also provides root builders for the five-row families, written from the
letter patterns without importing the generators.
"""
from fractions import Fraction as F
import gzip
import json
import sys

LETTERS = dict(D="obwbo", U="wbobo", V="bwbob", X="bowob", R="wobob", J="owobo", T="bobob")


class CertificateError(Exception):
    pass


def require(cond, msg):
    if not cond:
        raise CertificateError(msg)


def grid_neighbors(h, w):
    return tuple(frozenset(rr * w + cc for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
                           if 0 <= rr < h and 0 <= cc < w)
                 for r in range(h) for c in range(w))


def verify(doc):
    h, w = doc["height"], doc["width"]
    n = h * w
    require(type(h) is int and type(w) is int and 1 <= n <= 64, "dimensions")
    star_schema = len(doc["root"]) == 5
    require(len(doc["root"]) in (4, 5), "root arity")
    nbrs = grid_neighbors(h, w)

    def verts(x):
        require(type(x) is int and 0 <= x < 1 << n, "mask")
        return frozenset(v for v in range(n) if x >> v & 1)

    def number(qn, qd):
        require(type(qn) is int and type(qd) is int and qd > 0 and qd & (qd - 1) == 0, "not dyadic")
        return F(qn, qd)

    def flag(s):
        require(s in (0, 1), "star flag")
        return bool(s)

    def transitions(a, b, q, s):
        t = {v: (b - {v}, a - {v} - nbrs[v], -q, s) for v in a}
        if q.denominator != 1:
            t[-1] = (b, a, -(q - F(1, q.denominator)), s)
        elif q > 0:
            t[-1] = (b, a, -(q - 1), s)
        if s:
            t[-2] = (b, a, -q, False)
        return t

    def day(q):
        if q.denominator == 1:
            return abs(q.numerator)
        return abs(q.numerator) // q.denominator + 1 + (q.denominator.bit_length() - 1)

    def rank(a, b, q, s):
        return len(a | b) + day(q) + int(s)

    nodes = {}
    for rec in doc["nodes"]:
        if star_schema:
            require(len(rec) == 6, "node arity")
            am, bm, qn, qd, s, replies = rec
            key = (verts(am), verts(bm), number(qn, qd), flag(s))
        else:
            require(len(rec) == 5, "node arity")
            am, bm, qn, qd, replies = rec
            key = (verts(am), verts(bm), number(qn, qd), False)
        require(key not in nodes, "duplicate state")
        nodes[key] = replies
    if star_schema:
        am, bm, qn, qd, s = doc["root"]
        root = (verts(am), verts(bm), number(qn, qd), flag(s))
    else:
        am, bm, qn, qd = doc["root"]
        root = (verts(am), verts(bm), number(qn, qd), False)
    require(root in nodes, "root missing")
    children = {}
    edges = 0
    for key, replies in nodes.items():
        options = transitions(*key)
        require(type(replies) is list and len(replies) == len(options), "incomplete first-player coverage")
        require({r[0] for r in replies} == set(options), "first-player coverage mismatch")
        children[key] = []
        for first, reply in replies:
            mid = options[first]
            responses = transitions(*mid)
            require(reply in responses, "illegal reply")
            child = responses[reply]
            require(child in nodes, "successor missing")
            require(rank(*child) < rank(*mid) < rank(*key), "no descent")
            children[key].append(child)
            edges += 1
    seen = {root}
    stack = [root]
    while stack:
        for c in children[stack.pop()]:
            if c not in seen:
                seen.add(c)
                stack.append(c)
    require(len(seen) == len(nodes), "unreachable checkpoints")
    require(edges == doc["edges"], "edge count")
    return len(nodes), edges


def load(path):
    raw = open(path, "rb").read()
    if str(path).endswith(".gz"):
        raw = gzip.decompress(raw)
    return json.loads(raw)


# ------------------------------------------------------------------ roots
def family_masks(name, n):
    """Masks of the five-row family `name` at width n, from letter patterns."""
    cells = [(r, c) for r in range(5) for c in range(n)]
    perm = {v: "o" for v in cells}

    def put(col, pattern):
        for r, ch in enumerate(pattern):
            old = perm[(r, col)]
            blue = old in "ob" and ch in "ob"
            white = old in "ow" and ch in "ow"
            perm[(r, col)] = "o" if blue and white else "b" if blue else "w" if white else "."

    if name == "M":
        require(n % 2 == 1, "M needs odd width")
        bl, wh = (2, (n - 1) // 2), (0, 0)
        near = lambda v: {v, (v[0] - 1, v[1]), (v[0] + 1, v[1]), (v[0], v[1] - 1), (v[0], v[1] + 1)}
        a = {v for v in cells} - near(bl) - {wh}
        b = {v for v in cells} - {bl} - near(wh)
        return sum(1 << (r * n + c) for r, c in a), sum(1 << (r * n + c) for r, c in b)
    if name == "E":
        pass
    elif len(name) == 1:
        put(0, LETTERS[name])
    else:
        put(0, LETTERS[name[0]])
        put(n - 1, LETTERS[name[1]])
    a = sum(1 << (r * n + c) for (r, c), p in perm.items() if p in "ob")
    b = sum(1 << (r * n + c) for (r, c), p in perm.items() if p in "ow")
    return a, b


def claim_root(claim):
    """Root expected for a claim dict: family, width, player ('blue'|'white'),
    q (number G is compared with, as a string) and star (0/1).
    Statement certified: the named player, moving first in G - q (+*), loses."""
    a, b = family_masks(claim["family"], claim["width"])
    q = F(claim["q"])
    s = int(claim.get("star", 0))
    if claim["player"] == "blue":
        mover, other, qq = a, b, -q
    else:
        mover, other, qq = b, a, q
    return [mover, other, qq.numerator, qq.denominator] + ([s] if claim.get("schema_star") else [])


if __name__ == "__main__":
    for p in sys.argv[1:]:
        d = load(p)
        print(p, "VERIFIED", verify(d))
