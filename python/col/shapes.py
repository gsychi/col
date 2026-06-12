"""Component extraction and canonicalization for the CGT Col solver.

A position is a dict mapping (row, col) -> tint, where the tint records
which players are blocked from a free cell (adjacent to their own stone).
Stones themselves are not part of the dict: their entire influence is the
tint shadow they cast, which is why distinct stone arrangements with the
same shadow collapse to one shape.
"""

from __future__ import annotations

from typing import Dict, Iterator, List, Tuple

BLOCK_P1 = 1
BLOCK_P2 = 2
DEAD = BLOCK_P1 | BLOCK_P2

Pos = Tuple[int, int]
Cells = Dict[Pos, int]

ShapeKey = Tuple[Tuple[int, int, int], ...]

_TRANSFORMS = (
    lambda r, c: (r, c),
    lambda r, c: (-r, c),
    lambda r, c: (r, -c),
    lambda r, c: (-r, -c),
    lambda r, c: (c, r),
    lambda r, c: (-c, r),
    lambda r, c: (c, -r),
    lambda r, c: (-c, -r),
)


def initial_cells(m: int, n: int) -> Cells:
    return {(row, col): 0 for row in range(m) for col in range(n)}


def cells_from_masks(m: int, n: int, p1_mask: int, p2_mask: int) -> Cells:
    """Build the tinted free-cell dict for an arbitrary mask position."""
    occupied = p1_mask | p2_mask
    cells: Cells = {}
    for row in range(m):
        for col in range(n):
            bit = 1 << (row * n + col)
            if occupied & bit:
                continue
            tint = 0
            for nr, nc in _neighbors((row, col)):
                if 0 <= nr < m and 0 <= nc < n:
                    nbit = 1 << (nr * n + nc)
                    if p1_mask & nbit:
                        tint |= BLOCK_P1
                    if p2_mask & nbit:
                        tint |= BLOCK_P2
            cells[(row, col)] = tint
    return cells


def _neighbors(pos: Pos) -> Iterator[Pos]:
    row, col = pos
    yield row - 1, col
    yield row + 1, col
    yield row, col - 1
    yield row, col + 1


def play(cells: Cells, pos: Pos, player_block: int) -> Cells:
    """Place a stone for the player whose block bit is player_block."""
    result = dict(cells)
    del result[pos]
    for neighbor in _neighbors(pos):
        tint = result.get(neighbor)
        if tint is not None:
            result[neighbor] = tint | player_block
    return result


def live_components(cells: Cells) -> List[Cells]:
    """Drop dead cells, then split into 4-connected components."""
    live = {pos: tint for pos, tint in cells.items() if tint != DEAD}
    components: List[Cells] = []
    remaining = set(live)
    while remaining:
        seed = remaining.pop()
        component = {seed: live[seed]}
        stack = [seed]
        while stack:
            for neighbor in _neighbors(stack.pop()):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    component[neighbor] = live[neighbor]
                    stack.append(neighbor)
        components.append(component)
    return components


def _swap_tint(tint: int) -> int:
    return ((tint & BLOCK_P1) << 1) | ((tint & BLOCK_P2) >> 1)


_key_cache: Dict[frozenset, Tuple[ShapeKey, bool]] = {}
_KEY_CACHE_LIMIT = 4_000_000


def canonical_key(cells: Cells) -> Tuple[ShapeKey, bool]:
    """Canonical shape key under translation, the 8 dihedral transforms,
    and color swap.

    Cells are packed as ((row << 6 | col) << 2) | tint, so the key is a
    sorted tuple of small ints (fast comparison, compact pickling).

    Returns (key, swapped). If swapped is True, the cached value for the
    key is the value of the color-swapped shape, i.e. the negative of this
    shape's value.
    """
    cache_key = frozenset(cells.items())
    cached = _key_cache.get(cache_key)
    if cached is not None:
        return cached

    items = list(cells.items())
    tints = [tint for _, tint in items]
    swapped_tints = [_swap_tint(tint) for tint in tints]

    best_key: ShapeKey = None  # type: ignore[assignment]
    best_swapped = False
    for transform in _TRANSFORMS:
        points = [transform(r, c) for (r, c), _ in items]
        min_r = min(p[0] for p in points)
        min_c = min(p[1] for p in points)
        bases = [((r - min_r) << 6 | (c - min_c)) << 2 for r, c in points]
        for tint_list, swapped in ((tints, False), (swapped_tints, True)):
            key = tuple(sorted(map(int.__or__, bases, tint_list)))
            if best_key is None or key < best_key:
                best_key = key
                best_swapped = swapped

    result = (best_key, best_swapped)
    if len(_key_cache) >= _KEY_CACHE_LIMIT:
        _key_cache.clear()
    _key_cache[cache_key] = result
    return result
