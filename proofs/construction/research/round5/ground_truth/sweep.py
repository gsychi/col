#!/usr/bin/env python3
"""Run exact-value bisections with colout over (family, width) jobs in parallel.

Discovery only (EVIDENCE). Each job is one colout process (single thread,
small tables) with a wall-clock timeout; a timeout is recorded as Unknown.
Results are appended to runs/values.jsonl.

Usage: sweep.py [-j WORKERS] [--timeout SEC] [-S SMAX] FAM:WIDTH[:GUESS] ...
"""
import argparse
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import families

HERE = Path(__file__).resolve().parent
COLOUT = "/tmp/ground_truth/colout"
OUT = HERE / "runs" / "values.jsonl"


def job(spec, timeout, smax, tlog):
    parts = spec.split(":")
    fam, width = parts[0], int(parts[1])
    guess = parts[2] if len(parts) > 2 else None
    a, b = families.family(fam, width)
    label = f"{fam}_{width}"
    line = f"value 5 {width} {a} {b} {label}" + (f" {guess}" if guess else "") + "\n"
    t0 = time.time()
    rec = dict(family=fam, width=width, A=a, B=b, guess=guess, smax=smax, tool="colout")
    try:
        p = subprocess.run([COLOUT, "-S", str(smax), "-t", str(tlog), "-T", str(tlog)], input=line,
                           capture_output=True, text=True, timeout=timeout)
        rec["stderr_tail"] = p.stderr.strip().splitlines()[-12:]
        out = [l for l in p.stdout.splitlines() if l.startswith("value")]
        if p.returncode != 0 or not out:
            rec.update(status="Error", returncode=p.returncode)
        else:
            _, lab, val, secs, trail = out[0].split("\t")
            rec.update(status="Completed", value=val, trail=trail.strip("[] "))
    except subprocess.TimeoutExpired as e:
        err = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
        rec.update(status="Unknown", reason=f"timeout {timeout}s", stderr_tail=err.strip().splitlines()[-12:])
    rec["wall_seconds"] = round(time.time() - t0, 1)
    with OUT.open("a") as fh:
        fh.write(json.dumps(rec) + "\n")
    print(json.dumps({k: rec.get(k) for k in ("family", "width", "status", "value", "trail", "wall_seconds")}),
          flush=True)
    return rec


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-j", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("-S", type=int, default=14)
    ap.add_argument("-t", type=int, default=20)
    ap.add_argument("jobs", nargs="+")
    args = ap.parse_args()
    OUT.parent.mkdir(exist_ok=True)
    with ThreadPoolExecutor(args.j) as ex:
        list(ex.map(lambda s: job(s, args.timeout, args.S, args.t), args.jobs))
