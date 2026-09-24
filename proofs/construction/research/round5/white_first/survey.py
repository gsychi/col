#!/usr/bin/env python3
"""EVIDENCE survey: for K_n, every Blue opening (rows 0..2 by vertical
symmetry) -> child value (White next), and for each opening every White
reply -> grandchild value (Blue next). Uses colout5 (discovery solver).

Usage: survey.py N [--replies] [-j THREADS]
Output: JSON lines to stdout.
"""
import argparse
import json
import subprocess

import wf_families as W

COLOUT = "/tmp/white_first/colout5"


def values(queries, threads, extra=()):
    """queries: list of (label, n, a, b). Returns {label: value-string}."""
    inp = "".join(f"value 5 {n} {a} {b} {lab}\n" for lab, n, a, b in queries)
    p = subprocess.run([COLOUT, "-j", str(threads), "-t", "22", "-T", "22", *extra], input=inp,
                       capture_output=True, text=True)
    out = {}
    for line in p.stdout.splitlines():
        f = line.split("\t")
        if f[0] == "value":
            out[f[1]] = f[2]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int)
    ap.add_argument("--fam", default="KD")
    ap.add_argument("--replies", action="store_true")
    ap.add_argument("-j", type=int, default=4)
    a = ap.parse_args()
    n = a.n
    A, B = W.family(a.fam, n)
    qs = []
    meta = {}
    for r in range(3):
        for c in range(n):
            if not A & W.bit(r, c, n):
                continue
            a1, b1 = W.blue_move(A, B, r, c, n)
            lab = f"o{r}_{c}"
            qs.append((lab, n, a1, b1))
            meta[lab] = dict(open=(r, c))
            if a.replies:
                for rr in range(5):
                    for cc in range(n):
                        if b1 & W.bit(rr, cc, n):
                            a2, b2 = W.white_move(a1, b1, rr, cc, n)
                            l2 = f"o{r}_{c}_w{rr}_{cc}"
                            qs.append((l2, n, a2, b2))
                            meta[l2] = dict(open=(r, c), reply=(rr, cc))
    res = values(qs, a.j)
    for lab, *_ in qs:
        d = dict(meta[lab])
        d["value"] = res.get(lab, "?")
        print(json.dumps(d))


if __name__ == "__main__":
    main()
