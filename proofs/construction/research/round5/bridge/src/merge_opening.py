#!/usr/bin/env python3
"""Merge per-Blue-move col-hybrid-v1 certificates into one opening certificate.

usage: merge_opening.py OPENING REPLY OUT.json.gz SUB.json[.gz] ...

P is the empty 5 x 9 board after Blue OPENING and White REPLY.  Each SUB file
(written by `hy2 answer`) carries "move" v, "reply" x and a root "pos" for
P^{Blue v, White x}.  Every Blue move of P must be covered by some SUB, either
directly or as the image of a SUB's move under a reflection of the board that
fixes P.  The output has root "pos" (an expansion node for P) and the fields
"opening"/"reply" read by proofs/5x9/assemble.py.  Discovery tool only: the
result must be checked with proofs/5x9/verify.py.
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

H, W = 5, 9


def closed_nbhd(v):
    r, c = divmod(v, W)
    m = 1 << v
    for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
        if 0 <= rr < H and 0 <= cc < W:
            m |= 1 << (rr * W + cc)
    return m


def blue(A, B, v):
    return A & ~closed_nbhd(v), B & ~(1 << v)


def white(A, B, u):
    return A & ~(1 << u), B & ~closed_nbhd(u)


def refl(g, v):
    r, c = divmod(v, W)
    if g & 1:
        r = H - 1 - r
    if g & 2:
        c = W - 1 - c
    return r * W + c


def refl_mask(g, m):
    out = 0
    for v in range(H * W):
        if m >> v & 1:
            out |= 1 << refl(g, v)
    return out


def sym_cell(sym, h, w, r, c):
    if sym & 1:
        r, c, h, w = c, r, w, h
    if sym & 2:
        r = h - 1 - r
    if sym & 4:
        c = w - 1 - c
    return r, c, h, w


def mapmask(m, h, w, sym, dr, dc):
    out, v = 0, 0
    while m:
        if m & 1:
            r, c, _, _ = sym_cell(sym, h, w, *divmod(v, w))
            out |= 1 << ((r + dr) * W + c + dc)
        m >>= 1
        v += 1
    return out


def find_xf(node, At, Bt):
    h, w, a, b = node[:4]
    live = At | Bt
    cells = [v for v in range(H * W) if live >> v & 1]
    r0 = min(v // W for v in cells)
    c0 = min(v % W for v in cells)
    for t in range(8):
        _, _, ht, wt = sym_cell(t, h, w, 0, 0)
        if r0 + ht > H or c0 + wt > W:
            continue
        if mapmask(a, h, w, t, r0, c0) == At and mapmask(b, h, w, t, r0, c0) == Bt:
            return [t, r0, c0]
    raise SystemExit("no transform places a child node")


def load(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith(".gz") else raw)


def merge_docs(docs):
    """Merge node lists (identical claims shared).  Returns nodes and per-doc local maps."""
    nodes, index, maps = [], {}, []
    for doc in docs:
        recs = doc["nodes"]
        local = [None] * len(recs)
        for i, rec in enumerate(recs):
            key = tuple(rec[:7])
            if key not in index:
                index[key] = len(nodes)
                nodes.append(None)
            local[i] = index[key]
        for i, rec in enumerate(recs):
            gid = local[i]
            if nodes[gid] is not None:
                continue
            kind = rec[7]
            if kind == "A":
                nodes[gid] = rec
            elif kind == "E":
                nodes[gid] = rec[:8] + [[[e[0], e[1], local[e[2]], e[3], e[4], e[5]] for e in rec[8]]]
            else:
                nodes[gid] = rec[:8] + [rec[8], [[local[e[0]], e[1], e[2], e[3]] for e in rec[9]]]
        maps.append(local)
    return nodes, index, maps


def main():
    opening, reply, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    docs = [load(p) for p in sys.argv[4:]]
    full = (1 << (H * W)) - 1
    A, B = blue(full, full, opening)
    A, B = white(A, B, reply)
    syms = [g for g in range(4) if refl_mask(g, A) == A and refl_mask(g, B) == B]
    nodes, index, maps = merge_docs(docs)
    answers = {}
    for doc, local in zip(docs, maps):
        v, x = doc["move"], doc["reply"]
        nid = local[doc["roots"]["pos"]]
        for g in syms:
            vv, xx = refl(g, v), refl(g, x)
            if vv not in answers:
                answers[vv] = (xx, nid)
    edges = []
    missing = []
    for v in range(H * W):
        if not A >> v & 1:
            continue
        if v not in answers:
            missing.append(divmod(v, W))
            continue
        x, nid = answers[v]
        a1, b1 = blue(A, B, v)
        if not b1 >> x & 1:
            raise SystemExit(f"reply {x} illegal after Blue {v}")
        a2, b2 = white(a1, b1, x)
        edges.append([v, x, nid] + find_xf(nodes[nid], a2, b2))
    if missing:
        print("MISSING Blue moves:", missing)
        sys.exit(1)
    root = len(nodes)
    nodes.append([H, W, A, B, 0, 1, 0, "E", edges])
    doc = {"format": "col-hybrid-v1", "roots": {"pos": root}, "board": [H, W], "opening": opening, "reply": reply,
           "nodes": nodes}
    body = json.dumps(doc, separators=(",", ":")).replace("],[", "],\n[")
    data = body.encode()
    Path(out).write_bytes(gzip.compress(data, mtime=0) if out.endswith(".gz") else data)
    print(f"merged {len(docs)} sub-certificates, {len(nodes)} nodes -> {out}")


if __name__ == "__main__":
    main()
