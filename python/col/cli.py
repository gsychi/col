"""Shared command-line interface for Col solvers."""

from __future__ import annotations

import argparse
import inspect
import time
from pathlib import Path
from typing import Any, Dict, Optional, Protocol, Sequence, Type

from col.tablebase import Tablebase


class Solver(Protocol):
    name: str
    stats: object

    def __init__(
        self,
        m: int,
        n: int,
        use_symmetry: bool = True,
        tablebase: Optional[Tablebase] = None,
    ) -> None: ...

    def solve(self) -> bool: ...

    def optimal_first_move(self) -> Optional[int]: ...


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{value!r} is not an integer") from exc

    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Solve the 2D m x n Col placement game."
    )
    parser.add_argument("--m", type=positive_int, help="number of board rows")
    parser.add_argument("--n", type=positive_int, help="number of board columns")
    parser.add_argument(
        "--max-m",
        type=positive_int,
        help="maximum rows for a table; max mode only searches odd dimensions",
    )
    parser.add_argument(
        "--max-n",
        type=positive_int,
        help="maximum columns for a table; max mode only searches odd dimensions",
    )
    parser.add_argument(
        "--no-symmetry",
        action="store_true",
        help="disable geometric symmetry canonicalization",
    )
    parser.add_argument(
        "--no-tablebase",
        action="store_true",
        help="do not load or save the persistent tablebase",
    )
    parser.add_argument(
        "--tablebase-dir",
        type=Path,
        default=Path("data/tablebases"),
        help="directory for persistent tablebase files",
    )
    parser.add_argument(
        "--progress",
        action="store_true",
        help="print live search progress to stderr while solving",
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=positive_int,
        default=0,
        help="append a tablebase checkpoint after this many newly solved states",
    )
    parser.add_argument(
        "--prefer-reflection",
        action="store_true",
        help="try the 180-degree reflected reply first when available",
    )
    parser.add_argument(
        "--mobility-order",
        action="store_true",
        help="order moves by shallow legal-move mobility counts",
    )

    args = parser.parse_args(argv)
    single_board = args.m is not None or args.n is not None
    max_table = args.max_m is not None or args.max_n is not None

    if single_board == max_table:
        parser.error("provide either --m/--n or --max-m/--max-n")
    if single_board and (args.m is None or args.n is None):
        parser.error("--m and --n must be provided together")
    if max_table and (args.max_m is None or args.max_n is None):
        parser.error("--max-m and --max-n must be provided together")

    return args


def main_for_solver(solver_cls: Type[Solver]) -> int:
    args = parse_args()
    use_symmetry = not args.no_symmetry
    tablebase = Tablebase(args.tablebase_dir, enabled=not args.no_tablebase)
    solver_kwargs = solver_init_kwargs(solver_cls, args)

    if args.m is not None and args.n is not None:
        solve_single_board(solver_cls, args.m, args.n, use_symmetry, tablebase, solver_kwargs)
    else:
        solve_max_table(solver_cls, args.max_m, args.max_n, use_symmetry, tablebase, solver_kwargs)

    return 0


def solver_init_kwargs(solver_cls: Type[Solver], args: argparse.Namespace) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {}
    if getattr(args, "progress", False) and "progress" in inspect.signature(solver_cls.__init__).parameters:
        kwargs["progress"] = True
    if (
        getattr(args, "checkpoint_interval", 0)
        and "checkpoint_interval" in inspect.signature(solver_cls.__init__).parameters
    ):
        kwargs["checkpoint_interval"] = args.checkpoint_interval
    if (
        getattr(args, "prefer_reflection", False)
        and "prefer_reflection" in inspect.signature(solver_cls.__init__).parameters
    ):
        kwargs["prefer_reflection"] = True
    if (
        getattr(args, "mobility_order", False)
        and "mobility_order" in inspect.signature(solver_cls.__init__).parameters
    ):
        kwargs["mobility_order"] = True
    return kwargs


def solve_single_board(
    solver_cls: Type[Solver],
    m: int,
    n: int,
    use_symmetry: bool,
    tablebase: Tablebase,
    solver_kwargs: Optional[Dict[str, Any]] = None,
) -> None:
    solver = solver_cls(
        m,
        n,
        use_symmetry=use_symmetry,
        tablebase=tablebase,
        **(solver_kwargs or {}),
    )
    started_at = time.perf_counter()
    p1_wins = solver.solve()
    first_move = solver.optimal_first_move() if p1_wins else None
    elapsed = time.perf_counter() - started_at

    winner = "P1" if p1_wins else "P2"
    print(f"{m} x {n}: {winner} wins")
    print("deterministic under optimal play: yes")
    print(f"solver: {solver.name}")
    print(f"states searched: {solver.stats.states_searched}")
    print(f"memo hits: {solver.stats.memo_hits}")
    print(f"tablebase hits: {solver.stats.tablebase_hits}")
    print(f"pairing certificate hits: {solver.stats.pairing_certificate_hits}")
    print(f"time elapsed: {elapsed:.6f}s")
    if p1_wins:
        if first_move is None:
            raise RuntimeError("solver reported P1 win but found no winning first move")
        print(f"one optimal first move: {solver.board.format_cell(first_move)}")
    else:
        print("P2 has a response to every P1 opening")


def solve_max_table(
    solver_cls: Type[Solver],
    max_m: int,
    max_n: int,
    use_symmetry: bool,
    tablebase: Tablebase,
    solver_kwargs: Optional[Dict[str, Any]] = None,
) -> None:
    started_at = time.perf_counter()
    results = []
    m_values = list(range(1, max_m + 1, 2))
    n_values = list(range(1, max_n + 1, 2))

    for m in m_values:
        row = []
        for n in n_values:
            solver = solver_cls(
                m,
                n,
                use_symmetry=use_symmetry,
                tablebase=tablebase,
                **(solver_kwargs or {}),
            )
            row.append("P1" if solver.solve() else "P2")
        results.append(row)

    elapsed = time.perf_counter() - started_at
    row_label = "m/n"
    row_label_width = max(len(row_label), len(str(m_values[-1])))
    col_width = max(2, len(str(n_values[-1])))
    print("deterministic under optimal play: yes")
    print(f"solver: {solver_cls.name}")
    print("max search includes only boards where both m and n are odd")
    print(f"time elapsed: {elapsed:.6f}s")
    print()
    print(
        f"{row_label:>{row_label_width}} | "
        + " ".join(f"{n:>{col_width}}" for n in n_values)
    )
    print("-" * (row_label_width + 3 + len(n_values) * col_width + len(n_values) - 1))
    for m, row in zip(m_values, results):
        print(
            f"{m:>{row_label_width}} | "
            + " ".join(f"{cell:>{col_width}}" for cell in row)
        )
