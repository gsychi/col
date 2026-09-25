#!/usr/bin/env python3
"""Append colout5 results from an .out file to runs/values.jsonl.

Usage: record.py OUTFILE [--threads N] [--note TEXT]
Only 'value' lines with an exact value are recorded as Completed;
INCONCLUSIVE lines are recorded with status Unknown.
"""
import argparse
import json
import re
from pathlib import Path

import families

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--threads", type=int, default=1)
ap.add_argument("--note", default="")
a = ap.parse_args()
done = set()
vj = HERE / "runs" / "values.jsonl"
for line in vj.read_text().splitlines():
    r = json.loads(line)
    done.add((r["family"], r["width"], r.get("status"), r.get("value"), r.get("log")))
with vj.open("a") as fh:
    for line in Path(a.out).read_text().splitlines():
        if not line.startswith("value"):
            continue
        _, label, val, secs, trail = line.split("\t")
        fam, n = label.rsplit("_", 1)
        n = int(n)
        A, B = families.family(fam, n)
        st = "Unknown" if val.startswith("INCONCLUSIVE") or val.startswith("CONFUSED") else "Completed"
        key = (fam, n, st, val, str(a.out))
        if key in done:
            continue
        rec = dict(family=fam, width=n, A=A, B=B, smax=14, tool="colout5", status=st, value=val,
                   trail=trail.strip("[] "), wall_seconds=float(secs.rstrip("s")), threads=a.threads,
                   log=str(a.out))
        if a.note:
            rec["note"] = a.note
        fh.write(json.dumps(rec) + "\n")
        print(json.dumps(rec))
