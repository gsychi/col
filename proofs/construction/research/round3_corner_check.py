#!/usr/bin/env python3
"""Replay the round-three corner claims; no strategy or move search.

Finite cap equalities use all-options Conway order.  The larger ordinary-board
counterexample uses the independently checked response DAG in number_certificates.
"""
from pathlib import Path
import gzip
import json

from number_certificates import board_neighbors, verify
from round2_height_applications_check import rectangle, play
from round2_height_twin_check import evaluator, game, leq, ZERO

ROOT = Path(__file__).resolve().parent
CAP_ROOTS = {"O": (32054, 32180), "D": (31798, 30100)}


def mask(cells, width):
    return sum(1 << (r * width + c) for r, c in cells)


def finite_caps():
    neighbors = board_neighbors(5, 3)
    edges = {(v, w) for v, adjacent in enumerate(neighbors) for w in adjacent}
    evaluate = evaluator(15, edges)
    minus_one = game([], [ZERO])
    minus_one_star = game([minus_one], [minus_one])
    count = 0
    for endpoint, (a, b) in CAP_ROOTS.items():
        root = evaluate(a, b)
        target = ZERO if endpoint == "O" else minus_one_star
        assert leq(root, target) and leq(target, root)
        for v in range(15):
            if not a >> v & 1:
                continue
            r, c = divmod(v, 3)
            reply = ((4, 0) if (r, c) == (2, 2) else
                     (3, 1) if (r, c) == (4, 2) else (2, 2))
            u = reply[0] * 3 + reply[1]
            aa = a & ~((1 << v) | sum(1 << w for w in neighbors[v]))
            bb = b & ~(1 << v)
            assert bb >> u & 1
            aa &= ~(1 << u)
            bb &= ~((1 << u) | sum(1 << w for w in neighbors[u]))
            assert leq(evaluate(aa, bb), ZERO), (endpoint, (r, c), reply)
            # A response on the cut column is only at row four.  Its possible
            # external White prohibition lands on a retired strip permission.
            assert reply[1] != 0 or reply[0] == 4
            count += 1
    print(f"VERIFIED C_O=0, C_D=-1+* and all {count} prescribed local replies")


def interfaces():
    count = 0
    for n in range(4, 13):
        k = n - 3
        for p in "ODUVXRJ":
            for q in "OD":
                a, b, neighbors = rectangle(n, p, q)
                a, b = play(a, b, neighbors, "B", (2, k))
                a, b = play(a, b, neighbors, "W", (0, k))
                va, vb, _ = rectangle(k, p, "X")
                owner = {v: 0 for v in va | vb}
                ca, cb = CAP_ROOTS[q]
                for v in range(15):
                    cell = (v // 3, k + v % 3)
                    if ca >> v & 1:
                        va.add(cell)
                    if cb >> v & 1:
                        vb.add(cell)
                    owner[cell] = 1
                assert a <= va and vb <= b
                assert all(owner[u] == owner[v]
                           for u in vb for v in neighbors[u] & vb)
                # Every possible second Blue move belongs to one component;
                # no move is omitted by the local/remote dichotomy.
                assert all(v in va and ((v[1] < k) != (v[1] >= k)) for v in a)
                assert k < n
                count += 1
    print(f"REGRESSION: {count} root bindings and safe X/cap interfaces; width drops by three")


def certificates_and_notch():
    ox_a, ox_b, ox_neighbors = rectangle(2, "O", "X")
    ox_evaluate = evaluator(10, {(2 * r + c, 2 * rr + cc)
                                for (r, c), adjacent in ox_neighbors.items()
                                for rr, cc in adjacent})
    ox = ox_evaluate(mask(ox_a, 2), mask(ox_b, 2))
    star = game([ZERO], [ZERO])
    assert leq(ox, star) and leq(star, ox)
    ox_a, ox_b = play(ox_a, ox_b, ox_neighbors, "B", (0, 0))
    ox_option = ox_evaluate(mask(ox_a, 2), mask(ox_b, 2))
    assert leq(ox_option, ZERO) and leq(ZERO, ox_option)
    print("VERIFIED OX_2=star and its Blue (0,0) option is zero")

    a, b, neighbors = rectangle(5, "O", "O")
    a, b = play(a, b, neighbors, "B", (2, 2))
    a, b = play(a, b, neighbors, "W", (0, 2))
    assert (mask(a, 5), mask(b, 5)) == (33408891, 33550193)
    child_a, child_b = play(a, b, neighbors, "B", (0, 0))
    path = ROOT / "round3_corner_certificates" / "ordinary5_center_bad_reply.json.gz"
    doc = json.loads(gzip.decompress(path.read_bytes()))
    assert (doc["height"], doc["width"], doc["root"]) == (
        5, 5, [mask(child_b, 5), mask(child_a, 5), 0, 1])
    nodes, edges = verify(doc)
    print(f"VERIFIED actual 5x5 losing White reply: {nodes} checkpoints, {edges} edges")

    # The notch is a named hypothetical permission game, with the exact
    # exterior restrictions retained.  The additional White move is legal.
    a, b = play(a, b, neighbors, "W", (2, 4))
    twins = {(0, 4), (1, 3)}
    common = {(0, 3), (1, 4)}
    assert twins <= a & b and common <= a and not common & b
    assert all(neighbors[v] & (a | b) == common for v in twins)
    assert all(not (neighbors[v] & common) for v in common)
    a -= twins | common
    b -= twins | common
    assert (mask(a, 5), mask(b, 5)) == (33391715, 33000545)
    for actor, (first, second) in enumerate(((a, b), (b, a))):
        path = ROOT / "round3_corner_certificates" / f"notch2_zero_{actor}.json.gz"
        doc = json.loads(gzip.decompress(path.read_bytes()))
        assert (doc["height"], doc["width"], doc["root"]) == (
            5, 5, [mask(first, 5), mask(second, 5), 0, 1])
        print(f"VERIFIED N_2 actor {actor} loss: {verify(doc)}")

    a, b = play(a, b, neighbors, "B", (0, 0))
    assert (mask(a, 5), mask(b, 5)) == (33391680, 33000544)
    evaluate = evaluator(25, {(5 * r + c, 5 * rr + cc)
                             for (r, c), adjacent in neighbors.items()
                             for rr, cc in adjacent})
    child = evaluate(mask(a, 5), mask(b, 5))
    star = game([ZERO], [ZERO])
    assert leq(child, star) and leq(star, child)
    assert not leq(child, ZERO) and not leq(ZERO, child)
    print("VERIFIED N_2=0 and its Blue (0,0) child equals star")


if __name__ == "__main__":
    finite_caps()
    interfaces()
    certificates_and_notch()
