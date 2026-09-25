#!/usr/bin/env python3
"""Benchmark solver configurations: each query in a fresh process.

Usage: bench.py QUERYFILE 'label=binary args' ['label=binary args' ...]
Prints label, query label, value, seconds, root nodes (summed over the trail).
"""
import re
import subprocess
import sys
import time

qfile = sys.argv[1]
queries = [l for l in open(qfile).read().splitlines() if l.strip() and not l.startswith("#")]
for spec in sys.argv[2:]:
    label, cmd = spec.split("=", 1)
    tot = 0.0
    totn = 0
    for q in queries:
        t0 = time.time()
        p = subprocess.run(cmd.split(), input=q + "\n", capture_output=True, text=True)
        dt = time.time() - t0
        tot += dt
        out = [l for l in p.stdout.splitlines() if l.startswith("value")]
        nodes = sum(int(a) + int(b) for a, b in re.findall(r"nodes=(\d+)\+(\d+)", p.stderr))
        totn += nodes
        v = out[0].split("\t")[2] if out else "ERR"
        print(f"{label}\t{q.split()[5]}\t{v}\t{dt:.1f}s\t{nodes}", flush=True)
    print(f"{label}\tTOTAL\t\t{tot:.1f}s\t{totn}", flush=True)
