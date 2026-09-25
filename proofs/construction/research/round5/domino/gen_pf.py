#!/usr/bin/env python3
"""Emit colout5 queries testing the parity formula (PF) on random parity-respecting positions:
Blue stones on majority cells (r+c even), White stones on minority cells, at least one White
stone.  Guess = #free majority - #free minority.  Usage: gen_pf.py H W COUNT SEED PMAX QMAX"""
import random, sys
H, W, COUNT, SEED, PMAX, QMAX = map(int, sys.argv[1:7])
rng = random.Random(SEED)
X = [(r, c) for r in range(H) for c in range(W) if (r + c) % 2 == 0]
Y = [(r, c) for r in range(H) for c in range(W) if (r + c) % 2 == 1]
def nb(r, c):
    return [(rr, cc) for rr, cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)) if 0 <= rr < H and 0 <= cc < W]
seen = set()
while len(seen) < COUNT:
    P = frozenset(rng.sample(X, rng.randint(0, PMAX)))
    Q = frozenset(rng.sample(Y, rng.randint(1, QMAX)))
    if (P, Q) in seen:
        continue
    seen.add((P, Q))
    A = B = 0
    for r in range(H):
        for c in range(W):
            if (r, c) in P or (r, c) in Q:
                continue
            bit = 1 << (r * W + c)
            if not any(x in P for x in nb(r, c)): A |= bit
            if not any(x in Q for x in nb(r, c)): B |= bit
    F = (len(X) - len(P)) - (len(Y) - len(Q))
    label = "PF_%dx%d_B%s_W%s" % (H, W, "".join("%d%d" % p for p in sorted(P)) or "-", "".join("%d%d" % q for q in sorted(Q)))
    print(f"value {H} {W} {A} {B} {label} {F}")
