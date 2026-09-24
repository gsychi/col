"""Small-width discovery for oriented endpoint pairs; not an infinite proof."""
from fractions import Fraction as F
from functools import lru_cache
from itertools import combinations_with_replacement
from pathlib import Path
import argparse
import json

PATTERNS = dict(D="obwbo", U="wbobo", V="bwbob", X="bowob", R="wobob", J="owobo")
for name, pattern in list(PATTERNS.items()):
    if pattern[::-1] != pattern:
        PATTERNS[name + "bar"] = pattern[::-1]


def scan(width):
    full = (1 << (5 * width)) - 1
    closed = []
    for r in range(5):
        for c in range(width):
            closed.append(sum(1 << (rr * width + cc)
                              for rr, cc in [(r, c), (r-1, c), (r+1, c), (r, c-1), (r, c+1)]
                              if 0 <= rr < 5 and 0 <= cc < width))

    @lru_cache(None)
    def win(a, b, q, star):
        moves = a
        while moves:
            bit = moves & -moves
            moves -= bit
            v = bit.bit_length() - 1
            if not win(b & ~bit, a & ~closed[v], -q, star):
                return True
        left = q - F(1, q.denominator) if q.denominator > 1 else q - 1 if q > 0 else None
        if left is not None and not win(b, a, -left, star):
            return True
        return bool(star and not win(b, a, -q, False))

    def bounds(a, b):
        result = {}
        for q in [F(-2), F(-1), F(-3,4), F(-1,2), F(-1,4), F(0), F(1,4), F(1,2), F(3,4), F(1), F(2)]:
            l, r = win(a, b, -q, False), win(b, a, q, False)
            result[str(q)] = ("N" if r else "L") if l else ("R" if r else "P")
        return result

    rows = []
    # Include each relative orientation; reflecting the whole strip identifies
    # a simultaneous reversal, but never reverses just one endpoint.
    names = list(PATTERNS)
    for p, q in combinations_with_replacement(names, 2):
        a = b = full
        for column, name in [(0, p), (width - 1, q)]:
            for r, symbol in enumerate(PATTERNS[name]):
                bit = 1 << (r * width + column)
                if symbol not in "ob":
                    a &= ~bit
                if symbol not in "ow":
                    b &= ~bit
        values = bounds(a, b)
        rows.append(dict(left=p, right=q, width=width, comparisons=values))
        print(width, p, q, values["0"], "cache", win.cache_info().currsize, flush=True)
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("width", type=int)
    args = parser.parse_args()
    rows = scan(args.width)
    out = Path(__file__).with_name(f"round2_dx_pairs_w{args.width}.json")
    out.write_text(json.dumps(dict(patterns=PATTERNS, rows=rows), indent=2) + "\n")
