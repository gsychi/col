"""Cheap falsification tests for GENERAL_IDEAS.md, driving col_fastval.

band   2 x n strip whose top row is Blue-only (the price of a static cut
       under a 3 x n block, by the comparison principle).
sep    h x (k+1) block whose last column is Blue-only, and White-only; the
       middle column of h x (2k+1) is explosive iff the two are equal.
Run:  python3 ideas_tests.py /path/to/col_fastval
"""

import subprocess
import sys

BIN = sys.argv[1] if len(sys.argv) > 1 else "/tmp/literature/col_fastval"


def value(h, w, a, b):
    out = subprocess.run([BIN, "value", str(h), str(w), str(a), str(b)],
                         capture_output=True, text=True, check=True, timeout=600).stdout
    return out.strip().split(" = ")[-1]


def cells(h, w, pred):
    m = 0
    for r in range(h):
        for c in range(w):
            if pred(r, c):
                m |= 1 << (r * w + c)
    return m


def main():
    for n in (1, 3, 5, 7, 9, 11):
        full = cells(2, n, lambda r, c: True)
        b = cells(2, n, lambda r, c: r == 1)
        print(f"band 2x{n}, top row Blue-only: {value(2, n, full, b)}", flush=True)
    for h in (3, 5):
        for w in (2, 3, 4, 5):
            if h * w > 25:
                continue
            full = cells(h, w, lambda r, c: True)
            last = cells(h, w, lambda r, c: c == w - 1)
            vb = value(h, w, full, full & ~last)
            vw = value(h, w, full & ~last, full)
            print(f"sep {h}x{w}: last column Blue-only {vb}, White-only {vw}", flush=True)


if __name__ == "__main__":
    main()
