#!/usr/bin/env python3
"""Outcome tests G - q (+*) with the isolated Rust raw-permission solver.

Discovery only (EVIDENCE). The board occupies columns 0..n-1 of an ambient
5 x (n+2) board; column n is dead; column n+1 carries a vertical-path gadget
whose exact value (checked by gadgets.py with plain Conway order) is -q
(+* if requested). A budget-exhausted run is reported as Unknown.

Usage: rawtest.py FAMILY WIDTH Q [star] [--budget N]
  prints for Blue-first and White-first whether the mover wins.
"""
from fractions import Fraction as F
import argparse
import json
import subprocess
import sys

import families
import gadgets

RAW = "/tmp/ground_truth/gt_rawsolve"


def gadget_for(value, star):
    table = gadgets.table()
    key = (F(value), bool(star))
    if key not in table:
        raise SystemExit(f"no 5-cell gadget for {value}{'+*' if star else ''}")
    return table[key]


def ambient(a, b, n, pattern):
    width = n + 2
    aa = bb = 0
    for r in range(5):
        for c in range(n):
            if a >> (r * n + c) & 1:
                aa |= 1 << (r * width + c)
            if b >> (r * n + c) & 1:
                bb |= 1 << (r * width + c)
        s = pattern[r]
        if s in "ob":
            aa |= 1 << (r * width + n + 1)
        if s in "ow":
            bb |= 1 << (r * width + n + 1)
    return width, aa, bb


def run(width, aa, bb, turn, budget, timeout):
    try:
        raw = subprocess.check_output([RAW, "5", str(width), str(aa), str(bb), str(turn), str(budget)],
                                      text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return dict(status="Unknown", reason=f"timeout {timeout}s", turn=turn)
    res = json.loads(raw)
    res["status"] = "Unknown" if res["states"] >= budget else "Completed"
    return res


def test(a, b, n, q, star, budget, timeout=1800, turns=(0, 1)):
    pat = gadget_for(-F(q), star)
    width, aa, bb = ambient(a, b, n, pat)
    out = {}
    for turn, who in ((0, "blue_first"), (1, "white_first")):
        if turn in turns:
            out[who] = run(width, aa, bb, turn, budget, timeout)
        else:
            out[who] = dict(status="Skipped")
    return pat, out


def classify(out):
    """Outcome class of G - q (+*): L, R, P, N or Unknown."""
    bf, wf = out["blue_first"], out["white_first"]
    if bf["status"] != "Completed" or wf["status"] != "Completed":
        return "Unknown"
    blue = bf["actor_wins"]
    white = wf["actor_wins"]
    return {(True, True): "N", (True, False): "L", (False, True): "R", (False, False): "P"}[(blue, white)]


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("family")
    p.add_argument("width", type=int)
    p.add_argument("q")
    p.add_argument("star", nargs="?", default="")
    p.add_argument("--budget", type=int, default=10**10)
    p.add_argument("--timeout", type=int, default=1800)
    p.add_argument("--turn", choices=["both", "blue", "white"], default="both")
    args = p.parse_args()
    a, b = families.family(args.family, args.width)
    turns = {"both": (0, 1), "blue": (0,), "white": (1,)}[args.turn]
    pat, out = test(a, b, args.width, F(args.q), args.star == "star", args.budget, args.timeout, turns)
    cls = classify(out)
    print(json.dumps(dict(family=args.family, width=args.width, q=args.q, star=args.star == "star",
                          gadget=pat, outcome_of_G_minus_q=cls,
                          blue_first=out["blue_first"], white_first=out["white_first"])))
