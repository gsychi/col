#!/usr/bin/env python3
"""sub.py QDIR NAME CAP [K=V ...] -- CMD ARGS   (writes QDIR/jobs/NAME.job; logs in QDIR/logs)"""
import json
import os
import sys

qdir, name, cap = os.path.abspath(sys.argv[1]), sys.argv[2], float(sys.argv[3])
rest = sys.argv[4:]
k = rest.index("--")
env = dict(x.split("=", 1) for x in rest[:k])
cmd = rest[k + 1:]
os.makedirs(os.path.join(qdir, "logs"), exist_ok=True)
os.makedirs(os.path.join(qdir, "jobs"), exist_ok=True)
slots = int(env.pop("SLOTS", 1))
job = {"cmd": cmd, "env": env, "cap": cap, "slots": slots,
       "out": os.path.join(qdir, "logs", name + ".out"), "err": os.path.join(qdir, "logs", name + ".err")}
tmp = os.path.join(qdir, "jobs", "." + name)
with open(tmp, "w") as fh:
    json.dump(job, fh)
os.rename(tmp, os.path.join(qdir, "jobs", name + ".job"))
