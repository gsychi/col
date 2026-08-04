#!/usr/bin/env python3
"""Build rooted, replayable P2 strategy DAGs for solved odd 3xn boards.

Unlike the frontier-family miner, this artifact does not quotient away the
middle of a strip.  Every transition is an exact legal-mask state reached from
the empty root.  Leaves are either terminal for P1 or carry a half-turn pairing
strategy that can be checked without trusting the search.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Collection, Iterator, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "python"))

from col.core import ColBoard, P1, P2  # noqa: E402
from col.dfs import DfsSolver  # noqa: E402
from col.tablebase import Tablebase  # noqa: E402


SCHEMA_VERSION = 1
ARTIFACT_KIND = "col-3xn-rooted-strategy-dag"
DEFAULT_BOARDS = ("3x3", "3x5", "3x7", "3x9")


@dataclass(frozen=True, order=True)
class Board:
    m: int
    n: int

    @classmethod
    def parse(cls, text: str) -> "Board":
        try:
            m_text, n_text = text.lower().split("x")
            m, n = int(m_text), int(n_text)
        except (TypeError, ValueError) as exc:
            raise argparse.ArgumentTypeError(
                f"bad board {text!r}; expected 3xN"
            ) from exc
        if m != 3 or n < 3 or n % 2 == 0:
            raise argparse.ArgumentTypeError(
                "strategy DAG builder expects 3xN with odd N >= 3"
            )
        return cls(m, n)

    @property
    def label(self) -> str:
        return f"{self.m}x{self.n}"


def child_legals(
    board: ColBoard,
    p1_legal: int,
    p2_legal: int,
    turn: int,
    cell: int,
) -> tuple[int, int]:
    bit = 1 << cell
    blocked = bit | board.adjacency_masks[cell]
    if turn == P1:
        return p1_legal & ~blocked, p2_legal & ~bit
    return p1_legal & ~bit, p2_legal & ~blocked


def grid_from_masks(
    board: ColBoard,
    p1_legal: int,
    p2_legal: int,
) -> tuple[str, ...]:
    rows = []
    for row in range(board.m):
        chars = []
        for col in range(board.n):
            bit = 1 << (row * board.n + col)
            p1 = bool(p1_legal & bit)
            p2 = bool(p2_legal & bit)
            chars.append("o" if p1 and p2 else "b" if p1 else "w" if p2 else ".")
        rows.append("".join(chars))
    return tuple(rows)


def grid_symmetries(grid: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    horizontal = tuple(row[::-1] for row in grid)
    vertical = tuple(reversed(grid))
    both = tuple(row[::-1] for row in reversed(grid))
    variants = {grid, horizontal, vertical, both}
    if len(grid) == len(grid[0]):
        transpose = tuple(
            "".join(grid[row][col] for row in range(len(grid)))
            for col in range(len(grid[0]))
        )
        variants.update(
            {
                transpose,
                tuple(row[::-1] for row in transpose),
                tuple(reversed(transpose)),
                tuple(row[::-1] for row in reversed(transpose)),
            }
        )
    return tuple(variants)


def canonical_signature(board: ColBoard, p1_legal: int, p2_legal: int) -> str:
    grids = grid_symmetries(grid_from_masks(board, p1_legal, p2_legal))
    return min("/".join(grid) for grid in grids)


def state_id(board: ColBoard, p1_legal: int, p2_legal: int) -> str:
    return hex(board.shadow_key(p1_legal, p2_legal, P1))


def is_half_turn_pairing(board: ColBoard, p1_legal: int, p2_legal: int) -> bool:
    """Whether reflected replies restore the color-swapped legal-mask state."""
    return (
        p1_legal & board.fixed_reflection_mask == 0
        and board.reflect_mask(p1_legal) == p2_legal
    )


def iter_cells(mask: int) -> Iterator[int]:
    while mask:
        bit = mask & -mask
        mask ^= bit
        yield bit.bit_length() - 1


def response_rank(
    *,
    target_id: str,
    target_p1: int,
    target_p2: int,
    response_cell: int,
    known_ids: Collection[str],
    board: ColBoard,
) -> tuple[int, int, int, int]:
    """Prefer reuse, then independently checkable leaves, then small states."""
    if target_id in known_ids:
        category = 0
    elif target_p1 == 0:
        category = 1
    elif is_half_turn_pairing(board, target_p1, target_p2):
        category = 2
    else:
        category = 3
    return (
        category,
        (target_p1 | target_p2).bit_count(),
        response_cell,
        int(target_id, 16),
    )


def build_board_dag(board_spec: Board, *, progress: bool = False) -> dict[str, object]:
    """Solve one board freshly, then extract only the strategy reachable from root."""
    solver = DfsSolver(
        board_spec.m,
        board_spec.n,
        use_symmetry=True,
        tablebase=Tablebase(enabled=False),
        progress=progress,
        mobility_order=True,
    )
    empty_p1_wins = solver.solve()
    if empty_p1_wins:
        raise RuntimeError(f"{board_spec.label} is not a P2 win")

    board = solver.board
    root_p1 = board.all_cells_mask
    root_p2 = board.all_cells_mask
    root = state_id(board, root_p1, root_p2)

    known: dict[str, tuple[int, int]] = {root: (root_p1, root_p2)}
    pending = deque([root])
    nodes: dict[str, dict[str, object]] = {}

    while pending:
        source_id = pending.popleft()
        p1_legal, p2_legal = known[source_id]
        if solver.memo.get(int(source_id, 16)) is not False:
            raise RuntimeError(
                f"{board_spec.label}/{source_id}: source is not memo-proven losing for P1"
            )
        common: dict[str, object] = {
            "id": source_id,
            "p1_legal": hex(p1_legal),
            "p2_legal": hex(p2_legal),
            "signature": canonical_signature(board, p1_legal, p2_legal),
        }

        if p1_legal == 0:
            nodes[source_id] = {
                **common,
                "kind": "terminal",
                "transitions": [],
            }
            continue

        if is_half_turn_pairing(board, p1_legal, p2_legal):
            nodes[source_id] = {
                **common,
                "kind": "half_turn_pairing",
                "transitions": [],
            }
            continue

        transitions = []
        for p1_move in iter_cells(p1_legal):
            child_p1, child_p2 = child_legals(board, p1_legal, p2_legal, P1, p1_move)
            child_key = board.shadow_key(child_p1, child_p2, P2)
            if solver.memo.get(child_key) is not True:
                raise RuntimeError(
                    f"{board_spec.label}/{source_id}: P1 move {p1_move} "
                    "does not have a memo-proven winning P2 child"
                )

            candidates = []
            for p2_response in iter_cells(child_p2):
                target_p1, target_p2 = child_legals(
                    board, child_p1, child_p2, P2, p2_response
                )
                target_id = state_id(board, target_p1, target_p2)
                if solver.memo.get(int(target_id, 16)) is not False:
                    continue
                candidates.append(
                    (
                        response_rank(
                            target_id=target_id,
                            target_p1=target_p1,
                            target_p2=target_p2,
                            response_cell=p2_response,
                            known_ids=known,
                            board=board,
                        ),
                        p2_response,
                        target_id,
                        target_p1,
                        target_p2,
                    )
                )
            if not candidates:
                raise RuntimeError(
                    f"{board_spec.label}/{source_id}: P1 move {p1_move} "
                    "has no memo-proven losing P1 target"
                )

            _, p2_response, target_id, target_p1, target_p2 = min(candidates)
            if target_id not in known:
                known[target_id] = (target_p1, target_p2)
                pending.append(target_id)
            else:
                known_signature = canonical_signature(board, *known[target_id])
                target_signature = canonical_signature(board, target_p1, target_p2)
                if known_signature != target_signature:
                    raise RuntimeError(
                        f"{board_spec.label}: canonical key collision at {target_id}"
                    )
            transitions.append(
                {
                    "p1_move": p1_move,
                    "child": hex(child_key),
                    "p2_response": p2_response,
                    "target": target_id,
                }
            )

        nodes[source_id] = {
            **common,
            "kind": "transitions",
            "transitions": transitions,
        }

    ordered_nodes = sorted(nodes.values(), key=lambda node: int(str(node["id"]), 16))
    kind_counts = {
        kind: sum(node["kind"] == kind for node in ordered_nodes)
        for kind in ("transitions", "terminal", "half_turn_pairing")
    }
    transition_count = sum(len(node["transitions"]) for node in ordered_nodes)
    return {
        "board": board_spec.label,
        "root": root,
        "empty_p1_wins": empty_p1_wins,
        "solver": {
            "engine": "python.col.dfs.DfsSolver",
            "fresh_no_tablebase": True,
            "mobility_order": True,
            "states_searched": solver.stats.states_searched,
            "memo_entries": len(solver.memo),
            "pairing_certificate_hits": solver.stats.pairing_certificate_hits,
        },
        "summary": {
            "nodes": len(ordered_nodes),
            "transition_nodes": kind_counts["transitions"],
            "terminal_leaves": kind_counts["terminal"],
            "pairing_leaves": kind_counts["half_turn_pairing"],
            "transitions": transition_count,
        },
        "nodes": ordered_nodes,
    }


def build_artifact(
    boards: Sequence[Board],
    *,
    progress: bool = False,
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": ARTIFACT_KIND,
        "boards": [build_board_dag(board, progress=progress) for board in boards],
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--boards",
        nargs="+",
        type=Board.parse,
        default=[Board.parse(text) for text in DEFAULT_BOARDS],
        help="Odd 3xN boards (default: 3x3 3x5 3x7 3x9).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "reports" / "3xn-rooted-strategy-dag.json",
    )
    parser.add_argument("--progress", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    artifact = build_artifact(args.boards, progress=args.progress)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for board in artifact["boards"]:
        summary = board["summary"]
        print(
            f"{board['board']}: {summary['nodes']:,} nodes, "
            f"{summary['transitions']:,} transitions, "
            f"{summary['pairing_leaves']:,} pairing leaves"
        )
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
