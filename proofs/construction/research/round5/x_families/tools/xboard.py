"""Five-row permission boards and a pipe to the discovery evaluator xval.

Coordinates are (row, column).  Endpoint letters follow the handoff (section 9).
Internally xval uses column-major bits (5*c + r); `to_rowmajor` converts to the
project convention (bit r*w + c) for certificates and reports.
"""
from fractions import Fraction as F
import os
import subprocess

LETTERS = dict(D='obwbo', U='wbobo', V='bwbob', X='bowob', R='wobob', J='owobo',
               O='ooooo', T='bobob')
HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.environ.get('XVAL_BIN', '/tmp/x_families/xval')


def pattern(p):
    return LETTERS.get(p, p)


def board(width, left='O', right='O'):
    """Return (A,B) as sets of (r,c); width-one endpoint masks intersect."""
    a = {(r, c) for r in range(5) for c in range(width)}
    b = set(a)
    for c, p in ((0, pattern(left)), (width - 1, pattern(right))):
        for r, s in enumerate(p):
            if s not in 'ob':
                a.discard((r, c))
            if s not in 'ow':
                b.discard((r, c))
    return a, b


def closed(v):
    r, c = v
    return {v, (r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)}


def blue(pos, v):
    a, b = pos
    assert v in a, ('illegal Blue', v)
    return a - closed(v), b - {v}


def white(pos, v):
    a, b = pos
    assert v in b, ('illegal White', v)
    return a - {v}, b - closed(v)


def colmask(cells):
    return sum(1 << (5 * c + r) for r, c in cells)


def rowmask(cells, width):
    return sum(1 << (r * width + c) for r, c in cells)


def show(pos, width):
    a, b = pos
    rows = []
    for r in range(5):
        s = ''
        for c in range(width):
            v = (r, c)
            s += 'o' if v in a and v in b else 'b' if v in a else 'w' if v in b else '.'
        rows.append(s)
    return '\n'.join(rows)


def restrict_white(pos, cells):
    a, b = pos
    return a, b - set(cells)


def shift(pos, dc):
    a, b = pos
    return {(r, c + dc) for r, c in a}, {(r, c + dc) for r, c in b}


class Evaluator:
    def __init__(self, logsize=25, binary=BIN):
        self.p = subprocess.Popen([binary, str(logsize)], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, text=True, bufsize=1)
        self.cache = {}

    def value(self, pos, width=None):
        a, b = pos
        cells = a | b
        if not cells:
            return F(0), 0
        lo = min(c for _, c in cells)
        hi = max(c for _, c in cells)
        a2 = {(r, c - lo) for r, c in a}
        b2 = {(r, c - lo) for r, c in b}
        w = hi - lo + 1
        key = (colmask(a2), colmask(b2))
        if key in self.cache:
            return self.cache[key]
        assert w <= 12
        self.p.stdin.write(f'{w} {key[0]} {key[1]}\n')
        self.p.stdin.flush()
        line = self.p.stdout.readline().split()
        if len(line) < 3 or (len(line) > 3 and line[3] == 'ERR'):
            raise RuntimeError('evaluator error ' + ' '.join(line))
        v = (F(int(line[0]), int(line[1])), int(line[2]))
        self.cache[key] = v
        return v

    def close(self):
        self.p.stdin.close()
        self.p.wait()


def fmt(v):
    q, s = v
    t = str(q)
    if s:
        t = ('' if q == 0 else t + '+') + '*'
    return t
