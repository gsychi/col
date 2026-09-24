"""Exhaustive checks over every shadow state (A, B) of small fixed graphs.

For each graph, all 4^n permission assignments are evaluated exactly with
cgt_core (general canonical forms). Checked for every state:
  T1  value is x or x+*
  T2  G^L + * <= G (and G^L + 1 <= G at Blue-only cells), dually for White
  T3  G = x+*  =>  some Blue option and some White option equal x
  T5  outcome N <=> G = *,  outcome P <=> G = 0
Also collected: the set of values, the largest denominator, and the first
grid-subgraph counterexample to X1 (Blue-first wins via a shared cell).
Run:  python3 col_values_exhaustive.py [out.json]
"""

import json
import sys
import time
from itertools import combinations

from cgt_core import ColEvaluator, GameTable, fmt, graph_closed_nbhd, grid_closed_nbhd


def grid_edges(h, w):
    e = []
    for v in range(h * w):
        r, c = divmod(v, w)
        if c + 1 < w:
            e.append((v, v + 1))
        if r + 1 < h:
            e.append((v, v + w))
    return e


def check_graph(t, name, n, edges, x1_record):
    nb = graph_closed_nbhd(n, edges)
    ev = ColEvaluator(t, nb)
    star, one, zero = t.star, t.number(1), t.zero
    full = (1 << n) - 1
    counts = {"states": 0, "T1_fail": 0, "T2_fail": 0, "T3_fail": 0, "T5_fail": 0,
              "X1_checked": 0, "X1_fail": 0}
    values = {}
    maxden = 1
    t0 = time.time()
    for a in range(full + 1):
        for b in range(full + 1):
            counts["states"] += 1
            g = ev.value(a, b)
            cls = t.classify(g)
            if cls is None:
                counts["T1_fail"] += 1
                continue
            values[fmt(cls)] = values.get(fmt(cls), 0) + 1
            maxden = max(maxden, cls[0].denominator)
            lv = []
            for v, p in ev.left_options(a, b):
                gl = ev.value(*p)
                lv.append((v, gl))
                ok = t.leq(t.add(gl, star), g) and ((b >> v) & 1 or t.leq(t.add(gl, one), g))
                counts["T2_fail"] += not ok
            rv = []
            for v, p in ev.right_options(a, b):
                gr = ev.value(*p)
                rv.append(gr)
                ok = t.leq(g, t.add(gr, star)) and ((a >> v) & 1 or t.leq(t.add(g, one), gr))
                counts["T2_fail"] += not ok
            if cls[1] == 1:
                xg = t.number(cls[0])
                counts["T3_fail"] += not (any(gl == xg for _, gl in lv) and xg in rv)
            lw = not t.leq(g, zero)
            rw = not t.leq(zero, g)
            outcome = ("N" if rw else "L") if lw else ("R" if rw else "P")
            counts["T5_fail"] += not ((outcome == "N") == (g == star) and (outcome == "P") == (g == zero))
            if lw and (a & b):
                counts["X1_checked"] += 1
                if not any((b >> v) & 1 and t.leq(zero, gl) for v, gl in lv):
                    counts["X1_fail"] += 1
                    if x1_record.get(name) is None:
                        x1_record[name] = {"A": a, "B": b, "value": fmt(cls),
                                           "winning_moves": [v for v, gl in lv if t.leq(zero, gl)]}
    counts["distinct_values"] = len(values)
    counts["max_denominator"] = maxden
    counts["seconds"] = round(time.time() - t0, 1)
    counts["values_sample"] = dict(sorted(values.items(), key=lambda kv: -kv[1])[:12])
    return counts


def main():
    t = GameTable()
    out = {}
    x1 = {}
    graphs = []
    for (h, w) in [(1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (2, 2), (2, 3), (2, 4), (3, 3)]:
        graphs.append((f"grid_{h}x{w}", h * w, grid_edges(h, w)))
    for k in range(3, 8):
        graphs.append((f"cycle_{k}", k, [(i, (i + 1) % k) for i in range(k)]))
    graphs.append(("star_K1_4", 5, [(0, i) for i in range(1, 5)]))
    graphs.append(("K4", 4, list(combinations(range(4), 2))))
    graphs.append(("K2_3", 5, [(i, j) for i in range(2) for j in range(2, 5)]))
    graphs.append(("plus_cross_9", 9, [(0, 1), (1, 2), (0, 3), (3, 4), (0, 5), (5, 6), (0, 7), (7, 8)]))
    for name, n, edges in graphs:
        out[name] = check_graph(t, name, n, edges, x1)
        print(name, json.dumps({k: v for k, v in out[name].items() if k != "values_sample"}), flush=True)
    res = {"graphs": out, "X1_counterexamples": x1, "canonical_forms": len(t.left)}
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w") as fh:
            json.dump(res, fh, indent=1)
    print(json.dumps(x1, indent=1))


if __name__ == "__main__":
    main()
