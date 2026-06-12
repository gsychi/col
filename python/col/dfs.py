#!/usr/bin/env python3
"""DFS/minimax solver for the 2D m x n Col placement game."""

from __future__ import annotations

import sys
import time
from typing import Dict, Iterator, List, Optional, Tuple

from col.cli import main_for_solver
from col.core import ColBoard, P1, P2, SearchStats, StateKey
from col.endgame import ShapeValueCache
from col.tablebase import Tablebase


class DfsSolver:
    name = "DFS"

    def __init__(
        self,
        m: int,
        n: int,
        use_symmetry: bool = True,
        tablebase: Optional[Tablebase] = None,
        progress: bool = False,
        checkpoint_interval: int = 0,
        prefer_reflection: bool = False,
        mobility_order: bool = False,
    ) -> None:
        self.board = ColBoard(m, n, use_symmetry=use_symmetry)
        self.tablebase = tablebase or Tablebase(enabled=False)
        self.memo: Dict[StateKey, bool] = self.tablebase.load(self.board)
        self.tablebase_keys = set(self.memo)
        self.track_tablebase_hits = bool(self.tablebase_keys)
        self.stats = SearchStats()
        self.progress = progress
        self._progress_started_at: Optional[float] = None
        self._progress_last_report_at = 0.0
        self._progress_report_interval = 0.25
        self.checkpoint_interval = checkpoint_interval
        self.pending_entries: Dict[StateKey, bool] = {}
        self.prefer_reflection = prefer_reflection
        self.mobility_order = mobility_order
        self.endgame = ShapeValueCache(
            root=self.tablebase.root if self.tablebase.enabled else None,
            enabled=self.tablebase.enabled,
        )

    def solve(self) -> bool:
        if self.progress:
            self._report_progress(force=True, prefix="solving")
        result = self.is_winning(0, 0, P1)
        if self.stats.states_searched:
            if self.progress:
                self._report_progress(force=True, final=True)
            if self.checkpoint_interval:
                self.flush_checkpoint()
            else:
                self.tablebase.save(self.board, self.memo)
            self.endgame.save()
        elif self.progress:
            self._report_progress(force=True, final=True)
        return result

    def remember(self, key: StateKey, result: bool) -> None:
        existing = self.memo.get(key)
        if existing is not None:
            if existing != result:
                raise RuntimeError(f"conflicting result for key {key}")
            return

        self.memo[key] = result
        if self.checkpoint_interval and key not in self.tablebase_keys:
            self.pending_entries[key] = result
            if len(self.pending_entries) >= self.checkpoint_interval:
                self.flush_checkpoint()

    def flush_checkpoint(self) -> None:
        if not self.pending_entries:
            return
        self.tablebase.append(self.board, self.pending_entries)
        self.pending_entries.clear()

    def _report_progress(
        self,
        *,
        force: bool = False,
        final: bool = False,
        prefix: str = "states searched",
    ) -> None:
        if not self.progress:
            return

        now = time.perf_counter()
        if self._progress_started_at is None:
            self._progress_started_at = now
        if not force and not final and now - self._progress_last_report_at < self._progress_report_interval:
            return

        self._progress_last_report_at = now
        elapsed = now - self._progress_started_at
        searched = self.stats.states_searched
        rate = searched / elapsed if elapsed > 0 else 0.0
        line = (
            f"\r{prefix}: {searched:,} | "
            f"memo: {len(self.memo):,} | "
            f"cert hits: {self.stats.pairing_certificate_hits:,} | "
            f"{rate:,.0f}/s | "
            f"{elapsed:.1f}s"
        )
        sys.stderr.write(line)
        sys.stderr.flush()
        if final:
            sys.stderr.write("\n")
            sys.stderr.flush()

    def is_winning(
        self,
        p1_mask: int,
        p2_mask: int,
        turn: int,
        last_move: Optional[int] = None,
    ) -> bool:
        board = self.board
        p1_legal = board.legal_move_mask(p1_mask, p2_mask, P1)
        p2_legal = board.legal_move_mask(p1_mask, p2_mask, P2)
        key = board.shadow_key(p1_legal, p2_legal, turn)
        if board.has_even_dimension and p1_mask == 0 and p2_mask == 0 and turn == P1:
            self.remember(key, False)
            return False
        return self._is_winning_from_key(
            p1_mask, p2_mask, turn, key, p1_legal, p2_legal, last_move
        )

    def _is_winning_from_key(
        self,
        p1_mask: int,
        p2_mask: int,
        turn: int,
        key: StateKey,
        p1_legal: int,
        p2_legal: int,
        last_move: Optional[int],
    ) -> bool:
        board = self.board
        memo = self.memo
        cached = memo.get(key)
        if cached is not None:
            self.stats.memo_hits += 1
            if self.track_tablebase_hits and key in self.tablebase_keys:
                self.stats.tablebase_hits += 1
            return cached

        self.stats.states_searched += 1
        if self.progress:
            self._report_progress()

        legal_mask = p1_legal if turn == P1 else p2_legal

        if legal_mask == 0:
            self.remember(key, False)
            return False

        quick = self.endgame.try_evaluate(board, p1_legal, p2_legal, turn)
        if quick is not None:
            self.remember(key, quick)
            return quick

        if self.has_reflection_pairing_certificate(p1_mask, p2_mask, turn, legal_mask):
            self.stats.pairing_certificate_hits += 1
            self.remember(key, False)
            return False

        next_turn = P2 if turn == P1 else P1
        preferred_cell = self.preferred_cell(turn, legal_mask, last_move)
        ordered_moves = (
            self.mobility_ordered_moves(p1_mask, p2_mask, turn, legal_mask, preferred_cell)
            if self.mobility_order
            else self.ordered_moves(legal_mask, preferred_cell)
        )
        for child_cell, bit in ordered_moves:
            if turn == P1:
                child_p1 = p1_mask | bit
                child_p2 = p2_mask
            else:
                child_p1 = p1_mask
                child_p2 = p2_mask | bit

            child_occupied = child_p1 | child_p2
            child_p1_legal = board.all_cells_mask & ~(
                child_occupied | board._neighbor_union(child_p1)
            )
            child_p2_legal = board.all_cells_mask & ~(
                child_occupied | board._neighbor_union(child_p2)
            )
            child_key = board.shadow_key(child_p1_legal, child_p2_legal, next_turn)
            cached_child = memo.get(child_key)
            if cached_child is not None:
                self.stats.memo_hits += 1
                if self.track_tablebase_hits and child_key in self.tablebase_keys:
                    self.stats.tablebase_hits += 1
                if not cached_child:
                    self.remember(key, True)
                    return True
                continue

            child_legal_mask = child_p1_legal if next_turn == P1 else child_p2_legal
            if child_legal_mask == 0:
                self.remember(child_key, False)
                self.remember(key, True)
                return True

            opponent_wins = self._is_winning_from_key(
                child_p1,
                child_p2,
                next_turn,
                child_key,
                child_p1_legal,
                child_p2_legal,
                child_cell,
            )

            if not opponent_wins:
                self.remember(key, True)
                return True

        self.remember(key, False)
        return False

    def has_reflection_pairing_certificate(
        self,
        p1_mask: int,
        p2_mask: int,
        turn: int,
        legal_mask: int,
    ) -> bool:
        board = self.board
        fixed_mask = board.fixed_reflection_mask
        if legal_mask & fixed_mask:
            return False

        if turn == P1:
            actor_mask = p1_mask
            responder_mask = p2_mask
        else:
            actor_mask = p2_mask
            responder_mask = p1_mask

        nonfixed_mask = ~fixed_mask
        actor_nonfixed = actor_mask & nonfixed_mask
        responder_nonfixed = responder_mask & nonfixed_mask
        if board.reflect_mask(actor_nonfixed) != responder_nonfixed:
            return False

        occupied = p1_mask | p2_mask
        responder_legal_mask = board.all_cells_mask & ~(
            occupied | board._neighbor_union(responder_mask)
        )

        remaining = legal_mask
        while remaining:
            move_bit = remaining & -remaining
            cell = move_bit.bit_length() - 1
            response_bit = board.reflected_bit_masks[cell]
            if response_bit == move_bit or responder_legal_mask & response_bit == 0:
                return False
            remaining ^= move_bit

        return True

    def preferred_cell(
        self,
        turn: int,
        legal_mask: int,
        last_move: Optional[int],
    ) -> Optional[int]:
        board = self.board
        if turn == P1 and board.center_cell is not None:
            center_bit = 1 << board.center_cell
            if legal_mask & center_bit:
                return board.center_cell

        if self.prefer_reflection and turn == P2 and last_move is not None:
            reflected_cell = board.reflected_cells[last_move]
            reflected_bit = 1 << reflected_cell
            if legal_mask & reflected_bit:
                return reflected_cell

        return None

    def ordered_moves(
        self,
        legal_mask: int,
        preferred_cell: Optional[int],
    ) -> Iterator[Tuple[int, int]]:
        if preferred_cell is not None:
            yield preferred_cell, 1 << preferred_cell

        for cell, bit in self.board.move_order_pairs:
            if cell == preferred_cell or legal_mask & bit == 0:
                continue
            yield cell, bit

    def mobility_ordered_moves(
        self,
        p1_mask: int,
        p2_mask: int,
        turn: int,
        legal_mask: int,
        preferred_cell: Optional[int],
    ) -> Iterator[Tuple[int, int]]:
        if preferred_cell is not None:
            yield preferred_cell, 1 << preferred_cell

        scored_moves: List[Tuple[Tuple[int, int, int, int, int, int], int, int]] = []
        for order_index, (cell, bit) in enumerate(self.board.move_order_pairs):
            if cell == preferred_cell or legal_mask & bit == 0:
                continue
            if turn == P1:
                child_p1 = p1_mask | bit
                child_p2 = p2_mask
            else:
                child_p1 = p1_mask
                child_p2 = p2_mask | bit
            scored_moves.append(
                (
                    self.mobility_score(child_p1, child_p2, turn, cell)
                    + (order_index,),
                    cell,
                    bit,
                )
            )

        for _, cell, bit in sorted(scored_moves):
            yield cell, bit

    def mobility_score(
        self,
        p1_mask: int,
        p2_mask: int,
        turn: int,
        cell: int,
    ) -> Tuple[int, int, int, int, int, int]:
        board = self.board
        p1_legal = board.legal_move_mask(p1_mask, p2_mask, P1)
        p2_legal = board.legal_move_mask(p1_mask, p2_mask, P2)
        if turn == P1:
            own_legal = p1_legal
            opponent_legal = p2_legal
        else:
            own_legal = p2_legal
            opponent_legal = p1_legal

        shared_legal = own_legal & opponent_legal
        opponent_only = opponent_legal & ~own_legal
        return (
            0 if opponent_legal == 0 else 1,
            -board.center_distances[cell],
            -board.count_bits(own_legal),
            board.count_bits(opponent_legal),
            board.count_bits(shared_legal),
            board.count_bits(opponent_only),
        )

    def optimal_first_move(self) -> Optional[int]:
        for cell in self.board.legal_moves(0, 0, P1):
            if not self.is_winning(1 << cell, 0, P2, last_move=cell):
                return cell
        return None


def main() -> int:
    return main_for_solver(DfsSolver)


if __name__ == "__main__":
    sys.exit(main())
