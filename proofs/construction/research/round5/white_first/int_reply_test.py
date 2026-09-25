#!/usr/bin/env python3
"""EVIDENCE: for K_n openings that need a White reply, find reply + vertical
seam decompositions whose region bounds, rounded up to integers, sum to <= 0.

Integer bounds matter because G <= k for an integer k >= 0 needs only
Blue-first facts (INTEGER_BOUNDS.md), while fractional or negative bounds
need White-first facts unless obtained by private reserve moves.

Usage: int_reply_test.py N [--top K] [--max-seams S]
"""
import argparse
import itertools
import json
import math
from fractions import Fraction as F

import decomp as D
import wf_families as W


def ceil_int(v):
    x, star = v
    c = math.ceil(x)
    return c + 1 if star and x == c else c


def best_integer_split(n, A, B, max_seams):
    seam_sets = [s for k in range(1, max_seams + 1) for s in itertools.combinations(range(n - 1), k)]
    jobs = []
    for seams in seam_sets:
        for b, regions, choice in D.decompositions(n, A, B, seams):
            jobs.append((seams, [D.sub_masks(n, A, b, c0, c1) for c0, c1 in regions]))
    D.batch_values([s for _, subs in jobs for s in subs], threads=6)
    best = None
    for seams, subs in jobs:
        vals = [D._cache[s] for s in subs]
        key = (sum(ceil_int(v) for v in vals), seams, [D.fmt(v) for v in vals])
        if best is None or key[0] < best[0]:
            best = key
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int)
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--max-seams", type=int, default=2)
    args = ap.parse_args()
    n = args.n
    rows = [json.loads(l) for l in open(f"runs/survey_K{n}.jsonl")]

    def num(s):
        return (F(0) if s == "*" else F(s.replace("+*", ""))), s.endswith("*")

    A0, B0 = W.family("KD", n)
    needs = sorted({tuple(r["open"]) for r in rows if "reply" not in r})
    for o in needs:
        a1, b1 = W.blue_move(A0, B0, *o, n)
        solo = best_integer_split(n, a1, b1, args.max_seams)
        if solo[0] <= -1:
            print(json.dumps(dict(open=o, mode="no-reply", int_sum=solo[0], seams=solo[1], pieces=solo[2])), flush=True)
            continue
        reps = [r for r in rows if tuple(r["open"]) == o and "reply" in r]
        reps = [r for r in reps if num(r["value"])[0] < 0 or (num(r["value"])[0] == 0 and not num(r["value"])[1])]
        reps.sort(key=lambda r: num(r["value"])[0])
        found = None
        for r in reps[: args.top]:
            a2, b2 = W.white_move(a1, b1, *r["reply"], n)
            res = best_integer_split(n, a2, b2, args.max_seams)
            if found is None or res[0] < found[0]:
                found = (res[0], r["reply"], r["value"], res[1], res[2])
            if res[0] <= 0:
                break
        print(json.dumps(dict(open=o, mode="reply", int_sum=found[0], reply=found[1], exact=found[2],
                              seams=found[3], pieces=found[4], ok=found[0] <= 0)), flush=True)


if __name__ == "__main__":
    main()
