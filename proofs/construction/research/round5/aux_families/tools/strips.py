#!/usr/bin/env python3
"""Shared helpers: endpoint letters, strip construction, and a pipe to the
discovery evaluator colval (values only; never used as proof)."""
import os
import subprocess
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = '/tmp/aux_families'

# Endpoint letters, read top -> bottom.  Bar = vertical reflection.
LETTERS = {
    'O': 'ooooo',
    'D': 'obwbo', 'U': 'wbobo', 'V': 'bwbob', 'X': 'bowob', 'R': 'wobob', 'J': 'owobo',
    'u': 'obobw', 'v': 'bobwb', 'r': 'bobow', 'j': 'obowo',  # reflections of U V R J
    'T': 'bobob', 't': 'obobo',
}
BITS = {'.': (0, 0), 'b': (1, 0), 'w': (0, 1), 'o': (1, 1)}
CH = {(0, 0): '.', (1, 0): 'b', (0, 1): 'w', (1, 1): 'o'}


def meet(p, q):
    """Intersection of two permission characters."""
    a = BITS[p][0] & BITS[q][0]
    b = BITS[p][1] & BITS[q][1]
    return CH[(a, b)]


def pattern(x):
    return LETTERS.get(x, x)


def strip(P, Q, n, fill='ooooo'):
    """Rows of the 5 x n strip with left endpoint P, right endpoint Q."""
    P, Q = pattern(P), pattern(Q)
    cols = [fill] * n
    if n == 1:
        cols[0] = ''.join(meet(meet(a, b), c) for a, b, c in zip(P, Q, fill))
    else:
        cols[0] = ''.join(meet(a, c) for a, c in zip(P, fill))
        cols[-1] = ''.join(meet(a, c) for a, c in zip(Q, fill))
    return [''.join(col[r] for col in cols) for r in range(5)]


def cols_to_rows(cols):
    return [''.join(col[r] for col in cols) for r in range(5)]


def rows_to_cols(rows):
    return [''.join(row[c] for row in rows) for c in range(len(rows[0]))]


def play(rows, who, r, c):
    """Play a stone: who='B' or 'W'.  Returns new rows (permissions)."""
    g = [list(x) for x in rows]
    h, w = 5, len(rows[0])
    a = [[BITS[g[i][j]][0] for j in range(w)] for i in range(h)]
    b = [[BITS[g[i][j]][1] for j in range(w)] for i in range(h)]
    own, oth = (a, b) if who == 'B' else (b, a)
    assert own[r][c], ('illegal', who, r, c, rows)
    for rr, cc in ((r, c), (r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
        if 0 <= rr < h and 0 <= cc < w:
            own[rr][cc] = 0
    oth[r][c] = 0
    return [''.join(CH[(a[i][j], b[i][j])] for j in range(w)) for i in range(h)]


def parse_value(s):
    s = s.strip()
    star = 0
    if s == '*':
        return (Fraction(0), 1)
    if s.endswith('+*'):
        star = 1
        s = s[:-2]
    return (Fraction(s), star)


def fmt_value(v):
    x, s = v
    if s and x == 0:
        return '*'
    return f'{x}' + ('+*' if s else '')


class Evaluator:
    def __init__(self, logcap=24):
        exe = os.path.join(BUILD, 'colval')
        src = os.path.join(HERE, 'colval.cpp')
        if not os.path.exists(exe) or os.path.getmtime(exe) < os.path.getmtime(src):
            os.makedirs(BUILD, exist_ok=True)
            subprocess.check_call(['g++', '-O2', '-std=c++17', '-o', exe, src])
        self.p = subprocess.Popen([exe, str(logcap)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  text=True, bufsize=1)
        self.cache = {}

    def value(self, rows):
        key = tuple(rows)
        if key in self.cache:
            return self.cache[key]
        self.p.stdin.write(f'{len(rows[0])} ' + ' '.join(rows) + '\n')
        self.p.stdin.flush()
        out = self.p.stdout.readline()
        if out.startswith('ERR'):
            raise ValueError(out)
        v = parse_value(out)
        self.cache[key] = v
        return v

    def close(self):
        self.p.stdin.close()
        self.p.wait()


def le(v, w):
    """Exact order test between values x+e* (numbers or number+star)."""
    (x, e), (y, f) = v, w
    if e == f:
        return x <= y
    return x < y


def lt(v, w):
    return le(v, w) and v != w


def add(*vs):
    x = sum(v[0] for v in vs)
    s = 0
    for v in vs:
        s ^= v[1]
    return (x, s)
