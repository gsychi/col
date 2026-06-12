"""Shared board logic for the 2D Col solvers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple


P1 = 0
P2 = 1
StateKey = int


@dataclass
class SearchStats:
    states_searched: int = 0
    memo_hits: int = 0
    tablebase_hits: int = 0
    pairing_certificate_hits: int = 0


class ColBoard:
    def __init__(self, m: int, n: int, use_symmetry: bool = True) -> None:
        if m <= 0 or n <= 0:
            raise ValueError("m and n must be positive")

        self.m = m
        self.n = n
        self.num_cells = m * n
        self.all_cells_mask = (1 << self.num_cells) - 1
        self.use_symmetry = use_symmetry
        self.has_even_dimension = m % 2 == 0 or n % 2 == 0

        self.adjacency_masks = self._build_adjacency_masks()
        self.center_distances = self._build_center_distances()
        self.move_order = self._build_move_order()
        self.move_order_bits = [1 << cell for cell in self.move_order]
        self.move_order_pairs = [(cell, 1 << cell) for cell in self.move_order]
        self.center_cell: Optional[int] = (
            self._cell(m // 2, n // 2) if m % 2 == 1 and n % 2 == 1 else None
        )
        self.reflected_cells = self._build_reflected_cells()
        self.reflected_bit_masks = tuple(1 << cell for cell in self.reflected_cells)
        self.fixed_reflection_mask = self._build_fixed_reflection_mask()
        self.reflected_mask_cache: Dict[int, int] = {0: 0}
        self.transforms = self._build_symmetry_transforms() if use_symmetry else []
        self.transform_caches: List[Dict[int, int]] = [
            {0: 0} for _ in self.transforms
        ]
        self.neighbor_union_cache: Dict[int, int] = {0: 0}
        self.canonical_pair_cache: Dict[Tuple[int, int], Tuple[int, int]] = {}
        self.canonical_legal_pair_cache: Dict[int, Tuple[int, int]] = {}
        self.transformed_bit_masks: List[Tuple[int, ...]] = [
            tuple(1 << transform[cell] for cell in range(self.num_cells))
            for transform in self.transforms
        ]

        # Tall boards (m > n) are the transpose of a wide n x m board. Keys and
        # tablebase files are normalized to the wide orientation so e.g. 9x3
        # and 3x9 share one tablebase; gameplay and display keep this board's
        # own orientation.
        self.storage_m = m
        self.storage_n = n
        self._storage_board: Optional["ColBoard"] = None
        if use_symmetry and m > n:
            self._storage_board = ColBoard(n, m, use_symmetry=True)
            self.storage_m = n
            self.storage_n = m
            self._to_storage_bits = tuple(
                1 << ((cell % n) * m + cell // n) for cell in range(self.num_cells)
            )
            self._from_storage_bits = tuple(
                1 << ((cell % m) * n + cell // m) for cell in range(self.num_cells)
            )
            self._to_storage_cache: Dict[int, int] = {0: 0}
            self._from_storage_cache: Dict[int, int] = {0: 0}

    def pack_key(self, p1_mask: int, p2_mask: int, turn: int) -> StateKey:
        return (p1_mask << (self.num_cells + 1)) | (p2_mask << 1) | turn

    def unpack_key(self, key: StateKey) -> Tuple[int, int, int]:
        turn = key & 1
        p2_mask = (key >> 1) & self.all_cells_mask
        p1_mask = (key >> (self.num_cells + 1)) & self.all_cells_mask
        if self._storage_board is not None:
            p1_mask = self._permute_mask(p1_mask, self._from_storage_bits, self._from_storage_cache)
            p2_mask = self._permute_mask(p2_mask, self._from_storage_bits, self._from_storage_cache)
        return p1_mask, p2_mask, turn

    def start_key(self) -> StateKey:
        return self.cache_key(0, 0, P1)

    def cache_key(self, p1_mask: int, p2_mask: int, turn: int) -> StateKey:
        if self._storage_board is not None:
            return self._storage_board.cache_key(
                self._permute_mask(p1_mask, self._to_storage_bits, self._to_storage_cache),
                self._permute_mask(p2_mask, self._to_storage_bits, self._to_storage_cache),
                turn,
            )
        if not self.transforms:
            return self.pack_key(p1_mask, p2_mask, turn)

        p1_mask, p2_mask = self._canonical_pair(p1_mask, p2_mask)
        return self.pack_key(p1_mask, p2_mask, turn)

    def shadow_key(self, legal_p1: int, legal_p2: int, turn: int) -> StateKey:
        """Memo key from both players' legal masks (outcome depends only on these)."""
        if self._storage_board is not None:
            return self._storage_board.shadow_key(
                self._permute_mask(legal_p1, self._to_storage_bits, self._to_storage_cache),
                self._permute_mask(legal_p2, self._to_storage_bits, self._to_storage_cache),
                turn,
            )

        if not self.transforms:
            return self.pack_key(legal_p1, legal_p2, turn)

        legal_p1, legal_p2 = self._canonical_legal_pair(legal_p1, legal_p2)
        return self.pack_key(legal_p1, legal_p2, turn)

    def shadow_key_from_stones(self, p1_mask: int, p2_mask: int, turn: int) -> StateKey:
        return self.shadow_key(
            self.legal_move_mask(p1_mask, p2_mask, P1),
            self.legal_move_mask(p1_mask, p2_mask, P2),
            turn,
        )

    def _permute_mask(
        self,
        mask: int,
        bit_masks: Tuple[int, ...],
        cache: Dict[int, int],
    ) -> int:
        cached = cache.get(mask)
        if cached is not None:
            return cached

        lsb = mask & -mask
        rest = mask ^ lsb
        rest_permuted = cache.get(rest)
        if rest_permuted is None:
            rest_permuted = self._permute_mask(rest, bit_masks, cache)
        permuted = rest_permuted | bit_masks[lsb.bit_length() - 1]
        cache[mask] = permuted
        return permuted

    def _canonical_pair(self, p1_mask: int, p2_mask: int) -> Tuple[int, int]:
        cached = self.canonical_pair_cache.get((p1_mask, p2_mask))
        if cached is not None:
            return cached

        best = (p1_mask, p2_mask)
        for index in range(1, len(self.transforms)):
            transformed_p1 = self._transform_mask(p1_mask, index)
            if transformed_p1 > best[0]:
                continue

            transformed_p2 = self._transform_mask(p2_mask, index)
            if transformed_p1 < best[0] or transformed_p2 < best[1]:
                best = (transformed_p1, transformed_p2)
        self.canonical_pair_cache[(p1_mask, p2_mask)] = best
        return best

    def _canonical_legal_pair(self, legal_p1: int, legal_p2: int) -> Tuple[int, int]:
        pair_key = (legal_p1 << self.num_cells) | legal_p2
        cached = self.canonical_legal_pair_cache.get(pair_key)
        if cached is not None:
            return cached

        best = (legal_p1, legal_p2)
        for index in range(1, len(self.transforms)):
            transformed_p1 = self._transform_mask(legal_p1, index)
            if transformed_p1 > best[0]:
                continue

            transformed_p2 = self._transform_mask(legal_p2, index)
            if transformed_p1 < best[0] or transformed_p2 < best[1]:
                best = (transformed_p1, transformed_p2)
        self.canonical_legal_pair_cache[pair_key] = best
        return best

    def legal_move_mask(self, p1_mask: int, p2_mask: int, turn: int) -> int:
        occupied = p1_mask | p2_mask
        player_mask = p1_mask if turn == P1 else p2_mask
        blocked = occupied | self._neighbor_union(player_mask)
        return self.all_cells_mask & ~blocked

    def strip_isolated_spares(self, legal_p1: int, legal_p2: int) -> Tuple[int, int]:
        """Remove isolated legal cells from memo keys when a non-isolated core exists."""
        combined = legal_p1 | legal_p2
        isolated = 0
        bits = combined
        while bits:
            bit = bits & -bits
            cell = bit.bit_length() - 1
            if self.adjacency_masks[cell] & combined == 0:
                isolated |= bit
            bits ^= bit
        if isolated == combined:
            return legal_p1, legal_p2
        return legal_p1 & ~isolated, legal_p2 & ~isolated

    def legal_component_masks(self, legal_p1: int, legal_p2: int) -> List[Tuple[int, int]]:
        """Split the legal region into 4-connected components as mask pairs."""
        combined = legal_p1 | legal_p2
        components: List[Tuple[int, int]] = []
        remaining = combined
        while remaining:
            seed_bit = remaining & -remaining
            stack = [seed_bit]
            comp = 0
            remaining ^= seed_bit
            comp |= seed_bit
            while stack:
                bit = stack.pop()
                cell = bit.bit_length() - 1
                neighbors = self.adjacency_masks[cell] & combined
                while neighbors:
                    neighbor_bit = neighbors & -neighbors
                    neighbors ^= neighbor_bit
                    if neighbor_bit & comp:
                        continue
                    if neighbor_bit & remaining:
                        remaining ^= neighbor_bit
                        comp |= neighbor_bit
                        stack.append(neighbor_bit)
            components.append((legal_p1 & comp, legal_p2 & comp))
        return components

    @staticmethod
    def count_bits(mask: int) -> int:
        return bin(mask).count("1")

    def legal_moves(self, p1_mask: int, p2_mask: int, turn: int) -> List[int]:
        legal_mask = self.legal_move_mask(p1_mask, p2_mask, turn)
        return [cell for cell in self.move_order if legal_mask & (1 << cell)]

    def child_key(self, p1_mask: int, p2_mask: int, turn: int, bit: int) -> StateKey:
        if turn == P1:
            return self.cache_key(p1_mask | bit, p2_mask, P2)
        return self.cache_key(p1_mask, p2_mask | bit, P1)

    def ordered_child_keys(self, p1_mask: int, p2_mask: int, turn: int) -> List[StateKey]:
        legal_mask = self.legal_move_mask(p1_mask, p2_mask, turn)
        return [
            self.child_key(p1_mask, p2_mask, turn, bit)
            for bit in self.move_order_bits
            if legal_mask & bit
        ]

    def format_cell(self, cell: int) -> str:
        row = cell // self.n + 1
        col = cell % self.n + 1
        return f"row {row}, col {col}"

    def _neighbor_union(self, mask: int) -> int:
        cached = self.neighbor_union_cache.get(mask)
        if cached is not None:
            return cached

        lsb = mask & -mask
        rest = mask ^ lsb
        cell = lsb.bit_length() - 1
        rest_union = self.neighbor_union_cache.get(rest)
        if rest_union is None:
            rest_union = self._neighbor_union(rest)
        union = rest_union | self.adjacency_masks[cell]
        self.neighbor_union_cache[mask] = union
        return union

    def _transform_mask(self, mask: int, transform_index: int) -> int:
        cache = self.transform_caches[transform_index]
        cached = cache.get(mask)
        if cached is not None:
            return cached

        lsb = mask & -mask
        rest = mask ^ lsb
        rest_transformed = cache.get(rest)
        if rest_transformed is None:
            rest_transformed = self._transform_mask(rest, transform_index)
        cell = lsb.bit_length() - 1
        bit_masks = self.transformed_bit_masks[transform_index]
        transformed = rest_transformed | bit_masks[cell]
        cache[mask] = transformed
        return transformed

    def reflect_mask(self, mask: int) -> int:
        cached = self.reflected_mask_cache.get(mask)
        if cached is not None:
            return cached

        lsb = mask & -mask
        rest = mask ^ lsb
        rest_reflected = self.reflected_mask_cache.get(rest)
        if rest_reflected is None:
            rest_reflected = self.reflect_mask(rest)
        cell = lsb.bit_length() - 1
        reflected = rest_reflected | self.reflected_bit_masks[cell]
        self.reflected_mask_cache[mask] = reflected
        return reflected

    def _build_adjacency_masks(self) -> List[int]:
        masks: List[int] = []
        for row in range(self.m):
            for col in range(self.n):
                mask = 0
                for next_row, next_col in (
                    (row - 1, col),
                    (row + 1, col),
                    (row, col - 1),
                    (row, col + 1),
                ):
                    if 0 <= next_row < self.m and 0 <= next_col < self.n:
                        mask |= 1 << self._cell(next_row, next_col)
                masks.append(mask)
        return masks

    def _build_move_order(self) -> List[int]:
        return sorted(
            range(self.num_cells),
            key=lambda cell: (
                -self.center_distances[cell],
                cell,
            ),
        )

    def _build_center_distances(self) -> Tuple[int, ...]:
        return tuple(
            abs(2 * (cell // self.n) - (self.m - 1))
            + abs(2 * (cell % self.n) - (self.n - 1))
            for cell in range(self.num_cells)
        )

    def _build_symmetry_transforms(self) -> List[Tuple[int, ...]]:
        transforms = [
            self._transform_from_function(lambda row, col: (row, col)),
            self._transform_from_function(lambda row, col: (self.m - 1 - row, col)),
            self._transform_from_function(lambda row, col: (row, self.n - 1 - col)),
            self._transform_from_function(
                lambda row, col: (self.m - 1 - row, self.n - 1 - col)
            ),
        ]

        if self.m == self.n:
            size = self.m
            transforms.extend(
                [
                    self._transform_from_function(
                        lambda row, col: (col, size - 1 - row)
                    ),
                    self._transform_from_function(
                        lambda row, col: (size - 1 - col, row)
                    ),
                    self._transform_from_function(lambda row, col: (col, row)),
                    self._transform_from_function(
                        lambda row, col: (size - 1 - col, size - 1 - row)
                    ),
                ]
            )

        return self._dedupe_transforms(transforms)

    def _build_reflected_cells(self) -> Tuple[int, ...]:
        return tuple(
            self._cell(self.m - 1 - row, self.n - 1 - col)
            for row in range(self.m)
            for col in range(self.n)
        )

    def _build_fixed_reflection_mask(self) -> int:
        mask = 0
        for cell, reflected_cell in enumerate(self.reflected_cells):
            if cell == reflected_cell:
                mask |= 1 << cell
        return mask

    def _transform_from_function(
        self, fn: Callable[[int, int], Tuple[int, int]]
    ) -> Tuple[int, ...]:
        return tuple(
            self._cell(*fn(row, col))
            for row in range(self.m)
            for col in range(self.n)
        )

    @staticmethod
    def _dedupe_transforms(
        transforms: Sequence[Tuple[int, ...]]
    ) -> List[Tuple[int, ...]]:
        unique: List[Tuple[int, ...]] = []
        seen = set()
        for transform in transforms:
            if transform not in seen:
                seen.add(transform)
                unique.append(transform)
        return unique

    def _cell(self, row: int, col: int) -> int:
        return row * self.n + col
