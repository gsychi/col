"""Search-free finite checker for dx_interface_contracts.json.

This checker reconstructs short games and uses Conway's recursive order test.
It does not import the catalogue generator or its alternating-win evaluator.
The arbitrary-width obstruction itself is proved in the accompanying note;
the last checks here are finite regression checks of its two local invariants.
"""
from functools import lru_cache
from fractions import Fraction
from pathlib import Path
import json


GAMES = []
IDS = {}


def game(left=(), right=()):
    key = (frozenset(left), frozenset(right))
    if key not in IDS:
        IDS[key] = len(GAMES)
        GAMES.append(key)
    return IDS[key]


ZERO = game()
STAR = game([ZERO], [ZERO])


@lru_cache(None)
def leq(g, h):
    return (all(not leq(h, gl) for gl in GAMES[g][0]) and
            all(not leq(hr, g) for hr in GAMES[h][1]))


@lru_cache(None)
def number(q):
    if q == 0:
        return ZERO
    if q.denominator == 1:
        return game([number(q - 1)], []) if q > 0 else game([], [number(q + 1)])
    step = Fraction(1, q.denominator)
    return game([number(q - step)], [number(q + step)])


@lru_cache(None)
def add(g, h):
    return game([add(gl, h) for gl in GAMES[g][0]] + [add(g, hl) for hl in GAMES[h][0]],
                [add(gr, h) for gr in GAMES[g][1]] + [add(g, hr) for hr in GAMES[h][1]])


@lru_cache(None)
def path_game(blue, white):
    left, right = [], []
    for row in range(5):
        occupied = {row}
        closed = {i for i in (row - 1, row, row + 1) if 0 <= i < 5}
        if row in blue:
            left.append(path_game(blue - closed, white - occupied))
        if row in white:
            right.append(path_game(blue - occupied, white - closed))
    return game(left, right)


def permissions(pattern):
    return (frozenset(i for i, x in enumerate(pattern) if x in "ob"),
            frozenset(i for i, x in enumerate(pattern) if x in "ow"))


def verify_catalogue(data):
    assert set(data) == {"schema", "patterns", "scope", "contracts"}
    assert data["schema"] == 1
    assert data["patterns"] == dict(D="obwbo", U="wbobo", V="bwbob", X="bowob", R="wobob", J="owobo")
    assert data["scope"] == "neutral opening column; same-column reply only"
    seen = set()
    full = set(range(5))
    for record in data["contracts"]:
        assert set(record) == {"opening_row", "reply_row", "near_left", "near_right", "separator",
                               "left_white_support", "right_white_support", "separator_white_support", "value"}
        assert set(record["value"]) == {"number", "star"}
        assert type(record["value"]["star"]) is bool
        assert type(record["value"]["number"]) is str
        assert len(record["separator"]) == 5 and set(record["separator"]) <= set("obw.")
        opening, reply = record["opening_row"], record["reply_row"]
        names = record["near_left"], record["near_right"]
        key = opening, reply, *names
        assert key not in seen
        seen.add(key)
        supports = []
        for name in names:
            blue, white = permissions(data["patterns"][name])
            assert full - {opening} <= blue
            assert reply is None or reply not in white
            supports.append(white)
        actual_blue = full - {opening - 1, opening, opening + 1}
        actual_white = full - {opening}
        if reply is not None:
            assert reply in actual_white
            actual_blue -= {reply}
            actual_white -= {reply - 1, reply, reply + 1}
        blue, white = permissions(record["separator"])
        assert blue == actual_blue
        assert white == actual_white - supports[0] - supports[1]
        assert list(sorted(supports[0])) == record["left_white_support"]
        assert list(sorted(supports[1])) == record["right_white_support"]
        assert list(sorted(white)) == record["separator_white_support"]
        actual = path_game(blue, white)
        target = number(Fraction(record["value"]["number"]))
        if record["value"]["star"]:
            target = add(target, STAR)
        assert leq(actual, target) and leq(target, actual), record
    expected = set()
    for opening, names in [(0, "UR"), (1, "VJ"), (2, "DX")]:
        for i, left in enumerate(names):
            for right in names[i:]:
                white = permissions(data["patterns"][left])[1] | permissions(data["patterns"][right])[1]
                for reply in [None] + [r for r in range(5) if r != opening and r not in white]:
                    expected.add((opening, reply, left, right))
    assert seen == expected
    # Endpoint strengthening used by the new DD outer-opening reduction.
    root = path_game(*permissions("..wbo"))
    target = number(Fraction(-1, 2))
    assert leq(root, target) and leq(target, root)
    return len(seen)


def obstruction_regressions(patterns):
    count = 0
    candidates = []
    for q in patterns.values():
        for endpoint in (q, q[::-1]):
            candidates.extend([(patterns["D"], endpoint), (endpoint, patterns["D"])])
    for width in range(4, 11, 2):
        for column in range(1, width - 2):
            for row in (0, 1, 3, 4):
                blue = {(r, c) for r in range(5) for c in range(width)}
                white = set(blue)
                for c, label in [(0, "D"), (width - 1, "X")]:
                    aa, bb = permissions(patterns[label])
                    blue -= {(r, c) for r in range(5) if r not in aa}
                    white -= {(r, c) for r in range(5) if r not in bb}
                blue -= {(row, column), (row - 1, column), (row + 1, column),
                         (row, column - 1), (row, column + 1)}
                white.discard((row, column))
                for reply in [None] + list(white):
                    actual_blue, actual_white = set(blue), set(white)
                    if reply is not None:
                        rr, cc = reply
                        actual_blue.discard(reply)
                        actual_white -= {reply, (rr - 1, cc), (rr + 1, cc),
                                         (rr, cc - 1), (rr, cc + 1)}
                    for left, right in candidates:
                        virtual_blue = {(r, c) for r in range(5) for c in range(column + 1, width)}
                        virtual_white = set(virtual_blue)
                        for c, endpoint in [(column + 1, left), (width - 1, right)]:
                            aa, bb = permissions(endpoint)
                            virtual_blue -= {(r, c) for r in range(5) if r not in aa}
                            virtual_white -= {(r, c) for r in range(5) if r not in bb}
                        side_blue = {(r, c) for r, c in actual_blue if c > column}
                        side_white = {(r, c) for r, c in actual_white if c > column}
                        assert not (side_blue <= virtual_blue and virtual_white <= side_white)
                        count += 1
    return count


if __name__ == "__main__":
    data = json.loads(Path(__file__).with_name("dx_interface_contracts.json").read_text())
    count = verify_catalogue(data)
    regressions = obstruction_regressions(data["patterns"])
    print(f"Verified {count} complete one-column contracts and '..wbo' = -1/2.")
    print(f"Verified {regressions} rejected original-family side embeddings (finite regression only).")
