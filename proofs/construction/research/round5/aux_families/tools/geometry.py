#!/usr/bin/env python3
"""Comparison geometry for one Blue opening (optionally one White reply) in a
two-ended five-row strip (P,Q)_n, cut into

    left piece  (P,E)_L      columns 0 .. L-1          (absent if L = 0)
    cap                      columns L .. R            (actual permissions,
                                                        White retired on seams)
    right piece (E',Q)_M     columns R+1 .. n-1        (absent if M = 0)

The check is the admissible-comparison test of handoff section 2:
  A_actual <= A_virtual,  B_virtual <= B_actual,  and every edge between
  different regions has an endpoint that is virtually White-illegal.
Pure permission arithmetic; no game search."""
from strips import BITS, CH, play, strip


def cols(rows):
    return [''.join(r[c] for r in rows) for c in range(len(rows[0]))]


def rows_of(cl):
    return [''.join(c[r] for c in cl) for r in range(5)]


def white_rows(col):
    return {r for r, ch in enumerate(col) if BITS[ch][1]}


def retire_white(col, rows_):
    return ''.join(CH[(BITS[ch][0], 0 if r in rows_ else BITS[ch][1])] for r, ch in enumerate(col))


def dominates(virtual, actual):
    """virtual column admissibly replaces actual column."""
    for v, a in zip(virtual, actual):
        if BITS[a][0] and not BITS[v][0]:
            return False
        if BITS[v][1] and not BITS[a][1]:
            return False
    return True


def actual_after(P, Q, n, moves):
    rows = strip(P, Q, n)
    for who, r, c in moves:
        rows = play(rows, who, r, c)
    return rows


def build(P, Q, n, moves, L, R, E, Ep):
    """Return (ok, reason, cap_cols, left_piece, right_piece)."""
    act = cols(actual_after(P, Q, n, moves))
    M = n - 1 - R
    if not (0 <= L <= R < n):
        return False, 'range', None, None, None
    if any(not (L <= c <= R) for _, _, c in moves):
        return False, 'move outside cap', None, None, None
    if (L > 0) != (E is not None) or (M > 0) != (Ep is not None):
        return False, 'letter/piece mismatch', None, None, None
    virt = [None] * n
    left = right = None
    if L > 0:
        virt[:L] = cols(strip(P, E, L))
        left = (P, E, L)
    if M > 0:
        virt[R + 1:] = cols(strip(Ep, Q, M))
        right = (Ep, Q, M)
    cap = act[L:R + 1]
    if L > 0:
        cap[0] = retire_white(cap[0], white_rows(virt[L - 1]))
    if M > 0:
        cap[-1] = retire_white(cap[-1], white_rows(virt[R + 1]))
    virt[L:R + 1] = cap
    for c in range(n):
        if not dominates(virt[c], act[c]):
            return False, f'domination fails at column {c}', None, None, None
    for c in ([L - 1] if L > 0 else []) + ([R] if M > 0 else []):
        if white_rows(virt[c]) & white_rows(virt[c + 1]):
            return False, f'unsafe White seam {c}|{c+1}', None, None, None
    return True, 'ok', cap, left, right


if __name__ == '__main__':
    # Smoke test: the six DD separators at n = 9.
    tests = [
        ('U', 0, 3, None, 'U', '.wbob'), ('R', 0, 4, (2, 4), 'R', '...bo'),
        ('V', 1, 4, None, 'V', 'w.wbo'), ('J', 1, 3, None, 'J', '...ob'),
        ('X', 2, 4, (0, 4), 'X', '....o'), ('D', 2, 3, None, 'D', 'bw.wb'),
    ]
    for name, r, c, rep, let, sep in tests:
        moves = [('B', r, c)] + ([('W',) + rep] if rep else [])
        ok, why, cap, lp, rp = build('D', 'D', 9, moves, c, c, let, let)
        print(name, ok, why, cap, lp, rp, ok and cap[0] == sep)
