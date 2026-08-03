#!/usr/bin/env python3
"""Compare baseline vs --component-reduction on odd-by-odd boards."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "python"))

from col.boards import BoardSpec, odd_boards  # noqa: E402  # pyright: ignore[reportMissingImports]

METRICS = {
    "winner": re.compile(r"^\d+\s+x\s+\d+:\s+(P[12])\s+wins$"),
    "states": re.compile(r"^states searched:\s+(\d+)$"),
    "solve_seconds": re.compile(r"^time elapsed(?: \(solve\))?:\s+([0-9.]+)s$"),
    "states_per_second": re.compile(r"^states per second:\s+(\d+)$"),
}


@dataclass
class RunRow:
    board: str
    config: str
    winner: str | None
    states: int | None
    solve_seconds: float | None
    states_per_second: int | None
    ok: bool
    error: str | None = None


def boards_for_sweep(min_cells: int, max_cells: int) -> list[BoardSpec]:
    return [
        board
        for board in odd_boards(max_cells, include_one_by_one=False)
        if board.cells >= min_cells
    ]


def parse_output(text: str) -> dict[str, int | float | str]:
    parsed: dict[str, int | float | str] = {}
    for line in text.splitlines():
        for name, pattern in METRICS.items():
            match = pattern.match(line.strip())
            if match is None:
                continue
            value = match.group(1)
            if name == "winner":
                parsed[name] = value
            elif name == "solve_seconds":
                parsed[name] = float(value)
            else:
                parsed[name] = int(value)
            break
    return parsed


def run_board(
    solver: Path,
    m: int,
    n: int,
    *,
    reduction: bool,
    threads: int,
    timeout: float,
) -> RunRow:
    command = [
        str(solver),
        "--m",
        str(m),
        "--n",
        str(n),
        "--threads",
        str(threads),
        "--memo",
        "hash",
        "--move-order",
        "heuristic",
        "--endgame-size",
        "10",
        "--no-tablebase",
        "--no-endgame-cache",
    ]
    if reduction:
        command.append("--component-reduction")
    label = f"{m}x{n}"
    config = "reduction" if reduction else "baseline"
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return RunRow(label, config, None, None, None, None, False, f"timeout>{timeout}s")

    parsed = parse_output(completed.stdout)
    ok = completed.returncode == 0 and "winner" in parsed
    return RunRow(
        board=label,
        config=config,
        winner=parsed.get("winner"),  # type: ignore[arg-type]
        states=parsed.get("states"),  # type: ignore[arg-type]
        solve_seconds=parsed.get("solve_seconds"),  # type: ignore[arg-type]
        states_per_second=parsed.get("states_per_second"),  # type: ignore[arg-type]
        ok=ok,
        error=None if ok else completed.stdout[-2000:],
    )


def fmt_seconds(value: float | None) -> str:
    if value is None:
        return "-"
    if value < 0.001:
        return "<0.001s"
    return f"{value:.3f}s"


def fmt_int(value: int | None) -> str:
    return "-" if value is None else f"{value:,}"


def speedup(base: RunRow, red: RunRow) -> str:
    if not base.ok or not red.ok:
        return "-"
    if base.solve_seconds is None or red.solve_seconds is None:
        return "-"
    if base.solve_seconds == 0 and red.solve_seconds == 0:
        return "n/a"
    if red.solve_seconds == 0:
        return "∞"
    if base.solve_seconds == 0:
        return "0.00x"
    return f"{base.solve_seconds / red.solve_seconds:.2f}x"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--solver", type=Path, default=REPO_ROOT / "col-solve")
    parser.add_argument("--min-cells", type=int, default=3)
    parser.add_argument("--max-cells", type=int, default=39)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument(
        "--out-json",
        type=Path,
        default=REPO_ROOT / "reports/reduction-sweep-odd-39.json",
    )
    args = parser.parse_args()

    board_list = boards_for_sweep(args.min_cells, args.max_cells)
    results: list[RunRow] = []
    started = time.time()
    for index, board in enumerate(board_list, start=1):
        label = board.label
        print(f"[{index}/{len(board_list)}] {label} baseline...", flush=True)
        results.append(
            run_board(
                args.solver,
                board.m,
                board.n,
                reduction=False,
                threads=args.threads,
                timeout=args.timeout,
            )
        )
        print(f"[{index}/{len(board_list)}] {label} reduction...", flush=True)
        results.append(
            run_board(
                args.solver,
                board.m,
                board.n,
                reduction=True,
                threads=args.threads,
                timeout=args.timeout,
            )
        )

    args.out_json.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "boards": [board.label for board in board_list],
        "min_cells": args.min_cells,
        "max_cells": args.max_cells,
        "threads": args.threads,
        "elapsed_seconds": time.time() - started,
        "results": [row.__dict__ for row in results],
    }
    args.out_json.write_text(json.dumps(payload, indent=2) + "\n")

    print()
    print("| board | cells | baseline | reduction | speedup | baseline states | reduction states |")
    print("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for board in board_list:
        label = board.label
        base = next(r for r in results if r.board == label and r.config == "baseline")
        red = next(r for r in results if r.board == label and r.config == "reduction")
        print(
            f"| {label} | {board.cells} | {fmt_seconds(base.solve_seconds)} | "
            f"{fmt_seconds(red.solve_seconds)} | {speedup(base, red)} | "
            f"{fmt_int(base.states)} | {fmt_int(red.states)} |"
        )
    print()
    print(f"Wrote {args.out_json}")
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
