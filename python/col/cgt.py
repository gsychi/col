"""Minimal combinatorial game theory engine for Col values.

Every Col position has value z or z* (a dyadic number, optionally plus star)
by Conway's theorem. This module computes the value of {L | R} where all
options are themselves such values, via a small generic canonical-form
engine (hash-consed games, domination removal, reversible-option bypass).
The z-or-z* theorem is asserted on every result, so any rules bug or
engine bug surfaces immediately instead of corrupting the cache.

Values are represented as ``(Fraction, star: bool)`` tuples.
"""

from __future__ import annotations

import math
from fractions import Fraction
from typing import Dict, List, Optional, Sequence, Tuple

Value = Tuple[Fraction, bool]


class Game:
    __slots__ = ("lefts", "rights", "uid")

    def __init__(self, lefts: Tuple["Game", ...], rights: Tuple["Game", ...], uid: int) -> None:
        self.lefts = lefts
        self.rights = rights
        self.uid = uid


_intern: Dict[Tuple[Tuple[int, ...], Tuple[int, ...]], Game] = {}
_le_memo: Dict[Tuple[int, int], bool] = {}
_add_memo: Dict[Tuple[int, int], Game] = {}
_canon_memo: Dict[int, Game] = {}
_number_games: Dict[Fraction, Game] = {}
_number_values: Dict[int, Optional[Fraction]] = {}
_options_memo: Dict[Tuple[Tuple[Value, ...], Tuple[Value, ...]], Value] = {}


def make(lefts: Sequence[Game], rights: Sequence[Game]) -> Game:
    left_tuple = tuple(sorted({g.uid: g for g in lefts}.values(), key=lambda g: g.uid))
    right_tuple = tuple(sorted({g.uid: g for g in rights}.values(), key=lambda g: g.uid))
    key = (
        tuple(g.uid for g in left_tuple),
        tuple(g.uid for g in right_tuple),
    )
    game = _intern.get(key)
    if game is None:
        game = Game(left_tuple, right_tuple, len(_intern))
        _intern[key] = game
    return game


ZERO = make([], [])
STAR = make([ZERO], [ZERO])


def le(g: Game, h: Game) -> bool:
    """g <= h in the partial order of games."""
    if g.uid == h.uid:
        return True
    key = (g.uid, h.uid)
    cached = _le_memo.get(key)
    if cached is not None:
        return cached

    result = all(not le(h, gl) for gl in g.lefts) and all(
        not le(hr, g) for hr in h.rights
    )
    _le_memo[key] = result
    return result


def add(g: Game, h: Game) -> Game:
    if g is ZERO:
        return h
    if h is ZERO:
        return g
    key = (g.uid, h.uid) if g.uid <= h.uid else (h.uid, g.uid)
    cached = _add_memo.get(key)
    if cached is not None:
        return cached

    lefts = [add(gl, h) for gl in g.lefts] + [add(g, hl) for hl in h.lefts]
    rights = [add(gr, h) for gr in g.rights] + [add(g, hr) for hr in h.rights]
    result = make(lefts, rights)
    _add_memo[key] = result
    return result


def _filter_dominated(options: List[Game], keep_larger: bool) -> List[Game]:
    kept = []
    for g in options:
        dominated = False
        for h in options:
            if g is h:
                continue
            if keep_larger:
                worse = le(g, h)
            else:
                worse = le(h, g)
            if worse:
                equal = le(h, g) if keep_larger else le(g, h)
                if not equal or h.uid < g.uid:
                    dominated = True
                    break
        if not dominated:
            kept.append(g)
    return kept


def canonical(g: Game) -> Game:
    cached = _canon_memo.get(g.uid)
    if cached is not None:
        return cached

    lefts = [canonical(x) for x in g.lefts]
    rights = [canonical(x) for x in g.rights]

    while True:
        lefts = _filter_dominated(lefts, keep_larger=True)
        rights = _filter_dominated(rights, keep_larger=False)
        current = make(lefts, rights)

        changed = False
        new_lefts: List[Game] = []
        for gl in lefts:
            reverser = next((glr for glr in gl.rights if le(glr, current)), None)
            if reverser is not None:
                new_lefts.extend(reverser.lefts)
                changed = True
            else:
                new_lefts.append(gl)

        new_rights: List[Game] = []
        for gr in rights:
            reverser = next((grl for grl in gr.lefts if le(current, grl)), None)
            if reverser is not None:
                new_rights.extend(reverser.rights)
                changed = True
            else:
                new_rights.append(gr)

        if not changed:
            _canon_memo[g.uid] = current
            _canon_memo[current.uid] = current
            return current
        lefts, rights = new_lefts, new_rights


def number_game(value: Fraction) -> Game:
    cached = _number_games.get(value)
    if cached is not None:
        return cached

    denominator = value.denominator
    if denominator & (denominator - 1):
        raise ValueError(f"{value} is not dyadic")

    if denominator == 1:
        n = value.numerator
        if n == 0:
            game = ZERO
        elif n > 0:
            game = make([number_game(value - 1)], [])
        else:
            game = make([], [number_game(value + 1)])
    else:
        step = Fraction(1, denominator)
        game = make([number_game(value - step)], [number_game(value + step)])

    _number_games[value] = game
    _canon_memo[game.uid] = game
    return game


def _simplest_between(low: Optional[Fraction], high: Optional[Fraction]) -> Fraction:
    if low is None and high is None:
        return Fraction(0)
    if low is None:
        assert high is not None
        if high > 0:
            return Fraction(0)
        return Fraction(math.ceil(high) - 1 if high.denominator == 1 else math.floor(high))
    if high is None:
        if low < 0:
            return Fraction(0)
        return Fraction(math.floor(low) + 1)

    assert low < high
    if low < 0 < high:
        return Fraction(0)
    if low >= 0:
        candidate = Fraction(math.floor(low) + 1)
        if candidate < high:
            return candidate
    else:
        candidate = Fraction(math.ceil(high) - 1)
        if candidate > low:
            return candidate

    scale = 2
    while True:
        numerator = math.floor(low * scale) + 1
        if Fraction(numerator, scale) < high:
            return Fraction(numerator, scale)
        scale *= 2


def number_value(g: Game) -> Optional[Fraction]:
    """The number g equals, or None if g is not a number. g must be canonical."""
    cached = _number_values.get(g.uid)
    if cached is not None or g.uid in _number_values:
        return cached

    result: Optional[Fraction] = None
    if g is ZERO:
        result = Fraction(0)
    elif len(g.lefts) <= 1 and len(g.rights) <= 1:
        low = number_value(g.lefts[0]) if g.lefts else None
        high = number_value(g.rights[0]) if g.rights else None
        if (not g.lefts or low is not None) and (not g.rights or high is not None):
            if low is None or high is None or low < high:
                candidate = _simplest_between(low, high)
                if number_game(candidate) is g:
                    result = candidate

    _number_values[g.uid] = result
    return result


def value_to_game(value: Value) -> Game:
    z, star = value
    n = number_game(z)
    if not star:
        return n
    return canonical(make([n], [n]))


def extract_value(g: Game) -> Value:
    """Read off the (number, star) value of a canonical game.

    Raises AssertionError if g is not of the form z or z*, which for Col
    means a bug somewhere (Conway's theorem guarantees the class).
    """
    z = number_value(g)
    if z is not None:
        return (z, False)
    z = number_value(canonical(add(g, STAR)))
    if z is not None:
        return (z, True)
    raise AssertionError("game value is not a number or number plus star")


def add_values(a: Value, b: Value) -> Value:
    return (a[0] + b[0], a[1] ^ b[1])


def negate_value(a: Value) -> Value:
    return (-a[0], a[1])


def value_of_options(left_values: Sequence[Value], right_values: Sequence[Value]) -> Value:
    key = (tuple(sorted(set(left_values))), tuple(sorted(set(right_values))))
    cached = _options_memo.get(key)
    if cached is not None:
        return cached

    game = make(
        [value_to_game(v) for v in key[0]],
        [value_to_game(v) for v in key[1]],
    )
    result = extract_value(canonical(game))
    _options_memo[key] = result
    return result
