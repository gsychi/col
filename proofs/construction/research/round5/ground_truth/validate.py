#!/usr/bin/env python3
"""Validate a solver binary against every recorded value (runs/values.jsonl
"Completed" rows and the colval enumeration files), by full bisection
without a guess (or with the known value as guess if --guess).

Usage: validate.py BINARY [--maxw W] [--minw W] [--guess] [--fams F1,F2] [--args 'solver args']
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import families

HERE = Path(__file__).resolve().parent

ap = argparse.ArgumentParser()
ap.add_argument("binary")
ap.add_argument("--maxw", type=int, default=6)
ap.add_argument("--minw", type=int, default=1)
ap.add_argument("--guess", action="store_true")
ap.add_argument("--fams", default="")
ap.add_argument("--args", default="")
a = ap.parse_args()

known = {}
for name in ("colval_w1to5.txt", "colval_small_extra.txt"):
    p = HERE / "runs" / name
    if p.exists():
        for line in p.read_text().splitlines():
            m = re.match(r"^([A-Z]+)_(\d+)\t(\S+)\t", line)
            if m and not (m.group(1) == "M" and m.group(2) == "1"):
                known[(m.group(1), int(m.group(2)))] = m.group(3)
for line in (HERE / "runs" / "values.jsonl").read_text().splitlines():
    r = json.loads(line)
    if r.get("status") == "Completed" and r.get("tool", "colout") in ("colout", "colout5"):
        known.setdefault((r["family"], r["width"]), r["value"])


def norm(v):
    return "0+*" if v == "*" else v


fams = set(a.fams.split(",")) if a.fams else None
jobs = sorted(k for k in known if a.minw <= k[1] <= a.maxw and (fams is None or k[0] in fams))
bad = 0
t0 = time.time()
for fam, n in jobs:
    if fam == "M" and n % 2 == 0:
        continue
    A, B = families.family(fam, n)
    exp = known[(fam, n)]
    g = ""
    if a.guess:
        g = " " + (exp.replace("+*", "") if exp != "*" else "0")
    q = f"value 5 {n} {A} {B} {fam}_{n}{g}\n"
    p = subprocess.run([a.binary] + a.args.split(), input=q, capture_output=True, text=True)
    out = [l for l in p.stdout.splitlines() if l.startswith("value")]
    got = out[0].split("\t")[2] if out else f"ERR rc={p.returncode} {p.stderr[-200:]}"
    ok = norm(got) == norm(exp)
    bad += not ok
    print(f"{fam}_{n}\texpected {exp}\tgot {got}\t{'ok' if ok else 'MISMATCH'}\t{out[0].split(chr(9))[3] if out else ''}",
          flush=True)
print(f"{len(jobs)} checked, {bad} mismatches, {time.time() - t0:.0f}s")
sys.exit(1 if bad else 0)
