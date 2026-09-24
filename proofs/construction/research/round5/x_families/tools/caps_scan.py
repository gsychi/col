"""Discovery scan: X-end caps with Blue at the inner-edge column (EVIDENCE only).

K^{(r)}_m(S): width-m board, X at the right end, Blue played at (r,0), and
column 0 loses White wherever the adjoining letter S permits White.
"""
import sys
import time
from xboard import Evaluator, board, blue, pattern, fmt

CASES = [(2, 'X', 0), (2, 'D', 1), (0, 'U', 1), (0, 'R', 0), (1, 'V', 0), (1, 'J', 1)]


def xcap(m, r, s, right='X'):
    a, b = blue(board(m, 'O', right), (r, 0))
    return a, b - {(rr, 0) for rr, ch in enumerate(pattern(s)) if ch in 'ow'}


if __name__ == '__main__':
    maxw = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    ev = Evaluator(25)
    for r, s, par in CASES:
        for m in range(1, maxw + 1):
            if m % 2 != par or (r, 0) not in board(m, 'O', 'X')[0]:
                continue
            t = time.time()
            print(r, s, m, fmt(ev.value(xcap(m, r, s))), round(time.time() - t, 1), flush=True)
