#!/usr/bin/env python3
"""Rigorous one-sided bounds on a five-row family value from cut moves.

Lemma 4 of COL_VALUES.md (PROVED): for a White move v,  G <= G^{R,v} + *,  and
G <= G^{R,v} - 1 if v is White-only. Dually for a Blue move v, G^{L,v} + * <= G,
and G^{L,v} + 1 <= G if v is Blue-only. Iterating over a set S of pairwise
non-adjacent White-legal cells (White plays them one after another while Blue
"passes"; each stays legal because S is independent):

    G <= G^{R,S} + k*  - m        (k = #shared cells of S, m = #White-only cells of S)

and dually  G >= G^{L,S} + k* + m  for Blue sets. If S cuts the strip into
components, G^{R,S} is the sum of the component values. With exact component
values y_i + e_i*, the number part x of G satisfies

    x <= sum y_i - m      (White cut),       x >= sum y_i + m      (Blue cut).

(From G <= y + eta*: x + eps* <= y + eta* forces x <= y.)

Component values come from colout5 bisection (EVIDENCE), so the bounds are
EVIDENCE-level unless the component values are certified.

Usage: cutbound.py FAMILY WIDTH [--side white|blue|both] [--maxpiece N] [--win W] [--maxs K]
"""
import argparse
import itertools
import json
import subprocess
from fractions import Fraction as F
from pathlib import Path

import families

HERE = Path(__file__).resolve().parent
CACHE = HERE / "runs" / "piece_values.json"
SOLVER = "/tmp/ground_truth/colout5"
H = 5


def nbrs(v, n):
    r, c = divmod(v, n)
    out = []
    if r > 0: out.append(v - n)
    if r < H - 1: out.append(v + n)
    if c > 0: out.append(v - 1)
    if c < n - 1: out.append(v + 1)
    return out


def components(a, b, n):
    live = a | b
    comps = []
    seen = 0
    for v in range(H * n):
        if not (live >> v & 1) or (seen >> v & 1):
            continue
        comp = 1 << v
        stack = [v]
        while stack:
            u = stack.pop()
            for w in nbrs(u, n):
                if comp >> w & 1:
                    continue
                if ((a >> u & 1) and (a >> w & 1)) or ((b >> u & 1) and (b >> w & 1)):
                    comp |= 1 << w
                    stack.append(w)
        seen |= comp
        comps.append((a & comp, b & comp))
    return comps


def parse_val(s):
    if s == "*":
        return F(0), 1
    if s.endswith("+*"):
        return F(s[:-2]), 1
    return F(s), 0


class Valuer:
    def __init__(self, args):
        self.cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
        self.args = args

    def key(self, n, a, b):
        return f"{n}:{a}:{b}"

    def values(self, n, pieces):
        todo = [p for p in set(pieces) if self.key(n, *p) not in self.cache]
        if todo:
            q = "".join(f"value 5 {n} {a} {b} P{i}\n" for i, (a, b) in enumerate(todo))
            p = subprocess.run([SOLVER, "-S", "14", "-t", "20", "-T", "21", "-j", "1"], input=q,
                               capture_output=True, text=True)
            got = {}
            for line in p.stdout.splitlines():
                if line.startswith("value"):
                    _, lab, val, *_ = line.split("\t")
                    got[int(lab[1:])] = val
            for i, pc in enumerate(todo):
                if i not in got or got[i].startswith(("INCONCLUSIVE", "CONFUSED")):
                    raise SystemExit(f"piece valuation failed: {pc} {p.stderr[-300:]}")
                self.cache[self.key(n, *pc)] = got[i]
            CACHE.write_text(json.dumps(self.cache))
        return {pc: parse_val(self.cache[self.key(n, *pc)]) for pc in pieces}


def independent(cells, n):
    s = set(cells)
    return all(w not in s for v in cells for w in nbrs(v, n))


def cut_sets(n, lo_col, win, maxs):
    cells = [r * n + c for c in range(lo_col, min(n, lo_col + win)) for r in range(H)]
    for k in range(1, maxs + 1):
        for S in itertools.combinations(cells, k):
            if independent(S, n):
                yield S


def bounds(fam, n, side, maxpiece, win, maxs, valuer):
    A, B = families.family(fam, n)
    results = []
    sides = ["white", "blue"] if side == "both" else [side]
    for sd in sides:
        cand = []
        for c0 in range(0, n):
            for S in cut_sets(n, c0, win, maxs):
                Sm = sum(1 << v for v in S)
                closed = Sm
                for v in S:
                    for w in nbrs(v, n):
                        closed |= 1 << w
                if sd == "white":
                    if Sm & ~B:
                        continue
                    a2, b2 = A & ~Sm, B & ~closed
                    only = bin(Sm & ~A).count("1")
                else:
                    if Sm & ~A:
                        continue
                    a2, b2 = A & ~closed, B & ~Sm
                    only = bin(Sm & ~B).count("1")
                comps = components(a2, b2, n)
                if not comps or max(bin(a | b).count("1") for a, b in comps) > maxpiece:
                    continue
                cand.append((S, comps, only))
        # value all pieces in one batch
        allp = [p for _, comps, _ in cand for p in comps]
        vals = valuer.values(n, allp) if allp else {}
        best = None
        for S, comps, only in cand:
            y = sum(vals[p][0] for p in comps)
            e = (sum(vals[p][1] for p in comps) + len(S) - only) % 2
            bnd = y - only if sd == "white" else y + only
            if best is None or (sd == "white" and bnd < best[0]) or (sd == "blue" and bnd > best[0]):
                best = (bnd, S, [str(vals[p][0]) + ("+*" if vals[p][1] else "") for p in comps], only, e)
        results.append((sd, best, len(cand)))
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("family")
    ap.add_argument("width", type=int)
    ap.add_argument("--side", default="both")
    ap.add_argument("--maxpiece", type=int, default=30)
    ap.add_argument("--win", type=int, default=2)
    ap.add_argument("--maxs", type=int, default=6)
    a = ap.parse_args()
    v = Valuer(a)
    for sd, best, ncand in bounds(a.family, a.width, a.side, a.maxpiece, a.win, a.maxs, v):
        if best is None:
            print(f"{a.family}_{a.width} {sd}: no cut with pieces <= {a.maxpiece} ({ncand} candidates)")
            continue
        bnd, S, pv, only, e = best
        cells = [divmod(s, a.width) for s in S]
        rel = "<=" if sd == "white" else ">="
        print(f"{a.family}_{a.width} {sd}: x {rel} {bnd}   S={cells} pieces={pv} only={only} ({ncand} cuts)")
