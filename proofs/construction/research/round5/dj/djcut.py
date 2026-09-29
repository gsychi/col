#!/usr/bin/env python3
"""Cut-based bounds for 5-row strips (EVIDENCE tool).

Proves G <= q by Conway's definition, bounding options with the comparison
principle (COL_VALUES Lemma 2): cut at column seams, and for every cut edge
whose two endpoints are both White-legal, drop White at one endpoint. Then
G <= sum of pieces. Lower bounds use the colour swap (-G(A,B) = G(B,A)).

  G <= q  iff  every Blue option G^L <| q   and   G <| q^R (if q^R exists).
  G^L <| q : a cut of G^L with sum <| q, or a White reply y with G^{Ly} <= q
             (by a cut, by recursion, or by search).
  G <| q^R : a cut of G with sum <| q^R, or a White move y with G^y <= q^R.

Piece values are exact values from xcolout5 (bisection with outcome classes);
unresolved obligations may fall back to an xcolout5 outcome search.
Values are x or x+* (COL_VALUES Thm 5); `le`/`lf` implement Table 1.
"""
import json
import os
import subprocess
import sys
import time
from fractions import Fraction as F

HERE = os.path.dirname(os.path.abspath(__file__))
SOLVER = os.environ.get("XCOLOUT5", "/tmp/dj/xcolout5")
PVAL = os.environ.get("PVAL", "/tmp/dj/pval")
CACHE = os.path.join(HERE, "runs", "piece_values.txt")
FULL = 31


# ---------------------------------------------------------------- strips
def undraw(d):
    rows = d.split("/")
    w = len(rows[0])
    s = []
    for c in range(w):
        a = b = 0
        for r in range(5):
            ch = rows[r][c]
            if ch in "ob":
                a |= 1 << r
            if ch in "ow":
                b |= 1 << r
        s.append((a, b))
    return tuple(s)


def draw(s):
    out = []
    for r in range(5):
        line = ""
        for a, b in s:
            x, y = (a >> r) & 1, (b >> r) & 1
            line += "o" if x and y else "b" if x else "w" if y else "."
        out.append(line)
    return "/".join(out)


def family(left, right, w):
    """P at column 0 and Q at column w-1 (patterns top to bottom), neutral between."""
    def col(p):
        a = sum(1 << r for r in range(5) if p[r] in "ob")
        b = sum(1 << r for r in range(5) if p[r] in "ow")
        return a, b
    s = [(FULL, FULL)] * w
    la, lb = col(left)
    ra, rb = col(right)
    s[0] = (s[0][0] & la, s[0][1] & lb)
    s[w - 1] = (s[w - 1][0] & ra, s[w - 1][1] & rb)
    return tuple(s)


def bmove(s, r, c):
    s = list(s)
    a, b = s[c]
    if not (a >> r) & 1:
        return None
    a &= ~(1 << r)
    b &= ~(1 << r)
    if r > 0:
        a &= ~(1 << (r - 1))
    if r < 4:
        a &= ~(1 << (r + 1))
    s[c] = (a, b)
    if c > 0:
        s[c - 1] = (s[c - 1][0] & ~(1 << r), s[c - 1][1])
    if c + 1 < len(s):
        s[c + 1] = (s[c + 1][0] & ~(1 << r), s[c + 1][1])
    return tuple(s)


def swap(s):
    return tuple((b, a) for a, b in s)


def wmove(s, r, c):
    t = bmove(swap(s), r, c)
    return None if t is None else swap(t)


def vflip5(x):
    return sum(1 << (4 - r) for r in range(5) if (x >> r) & 1)


def trim_split(s):
    """Components separated by dead columns (value is additive)."""
    parts, cur = [], []
    for a, b in s:
        if a | b:
            cur.append((a, b))
        elif cur:
            parts.append(tuple(cur))
            cur = []
    if cur:
        parts.append(tuple(cur))
    return parts


def skey(s):
    return "".join(chr(97 + a) + chr(65 + b) for a, b in s)


def canon(s):
    v = tuple((vflip5(a), vflip5(b)) for a, b in s)
    return min(skey(s), skey(v), skey(s[::-1]), skey(v[::-1]))


def masks(s):
    w = len(s)
    A = B = 0
    for c, (a, b) in enumerate(s):
        for r in range(5):
            if (a >> r) & 1:
                A |= 1 << (r * w + c)
            if (b >> r) & 1:
                B |= 1 << (r * w + c)
    return A, B


# ---------------------------------------------------------------- values x + e*
def vparse(t):
    star = t.endswith("+*") or t == "*"
    if t == "*":
        return (F(0), 1)
    if star:
        t = t[:-2]
    return (F(t), 1 if star else 0)


def vstr(v):
    x, e = v
    if x == 0:
        return "*" if e else "0"
    return str(x) + ("+*" if e else "")


def vadd(u, v):
    return (u[0] + v[0], u[1] ^ v[1])


def le(u, v):
    """u <= v for values x+e* (COL_VALUES Table 1)."""
    return u[0] <= v[0] if u[1] == v[1] else u[0] < v[0]


def lf(u, v):
    """u <| v  (not v <= u)."""
    return not le(v, u)


def neg(v):
    return (-v[0], v[1])


def right_option(q):
    x, e = q
    if e:
        return (x, 0)
    if x.denominator == 1:
        return None if x >= 0 else (x + 1, 0)
    return (x + F(1, x.denominator), 0)


def left_option(q):
    r = right_option(neg(q))
    return None if r is None else neg(r)


# ---------------------------------------------------------------- value oracle
class Oracle:
    def __init__(self, maxw=6, log=None):
        self.vals = {}
        self.maxw = maxw
        self.proc = None
        self.log = log
        self.nq = 0
        if os.path.exists(CACHE):
            for line in open(CACHE):
                k, v = line.split()
                self.vals[k] = vparse(v)
        self.fh = open(CACHE, "a")

    def _start(self):
        self.proc = subprocess.Popen([PVAL, "23"], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)

    def comp(self, s):
        k = canon(s)
        if k in self.vals:
            return self.vals[k]
        if len(s) > self.maxw:
            return None
        if self.proc is None:
            self._start()
        A, B = masks(s)
        self.proc.stdin.write(f"{len(s)} {A} {B}\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline().strip()
        if not line:
            raise RuntimeError("pval failed")
        v = vparse(line)
        self.nq += 1
        self.vals[k] = v
        self.fh.write(f"{k} {vstr(v)}\n")
        self.fh.flush()
        return v

    def value(self, s):
        tot = (F(0), 0)
        for p in trim_split(s):
            v = self.comp(p)
            if v is None:
                return None
            tot = vadd(tot, v)
        return tot


def search_first(s, q, who, limit):
    """Outcome of G - q with `who` moving first, by xcolout5 (time-limited)."""
    A, B = masks(s)
    qs = str(q[0])
    inp = f"first 5 {len(s)} {A} {B} {qs} {q[1]} s {who}\n"
    try:
        r = subprocess.run([SOLVER, "-j", str(THREADS), "-t", "22", "-T", "24", "-L", str(limit)], input=inp,
                           capture_output=True, text=True, timeout=limit + 120)
    except subprocess.TimeoutExpired:
        return None
    for line in r.stdout.splitlines():
        f = line.split("\t")
        if f[0] == "first":
            return {"WINS": True, "LOSES": False}.get(f[4])
    return None


THREADS = 2


# ---------------------------------------------------------------- cuts
def upper_cuts(s, maxw, maxseams=2, alldrops=True, focus=None):
    """Yield (pieces, description) with G(s) <= sum(pieces)."""
    w = len(s)
    seams_all = list(range(w - 1))
    cands = []
    for j in seams_all:
        cands.append((j,))
    if maxseams >= 2:
        for i in seams_all:
            for j in seams_all:
                if j > i:
                    cands.append((i, j))
    if maxseams >= 3:
        for i in seams_all:
            for j in seams_all:
                for k in seams_all:
                    if i < j < k:
                        cands.append((i, j, k))

    def widths(sm):
        b = [-1] + list(sm) + [w - 1]
        return [b[t + 1] - b[t] for t in range(len(b) - 1)]

    cands = [c for c in cands if max(widths(c)) <= maxw]
    if focus is not None:
        cands.sort(key=lambda c: (max(widths(c)), min(abs(j + 0.5 - focus) for j in c)))
    else:
        cands.sort(key=lambda c: (max(widths(c)), len(c)))
    for sm in cands:
        # rows that need a White drop at each seam
        for drops in drop_choices(s, sm, alldrops):
            t = list(s)
            for j, (L, R) in zip(sm, drops):
                t[j] = (t[j][0], t[j][1] & ~L)
                t[j + 1] = (t[j + 1][0], t[j + 1][1] & ~R)
            ok = True
            for j in sm:
                if t[j][1] & t[j + 1][1]:
                    ok = False
            if not ok:
                continue
            b = [-1] + list(sm) + [w - 1]
            pieces = [tuple(t[b[i] + 1:b[i + 1] + 1]) for i in range(len(b) - 1)]
            yield pieces, (sm, drops)


def drop_choices(s, sm, alldrops):
    per = []
    for j in sm:
        need = s[j][1] & s[j + 1][1]
        rows = [r for r in range(5) if (need >> r) & 1]
        opts = []
        if alldrops:
            for m in range(1 << len(rows)):
                L = sum(1 << rows[i] for i in range(len(rows)) if (m >> i) & 1)
                opts.append((L, need & ~L))
        else:
            opts = [(need, 0), (0, need)]
        per.append(opts)
    out = [[]]
    for opts in per:
        out = [o + [x] for o in out for x in opts]
    return out


class Prover:
    def __init__(self, oracle, maxw=6, maxseams=2, search_limit=0, verbose=True):
        self.o = oracle
        self.maxw = maxw
        self.maxseams = maxseams
        self.search_limit = search_limit
        self.verbose = verbose
        self.diag = False
        self.stats = {"cut": 0, "rec": 0, "search": 0, "fail": 0}

    def best_cut(self, s, pred, focus=None):
        for pieces, desc in upper_cuts(s, self.maxw, self.maxseams, True, focus):
            tot = (F(0), 0)
            ok = True
            for p in pieces:
                v = self.o.value(p)
                if v is None:
                    ok = False
                    break
                tot = vadd(tot, v)
            if ok and pred(tot):
                return tot, desc, pieces
        return None

    def le(self, s, q, depth, ctx=""):
        """Try to prove G(s) <= q. Returns a rule tree or None."""
        rule = {"q": vstr(q), "B": [], "W": None}
        qr = right_option(q)
        if qr is not None:
            r = self.lf_target(s, qr, depth)
            if r is None:
                return None
            rule["W"] = r
        w = len(s)
        for c in range(w):
            for r_ in range(5):
                t = bmove(s, r_, c)
                if t is None:
                    continue
                sub = self.blue_option(t, q, depth, (r_, c))
                if sub is None:
                    if self.verbose:
                        print(f"{ctx}  FAIL Blue {(r_, c)} vs q={vstr(q)} depth={depth}", flush=True)
                    if not (self.diag and ctx == ""):
                        return None
                    rule["fail"] = rule.get("fail", []) + [(r_, c)]
                    continue
                rule["B"].append(sub)
        return None if "fail" in rule else rule

    def lf_target(self, s, q, depth):
        """Prove G(s) <| q: a no-move cut with sum <| q, or a White move y with G^y <= q."""
        c = self.best_cut(s, lambda v: lf(v, q))
        if c:
            return {"type": "nomove", "sum": vstr(c[0]), "cut": str(c[1])}
        for y in self.white_moves(s, None):
            t = wmove(s, *y)
            c = self.best_cut(t, lambda v: le(v, q), focus=y[1])
            if c:
                return {"type": "white", "white": y, "sum": vstr(c[0]), "cut": str(c[1])}
        if depth > 0:
            for y in self.white_moves(s, None):
                t = wmove(s, *y)
                sub = self.le(t, q, depth - 1, ctx="    ")
                if sub:
                    return {"type": "white-rec", "white": y, "sub": sub}
        if self.search_limit:
            res = search_first(s, q, "white", self.search_limit)
            if res:
                self.stats["search"] += 1
                return {"type": "search", "q": vstr(q)}
        return None

    def white_moves(self, s, near):
        mv = []
        for c in range(len(s)):
            for r in range(5):
                if (s[c][1] >> r) & 1:
                    mv.append((r, c))
        if near is not None:
            mv.sort(key=lambda y: (abs(y[1] - near[1]) + abs(y[0] - near[0]), y))
        return mv

    def blue_option(self, t, q, depth, x):
        c = self.best_cut(t, lambda v: lf(v, q), focus=x[1])
        if c:
            self.stats["cut"] += 1
            return {"open": x, "type": "noreply", "sum": vstr(c[0]), "cut": str(c[1])}
        for y in self.white_moves(t, x):
            u = wmove(t, *y)
            c = self.best_cut(u, lambda v: le(v, q), focus=x[1])
            if c:
                self.stats["cut"] += 1
                return {"open": x, "type": "reply", "white": y, "sum": vstr(c[0]), "cut": str(c[1])}
        if depth > 0:
            for y in self.white_moves(t, x)[:6]:
                u = wmove(t, *y)
                sub = self.le(u, q, depth - 1, ctx="    ")
                if sub:
                    self.stats["rec"] += 1
                    return {"open": x, "type": "reply-rec", "white": y, "sub": sub}
        if self.search_limit:
            res = search_first(t, q, "white", self.search_limit)
            if res:
                self.stats["search"] += 1
                return {"open": x, "type": "search"}
        self.stats["fail"] += 1
        return None


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("draw", help="strip drawing rows joined by / (or FAMILY:w like DJ:9)")
    ap.add_argument("q")
    ap.add_argument("--ge", action="store_true", help="prove G >= q instead")
    ap.add_argument("--maxw", type=int, default=5)
    ap.add_argument("--seams", type=int, default=2)
    ap.add_argument("--depth", type=int, default=0)
    ap.add_argument("--search", type=int, default=0, help="search fallback time limit (s)")
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--out")
    ap.add_argument("--diag", action="store_true", help="report every failing root opening")
    a = ap.parse_args()
    global THREADS
    THREADS = a.threads
    LET = {"D": "obwbo", "U": "wbobo", "V": "bwbob", "X": "bowob", "R": "wobob", "J": "owobo", "T": "bobob"}
    if ":" in a.draw:
        fam, w = a.draw.split(":")
        s = family(LET[fam[0]], LET[fam[1]], int(w))
    else:
        s = undraw(a.draw)
    q = vparse(a.q)
    if a.ge:
        s, q = swap(s), neg(q)
    o = Oracle(maxw=a.maxw)
    p = Prover(o, maxw=a.maxw, maxseams=a.seams, search_limit=a.search)
    p.diag = a.diag
    t0 = time.time()
    rule = p.le(s, q, a.depth)
    print(("PROVED " if rule else "NOT PROVED ") + ("G >= " if a.ge else "G <= ") + a.q, draw(s if not a.ge else swap(s)),
          p.stats, f"solver-queries={o.nq}", f"{time.time() - t0:.1f}s", flush=True)
    if a.out and rule:
        json.dump({"draw": draw(s), "ge": a.ge, "q": a.q, "rule": rule}, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()


def static_best(s, oracle, maxw, maxseams=2):
    """Smallest cut upper bound of G(s) (ordered by number part, then star)."""
    best = None
    for pieces, desc in upper_cuts(s, maxw, maxseams, True):
        tot = (F(0), 0)
        for p in pieces:
            v = oracle.value(p)
            if v is None:
                tot = None
                break
            tot = vadd(tot, v)
        if tot is None:
            continue
        if best is None or tot[0] < best[0][0]:
            best = (tot, desc, [draw(p) for p in pieces])
    return best
