#!/usr/bin/env python3
"""Check the finite local contracts underlying the symbolic six-case DD proof.

The all-width proof is in five_row_boundary_induction.md.  This checker checks
its finite column data, exact local DAG certificates, and optional assembly
regressions.  A finite width sweep is not an infinite-width proof.
"""
from fractions import Fraction
from pathlib import Path
import argparse
import gzip
import json

from number_certificates import generate, verify

ROOT = Path(__file__).resolve().parent
PATTERNS = dict(D='obwbo', U='wbobo', V='bwbob', X='bowob', R='wobob', J='owobo')
BITS = {'.': (False, False), 'b': (True, False), 'w': (False, True), 'o': (True, True)}
# label, opening row, White reply row (same column), side endpoint, separator, value
CONTRACTS = (
    ('U', 0, None, 'U', '.wbob', Fraction(0)),
    ('R', 0, 2, 'R', '...bo', Fraction(1, 2)),
    ('V', 1, None, 'V', 'w.wbo', Fraction(-3, 2)),
    ('J', 1, None, 'J', '...ob', Fraction(1, 2)),
    ('X', 2, 0, 'X', '....o', None),
    ('D', 2, None, 'D', 'bw.wb', Fraction(0)),
    ('corner', 0, 4, 'R', '..wb.', Fraction(0)),
    ('R_no_reply', 0, None, 'R', '..obo', Fraction(0)),
    ('corner_no_reply', 0, None, 'R', '..wbo', Fraction(-1, 2)),
    ('X_no_reply', 2, None, 'X', 'o...o', Fraction(0)),
)


def permissions(pattern):
    return tuple({r for r, s in enumerate(pattern) if BITS[s][p]} for p in (0, 1))


def play(a, b, player, row):
    a, b = set(a), set(b)
    own, other = (a, b) if player == 0 else (b, a)
    assert row in own, ('illegal local move', player, row)
    own.difference_update({row - 1, row, row + 1})
    other.discard(row)
    return a, b


def check_local_contracts():
    # Interior column starts neutral.  The exceptional corner inherits D.
    for label, blue, white, endpoint, sep, _ in CONTRACTS:
        a, b = permissions(PATTERNS['D'] if label in ('corner', 'corner_no_reply') else 'ooooo')
        a, b = play(a, b, 0, blue)
        if white is not None:
            a, b = play(a, b, 1, white)
        sa, sb = permissions(sep)
        assert a <= sa and sb <= b, (label, 'separator direction')
        # The adjacent column loses Blue only in the opening row and White
        # only in the reply row.  Additional restrictions are virtual.
        adjacent_a = set(range(5)) - {blue}
        adjacent_b = set(range(5)) - ({white} if white is not None else set())
        ea, eb = permissions(PATTERNS[endpoint])
        assert adjacent_a <= ea and eb <= adjacent_b, (label, 'side direction')
        assert not (sb & eb), (label, 'unsafe White seam')
    # The only other endpoint opening uses V, whose separator already meets D.
    a, b = play(*permissions(PATTERNS['D']), 0, 1)
    sa, sb = permissions('w.wbo')
    assert a <= sa and sb <= b
    # X's isolated shared vertex is exactly star, with both options empty.
    assert permissions('....o') == ({4}, {4})
    print('VERIFIED 10 local contracts, endpoint V, and the isolated star')


def masks(pattern):
    return [sum(1 << r for r in s) for s in permissions(pattern)]


def local_certificate_specs():
    for label, _, _, _, sep, q in CONTRACTS:
        if q is None:
            continue
        a, b = masks(sep)
        yield label + '_le', a, b, -q
        yield label + '_ge', b, a, q


def local_certificates(regenerate=False):
    out = ROOT / 'dd_local_certificates'
    if regenerate:
        out.mkdir(exist_ok=True)
    total_nodes = total_edges = 0
    for name, a, b, q in local_certificate_specs():
        path = out / (name + '.json.gz')
        if regenerate:
            doc = generate(5, 1, a, b, q)
            path.write_bytes(gzip.compress(json.dumps(doc, separators=(',', ':')).encode(), mtime=0))
        doc = json.loads(gzip.decompress(path.read_bytes()))
        assert (doc['height'], doc['width'], doc['root']) == (5, 1, [a, b, q.numerator, q.denominator]), name
        nodes, edges = verify(doc)  # independent set-based, search-free DAG check
        total_nodes += nodes
        total_edges += edges
    print(f'VERIFIED 18 bound certificates: {total_nodes} checkpoints, {total_edges} edges')


def rectangle(n, left='D', right='D'):
    a = {(r, c) for r in range(5) for c in range(n)}
    b = set(a)
    for c, name in ((0, left), (n - 1, right)):
        aa, bb = permissions(PATTERNS[name])
        a -= {(r, c) for r in range(5) if r not in aa}
        b -= {(r, c) for r in range(5) if r not in bb}
    return a, b


def board_play(a, b, who, v):
    a, b = set(a), set(b)
    own, other = (a, b) if who == 0 else (b, a)
    assert v in own
    r, c = v
    own.difference_update({v, (r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)})
    other.discard(v)
    return a, b


def assembly_regression(limit, strengthen=False):
    count = 0
    for n in range(3, limit + 1, 2):
        initial_a, initial_b = rectangle(n)
        for r, c in sorted(initial_a):
            if r > 2:
                continue  # vertical reflection of checked contracts
            if r == 0:
                label = 'corner' if c in (0, n - 1) else ('U' if c % 2 else 'R')
            elif r == 1:
                label = 'J' if c % 2 else 'V'
            else:
                label = 'D' if c % 2 else 'X'
            if strengthen and label in ('R', 'corner', 'X'):
                label += '_no_reply'
            _, _, white, endpoint, sep, _ = next(t for t in CONTRACTS if t[0] == label)
            aa, bb = board_play(initial_a, initial_b, 0, (r, c))
            if white is not None:
                aa, bb = board_play(aa, bb, 1, (white, c))
            va, vb, regions = set(), set(), {}
            for width, offset, left, right, reg in (
                (c, 0, 'D', endpoint, 0),
                (n - c - 1, c + 1, endpoint, 'D', 2),
            ):
                if not width:
                    continue  # empty side is 0; never calls a width-zero lemma
                assert width < n
                xa, xb = rectangle(width, left, right)
                va |= {(rr, cc + offset) for rr, cc in xa}
                vb |= {(rr, cc + offset) for rr, cc in xb}
                regions.update({(rr, cc + offset): reg for rr in range(5) for cc in range(width)})
            sa, sb = permissions(sep)
            va |= {(rr, c) for rr in sa}
            vb |= {(rr, c) for rr in sb}
            regions.update({(rr, c): 1 for rr in range(5)})
            assert aa <= va and vb <= bb, (n, r, c, label, 'direction')
            for rr, cc in vb:
                for other in ((rr + 1, cc), (rr, cc + 1)):
                    assert other not in vb or regions[rr, cc] == regions[other], (n, r, c, 'White edge')
            count += 1
    print(f'REGRESSION ONLY: {count} normalized openings, odd widths 3..{limit}, strengthened R/X={strengthen}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate', action='store_true')
    parser.add_argument('--regression-max', type=int, default=31)
    args = parser.parse_args()
    check_local_contracts()
    local_certificates(args.generate)
    assembly_regression(args.regression_max)
    assembly_regression(args.regression_max, strengthen=True)
