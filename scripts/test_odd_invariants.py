#!/usr/bin/env python3
"""Falsify candidate symmetry/cancellation invariants on solved odd boards."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "python"))

from col.boards import BoardSpec, odd_boards  # noqa: E402
from col.cgt import negate_value  # noqa: E402
from col.core import ColBoard, P1  # noqa: E402
from col.dfs import DfsSolver  # noqa: E402
from col.endgame import ShapeValueCache, ZERO_VALUE  # noqa: E402
from col.shapes import canonical_key, live_components  # noqa: E402
from col.tablebase import Tablebase  # noqa: E402


@dataclass
class BoardResult:
    board: str
    states: int
    seconds: float
    naive_candidates: int
    naive_counterexamples: int
    component_candidates: int
    component_counterexamples: int
    skipped: str | None = None


@dataclass
class Counterexample:
    board: str
    key: str
    turn: str
    side_to_move_wins: bool
    p1_legal: str
    p2_legal: str
    reason: str


def parse_board(text: str) -> BoardSpec:
    try:
        board = BoardSpec.parse(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if board.m % 2 == 0 or board.n % 2 == 0 or board.m == 1:
        raise argparse.ArgumentTypeError("expected a non-path odd-by-odd board")
    return board


def vertical_reflect_mask(board: ColBoard, mask: int) -> int:
    reflected = 0
    while mask:
        bit = mask & -mask
        mask ^= bit
        cell = bit.bit_length() - 1
        row, col = divmod(cell, board.n)
        reflected |= 1 << (row * board.n + (board.n - 1 - col))
    return reflected


def middle_column_mask(board: ColBoard) -> int:
    col = board.n // 2
    return sum(1 << (row * board.n + col) for row in range(board.m))


def naive_middle_column_zero(
    board: ColBoard,
    cache: ShapeValueCache,
    p1_legal: int,
    p2_legal: int,
) -> bool:
    middle = middle_column_mask(board)
    wings = board.all_cells_mask & ~middle
    if vertical_reflect_mask(board, p1_legal & wings) != p2_legal & wings:
        return False
    middle_cells = cache.cells_from_legal_masks(
        board,
        p1_legal & middle,
        p2_legal & middle,
    )
    return cache.position_value(middle_cells) == ZERO_VALUE


def component_cancellation_zero(
    board: ColBoard,
    cache: ShapeValueCache,
    p1_legal: int,
    p2_legal: int,
    max_component_cells: int,
) -> bool | None:
    cells = cache.cells_from_legal_masks(board, p1_legal, p2_legal)
    counts: dict[tuple, list[int]] = {}
    values = {}
    for component in live_components(cells):
        if len(component) > max_component_cells:
            return None
        key, swapped = canonical_key(component)
        bucket = counts.setdefault(key, [0, 0])
        bucket[1 if swapped else 0] += 1
        cache.component_value(component)
        values[key] = cache.values[key]

    for key, (normal, swapped) in counts.items():
        pairs = min(normal, swapped)
        normal -= pairs
        swapped -= pairs
        value = values[key]
        if normal and value != ZERO_VALUE:
            return False
        if swapped and negate_value(value) != ZERO_VALUE:
            return False
    return True


def scan_board(
    board_spec: BoardSpec,
    max_component_cells: int,
    max_counterexamples: int,
    counterexamples: list[Counterexample],
) -> BoardResult:
    solver = DfsSolver(
        board_spec.m,
        board_spec.n,
        use_symmetry=True,
        tablebase=Tablebase(enabled=False),
        progress=False,
    )
    started = time.perf_counter()
    solver.solve()
    seconds = time.perf_counter() - started
    board = solver.board
    cache = ShapeValueCache(enabled=False, max_component_size=max_component_cells)
    naive_candidates = 0
    naive_counterexamples = 0
    component_candidates = 0
    component_counterexamples = 0

    for key, side_to_move_wins in solver.memo.items():
        p1_legal, p2_legal, turn = board.unpack_key(key)
        if naive_middle_column_zero(board, cache, p1_legal, p2_legal):
            naive_candidates += 1
            if side_to_move_wins:
                naive_counterexamples += 1
                if len(counterexamples) < max_counterexamples:
                    counterexamples.append(
                        Counterexample(
                            board=board_spec.label,
                            key=hex(key),
                            turn=f"P{turn + 1}",
                            side_to_move_wins=True,
                            p1_legal=hex(p1_legal),
                            p2_legal=hex(p2_legal),
                            reason="symmetric wings plus isolated middle-column value zero",
                        )
                    )

        cancellation = component_cancellation_zero(
            board,
            cache,
            p1_legal,
            p2_legal,
            max_component_cells,
        )
        if cancellation:
            component_candidates += 1
            predicted_stm_wins = False
            if side_to_move_wins != predicted_stm_wins:
                component_counterexamples += 1
                if len(counterexamples) < max_counterexamples:
                    counterexamples.append(
                        Counterexample(
                            board=board_spec.label,
                            key=hex(key),
                            turn=f"P{turn + 1}",
                            side_to_move_wins=side_to_move_wins,
                            p1_legal=hex(p1_legal),
                            p2_legal=hex(p2_legal),
                            reason="certified independent components sum to zero",
                        )
                    )

    return BoardResult(
        board=board_spec.label,
        states=len(solver.memo),
        seconds=seconds,
        naive_candidates=naive_candidates,
        naive_counterexamples=naive_counterexamples,
        component_candidates=component_candidates,
        component_counterexamples=component_counterexamples,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boards", nargs="+", type=parse_board)
    parser.add_argument("--max-cells", type=int, default=39)
    parser.add_argument(
        "--max-fresh-cells",
        type=int,
        default=27,
        help="Skip larger boards unless explicitly passed with --boards.",
    )
    parser.add_argument("--max-component-cells", type=int, default=10)
    parser.add_argument("--max-counterexamples", type=int, default=100)
    parser.add_argument(
        "--rust-report-dir",
        type=Path,
        default=REPO_ROOT / "reports" / "invariant-rust",
        help="Merge full Rust memo scans for boards skipped by fresh Python search.",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=REPO_ROOT / "reports" / "odd-invariant-search.json",
    )
    parser.add_argument(
        "--out-md",
        type=Path,
        default=REPO_ROOT / "reports" / "odd-invariant-search.md",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    boards = args.boards or [
        board
        for board in odd_boards(args.max_cells)
        if not board.is_path
    ]
    explicit = args.boards is not None
    results: list[BoardResult] = []
    counterexamples: list[Counterexample] = []
    for board in boards:
        if not explicit and board.cells > args.max_fresh_cells:
            rust_path = args.rust_report_dir / f"{board.label}.json"
            if rust_path.is_file():
                rust_payload = json.loads(rust_path.read_text(encoding="utf-8"))
                results.append(
                    BoardResult(
                        board=board.label,
                        states=int(rust_payload["entries"]),
                        seconds=0.0,
                        naive_candidates=int(rust_payload["naive_candidates"]),
                        naive_counterexamples=int(rust_payload["naive_counterexamples"]),
                        component_candidates=0,
                        component_counterexamples=0,
                        skipped="Rust full-memo naive scan; component cancellation not scanned",
                    )
                )
                for example in rust_payload.get("examples", []):
                    if len(counterexamples) >= args.max_counterexamples:
                        break
                    counterexamples.append(
                        Counterexample(
                            board=board.label,
                            key=str(example["key"]),
                            turn=str(example["turn"]),
                            side_to_move_wins=True,
                            p1_legal=str(example["p1_legal"]),
                            p2_legal=str(example["p2_legal"]),
                            reason="symmetric wings plus isolated middle-column value zero",
                        )
                    )
                continue
            results.append(
                BoardResult(
                    board=board.label,
                    states=0,
                    seconds=0.0,
                    naive_candidates=0,
                    naive_counterexamples=0,
                    component_candidates=0,
                    component_counterexamples=0,
                    skipped=f"fresh-search cap {args.max_fresh_cells}",
                )
            )
            continue
        print(f"scanning {board.label}", flush=True)
        results.append(
            scan_board(
                board,
                args.max_component_cells,
                args.max_counterexamples,
                counterexamples,
            )
        )

    payload = {
        "schema_version": 1,
        "results": [asdict(result) for result in results],
        "counterexamples": [asdict(example) for example in counterexamples],
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Odd-board Invariant Search",
        "",
        "| Board | States | Naive candidates | Naive counterexamples | Component-sum candidates | Component-sum counterexamples | Status |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for result in results:
        lines.append(
            f"| {result.board} | {result.states:,} | {result.naive_candidates:,} | "
            f"{result.naive_counterexamples:,} | {result.component_candidates:,} | "
            f"{result.component_counterexamples:,} | {result.skipped or 'scanned'} |"
        )
    lines.extend(
        [
            "",
            "The naive invariant deliberately ignores attachments between the middle column "
            "and wings; any listed counterexample rules out that formulation. The component-sum "
            "invariant uses actual disconnected components and exact local values, so a replay "
            "counterexample would indicate an implementation defect.",
            "",
            f"- Saved counterexamples: `{len(counterexamples):,}`",
        ]
    )
    args.out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.out_json}")
    print(f"wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
