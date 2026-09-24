"""Cross-check col_fastval (theorem-based, C++) against cgt_core (general
canonical forms, Python) on random shadow states of small grids.

Run:  python3 fastval_crosscheck.py /path/to/col_fastval [count]
"""

import subprocess
import sys

from cgt_core import ColEvaluator, GameTable, fmt, grid_closed_nbhd


def main():
    exe = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    t = GameTable()
    total = mismatches = 0
    for (h, w, seed) in [(2, 3, 1), (3, 3, 2), (2, 5, 3), (3, 4, 4), (4, 3, 5), (2, 6, 6), (3, 5, 7), (4, 4, 8)]:
        out = subprocess.run([exe, "random", str(h), str(w), str(count), str(seed)],
                             capture_output=True, text=True, check=True).stdout.split("\n")
        ev = ColEvaluator(t, grid_closed_nbhd(h, w))
        n_here = 0
        for line in out:
            if not line.strip():
                continue
            a, b, claimed = line.split()
            got = fmt(t.classify(ev.value(int(a), int(b))))
            total += 1
            n_here += 1
            if got != claimed:
                mismatches += 1
                print("MISMATCH", h, w, a, b, claimed, got)
            if h * w >= 15 and n_here >= count // 4:
                break
        print(f"{h}x{w}: checked {n_here}", flush=True)
    print(f"total {total}, mismatches {mismatches}")


if __name__ == "__main__":
    main()
