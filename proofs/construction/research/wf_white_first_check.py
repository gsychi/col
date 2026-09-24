#!/usr/bin/env python3
"""Search-free root/strategy checker for the White-first DD base obligations.

Run with --generate to rediscover the checked response DAGs; the default only
loads and independently verifies certificates through number_certificates.py.
No bounded-width check here asserts an arbitrary-width family inequality.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import gzip
import json
from pathlib import Path

from number_certificates import board_neighbors, generate, verify

ROOT = Path(__file__).resolve().parent
CERTS = ROOT / 'wf_certificates'
PATTERNS = {'D': 'obwbo', 'U': 'wbobo', 'J': 'owobo',
            'T': 'bobob'}


def endpoint_masks(width, left, right):
    """Row-major permissions; restrictions intersect when width is one."""
    blue = white = (1 << (5 * width)) - 1
    for column, pattern in ((0, left), (width - 1, right)):
        for row, permission in enumerate(pattern):
            cell = 1 << (row * width + column)
            if permission not in 'ob':
                blue &= ~cell
            if permission not in 'ow':
                white &= ~cell
    return blue, white


def white_move(width, blue, white, row, column):
    cell = row * width + column
    if not (white >> cell) & 1:
        raise ValueError('Illegal White opening')
    neighborhood = {cell} | set(board_neighbors(5, width)[cell])
    return blue & ~(1 << cell), white & ~sum(1 << v for v in neighborhood)


def roots():
    result = []
    a, b = endpoint_masks(1, PATTERNS['D'], PATTERNS['D'])
    assert (a, b) == (27, 21)
    result.extend([('dd1_blue', 1, a, b, Fraction(0)),
                   ('dd1_white', 1, b, a, Fraction(0))])
    a, b = endpoint_masks(3, PATTERNS['D'], PATTERNS['D'])
    assert (a, b) == (32447, 30167)
    result.append(('dd3_blue', 3, a, b, Fraction(0)))
    aa, bb = white_move(3, a, b, 2, 0)
    assert (aa, bb) == (32447, 29975)
    result.append(('dd3_white_center_endpoint_child', 3, aa, bb, Fraction(0)))
    a, b = endpoint_masks(1, PATTERNS['D'], PATTERNS['U'])
    result.append(('du1_plus_eighth_blue', 1, a, b, Fraction(1, 8)))
    a, b = endpoint_masks(1, PATTERNS['D'], PATTERNS['J'])
    result.append(('dj1_plus_three_eighths_blue', 1, a, b, Fraction(3, 8)))
    # Zero-valued new boundary state from the elementary endpoint cuts.
    for symbol in ('T',):
        a, b = endpoint_masks(2, PATTERNS['D'], PATTERNS[symbol])
        result.extend([(f'd{symbol.lower()}2_blue', 2, a, b, Fraction(0)),
                       (f'd{symbol.lower()}2_white', 2, b, a, Fraction(0))])
    for name, pattern, value in (('white_center_cap', 'ob.bo', Fraction(1)),
                                 ('white_corner_cap', '.bwbo', Fraction(1, 2))):
        a, b = endpoint_masks(1, pattern, pattern)
        result.extend([(f'{name}_minus_value_blue', 1, a, b, -value),
                       (f'{name}_minus_value_white', 1, b, a, value)])
    return result


def check_resource_identity():
    """Exhaustively checks the local set identities on every five-cell path.

    The note proves the identities for arbitrary graphs. This finite check is
    regression coverage, not the basis for the general statement.
    """
    neighborhoods = [{v} | set(s) for v, s in enumerate(board_neighbors(5, 1))]
    count = 0
    for a in range(32):
        aa = {v for v in range(5) if a >> v & 1}
        for b in range(32):
            bb = {v for v in range(5) if b >> v & 1}
            for v in bb:
                after_a = aa - {v}
                after_b = bb - neighborhoods[v]
                assert after_b - after_a == (bb - aa) - neighborhoods[v]
                count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate', action='store_true')
    args = parser.parse_args()
    total_nodes = total_edges = 0
    summary = []
    for name, width, a, b, q in roots():
        path = CERTS / f'{name}.json.gz'
        if args.generate:
            CERTS.mkdir(exist_ok=True)
            document = generate(5, width, a, b, q)
            path.write_bytes(gzip.compress(json.dumps(document, separators=(',', ':')).encode(), mtime=0))
        document = json.loads(gzip.decompress(path.read_bytes()))
        expected = (5, width, [a, b, q.numerator, q.denominator])
        if (document['height'], document['width'], document['root']) != expected:
            raise ValueError(f'Wrong root for {name}')
        nodes, edges = verify(document)
        total_nodes += nodes
        total_edges += edges
        summary.append({'name': name, 'root': expected, 'nodes': nodes, 'edges': edges})
        print(f'VERIFIED {name}: {nodes} checkpoints, {edges} edges')
    checks = check_resource_identity()
    if args.generate:
        (CERTS / 'manifest.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(f'VERIFIED {len(summary)} certificates, {total_nodes} checkpoints, {total_edges} edges')
    print(f'REGRESSION: {checks} five-cell White-move support identities')
    print('Claims: DD1=0; DD3<0; DU1<=-1/8; DJ1<=-3/8; DT2=0; local caps 1 and 1/2.')


if __name__ == '__main__':
    main()
