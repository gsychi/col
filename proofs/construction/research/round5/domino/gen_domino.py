#!/usr/bin/env python3
"""Emit colout5 queries for every domino position D(v,u) on an H x W board, up to
the board's reflections: Blue stone on a majority cell v (r+c even), White stone
on an orthogonal neighbour u, all else empty. Guess 1 (the domino conjecture)."""
import sys
H, W = int(sys.argv[1]), int(sys.argv[2])
N = H * W
def nb(r, c):
    return [(rr, cc) for rr, cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)) if 0 <= rr < H and 0 <= cc < W]
def syms(r, c):
    return [(r, c), (H-1-r, c), (r, W-1-c), (H-1-r, W-1-c)]
seen = set()
for r in range(H):
    for c in range(W):
        if (r + c) % 2: continue
        for (ur, uc) in nb(r, c):
            key = min(tuple(zip(syms(r, c), syms(ur, uc))))
            if key in seen: continue
            seen.add(key)
            blue, white = {(r, c)}, {(ur, uc)}
            A = B = 0
            for rr in range(H):
                for cc in range(W):
                    if (rr, cc) in blue or (rr, cc) in white: continue
                    bit = 1 << (rr * W + cc)
                    if not any(x in blue for x in nb(rr, cc)): A |= bit
                    if not any(x in white for x in nb(rr, cc)): B |= bit
            print(f"value {H} {W} {A} {B} D_{H}x{W}_B{r}{c}_W{ur}{uc} 1")
