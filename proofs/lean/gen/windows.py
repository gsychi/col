"""Window gadgets for the Lean proof.

A window of width ww is the actual local position after Blue's opening v and
White's reply u (local coordinates), with White additionally retiring the
seam cells her neighbours require:
  left  = "E4":   E4's right port is 010, so the window drops White at (1,0)
  left  = "H":    an empty board's right port is 111, so drop all of column 0
  left  = "edge": nothing
  right = "Ebar": Ebar's left port is 010, so drop White at (1,ww-1)
  right = "edge": nothing
"""

from __future__ import annotations

from colsolve import ROWS, Solver


def window_masks(ww, v, u, left, right):
    s = Solver(ww)
    full = (1 << (ROWS * ww)) - 1
    idx = lambda r, c: r * ww + c  # noqa: E731
    a, b = full, full
    if v is not None:
        a, b = s.blue_move(a, b, idx(*v))
    if u is not None:
        a, b = s.white_move(a, b, idx(*u))
    if left == "E4":
        b &= ~(1 << idx(1, 0))
    elif left == "H":
        for r in range(ROWS):
            b &= ~(1 << idx(r, 0))
    if right == "Ebar":
        b &= ~(1 << idx(1, ww - 1))
    return s, a, b


def check(ww, v, u, left, right):
    s, a, b = window_masks(ww, v, u, left, right)
    return s.blue_loses(a, b), s, a, b


# The windows used by the all-width induction (n = 4k+3 >= 15).
CASE_WINDOWS = {
    "case1_0_1": (7, (0, 1), (1, 4), "E4", "Ebar"),
    "case1_0_3": (7, (0, 3), (1, 4), "E4", "Ebar"),
    "case1_1_0": (7, (1, 0), (1, 4), "E4", "Ebar"),
    "case1_1_2": (7, (1, 2), (1, 4), "E4", "Ebar"),
    "case2": (3, (0, 0), (2, 2), "edge", "Ebar"),
    "case3": (7, (0, 2), (2, 0), "E4", "Ebar"),
    "case4": (7, (0, 4), (2, 6), "E4", "Ebar"),
    "case5": (7, (1, 1), (0, 0), "E4", "Ebar"),
    "case6": (8, (1, 0), (0, 1), "H", "Ebar"),
}

if __name__ == "__main__":
    for name, spec in CASE_WINDOWS.items():
        ok, s, a, b = check(*spec)
        print(name, ok, len(s.certificate(a, b)) if ok else "-")
