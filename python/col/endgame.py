"""Small-component endgame database for exact Col shape values."""

from __future__ import annotations

import pickle
from fractions import Fraction
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

from col.cgt import Value, add_values, negate_value, value_of_options
from col.core import ColBoard, P1
from col.shapes import (
    BLOCK_P1,
    BLOCK_P2,
    Cells,
    ShapeKey,
    canonical_key,
    live_components,
    play,
)

CACHE_VERSION = 2
CACHE_FILENAME = "cgt_shapes.pkl"
ZERO_VALUE: Value = (Fraction(0), False)
DEFAULT_MAX_COMPONENT_SIZE = 10


class ShapeValueCache:
    def __init__(
        self,
        root: Optional[Path] = None,
        enabled: bool = True,
        max_component_size: int = DEFAULT_MAX_COMPONENT_SIZE,
    ) -> None:
        self.enabled = enabled
        self.max_component_size = max_component_size
        self.root = Path(root) if root is not None else Path("data/tablebases")
        self.cache_path = self.root / CACHE_FILENAME if enabled else None
        self.values: Dict[ShapeKey, Value] = self._load()
        self.loaded_keys: Set[ShapeKey] = set(self.values)
        self.hits = 0
        self.misses = 0

    def _load(self) -> Dict[ShapeKey, Value]:
        if self.cache_path is None or not self.cache_path.exists():
            return {}
        with self.cache_path.open("rb") as handle:
            payload = pickle.load(handle)
        if not isinstance(payload, dict) or payload.get("version") != CACHE_VERSION:
            return {}
        shapes = payload.get("shapes")
        return shapes if isinstance(shapes, dict) else {}

    def save(self) -> None:
        if self.cache_path is None or self.misses == 0:
            return
        self.root.mkdir(parents=True, exist_ok=True)
        payload = {"version": CACHE_VERSION, "shapes": self.values}
        tmp_path = self.cache_path.with_suffix(".pkl.tmp")
        with tmp_path.open("wb") as handle:
            pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
        tmp_path.replace(self.cache_path)

    @staticmethod
    def cells_from_legal_masks(board: ColBoard, legal_p1: int, legal_p2: int) -> Cells:
        cells: Cells = {}
        combined = legal_p1 | legal_p2
        bits = combined
        while bits:
            bit = bits & -bits
            cell = bit.bit_length() - 1
            row, col = divmod(cell, board.n)
            tint = 0
            if not (legal_p1 & bit):
                tint |= BLOCK_P1
            if not (legal_p2 & bit):
                tint |= BLOCK_P2
            cells[(row, col)] = tint
            bits ^= bit
        return cells

    def component_value(self, component: Cells) -> Value:
        key, swapped = canonical_key(component)
        cached = self.values.get(key)
        if cached is not None:
            self.hits += 1
            return negate_value(cached) if swapped else cached

        self.misses += 1
        left_values = []
        right_values = []
        for pos, tint in component.items():
            if not tint & BLOCK_P1:
                left_values.append(self.position_value(play(component, pos, BLOCK_P1)))
            if not tint & BLOCK_P2:
                right_values.append(self.position_value(play(component, pos, BLOCK_P2)))

        value = value_of_options(left_values, right_values)
        self.values[key] = negate_value(value) if swapped else value
        return value

    def position_value(self, cells: Cells) -> Value:
        total = ZERO_VALUE
        for component in live_components(cells):
            total = add_values(total, self.component_value(component))
        return total

    @staticmethod
    def first_player_wins(value: Value) -> bool:
        z, star = value
        return z > 0 or (z == 0 and star)

    def try_evaluate(
        self,
        board: ColBoard,
        legal_p1: int,
        legal_p2: int,
        turn: int,
    ) -> Optional[bool]:
        """Return win/loss if every legal component is small enough; else None."""
        if not self.enabled:
            return None

        components = board.legal_component_masks(legal_p1, legal_p2)
        if not components:
            return False

        total = ZERO_VALUE
        for comp_p1, comp_p2 in components:
            size = board.count_bits(comp_p1 | comp_p2)
            if size > self.max_component_size:
                return None
            cells = self.cells_from_legal_masks(board, comp_p1, comp_p2)
            for component in live_components(cells):
                if len(component) > self.max_component_size:
                    return None
                total = add_values(total, self.component_value(component))

        if turn == P1:
            return self.first_player_wins(total)
        return self.first_player_wins(negate_value(total))
