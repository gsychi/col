#!/usr/bin/env python3
"""Launch a command fully detached (new session, stdin from a file, logs to files)
with a wall-clock cap. The child survives the death of the launching shell.

Usage: launch.py --cap SECONDS --in QUERYFILE --out OUT --err ERR -- CMD ARGS...
On cap expiry the child gets SIGTERM, then SIGKILL; a line
"LAUNCH: TIMEOUT after N s" is appended to ERR (a timeout is INCONCLUSIVE).
"""
import argparse
import os
import signal
import sys
import time

ap = argparse.ArgumentParser()
ap.add_argument("--cap", type=int, required=True)
ap.add_argument("--in", dest="inp", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--err", required=True)
ap.add_argument("cmd", nargs=argparse.REMAINDER)
a = ap.parse_args()
cmd = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd

if os.fork():
    sys.exit(0)
os.setsid()
if os.fork():
    os._exit(0)
# grandchild: supervisor in its own session
devnull = os.open(os.devnull, os.O_RDWR)
os.dup2(devnull, 0)
t0 = time.time()
pid = os.fork()
if pid == 0:
    fi = os.open(a.inp, os.O_RDONLY)
    fo = os.open(a.out, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    fe = os.open(a.err, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    os.dup2(fi, 0)
    os.dup2(fo, 1)
    os.dup2(fe, 2)
    os.execv(cmd[0], cmd)
with open(a.err, "a") as fh:
    fh.write(f"LAUNCH: pid {pid} started {time.ctime(t0)} cap {a.cap}s cmd {' '.join(cmd)}\n")
while True:
    done, status = os.waitpid(pid, os.WNOHANG)
    if done:
        with open(a.err, "a") as fh:
            fh.write(f"LAUNCH: exit status {status} after {time.time() - t0:.0f} s\n")
        break
    if time.time() - t0 > a.cap:
        os.kill(pid, signal.SIGTERM)
        time.sleep(5)
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        os.waitpid(pid, 0)
        with open(a.err, "a") as fh:
            fh.write(f"LAUNCH: TIMEOUT after {a.cap} s (INCONCLUSIVE)\n")
        break
    time.sleep(2)
