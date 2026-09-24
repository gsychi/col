#!/usr/bin/env python3
"""Detached job pool with a STOP switch.

pool.py QDIR NSLOTS
Jobs are JSON files QDIR/jobs/NAME.job: {"cmd": [...], "env": {...}, "cap": s,
"out": path, "err": path, "cwd": path}.  Up to NSLOTS run at once (a job may
declare "slots": k).  Each job moves jobs/ -> running/ -> done/ (done file gets
"status" and "seconds").  If the STOP file exists, every child is killed and
the pool exits.  QDIR/NSLOTS may be rewritten while running (file QDIR/slots).
"""
import json
import os
import signal
import sys
import time

STOP = "/Users/gsychi/Documents/col/proofs/construction/research/round5/STOP"
qdir = sys.argv[1]
nslots = int(sys.argv[2])
for d in ("jobs", "running", "done"):
    os.makedirs(os.path.join(qdir, d), exist_ok=True)

if os.fork():
    sys.exit(0)
os.setsid()
if os.fork():
    os._exit(0)
devnull = os.open(os.devnull, os.O_RDWR)
os.dup2(devnull, 0)
logf = open(os.path.join(qdir, "pool.log"), "a", buffering=1)
os.dup2(logf.fileno(), 1)
os.dup2(logf.fileno(), 2)
with open(os.path.join(qdir, "pool.pid"), "w") as fh:
    fh.write(str(os.getpid()))
print(f"pool {os.getpid()} started {time.ctime()} slots {nslots}", flush=True)
running = {}  # pid -> (name, job, t0)


def used():
    return sum(j.get("slots", 1) for _, j, _ in running.values())


def killall(sig):
    for pid in list(running):
        try:
            os.killpg(pid, sig)
        except ProcessLookupError:
            pass


while True:
    if os.path.exists(STOP):
        print(f"STOP seen {time.ctime()}; killing {len(running)} jobs", flush=True)
        killall(signal.SIGTERM)
        time.sleep(3)
        killall(signal.SIGKILL)
        break
    try:
        with open(os.path.join(qdir, "slots")) as fh:
            nslots = int(fh.read().strip())
    except (OSError, ValueError):
        pass
    # reap
    for pid in list(running):
        done, status = os.waitpid(pid, os.WNOHANG)
        name, job, t0 = running[pid]
        timeout = False
        if not done and time.time() - t0 > job.get("cap", 1e9):
            os.killpg(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
            done, status, timeout = pid, -9, True
        if done:
            del running[pid]
            job["status"] = "TIMEOUT" if timeout else status
            job["seconds"] = round(time.time() - t0)
            os.remove(os.path.join(qdir, "running", name))
            with open(os.path.join(qdir, "done", name), "w") as fh:
                json.dump(job, fh)
            print(f"done {name} status {job['status']} {job['seconds']}s", flush=True)
    # launch
    pending = sorted(f for f in os.listdir(os.path.join(qdir, "jobs")) if f.endswith(".job"))
    for name in pending:
        path = os.path.join(qdir, "jobs", name)
        try:
            with open(path) as fh:
                job = json.load(fh)
        except (OSError, ValueError):
            continue
        if used() + job.get("slots", 1) > nslots:
            break
        os.rename(path, os.path.join(qdir, "running", name))
        pid = os.fork()
        if pid == 0:
            os.setpgid(0, 0)
            env = dict(os.environ)
            env.update({k: str(v) for k, v in job.get("env", {}).items()})
            fo = os.open(job["out"], os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
            fe = os.open(job["err"], os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
            os.dup2(fo, 1)
            os.dup2(fe, 2)
            if job.get("cwd"):
                os.chdir(job["cwd"])
            os.execve(job["cmd"][0], job["cmd"], env)
        running[pid] = (name, job, time.time())
        print(f"start {name} pid {pid} {time.ctime()}", flush=True)
    time.sleep(2)
print(f"pool exit {time.ctime()}", flush=True)
