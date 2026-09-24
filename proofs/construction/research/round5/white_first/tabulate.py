#!/usr/bin/env python3
"""EVIDENCE: exact values of the white_first families, appended to
runs/values.jsonl (one JSON object per value). Widths <= 5 use colval, wider
ones colout5 bisection (P-outcome at the value).

Usage: tabulate.py FAM[,FAM...] W1-W2 [-j THREADS] [-L SECONDS]
"""
import argparse
import json
import subprocess
import time
from pathlib import Path

import wf_families as W

HERE = Path(__file__).resolve().parent
OUT = HERE / "runs" / "values.jsonl"


def known():
    d = {}
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            r = json.loads(line)
            d[(r["family"], r["width"])] = r["value"]
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fams")
    ap.add_argument("widths")
    ap.add_argument("-j", type=int, default=4)
    ap.add_argument("-L", type=float, default=1800)
    a = ap.parse_args()
    w1, w2 = map(int, a.widths.split("-"))
    have = known()
    for w in range(w1, w2 + 1):
        for f in a.fams.split(","):
            if (f, w) in have:
                continue
            try:
                A, B = W.family(f, w)
            except AssertionError:
                continue
            t0 = time.time()
            if w <= 5:
                p = subprocess.run(["/tmp/white_first/colval", "-t", "22"], input=f"5 {w} {A} {B} x\n",
                                   capture_output=True, text=True)
                val = p.stdout.split("\t")[1]
                tool = "colval"
            else:
                p = subprocess.run(["/tmp/white_first/colout5", "-j", str(a.j), "-t", "22", "-T", "23",
                                    "-L", str(a.L)], input=f"value 5 {w} {A} {B} x\n",
                                   capture_output=True, text=True)
                line = [l for l in p.stdout.splitlines() if l.startswith("value")]
                val = line[0].split("\t")[2] if line else "ERROR"
                tool = "colout5"
            rec = dict(family=f, width=w, A=A, B=B, value=val, tool=tool, secs=round(time.time() - t0, 1))
            with OUT.open("a") as fh:
                fh.write(json.dumps(rec) + "\n")
            print(f, w, val, rec["secs"], flush=True)


if __name__ == "__main__":
    main()
