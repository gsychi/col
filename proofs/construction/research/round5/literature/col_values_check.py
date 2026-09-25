"""Randomised exact checks of the Col value theorem and related claims.

Every value is an exact canonical form from cgt_core (no Col-specific
assumption). A subset of values is re-certified by plain minimax on
G - x - eps*, independently of the canonical-form code.

Claims tested (labels match COL_VALUES.md):
  T1  every position is x or x+* (dyadic x)
  T2  G^L + * <= G for every Blue move; G^L + 1 <= G if the cell is Blue-only;
      dually G <= G^R + *, and G <= G^R - 1 if the cell is White-only
  T3  if G = x+*, some Blue option and some White option equal x exactly
  T4  monotonicity: adding a Blue permission or removing a White permission,
      or deleting an edge with a White-illegal endpoint, never decreases G
  T5  outcome N <=> G = *, outcome P <=> G = 0
  T6  explosive cut vertex (ONAG p.94): if C_b = C_w then G = G - u
  T7  adjacent shared true twins (ONAG p.94): tint one Blue-only, one White-only
  X1  exploratory: if Blue moving first wins and a shared Blue-legal cell
      exists, some shared-cell move wins
  X2  exploratory: size of G(A+u,B) - G(A,B) for u not in A
Run:  python3 col_values_check.py [seconds] [seed]
"""

import json
import random
import sys
import time
from fractions import Fraction

from cgt_core import (ColEvaluator, GameTable, SumOutcome, fmt,
                      graph_closed_nbhd, grid_closed_nbhd)


def rand_graph(rng, n, p):
    edges = [(u, v) for u in range(n) for v in range(u + 1, n) if rng.random() < p]
    return edges


def grid_subgraph(rng, h, w, keep):
    cells = [v for v in range(h * w) if rng.random() < keep]
    idx = {v: i for i, v in enumerate(cells)}
    edges = []
    for v in cells:
        r, c = divmod(v, w)
        for rr, cc in ((r + 1, c), (r, c + 1)):
            u = rr * w + cc
            if rr < h and cc < w and u in idx:
                edges.append((idx[v], idx[u]))
    return len(cells), edges


def rand_perms(rng, n, weights=(3, 1, 1, 1)):
    a = b = 0
    for v in range(n):
        k = rng.choices("obw.", weights=weights)[0]
        if k in "ob":
            a |= 1 << v
        if k in "ow":
            b |= 1 << v
    return a, b


class Checker:
    def __init__(self, seconds, seed):
        self.rng = random.Random(seed)
        self.t = GameTable()
        self.deadline = time.time() + seconds
        self.stats = {k: [0, 0] for k in
                      ["T1", "T1_sum_certified", "T2", "T3", "T4", "T5", "T6", "T7", "X1", "X2"]}
        self.failures = []
        self.x2_max = {}
        self.positions = 0
        self.seed = seed
        star = self.t.star
        self.one = self.t.number(1)

    def rec(self, key, ok, info=None):
        self.stats[key][0] += 1
        if not ok:
            self.stats[key][1] += 1
            if len(self.failures) < 60:
                self.failures.append({"claim": key, "info": info})

    def val(self, ev, a, b):
        g = ev.value(a, b)
        return g, self.t.classify(g)

    def check_position(self, n, edges, a, b, kind, certify):
        t = self.t
        nb = graph_closed_nbhd(n, edges)
        ev = ColEvaluator(t, nb)
        g, cls = self.val(ev, a, b)
        info = {"kind": kind, "n": n, "edges": edges, "A": a, "B": b}
        self.rec("T1", cls is not None, info)
        if cls is None:
            return
        x, eps = cls
        if certify:
            so = SumOutcome(t, nb)
            ok = so.is_second_player_win(a, b, t.number(-x), eps)
            self.rec("T1_sum_certified", ok, info)
        star, one = t.star, self.one
        gs = t.add(g, star)
        # T2 and T3
        left_vals, right_vals = [], []
        for v, (a1, b1) in ev.left_options(a, b):
            gl = ev.value(a1, b1)
            left_vals.append(gl)
            ok = t.leq(t.add(gl, star), g)
            if not (b >> v) & 1:
                ok = ok and t.leq(t.add(gl, one), g)
            self.rec("T2", ok, dict(info, move=("L", v)))
        for v, (a1, b1) in ev.right_options(a, b):
            gr = ev.value(a1, b1)
            right_vals.append(gr)
            ok = t.leq(g, t.add(gr, star))
            if not (a >> v) & 1:
                ok = ok and t.leq(t.add(g, one), gr)
            self.rec("T2", ok, dict(info, move=("R", v)))
        if eps == 1:
            xg = t.number(x)
            self.rec("T3", xg in left_vals and xg in right_vals, info)
        # T5 outcome classes via order with zero
        z = t.zero
        left_wins_first = not t.leq(g, z)
        right_wins_first = not t.leq(z, g)
        outcome = ("N" if right_wins_first else "L") if left_wins_first else ("R" if right_wins_first else "P")
        self.rec("T5", (outcome == "N") == (g == star) and (outcome == "P") == (g == z), info)
        # T4 monotonicity
        u = self.rng.randrange(n)
        a2, b2 = a | (1 << u), b & ~(1 << u)
        self.rec("T4", t.leq(g, ev.value(a2, b)) and t.leq(g, ev.value(a, b2)), dict(info, u=u))
        cut = [e for e in edges if not ((b >> e[0]) & 1 and (b >> e[1]) & 1)]
        if cut:
            e = self.rng.choice(cut)
            rest = [f for f in edges if f != e]
            ev2 = ColEvaluator(t, graph_closed_nbhd(n, rest))
            self.rec("T4", t.leq(g, ev2.value(a, b)), dict(info, cut=e))
        # X1 shared-move sufficiency for Blue moving first
        if left_wins_first and (a & b):
            wins_shared = False
            for v, (a1, b1) in ev.left_options(a, b):
                if (b >> v) & 1 and t.leq(z, ev.value(a1, b1)):
                    wins_shared = True
                    break
            self.rec("X1", wins_shared, info)
        # X2 increments of adding a Blue permission
        if ~a & ((1 << n) - 1):
            cand = [v for v in range(n) if not (a >> v) & 1]
            u = self.rng.choice(cand)
            g2 = ev.value(a | (1 << u), b)
            d = t.classify(t.add(g2, t.neg(g)))
            typ = "u_was_white_only" if (b >> u) & 1 else "u_was_dead"
            if d is not None:
                cur = self.x2_max.get(typ)
                key = (d[0], d[1])
                if cur is None or key > cur:
                    self.x2_max[typ] = key
            self.rec("X2", d is not None, dict(info, u=u))

    def check_explosive(self):
        """T6: C and D share exactly the cut vertex u (index 0)."""
        t, rng = self.t, self.rng
        nc, nd = rng.randint(2, 6), rng.randint(2, 6)
        n = nc + nd - 1
        ce = [(u, v) for u in range(nc) for v in range(u + 1, nc) if rng.random() < 0.45]
        dmap = [0] + list(range(nc, n))
        de = [(dmap[u], dmap[v]) for u in range(nd) for v in range(u + 1, nd) if rng.random() < 0.45]
        a, b = rand_perms(rng, n)
        cmask = (1 << nc) - 1
        evc = ColEvaluator(t, graph_closed_nbhd(nc, ce))
        cb = evc.value(a & cmask, b & cmask & ~1)
        cw = evc.value(a & cmask & ~1, b & cmask)
        if cb != cw:
            return
        ev = ColEvaluator(t, graph_closed_nbhd(n, ce + de))
        g = ev.value(a, b)
        gdel = ev.value(a & ~1, b & ~1)
        self.rec("T6", g == gdel, {"C_edges": ce, "D_edges": de, "A": a, "B": b, "n": n})

    def check_twins(self):
        """T7: adjacent shared u,v with N[u]=N[v] may be tinted Blue-only/White-only."""
        t, rng = self.t, self.rng
        n = rng.randint(3, 9)
        edges = set(rand_graph(rng, n, 0.4))
        edges = {e for e in edges if 0 not in e and 1 not in e}
        nbrs = [v for v in range(2, n) if rng.random() < 0.5]
        edges |= {(0, 1)} | {(0, v) for v in nbrs} | {(1, v) for v in nbrs}
        a, b = rand_perms(rng, n)
        a |= 3
        b |= 3
        ev = ColEvaluator(t, graph_closed_nbhd(n, sorted(edges)))
        g = ev.value(a, b)
        g2 = ev.value(a & ~2, b & ~1)
        self.rec("T7", g == g2, {"edges": sorted(edges), "A": a, "B": b, "n": n})

    def run(self):
        rng = self.rng
        while time.time() < self.deadline:
            self.positions += 1
            r = rng.random()
            if r < 0.4:
                n = rng.randint(1, 10)
                edges = rand_graph(rng, n, rng.choice([0.15, 0.3, 0.5]))
                kind = "random_graph"
            elif r < 0.85:
                h, w = rng.choice([(2, 4), (2, 5), (3, 3), (3, 4), (2, 6), (4, 4), (3, 5)])
                n, edges = grid_subgraph(rng, h, w, rng.choice([0.7, 0.85, 1.0]))
                if n == 0:
                    continue
                kind = f"grid_sub_{h}x{w}"
            else:
                h, w = rng.choice([(3, 3), (2, 5), (3, 4)])
                n, edges = grid_subgraph(rng, h, w, 1.0)
                kind = f"full_grid_{h}x{w}"
            weights = rng.choice([(3, 1, 1, 1), (6, 1, 1, 0), (1, 1, 1, 1), (1, 0, 0, 0)])
            a, b = rand_perms(rng, n, weights)
            self.check_position(n, edges, a, b, kind, certify=(n <= 9 or rng.random() < 0.2))
            self.check_explosive()
            self.check_twins()
        return {
            "seed": self.seed,
            "positions": self.positions,
            "stats": {k: {"checked": v[0], "failed": v[1]} for k, v in self.stats.items()},
            "X2_max_increment": {k: fmt(v) for k, v in self.x2_max.items()},
            "failures": self.failures[:20],
            "canonical_forms_in_table": len(self.t.left),
        }


if __name__ == "__main__":
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 60
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 20260923
    res = Checker(seconds, seed).run()
    print(json.dumps({k: v for k, v in res.items() if k != "failures"}, indent=1))
    for f in res["failures"][:8]:
        print("FAIL", f)
    out = sys.argv[3] if len(sys.argv) > 3 else None
    if out:
        with open(out, "w") as fh:
            json.dump(res, fh, indent=1, default=str)
