#!/usr/bin/env python3
"""EVIDENCE tool: best vertical-seam comparison bounds for a 5 x n position.

A decomposition chooses seams (between column j and j+1) and, at each seam,
for every row whose two cells are both White-legal, which side loses its
White permission (Lemma 2 needs one endpoint of every deleted edge outside
B'). Regions are the column intervals between seams; each is valued exactly
(colval for width <= 5, colout5 otherwise), cached. Bound = sum of regions.

Library use: best_bounds(n, A, B, seam_candidates, max_seams).
"""
import itertools
import subprocess
from fractions import Fraction as F

import wf_families as W

COLVAL = "/tmp/white_first/colval"
COLOUT = "/tmp/white_first/colout5"
_cache = {}


def parse_val(s):
    star = s.endswith("+*") or s == "*"
    x = s[:-2] if s.endswith("+*") else ("0" if s == "*" else s)
    return F(x), star


def sub_masks(n, A, B, c0, c1):
    """Restrict (A,B) on 5 x n to columns c0..c1 inclusive -> masks on 5 x w."""
    w = c1 - c0 + 1
    a = b = 0
    for r in range(5):
        for c in range(c0, c1 + 1):
            if A >> (r * n + c) & 1:
                a |= 1 << (r * w + c - c0)
            if B >> (r * n + c) & 1:
                b |= 1 << (r * w + c - c0)
    return w, a, b


def batch_values(items, threads=4):
    """items: list of (w, a, b). Fills the cache. Width<=5 via colval."""
    todo = [(w, a, b) for (w, a, b) in set(items) if (w, a, b) not in _cache]
    small = [t for t in todo if t[0] <= 5]
    big = [t for t in todo if t[0] > 5]
    if small:
        inp = "".join(f"5 {w} {a} {b} q{i}\n" for i, (w, a, b) in enumerate(small))
        p = subprocess.run([COLVAL, "-t", "22"], input=inp, capture_output=True, text=True)
        for line in p.stdout.splitlines():
            f = line.split("\t")
            _cache[small[int(f[0][1:])]] = parse_val(f[1])
    if big:
        inp = "".join(f"value 5 {w} {a} {b} q{i}\n" for i, (w, a, b) in enumerate(big))
        p = subprocess.run([COLOUT, "-j", str(threads), "-t", "22", "-T", "22"], input=inp,
                           capture_output=True, text=True)
        for line in p.stdout.splitlines():
            f = line.split("\t")
            if f[0] == "value":
                _cache[big[int(f[1][1:])]] = parse_val(f[2])
    missing = [t for t in set(items) if t not in _cache]
    assert not missing, missing[:3]


def decompositions(n, A, B, seams):
    """Yield (A', B') virtual masks and the region list for every drop choice."""
    per_seam = []
    for j in seams:
        rows = [r for r in range(5) if B >> (r * n + j) & 1 and B >> (r * n + j + 1) & 1]
        per_seam.append([(j, rows, ch) for ch in itertools.product((0, 1), repeat=len(rows))])
    for choice in itertools.product(*per_seam):
        b = B
        for j, rows, ch in choice:
            for r, side in zip(rows, ch):
                b &= ~(1 << (r * n + j + side))
        cuts = [-1] + sorted(seams) + [n - 1]
        regions = [(cuts[i] + 1, cuts[i + 1]) for i in range(len(cuts) - 1)]
        yield b, regions, choice


def total(value_list):
    x = sum(v[0] for v in value_list)
    s = sum(v[1] for v in value_list) % 2
    return x, bool(s)


def best_bounds(n, A, B, seam_sets, keep=5):
    """Evaluate all drop choices for each seam set; return the best `keep`
    bounds as (x, star, seams, regions, drops, region_values)."""
    jobs = []
    for seams in seam_sets:
        for b, regions, choice in decompositions(n, A, B, seams):
            subs = [sub_masks(n, A, b, c0, c1) for c0, c1 in regions]
            jobs.append((seams, regions, choice, subs))
    batch_values([s for j in jobs for s in j[3]])
    res = []
    for seams, regions, choice, subs in jobs:
        vals = [_cache[s] for s in subs]
        x, st = total(vals)
        res.append((x, st, seams, regions, choice, vals))
    res.sort(key=lambda t: (t[0], not t[1]))
    return res[:keep]


def fmt(v):
    x, s = v
    return f"{x}" + ("+*" if s else "") if x != 0 or not s else "*"
