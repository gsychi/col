"""Discover the smallest one-column contracts used in dx_boundary_obstruction.md.

The output is a finite catalogue, not an arbitrary-width game evaluation.
Run directly to regenerate dx_interface_contracts.json.  The separate verifier
uses short-game order, rather than this alternating outcome evaluator.
"""
from functools import lru_cache
from fractions import Fraction
from itertools import combinations_with_replacement
from pathlib import Path
import json


PATTERNS = dict(D="obwbo", U="wbobo", V="bwbob", X="bowob", R="wobob", J="owobo")
ALL = 31
NEIGHBORS = [sum(1 << j for j in (i - 1, i + 1) if 0 <= j < 5) for i in range(5)]


def masks(pattern):
    return (sum(1 << i for i, x in enumerate(pattern) if x in "ob"),
            sum(1 << i for i, x in enumerate(pattern) if x in "ow"))


def pattern(a, b):
    return "".join("o" if a >> i & b >> i & 1 else "b" if a >> i & 1 else
                   "w" if b >> i & 1 else "." for i in range(5))


@lru_cache(None)
def first_wins(a, b, q, star):
    """Current player wins in the path game plus dyadic q plus star."""
    for i in range(5):
        bit = 1 << i
        if a & bit and not first_wins(b & ~bit, a & ~(bit | NEIGHBORS[i]), -q, star):
            return True
    if q.denominator > 1:
        left = q - Fraction(1, q.denominator)
    elif q > 0:
        left = q - 1
    else:
        left = None
    if left is not None and not first_wins(b, a, -left, star):
        return True
    if star and not first_wins(b, a, -q, False):
        return True
    return False


def exact_value(a, b):
    for numerator in range(-16, 17):
        q = Fraction(numerator, 4)
        for star in (False, True):
            if not first_wins(a, b, -q, star) and not first_wins(b, a, q, star):
                return dict(number=str(q), star=star)
    raise AssertionError((a, b))


def catalogue():
    rows = []
    for opening, candidates in [(0, "UR"), (1, "VJ"), (2, "DX")]:
        for left, right in combinations_with_replacement(candidates, 2):
            left_a, left_b = masks(PATTERNS[left])
            right_a, right_b = masks(PATTERNS[right])
            # Neighbouring side columns lose Blue only in the opening row.
            assert (ALL & ~(1 << opening)) & ~(left_a & right_a) == 0
            for reply in [None] + [i for i in range(5) if i != opening]:
                a = ALL & ~((1 << opening) | NEIGHBORS[opening])
                b = ALL & ~(1 << opening)
                if reply is not None:
                    # A same-column White reply forbids White at that row on
                    # both adjacent side columns.
                    if (left_b | right_b) & (1 << reply):
                        continue
                    a &= ~(1 << reply)
                    b &= ~((1 << reply) | NEIGHBORS[reply])
                # Largest White support safe on both seams is optimal for
                # this fixed pair of near-side endpoint patterns.
                b &= ~(left_b | right_b)
                rows.append(dict(opening_row=opening, reply_row=reply,
                                 near_left=left, near_right=right,
                                 separator=pattern(a, b),
                                 left_white_support=[i for i in range(5) if left_b >> i & 1],
                                 right_white_support=[i for i in range(5) if right_b >> i & 1],
                                 separator_white_support=[i for i in range(5) if b >> i & 1],
                                 value=exact_value(a, b)))
    return dict(schema=1, patterns=PATTERNS, scope="neutral opening column; same-column reply only", contracts=rows)


if __name__ == "__main__":
    result = catalogue()
    output = Path(__file__).with_suffix(".json")
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Wrote {len(result['contracts'])} contracts to {output.name}")
