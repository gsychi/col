"""Extra exact checks for COL_VALUES.md (sections 6-7).

I1  (proved)     u not White-legal:  G(A, B) <= G(A+u, B) <= G(A, B) + 1
I2  (proved)     u White-only:       G(A+u, B) <= G(A, B) + 2
I3  (refuted)    u White-only:       G(A+u, B) <= G(A, B) + 1 + *
    Exhaustive over every shadow state of the listed grids and every u.
E1  (proved)     explosive separator set S: if C with S tinted Blue-only equals
                 C with S tinted White-only, then G = C + (D - S) = G - S.
                 Random graphs, C and D sharing exactly S.
Run:  python3 col_values_extra.py [out.json]
"""

import json
import random
import sys

from cgt_core import ColEvaluator, GameTable, fmt, graph_closed_nbhd
from col_values_exhaustive import grid_edges


def increments(t, name, n, edges):
    ev = ColEvaluator(t, graph_closed_nbhd(n, edges))
    one, two, star = t.number(1), t.number(2), t.star
    one_star = t.add(one, star)
    full = (1 << n) - 1
    res = {"I1": [0, 0], "I2": [0, 0], "I3": [0, 0]}
    worst = {}
    witness = {}
    first_fail = {}
    for a in range(full + 1):
        for b in range(full + 1):
            g = ev.value(a, b)
            for u in range(n):
                if (a >> u) & 1:
                    continue
                g2 = ev.value(a | (1 << u), b)
                d = t.classify(t.add(g2, t.neg(g)))
                if (b >> u) & 1:
                    ok2 = t.leq(g, g2) and t.leq(g2, t.add(g, two))
                    ok3 = t.leq(g2, t.add(g, one_star))
                    res["I2"][0] += 1
                    res["I2"][1] += not ok2
                    res["I3"][0] += 1
                    res["I3"][1] += not ok3
                    if not ok3 and "I3" not in first_fail:
                        first_fail["I3"] = {"A": a, "B": b, "u": u, "diff": fmt(d)}
                    kind = "white_only"
                else:
                    ok1 = t.leq(g, g2) and t.leq(g2, t.add(g, one))
                    res["I1"][0] += 1
                    res["I1"][1] += not ok1
                    if not ok1 and "I1" not in first_fail:
                        first_fail["I1"] = {"A": a, "B": b, "u": u, "diff": fmt(d)}
                    kind = "dead"
                if d is not None:
                    cur = worst.get(kind)
                    if cur is None or d > cur:
                        worst[kind] = d
                        witness[kind] = {"A": a, "B": b, "u": u}
    return {"graph": name,
            "checked_failed": res,
            "max_increment": {k: fmt(v) for k, v in worst.items()},
            "max_witness": witness,
            "first_failures": first_fail}


def explosive_sets(t, rng, trials):
    ok = bad = applicable = 0
    example = None
    for _ in range(trials):
        s = rng.randint(1, 2)
        nc, nd = rng.randint(s + 1, s + 4), rng.randint(s + 1, s + 4)
        n = nc + nd - s
        # C uses vertices 0..nc-1; S = 0..s-1; D uses S and nc..n-1
        ce = [(u, v) for u in range(nc) for v in range(u + 1, nc) if rng.random() < 0.45]
        dverts = list(range(s)) + list(range(nc, n))
        de = [(dverts[i], dverts[j]) for i in range(len(dverts)) for j in range(i + 1, len(dverts))
              if rng.random() < 0.45 and not (dverts[i] < s and dverts[j] < s)]
        a = b = 0
        for v in range(n):
            k = rng.choices("obw.", weights=(3, 1, 1, 1))[0]
            a |= (k in "ob") << v
            b |= (k in "ow") << v
        smask = (1 << s) - 1
        cmask = (1 << nc) - 1
        evc = ColEvaluator(t, graph_closed_nbhd(nc, ce))
        cb = evc.value(a & cmask, b & cmask & ~smask)
        cw = evc.value(a & cmask & ~smask, b & cmask)
        if cb != cw:
            continue
        applicable += 1
        c0 = evc.value(a & cmask, b & cmask)
        ev = ColEvaluator(t, graph_closed_nbhd(n, ce + de))
        g = ev.value(a, b)
        # D - S : vertices nc..n-1 only
        g_rest = ev.value(a & ~cmask, b & ~cmask)
        rhs = t.add(c0, g_rest)
        g_minus_s = ev.value(a & ~smask, b & ~smask)
        if g == rhs and g == g_minus_s:
            ok += 1
        else:
            bad += 1
            if example is None:
                example = {"n": n, "s": s, "C_edges": ce, "D_edges": de, "A": a, "B": b}
    return {"trials": trials, "applicable": applicable, "ok": ok, "failed": bad, "example": example}


def save(out):
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w") as fh:
            json.dump(out, fh, indent=1)


def main():
    t = GameTable()
    out = {"increments": []}
    out["explosive_sets"] = explosive_sets(t, random.Random(7), 3000)
    print(json.dumps(out["explosive_sets"]), flush=True)
    save(out)
    for (h, w) in [(1, 5), (1, 6), (2, 3), (2, 4), (3, 3)]:
        r = increments(t, f"grid_{h}x{w}", h * w, grid_edges(h, w))
        print(json.dumps(r), flush=True)
        out["increments"].append(r)
        save(out)


if __name__ == "__main__":
    main()
