#!/usr/bin/env python3
"""Assemble per-opening col-hybrid-v1 certificates into the package.

Usage: python3 assemble.py OPENING_CERT.json[.gz] ... [--out DIR]

Each input certificate proves one representative opening: it names the Blue
opening, the White reply and a root node "pos" for the position after both
moves.  This script merges the node sets (identical claims are shared), adds
the empty-board root, which answers all 45 openings by reflecting the 15
representatives, and writes certificate.json.gz, manifest.json and
SHA256SUMS.  It does not decide anything: run verify.py afterwards.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

H, W = 5, 9
HERE = Path(__file__).resolve().parent


def closed_nbhd(v: int) -> int:
    r, c = divmod(v, W)
    m = 1 << v
    for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
        if 0 <= rr < H and 0 <= cc < W:
            m |= 1 << (rr * W + cc)
    return m


def sym_cell(sym, h, w, r, c):
    if sym & 1:
        r, c, h, w = c, r, w, h
    if sym & 2:
        r = h - 1 - r
    if sym & 4:
        c = w - 1 - c
    return r, c, h, w


def mapmask(m, h, w, sym, dr, dc, Wt):
    out = 0
    v = 0
    while m:
        if m & 1:
            r, c, _, _ = sym_cell(sym, h, w, *divmod(v, w))
            out |= 1 << ((r + dr) * Wt + c + dc)
        m >>= 1
        v += 1
    return out


def find_xf(node, At, Bt):
    h, w, a, b = node[:4]
    live = At | Bt
    r0 = min(v // W for v in range(H * W) if live >> v & 1)
    c0 = min(v % W for v in range(H * W) if live >> v & 1)
    for t in range(8):
        _, _, ht, wt = sym_cell(t, h, w, 0, 0)
        if r0 + ht > H or c0 + wt > W:
            continue
        if mapmask(a, h, w, t, r0, c0, W) == At and mapmask(b, h, w, t, r0, c0, W) == Bt:
            return [t, r0, c0]
    raise SystemExit("no transform places the opening node")


def reflect(g, r, c):
    if g & 1:
        r = H - 1 - r
    if g & 2:
        c = W - 1 - c
    return r, c


def load(path: Path) -> dict:
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("certs", nargs="+")
    ap.add_argument("--out", default=str(HERE))
    args = ap.parse_args()
    out = Path(args.out)
    (out / "certificates").mkdir(parents=True, exist_ok=True)

    nodes: list = []
    index: dict = {}
    reps = {}
    for name in args.certs:
        doc = load(Path(name))
        recs = doc["nodes"]
        local = [None] * len(recs)
        # first pass: claim keys
        for i, rec in enumerate(recs):
            key = tuple(rec[:7])
            if key in index:
                local[i] = index[key]
            else:
                local[i] = len(nodes)
                index[key] = local[i]
                nodes.append(None)
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
        v, u = doc["opening"], doc["reply"]
        br, bc = divmod(v, W)
        require_rep = 0 <= br <= 2 and 0 <= bc <= 4
        if not require_rep:
            raise SystemExit(f"{name}: opening {v} is not a representative")
        reps[v] = (u, local[doc["roots"]["pos"]])

    full = (1 << (H * W)) - 1
    edges = {}
    openings = []
    for v in sorted(reps):
        u, nid = reps[v]
        br, bc = divmod(v, W)
        wr, wc = divmod(u, W)
        orbit = []
        for g in range(4):
            vr, vc = reflect(g, br, bc)
            rr, rc = reflect(g, wr, wc)
            vv, uu = vr * W + vc, rr * W + rc
            if vv in edges:
                continue
            a1, b1 = full & ~closed_nbhd(vv), full & ~(1 << vv)
            a2, b2 = a1 & ~(1 << uu), b1 & ~closed_nbhd(uu)
            edges[vv] = [vv, uu, nid] + find_xf(nodes[nid], a2, b2)
            orbit.append([vr, vc])
        openings.append({"blue": [br, bc], "white": [wr, wc], "node": None, "orbit": orbit, "_nid": nid})
    if len(edges) != H * W:
        missing = sorted(set(range(H * W)) - set(edges))
        raise SystemExit(f"openings not covered: {[divmod(m, W) for m in missing]}")

    # put the root first, renumber by reachability order
    root_rec = [H, W, full, full, 0, 1, 0, "E", [edges[v] for v in range(H * W)]]
    allnodes = [root_rec] + nodes
    shift = lambda i: i + 1  # noqa: E731
    fixed = [root_rec[:8] + [[[e[0], e[1], shift(e[2]), e[3], e[4], e[5]] for e in root_rec[8]]]]
    for rec in nodes:
        if rec[7] == "A":
            fixed.append(rec)
        elif rec[7] == "E":
            fixed.append(rec[:8] + [[[e[0], e[1], shift(e[2]), e[3], e[4], e[5]] for e in rec[8]]])
        else:
            fixed.append(rec[:8] + [rec[8], [[shift(e[0]), e[1], e[2], e[3]] for e in rec[9]]])
    del allnodes
    for op in openings:
        op["node"] = shift(op.pop("_nid"))

    doc = {"format": "col-hybrid-v1", "roots": {"empty": 0}, "board": [H, W], "nodes": fixed}
    body = json.dumps(doc, separators=(",", ":")).replace("],[", "],\n[")
    cert_path = out / "certificates" / "certificate.json.gz"
    cert_path.write_bytes(gzip.compress(body.encode(), mtime=0))
    digest = hashlib.sha256(cert_path.read_bytes()).hexdigest()
    manifest = {
        "format": "col-5x9-proof-v1",
        "board": {"height": H, "width": W},
        "first_player": "Blue",
        "claim": "the empty 5x9 Col board is a second-player win (value 0)",
        "certificate": {"path": "certificates/certificate.json.gz", "sha256": digest, "nodes": len(fixed)},
        "root_node": 0,
        "openings": openings,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"assembled {len(fixed)} nodes, {len(openings)} representatives -> {cert_path}")


if __name__ == "__main__":
    main()
