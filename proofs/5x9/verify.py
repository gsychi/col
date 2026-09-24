#!/usr/bin/env python3
"""Independent, search-free verifier for the 5 x 9 Col certificate package.

Python 3.10+, standard library only.  Nothing here searches a game tree: every
node of the certificate carries its own justification, and this program only
checks those justifications and that the justification graph is acyclic.

Certificate format ``col-hybrid-v1``.  A node

    [h, w, A, B, qnum, qden, s, kind, ...]

is the claim  G(A, B) + q + s*  <=  0  (Blue to move), where G(A, B) is the
Col shadow position on an h x w grid with Blue-legal cells A and White-legal
cells B (row-major bit masks, bit r*w + c), q = qnum/qden is a dyadic number
(played as its canonical game) and s is a star bit.  Justification kinds:

  "A"  arithmetic: A is empty, and q < 0 or (q = 0 and s = 0).
  "E"  expansion: a list of [move, reply, child, sym, dr, dc].  The moves must
       be exactly Blue's options (every cell of A; -1 = the Left option of q,
       when it exists; -2 = the star, when present).  The reply is a legal
       White option after that move (a cell; -1 = the Right option of the
       number; -2 = the star).  The resulting position must equal the image
       of the child node under the transform (sym, dr, dc), with the same
       number and star.
  "C"  comparison: [retired, [[child, sym, dr, dc], ...]].  With
       B' = B minus retired (retired must be a subset of B) and child images
       (A_i, B_i): the live sets A_i u B_i are pairwise disjoint, A is covered
       by the union of the A_i, every B_i lies in B', and no grid edge joins a
       White-legal cell of one child to a White-legal cell of another.  With
       Q = q - sum q_i and p = s xor (xor s_i): Q < 0, or Q = 0 and p = 0.

Transforms: a child cell (r, c) of an h_c x w_c box is mapped by sym (bit 0:
transpose, then bit 1: flip rows, bit 2: flip columns, using the dimensions
after transposing) and then shifted by (dr, dc); the image must lie inside
the parent box.  These are grid isometries, so the child game and its image
are the same game (cells legal for neither player are irrelevant).
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import time
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent


class InvalidCertificate(ValueError):
    pass


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise InvalidCertificate(msg)


# ---------------------------------------------------------------- geometry

_NEIGH: dict[tuple[int, int], tuple[list[int], list[int]]] = {}


def geometry(h: int, w: int) -> tuple[list[int], list[int]]:
    """Open and closed neighbourhood masks of every cell of the h x w grid."""
    key = (h, w)
    if key not in _NEIGH:
        opened, closed = [], []
        for v in range(h * w):
            r, c = divmod(v, w)
            m = 0
            for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if 0 <= rr < h and 0 <= cc < w:
                    m |= 1 << (rr * w + cc)
            opened.append(m)
            closed.append(m | (1 << v))
        _NEIGH[key] = (opened, closed)
    return _NEIGH[key]


def bits(m: int):
    while m:
        low = m & -m
        yield low.bit_length() - 1
        m ^= low


def sym_cell(sym: int, h: int, w: int, r: int, c: int) -> tuple[int, int, int, int]:
    """Image of (r, c) and the image box dimensions."""
    if sym & 1:
        r, c, h, w = c, r, w, h
    if sym & 2:
        r = h - 1 - r
    if sym & 4:
        c = w - 1 - c
    return r, c, h, w


_XF: dict[tuple, list[list[int]]] = {}


def transform_tables(hc: int, wc: int, sym: int, dr: int, dc: int, H: int, W: int) -> list[list[int]]:
    key = (hc, wc, sym, dr, dc, H, W)
    tabs = _XF.get(key)
    if tabs is None:
        require(0 <= sym < 8 and type(dr) is int and type(dc) is int, "bad transform")
        image = []
        for v in range(hc * wc):
            r, c, _, _ = sym_cell(sym, hc, wc, *divmod(v, wc))
            rr, cc = r + dr, c + dc
            require(0 <= rr < H and 0 <= cc < W, "transformed child leaves the parent box")
            image.append(1 << (rr * W + cc))
        tabs = []
        for start in range(0, hc * wc, 4):
            tab = [0] * 16
            for x in range(16):
                m = 0
                for i in range(4):
                    if x >> i & 1 and start + i < hc * wc:
                        m |= image[start + i]
                tab[x] = m
            tabs.append(tab)
        _XF[key] = tabs
    return tabs


def transform(mask: int, tabs: list[list[int]]) -> int:
    out = 0
    i = 0
    while mask:
        out |= tabs[i][mask & 15]
        mask >>= 4
        i += 1
    return out


# ---------------------------------------------------------------- numbers

def left_option(q: Fraction):
    if q.denominator > 1:
        return q - Fraction(1, q.denominator)
    return q - 1 if q > 0 else None


def right_option(q: Fraction):
    if q.denominator > 1:
        return q + Fraction(1, q.denominator)
    return q + 1 if q < 0 else None


# ---------------------------------------------------------------- nodes

def parse_node(rec, idx: int):
    require(isinstance(rec, list) and len(rec) >= 8, f"node {idx}: malformed")
    h, w, a, b, qn, qd, s, kind = rec[:8]
    for x in (h, w, a, b, qn, qd, s):
        require(type(x) is int, f"node {idx}: non-integer field")
    require(0 <= h <= 12 and 0 <= w <= 12 and h * w <= 64, f"node {idx}: bad dimensions")
    n = h * w
    require(0 <= a < (1 << n) and 0 <= b < (1 << n), f"node {idx}: mask outside box")
    require(qd >= 1 and qd & (qd - 1) == 0, f"node {idx}: denominator not a power of two")
    require(s in (0, 1), f"node {idx}: star flag")
    require(kind in ("A", "E", "C"), f"node {idx}: unknown kind")
    return h, w, a, b, Fraction(qn, qd), s, kind, rec[8:]


class Certificate:
    def __init__(self, records: list):
        self.nodes = [parse_node(rec, i) for i, rec in enumerate(records)]
        self.children: list[list[int]] = [[] for _ in self.nodes]
        self.stats = {"A": 0, "E": 0, "C": 0, "edges": 0, "comparisons_children": 0}

    def child_image(self, parent: int, ref: list, H: int, W: int):
        require(isinstance(ref, list) and len(ref) == 4, f"node {parent}: malformed child reference")
        cid, sym, dr, dc = ref
        require(type(cid) is int and 0 <= cid < len(self.nodes), f"node {parent}: bad child id")
        hc, wc, ac, bc, qc, sc, _, _ = self.nodes[cid]
        if hc * wc == 0:
            return cid, 0, 0, qc, sc
        tabs = transform_tables(hc, wc, sym, dr, dc, H, W)
        return cid, transform(ac, tabs), transform(bc, tabs), qc, sc

    def check_node(self, i: int) -> None:
        h, w, a, b, q, s, kind, rest = self.nodes[i]
        if kind == "A":
            require(not rest, f"node {i}: arithmetic node has payload")
            require(a == 0 and (q < 0 or (q == 0 and s == 0)), f"node {i}: arithmetic claim fails")
            self.stats["A"] += 1
            return
        opened, closed = geometry(h, w)
        if kind == "E":
            require(len(rest) == 1 and isinstance(rest[0], list), f"node {i}: malformed expansion")
            options = {}
            for v in bits(a):
                options[v] = (a & ~closed[v], b & ~(1 << v), q, s)
            ql = left_option(q)
            if ql is not None:
                options[-1] = (a, b, ql, s)
            if s:
                options[-2] = (a, b, q, 0)
            seen = set()
            for e in rest[0]:
                require(isinstance(e, list) and len(e) == 6, f"node {i}: malformed edge")
                mv, rep = e[0], e[1]
                require(type(mv) is int and type(rep) is int, f"node {i}: non-integer move")
                require(mv in options and mv not in seen, f"node {i}: unknown or repeated Blue option {mv}")
                seen.add(mv)
                ma, mb, mq, ms = options[mv]
                if rep >= 0:
                    require(rep < h * w and mb >> rep & 1, f"node {i}: illegal White reply {rep}")
                    res = (ma & ~(1 << rep), mb & ~closed[rep], mq, ms)
                elif rep == -1:
                    qr = right_option(mq)
                    require(qr is not None, f"node {i}: number has no Right option")
                    res = (ma, mb, qr, ms)
                elif rep == -2:
                    require(ms == 1, f"node {i}: no star to take")
                    res = (ma, mb, mq, 0)
                else:
                    raise InvalidCertificate(f"node {i}: bad reply code")
                cid, ia, ib, qc, sc = self.child_image(i, e[2:], h, w)
                require((ia, ib, qc, sc) == res, f"node {i}: child {cid} does not match the position after move {mv}, reply {rep}")
                self.children[i].append(cid)
                self.stats["edges"] += 1
            require(seen == set(options), f"node {i}: not every Blue option is answered")
            self.stats["E"] += 1
            return
        # comparison
        require(len(rest) == 2 and type(rest[0]) is int and isinstance(rest[1], list), f"node {i}: malformed comparison")
        retired, refs = rest
        require(retired >= 0 and retired & ~b == 0, f"node {i}: retired cells are not White-legal")
        bprime = b & ~retired
        lives, whites = [], []
        cover_a, qsum, par = 0, Fraction(0), s
        used = 0
        for ref in refs:
            cid, ia, ib, qc, sc = self.child_image(i, ref, h, w)
            live = ia | ib
            require(live & used == 0, f"node {i}: overlapping children")
            used |= live
            require(ib & ~bprime == 0, f"node {i}: child gives White a cell outside B minus retired")
            cover_a |= ia
            qsum += qc
            par ^= sc
            lives.append(live)
            whites.append(ib)
            self.children[i].append(cid)
        require(a & ~cover_a == 0, f"node {i}: a Blue-legal cell is not covered")
        bstar = 0
        for x in whites:
            bstar |= x
        for live, wb in zip(lives, whites):
            others = bstar & ~live
            for v in bits(wb):
                require(opened[v] & others == 0, f"node {i}: seam edge with two White-legal endpoints at cell {v}")
        total = q - qsum
        require(total < 0 or (total == 0 and par == 0), f"node {i}: comparison bound is not <= 0 with Blue to move")
        self.stats["C"] += 1
        self.stats["comparisons_children"] += len(refs)

    def check_all(self) -> None:
        for i in range(len(self.nodes)):
            self.check_node(i)

    def check_acyclic_from(self, root: int) -> int:
        """Every node reachable from root; the justification graph is acyclic."""
        state = [0] * len(self.nodes)  # 0 new, 1 on stack, 2 done
        stack = [(root, 0)]
        state[root] = 1
        while stack:
            v, k = stack[-1]
            ch = self.children[v]
            if k < len(ch):
                stack[-1] = (v, k + 1)
                c = ch[k]
                require(state[c] != 1, f"cycle through node {c}")
                if state[c] == 0:
                    state[c] = 1
                    stack.append((c, 0))
            else:
                state[v] = 2
                stack.pop()
        reached = sum(1 for x in state if x == 2)
        require(reached == len(self.nodes), f"{len(self.nodes) - reached} unreachable nodes")
        return reached


def load_records(path: Path) -> list:
    raw = path.read_bytes()
    data = gzip.decompress(raw) if path.suffix == ".gz" else raw
    doc = json.loads(data)
    require(doc.get("format") == "col-hybrid-v1", f"{path.name}: unknown format")
    return doc


# ---------------------------------------------------------------- package

REFLECTIONS = ("identity", "flip rows", "flip columns", "rotate 180")


def reflect(g: int, r: int, c: int, H: int, W: int) -> tuple[int, int]:
    if g & 1:
        r = H - 1 - r
    if g & 2:
        c = W - 1 - c
    return r, c


def check_sha256sums(root: Path) -> int:
    lines = (root / "SHA256SUMS").read_text().split("\n")
    count = 0
    for line in lines:
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        name = name.strip().lstrip("*")
        actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
        require(actual == digest, f"SHA256 mismatch for {name}")
        count += 1
    require(count > 0, "SHA256SUMS is empty")
    return count


def verify_package(root: Path, check_sums: bool = True) -> dict:
    t0 = time.time()
    manifest = json.loads((root / "manifest.json").read_text())
    sums = check_sha256sums(root) if check_sums else 0
    cert_path = root / manifest["certificate"]["path"]
    require(hashlib.sha256(cert_path.read_bytes()).hexdigest() == manifest["certificate"]["sha256"],
            "certificate checksum mismatch")
    doc = load_records(cert_path)
    out = verify_documents(manifest, doc)
    out["sha256_files"] = sums
    out["seconds"] = round(time.time() - t0, 1)
    return out


def verify_documents(manifest: dict, doc: dict) -> dict:
    """Check the manifest and the decoded certificate (no file access)."""
    require(manifest.get("format") == "col-5x9-proof-v1", "unknown manifest format")
    require(doc.get("format") == "col-hybrid-v1", "unknown certificate format")
    H, W = manifest["board"]["height"], manifest["board"]["width"]
    require((H, W) == (5, 9), "this package is about the 5 x 9 board")
    cert = Certificate(doc["nodes"])
    rid = doc["roots"]["empty"]
    require(rid == manifest["root_node"], "manifest root differs from certificate root")
    h, w, a, b, q, s, kind, rest = cert.nodes[rid]
    full = (1 << (H * W)) - 1
    require((h, w, a, b, q, s) == (H, W, full, full, 0, 0), "root is not the empty 5 x 9 board with bound 0")
    require(kind == "E", "root must be an expansion over all openings")
    cert.check_all()
    reached = cert.check_acyclic_from(rid)

    # Opening table: 15 representatives cover the 45 openings under the
    # reflections of the board, and the root's answers are their images.
    root_edges = {e[0]: e for e in rest[0]}
    openings = manifest["openings"]
    covered = {}
    for op in openings:
        br, bc = op["blue"]
        wr, wc = op["white"]
        require(0 <= br <= (H - 1) // 2 and 0 <= bc <= (W - 1) // 2, "representative outside rows 0-2, columns 0-4")
        e = root_edges[br * W + bc]
        require(e[1] == wr * W + wc and e[2] == op["node"], f"opening {op['blue']}: table differs from certificate")
        for g in range(4):
            vr, vc = reflect(g, br, bc, H, W)
            rr, rc = reflect(g, wr, wc, H, W)
            v = vr * W + vc
            if v in covered:
                require(covered[v] == (br, bc), "two representatives share an orbit")
                continue
            covered[v] = (br, bc)
            ev = root_edges[v]
            require(ev[1] == rr * W + rc and ev[2] == op["node"], f"opening {v}: not the reflected answer")
    require(len(openings) == 15 and len(covered) == H * W, "representatives do not cover all 45 openings")

    return {
        "result": "VERIFIED",
        "claim": "empty 5x9 Col: Blue moving first loses, so the value is 0",
        "nodes": len(cert.nodes),
        "reachable": reached,
        "arith_nodes": cert.stats["A"],
        "expansion_nodes": cert.stats["E"],
        "comparison_nodes": cert.stats["C"],
        "blue_move_white_reply_edges": cert.stats["edges"],
        "comparison_children": cert.stats["comparisons_children"],
        "openings": len(openings),
        "openings_covered": len(covered),
    }


def verify_file(path: Path, root_name: str) -> dict:
    doc = load_records(path)
    cert = Certificate(doc["nodes"])
    rid = doc["roots"][root_name]
    cert.check_all()
    cert.check_acyclic_from(rid)
    h, w, a, b, q, s, kind, _ = cert.nodes[rid]
    return {"nodes": len(cert.nodes), "root": [h, w, a, b, str(q), s], **cert.stats}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--package", default=str(HERE), help="package directory (default: this one)")
    ap.add_argument("--file", help="check a single col-hybrid-v1 file instead of the package")
    ap.add_argument("--root", default="root", help="root name for --file")
    ap.add_argument("--no-sums", action="store_true", help="skip SHA256SUMS (for negative controls)")
    args = ap.parse_args()
    try:
        if args.file:
            out = verify_file(Path(args.file), args.root)
        else:
            out = verify_package(Path(args.package), check_sums=not args.no_sums)
    except (InvalidCertificate, KeyError, IndexError, TypeError, ValueError) as exc:
        print(json.dumps({"result": "REJECTED", "reason": f"{type(exc).__name__}: {exc}"}))
        return 1
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
