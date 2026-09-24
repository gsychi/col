#!/usr/bin/env python3
"""Independent finite order checks for the exact shared-twin module identity.

Constructs short games from all legal options and compares by Conway order.
These finite checks supplement, rather than prove, the symbolic theorem.
"""
from functools import lru_cache
from itertools import product


GAMES = []
IDS = {}


def game(left=(), right=()):
    key = frozenset(left), frozenset(right)
    if key not in IDS:
        IDS[key] = len(GAMES)
        GAMES.append(key)
    return IDS[key]


ZERO = game()


@lru_cache(None)
def leq(g, h):
    return (all(not leq(h, option) for option in GAMES[g][0]) and
            all(not leq(option, g) for option in GAMES[h][1]))


def evaluator(size, edges):
    neighbors = [set() for _ in range(size)]
    for u, v in edges:
        assert 0 <= u < size and 0 <= v < size and u != v
        neighbors[u].add(v)
        neighbors[v].add(u)
    closed = [sum(1 << v for v in adjacent | {u})
              for u, adjacent in enumerate(neighbors)]

    @lru_cache(None)
    def evaluate(a, b):
        left, right = [], []
        for v in range(size):
            bit = 1 << v
            if a & bit:
                left.append(evaluate(a & ~closed[v], b & ~bit))
            if b & bit:
                right.append(evaluate(a & ~bit, b & ~closed[v]))
        return game(left, right)

    return evaluate


def check_fixture(name, p, h, outside, h_edges=(), attachments=(), outside_edges=(),
                  permission_limited=False):
    # The shared false twins occupy [0,p); H and the outside follow them.
    size = p + h + outside
    edges = {(i, p + j) for i in range(p) for j in range(h)}
    edges |= {(p + u, p + v) for u, v in h_edges}
    edges |= {(p + u, p + h + v) for u, v in attachments}
    edges |= {(p + h + u, p + h + v) for u, v in outside_edges}
    evaluate = evaluator(size, edges)
    shared = (1 << p) - 1
    outside_mask = ((1 << outside) - 1) << (p + h)
    count = 0
    for states in product(range(4), repeat=h + outside):
        if permission_limited:
            # This fixture's H has no edges, so its permission-restricted
            # independence numbers are exactly the two legal-cell counts.
            assert not h_edges
            if any(sum(bool(state & player) for state in states[:h]) > p
                   for player in (1, 2)):
                continue
        a = b = shared
        for j, state in enumerate(states, start=p):
            if state & 1:
                a |= 1 << j
            if state & 2:
                b |= 1 << j
        actual = evaluate(a, b)
        deleted = evaluate(a & outside_mask, b & outside_mask)
        assert leq(actual, deleted) and leq(deleted, actual), (name, states)
        count += 1
    print(f"VERIFIED {name}: exact deletion for {count} permission assignments")
    return count


def sharpness():
    # Three shared independent cells are not a nonpositive contract.
    g = evaluator(3, set())(7, 7)
    assert not leq(g, ZERO)
    # Two shared twins cannot neutralize three independent private vertices.
    edges = {(i, j) for i in range(2) for j in range(2, 5)}
    g = evaluator(5, edges)(31, 3)
    assert leq(ZERO, g) and not leq(g, ZERO)
    print("VERIFIED odd-support and independence-budget counterexamples")


if __name__ == "__main__":
    total = 0
    total += check_fixture("two isolated twins", 2, 0, 1)
    total += check_fixture("two leaves and attached center", 2, 1, 2,
                           attachments=((0, 0), (0, 1)), outside_edges=((0, 1),))
    total += check_fixture("twin square with outside attachment", 2, 2, 1,
                           attachments=((0, 0), (1, 0)))
    total += check_fixture("three-vertex neighborhood of independence two", 2, 3, 1,
                           h_edges=((0, 1), (1, 2)), attachments=((0, 0), (2, 0)))
    total += check_fixture("four shared twins and three private vertices", 4, 3, 0)
    total += check_fixture("permission-sensitive independence bound", 2, 3, 1,
                           attachments=((0, 0), (2, 0)), permission_limited=True)
    sharpness()
    print(f"REGRESSION ONLY: {total} identities; arbitrary-graph proof is symbolic.")
