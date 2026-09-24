#!/usr/bin/env python3
"""Independent checks for staircase, empty-strip, and actual-corner ideas.

No bounded minimax discovery program is imported. Numerical claims are checked
by all-options Conway order or the independent stored response-DAG verifier.
"""
from pathlib import Path
from itertools import product
import gzip
import json

from number_certificates import board_neighbors, verify
from round2_height_twin_check import evaluator, leq, ZERO
from round2_height_applications_check import grid

ROOT = Path(__file__).resolve().parent
CHECKED = {}


def record_artifact(path, doc, schema):
    CHECKED[str(path.relative_to(ROOT))] = {
        'height': doc['height'], 'width': doc['width'], 'root': doc['root'],
        'checkpoints': len(doc['nodes']), 'edges': doc['edges'], 'schema': schema}


def alternating_paths_and_tiles():
    count = 0
    for p in range(2, 10):
        length = 2 * p - 1
        evaluate = evaluator(length, {(i, i + 1) for i in range(length - 1)})
        g = evaluate((1 << length) - 1, sum(1 << i for i in range(0, length, 2)))
        assert leq(ZERO, g)
        assert leq(g, ZERO) == (p == 2)
        count += 1
    evaluate = evaluator(4, {(0, 1), (0, 2), (1, 3), (2, 3)})
    for b in range(16):
        g = evaluate(15, b)
        if leq(g, ZERO):
            assert leq(ZERO, g)  # No negative square compensation is discarded.
            assert b & 9 == 9 or b & 6 == 6
    for b in (9, 6):
        g = evaluate(15, b)
        assert leq(g, ZERO) and leq(ZERO, g)
    print(f"VERIFIED {count} alternating-path sign regressions and all 16 tile masks")


def staircase_geometry():
    count = 0
    for n in range(3, 32, 2):
        cells, neighbors = grid(5, n)
        N = (n - 1) // 2
        for a in range(0, n, 2):
            for b in range(a, n, 2):
                A, B = a // 2, b // 2
                path = ([(0, c) for c in range(a + 1)] + [(1, a)] +
                        [(2, c) for c in range(a, b + 1)] + [(3, b)] +
                        [(4, c) for c in range(b, n)])
                p = (len(path) + 1) // 2
                majority = set(path[::2])
                assert len(path) == n + 4 and len(majority) == N + 3 == p
                assert len(set(path)) == len(path)
                path_set = set(path)
                assert all(neighbors[v] & path_set ==
                           set(path[max(0, i - 1):i]) | set(path[i + 1:i + 2])
                           for i, v in enumerate(path))
                for left, right in product(range(2), repeat=2):
                    tiles, support = [], set()
                    for r, lo, hi, phase in ((1, 0, a, left), (3, 0, b, left),
                                           (0, a + 1, n, right), (2, b + 1, n, right)):
                        for c in range(lo, hi, 2):
                            tile = {(r + x, c + y) for x, y in product(range(2), repeat=2)}
                            tiles.append(tile)
                            support |= {v for v in tile if sum(v) % 2 == phase}
                    outside = set().union(*tiles)
                    assert len(outside) == sum(map(len, tiles))
                    assert not outside & path_set and outside | path_set == cells
                    assert all(not neighbors[v] & support for v in support)
                    white = {v for v in path if not neighbors[v] & support}
                    assert len(white) <= p
                    if len(white) == p:
                        assert white == majority or len(white & majority) % 2 == 1
                    if b > 0 and a < n - 1 and (left, right) == (0, 1):
                        assert len(white) == N + 1 + A - B + (A == 0) + (A < B)
                        assert len(white) < p
                    count += 1
    print(f"REGRESSION: {count} staircase partitions, seam supports, and symbolic count cases")


def empty_strip_caps():
    count = 0
    for n in (3, 5, 7, 9):
        neighbors = board_neighbors(2, n)
        closed = [sum(1 << x for x in adjacent | {v})
                  for v, adjacent in enumerate(neighbors)]
        evaluate = evaluator(2 * n, {(v, w) for v, adjacent in enumerate(neighbors)
                                    for w in adjacent})
        full = (1 << (2 * n)) - 1
        bottom = ((1 << n) - 1) << n
        for blue in range(2 * n):
            for white in range(n, 2 * n):
                if white == blue:
                    continue
                a = full & ~closed[blue] & ~(1 << white)
                b = bottom & ~(1 << blue) & ~closed[white]
                assert not leq(evaluate(a, b), ZERO), (n, blue, white)
                count += 1
    print(f"VERIFIED {count} empty-3-row/2-row-cap attempts are not nonpositive (widths 3,5,7,9)")
    corner_cases = 0
    for n in range(3, 102, 2):
        m = (n - 1) // 2
        for w in range(1, n):
            left = max(0, w - 2)  # cells 1,...,w-2
            right = max(0, n - w - 2)  # cells w+2,...,n-1
            assert (left + 1) // 2 + (right + 1) // 2 == m - 1
            corner_cases += 1
    print(f"REGRESSION: {corner_cases} corner-cap lower-bound interval counts equal one")


def center_reply_certificates():
    n = 5
    neighbors = board_neighbors(5, n)
    closed = [sum(1 << x for x in adjacent | {v})
              for v, adjacent in enumerate(neighbors)]
    full = (1 << 25) - 1
    nodes = edges = 0
    for white in (0, 1, 2, 6, 7):
        a = full & ~closed[12] & ~(1 << white)
        b = full & ~(1 << 12) & ~closed[white]
        if white == 0:
            cases = [("blue", a, b), ("white", b, a)]
        else:
            assert a & 1
            cases = [("blue0_child_white", b & ~1, a & ~closed[0])]
        for label, aa, bb in cases:
            if white == 2:
                path = ROOT / "round3_corner_certificates" / "ordinary5_center_bad_reply.json.gz"
            else:
                path = ROOT / "round4_bridge_certificates" / f"center5_w{white}_{label}.json.gz"
            doc = json.loads(gzip.decompress(path.read_bytes()))
            assert (doc['height'], doc['width'], doc['root']) == (5, 5, [aa, bb, 0, 1])
            nn, ee = verify(doc)
            record_artifact(path, doc, 'canonical-dyadic-response-dag-v1')
            nodes += nn
            edges += ee
    # These are exactly the D4 orbits of White replies to the central Blue cell.
    covered = set()
    for v in (0, 1, 2, 6, 7):
        r, c = divmod(v, 5)
        covered |= {(rr, cc) for rr, cc in ((r, c), (r, 4-c), (4-r, c), (4-r, 4-c),
                                          (c, r), (c, 4-r), (4-c, r), (4-c, 4-r))}
    assert covered == {(r, c) for r in range(5) for c in range(5)} - {(2, 2)}
    print(f"VERIFIED only corners win against center Blue on 5x5: {nodes} DAG checkpoints, {edges} edges")


def center7_certificate():
    """Independent coordinate-set replay; no numeric options or minimax search.

    This separate schema avoids weakening the 30-cell dimension guard of the
    older number-certificate checker. Its only claim is this fixed 35-cell root.
    """
    path = ROOT / 'round4_bridge_certificates' / 'center7_blue.json.gz'
    data = json.loads(gzip.decompress(path.read_bytes()))
    assert (data['height'], data['width']) == (5, 7)
    cells, neighbors = grid(5, 7)

    def vertices(bits):
        assert type(bits) is int and 0 <= bits < 1 << 35
        return frozenset((i // 7, i % 7) for i in range(35) if bits >> i & 1)

    def move(first, second, v):
        assert v in first
        return second - {v}, first - {v} - neighbors[v]

    records = {}
    for index, (aa, bb, replies) in enumerate(data['nodes']):
        assert type(aa) is int and type(bb) is int
        assert 0 <= aa < 1 << 35 and 0 <= bb < 1 << 35
        key = aa, bb
        assert key not in records
        records[key] = index
    a = cells - {(2, 3)} - neighbors[(2, 3)] - {(0, 0)}
    b = cells - {(2, 3), (0, 0)} - neighbors[(0, 0)]
    root_sets = frozenset(a), frozenset(b)
    assert tuple(map(vertices, data['root'])) == root_sets
    root = tuple(data['root'])
    assert root in records
    masks = {(r, c): 1 << (7*r+c) for r, c in cells}
    to_mask = lambda vs: sum(masks[v] for v in vs)
    seen = bytearray(len(records))
    root_index = records[root]
    seen[root_index] = 1
    queue = [root_index]
    edges = count = 0
    while queue:
        aa_mask, bb_mask, replies = data['nodes'][queue.pop()]
        aa, bb = vertices(aa_mask), vertices(bb_mask)
        count += 1
        first_moves = {(v // 7, v % 7) for v, _ in replies}
        assert len(replies) == len(aa) and first_moves == aa
        for first, reply in replies:
            assert type(first) is int and type(reply) is int
            assert 0 <= first < 35 and 0 <= reply < 35
            v, u = divmod(first, 7), divmod(reply, 7)
            mid = move(aa, bb, v)
            child = move(*mid, u)
            child_masks = to_mask(child[0]), to_mask(child[1])
            assert child_masks in records
            assert len(child[0] | child[1]) < len(mid[0] | mid[1]) < len(aa | bb)
            edges += 1
            child_index = records[child_masks]
            if not seen[child_index]:
                seen[child_index] = 1
                queue.append(child_index)
    assert count == len(records) and edges == data['edges']
    record_artifact(path, data, 'zero-offset-response-dag-v1')
    print(f"VERIFIED M_7<=0: {len(records)} checkpoints, {edges} edges")


def center3_certificates():
    cells, neighbors = grid(5, 3)
    a = cells - {(2, 1)} - neighbors[(2, 1)] - {(0, 0)}
    b = cells - {(2, 1), (0, 0)} - neighbors[(0, 0)]
    mask = lambda vs: sum(1 << (3*r+c) for r, c in vs)
    assert (mask(a), mask(b)) == (31278, 32628)
    assert (0, 2) in b
    cases = [('center3_blue', a, b),
             ('center3_white2_child_blue', a - {(0, 2)},
              b - {(0, 2)} - neighbors[(0, 2)])]
    nodes = edges = 0
    for name, aa, bb in cases:
        path = ROOT / 'round4_bridge_certificates' / (name + '.json.gz')
        doc = json.loads(gzip.decompress(path.read_bytes()))
        assert (doc['height'], doc['width'], doc['root']) == (5, 3, [mask(aa), mask(bb), 0, 1])
        nn, ee = verify(doc)
        record_artifact(path, doc, 'canonical-dyadic-response-dag-v1')
        nodes += nn
        edges += ee
    print(f"VERIFIED M_3<0: {nodes} checkpoints, {edges} edges")


def check_manifest():
    manifest = json.loads((ROOT / 'round4_bridge_certificates' / 'manifest.json').read_text())
    rows = manifest['artifacts']
    assert len(rows) == len(CHECKED) == 9
    assert {row['path'] for row in rows} == set(CHECKED)
    for row in rows:
        assert all(row[key] == value for key, value in CHECKED[row['path']].items())
        assert row['reused'] == row['path'].startswith('round3_corner_certificates/')
    for label, selected in (('new', [r for r in rows if not r['reused']]),
                            ('reused', [r for r in rows if r['reused']]), ('total', rows)):
        expected = dict(certificates=len(selected),
                        checkpoints=sum(r['checkpoints'] for r in selected),
                        edges=sum(r['edges'] for r in selected))
        assert manifest['summary'][label] == expected
        print(f"VERIFIED manifest {label}: {expected}")


if __name__ == '__main__':
    alternating_paths_and_tiles()
    staircase_geometry()
    empty_strip_caps()
    center_reply_certificates()
    center3_certificates()
    center7_certificate()
    check_manifest()
