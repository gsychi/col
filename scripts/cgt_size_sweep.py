#!/usr/bin/env python3
"""Sweep Col solver CGT cutoffs and generate comparison tables.

The goal is to estimate where a larger CGT endgame cutoff pays for itself:
each cutoff is compared against the same board solved with
``--endgame-size 0``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "python"))

from col.boards import BoardSpec, odd_boards  # noqa: E402


DEFAULT_CGT_SIZES = (0, 6, 8, 10, 12, 14)
METRIC_PATTERNS = {
    "states_searched": re.compile(r"^states searched: (\d+)$"),
    "memo_hits": re.compile(r"^memo hits: (\d+)$"),
    "endgame_hits": re.compile(r"^endgame hits: (\d+)$"),
    "endgame_raw_cache_hits": re.compile(r"^endgame raw cache hits: (\d+)$"),
    "endgame_canonical_cache_hits": re.compile(r"^endgame canonical cache hits: (\d+)$"),
    "endgame_cgt_misses": re.compile(r"^endgame cgt misses: (\d+)$"),
    "endgame_component_evals": re.compile(r"^endgame component evals: (\d+)$"),
    "states_per_second": re.compile(r"^states per second: (\d+)$"),
    "time_elapsed": re.compile(r"^time elapsed(?: \(solve\))?: ([0-9.]+)s$"),
}


@dataclass
class RunResult:
    board: str
    m: int
    n: int
    cgt_size: int
    repeat: int
    ok: bool
    command: list[str]
    wall_time: float
    states_searched: int | None = None
    memo_hits: int | None = None
    endgame_hits: int = 0
    endgame_raw_cache_hits: int = 0
    endgame_canonical_cache_hits: int = 0
    endgame_cgt_misses: int = 0
    endgame_component_evals: int = 0
    states_per_second: int | None = None
    time_elapsed: float | None = None
    error: str | None = None


@dataclass
class Aggregate:
    board: str
    m: int
    n: int
    cgt_size: int
    repeats: int
    ok_repeats: int
    time_elapsed: float | None
    wall_time: float | None
    states_searched: int | None
    memo_hits: int | None
    endgame_hits: int | None
    endgame_cgt_misses: int | None
    endgame_component_evals: int | None
    states_per_second: int | None


def parse_int_list(text: str) -> list[int]:
    values = [int(part) for part in re.split(r"[,\s]+", text.strip()) if part]
    if not values:
        raise argparse.ArgumentTypeError("expected at least one integer")
    return values


def parse_board(text: str) -> BoardSpec:
    try:
        board = BoardSpec.parse(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if board.m % 2 == 0 or board.n % 2 == 0:
        raise argparse.ArgumentTypeError("CGT sweep boards must have odd dimensions")
    return board


def default_boards(max_cells: int) -> list[BoardSpec]:
    return odd_boards(max_cells)


def build_solver(args: argparse.Namespace) -> None:
    if args.skip_build:
        return
    subprocess.run(
        ["cargo", "build", "--release"],
        cwd=REPO_ROOT / "solver",
        env={
            **os.environ,
            "CARGO_TARGET_DIR": str(REPO_ROOT / "solver" / "target"),
        },
        check=True,
    )


def solver_command(args: argparse.Namespace, board: BoardSpec, cgt_size: int) -> list[str]:
    return [
        str(args.solver),
        "--m",
        str(board.m),
        "--n",
        str(board.n),
        "--threads",
        str(args.threads),
        "--memo",
        args.memo,
        "--no-tablebase",
        "--move-order",
        args.move_order,
        "--endgame-size",
        str(cgt_size),
    ]


def parse_solver_output(output: str) -> dict[str, int | float]:
    parsed: dict[str, int | float] = {}
    for line in output.splitlines():
        for name, pattern in METRIC_PATTERNS.items():
            match = pattern.match(line.strip())
            if not match:
                continue
            value = match.group(1)
            parsed[name] = float(value) if name == "time_elapsed" else int(value)
            break
    return parsed


def run_one(
    args: argparse.Namespace,
    board: BoardSpec,
    cgt_size: int,
    repeat: int,
) -> RunResult:
    command = solver_command(args, board, cgt_size)
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=args.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as err:
        return RunResult(
            board=board.label,
            m=board.m,
            n=board.n,
            cgt_size=cgt_size,
            repeat=repeat,
            ok=False,
            command=command,
            wall_time=time.perf_counter() - started,
            error=f"timeout after {err.timeout}s",
        )

    parsed = parse_solver_output(completed.stdout)
    result = RunResult(
        board=board.label,
        m=board.m,
        n=board.n,
        cgt_size=cgt_size,
        repeat=repeat,
        ok=completed.returncode == 0 and "states_searched" in parsed,
        command=command,
        wall_time=time.perf_counter() - started,
        error=None if completed.returncode == 0 else completed.stdout[-2000:],
    )
    for name, value in parsed.items():
        setattr(result, name, value)
    return result


def median_int(values: Iterable[int | None]) -> int | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return int(statistics.median(present))


def median_float(values: Iterable[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return float(statistics.median(present))


def aggregate_results(results: list[RunResult]) -> list[Aggregate]:
    groups: dict[tuple[str, int], list[RunResult]] = {}
    for result in results:
        groups.setdefault((result.board, result.cgt_size), []).append(result)

    aggregates = []
    for (_, _), group in sorted(groups.items(), key=lambda item: (group_key(item[1][0]), item[0][1])):
        ok = [result for result in group if result.ok]
        sample = group[0]
        aggregates.append(
            Aggregate(
                board=sample.board,
                m=sample.m,
                n=sample.n,
                cgt_size=sample.cgt_size,
                repeats=len(group),
                ok_repeats=len(ok),
                time_elapsed=median_float(result.time_elapsed for result in ok),
                wall_time=median_float(result.wall_time for result in ok),
                states_searched=median_int(result.states_searched for result in ok),
                memo_hits=median_int(result.memo_hits for result in ok),
                endgame_hits=median_int(result.endgame_hits for result in ok),
                endgame_cgt_misses=median_int(result.endgame_cgt_misses for result in ok),
                endgame_component_evals=median_int(result.endgame_component_evals for result in ok),
                states_per_second=median_int(result.states_per_second for result in ok),
            )
        )
    return aggregates


def group_key(result: RunResult) -> tuple[int, int]:
    return (result.m, result.n)


def aggregate_map(aggregates: list[Aggregate]) -> dict[tuple[str, int], Aggregate]:
    return {(aggregate.board, aggregate.cgt_size): aggregate for aggregate in aggregates}


def fmt_number(value: int | None) -> str:
    if value is None:
        return "-"
    return f"{value:,}"


def fmt_seconds(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}s"


def fmt_ratio(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}x"


def fmt_percent(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value * 100:.1f}%"


def metric_speedup(current: Aggregate, baseline: Aggregate | None) -> float | None:
    if baseline is None or baseline.time_elapsed is None or current.time_elapsed in (None, 0):
        return None
    return baseline.time_elapsed / current.time_elapsed


def metric_state_reduction(current: Aggregate, baseline: Aggregate | None) -> float | None:
    if baseline is None or baseline.states_searched in (None, 0) or current.states_searched is None:
        return None
    return 1.0 - current.states_searched / baseline.states_searched


def metric_hit_rate(current: Aggregate, _baseline: Aggregate | None) -> float | None:
    if current.states_searched in (None, 0) or current.endgame_hits is None:
        return None
    return current.endgame_hits / current.states_searched


def metric_cgt_pressure(current: Aggregate, _baseline: Aggregate | None) -> float | None:
    if current.states_searched in (None, 0) or current.endgame_cgt_misses is None:
        return None
    return current.endgame_cgt_misses / current.states_searched


def metric_component_pressure(current: Aggregate, _baseline: Aggregate | None) -> float | None:
    if current.states_searched in (None, 0) or current.endgame_component_evals is None:
        return None
    return current.endgame_component_evals / current.states_searched


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    out = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    out.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(out)


def matrix_section(
    title: str,
    aggregates: list[Aggregate],
    cgt_size: int,
    formatter,
    metric,
) -> str:
    by_key = aggregate_map(aggregates)
    boards = sorted({BoardSpec(aggregate.m, aggregate.n) for aggregate in aggregates})
    rows = sorted({board.m for board in boards})
    cols = sorted({board.n for board in boards})
    table_rows = []
    for m in rows:
        table_row = [str(m)]
        for n in cols:
            board = BoardSpec(m, n)
            current = by_key.get((board.label, cgt_size))
            baseline = by_key.get((board.label, 0))
            table_row.append(formatter(metric(current, baseline)) if current else "-")
        table_rows.append(table_row)
    return f"### {title}: CGT {cgt_size}\n\n" + markdown_table(["m \\ n", *map(str, cols)], table_rows)


def summary_rows(aggregates: list[Aggregate]) -> list[list[str]]:
    by_key = aggregate_map(aggregates)
    rows = []
    for aggregate in aggregates:
        baseline = by_key.get((aggregate.board, 0))
        rows.append(
            [
                aggregate.board,
                str(aggregate.cgt_size),
                f"{aggregate.ok_repeats}/{aggregate.repeats}",
                fmt_seconds(aggregate.time_elapsed),
                fmt_number(aggregate.states_searched),
                fmt_ratio(metric_speedup(aggregate, baseline)),
                fmt_percent(metric_state_reduction(aggregate, baseline)),
                fmt_percent(metric_hit_rate(aggregate, baseline)),
                fmt_percent(metric_cgt_pressure(aggregate, baseline)),
                fmt_ratio(metric_component_pressure(aggregate, baseline)),
            ]
        )
    return rows


def generate_markdown(args: argparse.Namespace, results: list[RunResult]) -> str:
    aggregates = aggregate_results(results)
    cgt_sizes = sorted({aggregate.cgt_size for aggregate in aggregates})
    nonzero_sizes = [size for size in cgt_sizes if size != 0]

    lines = [
        "# CGT Size Sweep",
        "",
        "Fresh solver runs comparing each `--endgame-size` against the same board with CGT disabled.",
        "",
        "## Configuration",
        "",
        markdown_table(
            ["Setting", "Value"],
            [
                ["threads", str(args.threads)],
                ["memo", args.memo],
                ["move order", args.move_order],
                ["tablebase", "disabled"],
                ["repeats", str(args.repeats)],
                ["timeout", "none" if args.timeout is None else f"{args.timeout}s"],
            ],
        ),
        "",
        "## Summary",
        "",
        markdown_table(
            [
                "Board",
                "CGT",
                "OK",
                "Time",
                "States",
                "Speedup",
                "State reduction",
                "Endgame hit rate",
                "CGT miss pressure",
                "Component evals/state",
            ],
            summary_rows(aggregates),
        ),
    ]

    for size in nonzero_sizes:
        lines.extend(
            [
                "",
                matrix_section("Runtime speedup vs CGT 0", aggregates, size, fmt_ratio, metric_speedup),
                "",
                matrix_section(
                    "State reduction vs CGT 0",
                    aggregates,
                    size,
                    fmt_percent,
                    metric_state_reduction,
                ),
                "",
                matrix_section("Endgame hit rate", aggregates, size, fmt_percent, metric_hit_rate),
                "",
                matrix_section("CGT miss pressure", aggregates, size, fmt_percent, metric_cgt_pressure),
            ]
        )

    failed = [result for result in results if not result.ok]
    if failed:
        lines.extend(["", "## Failed Runs", ""])
        lines.append(
            markdown_table(
                ["Board", "CGT", "Repeat", "Error"],
                [
                    [
                        result.board,
                        str(result.cgt_size),
                        str(result.repeat),
                        (result.error or "missing metrics").replace("\n", " ")[:300],
                    ]
                    for result in failed
                ],
            )
        )

    return "\n".join(lines) + "\n"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--boards",
        nargs="+",
        type=parse_board,
        help="Boards to sweep, e.g. 3x9 3x11 5x7. Defaults to odd boards up to --max-cells.",
    )
    parser.add_argument(
        "--max-cells",
        type=int,
        default=39,
        help="Default-board generator limit when --boards is omitted.",
    )
    parser.add_argument(
        "--cgt-sizes",
        type=parse_int_list,
        default=list(DEFAULT_CGT_SIZES),
        help="Comma/space separated endgame sizes, default: 0,6,8,10,12.",
    )
    parser.add_argument("--threads", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--memo", choices=("hash", "open", "fixed"), default="hash")
    parser.add_argument("--move-order", choices=("auto", "legacy", "heuristic"), default="auto")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=None, help="Per-run timeout in seconds.")
    parser.add_argument(
        "--solver",
        type=Path,
        default=REPO_ROOT / "col-solve",
        help="Path to solver wrapper/binary.",
    )
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--out-json", type=Path, default=REPO_ROOT / "reports" / "cgt-size-sweep.json")
    parser.add_argument("--out-md", type=Path, default=REPO_ROOT / "reports" / "cgt-size-sweep.md")
    args = parser.parse_args(argv)

    if args.repeats <= 0:
        parser.error("--repeats must be positive")
    if any(size < 0 for size in args.cgt_sizes):
        parser.error("--cgt-sizes cannot contain negative values")
    if 0 not in args.cgt_sizes:
        args.cgt_sizes = [0, *args.cgt_sizes]
    if any(size > 14 for size in args.cgt_sizes):
        parser.error("CGT sizes above 14 are not supported by the current local evaluator")
    if args.boards is None:
        args.boards = default_boards(args.max_cells)
    args.boards = sorted(set(args.boards))
    args.cgt_sizes = sorted(set(args.cgt_sizes))
    return args


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    build_solver(args)

    results: list[RunResult] = []
    total = len(args.boards) * len(args.cgt_sizes) * args.repeats
    completed_count = 0
    for board in args.boards:
        for cgt_size in args.cgt_sizes:
            for repeat in range(1, args.repeats + 1):
                completed_count += 1
                print(
                    f"[{completed_count}/{total}] {board.label} cgt={cgt_size} repeat={repeat}",
                    flush=True,
                )
                result = run_one(args, board, cgt_size, repeat)
                status = "ok" if result.ok else "failed"
                elapsed = fmt_seconds(result.time_elapsed or result.wall_time)
                states = fmt_number(result.states_searched)
                print(f"  {status}: {elapsed}, states={states}", flush=True)
                results.append(result)

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps([asdict(result) for result in results], indent=2) + "\n",
        encoding="utf-8",
    )
    args.out_md.write_text(generate_markdown(args, results), encoding="utf-8")
    print(f"wrote {args.out_json}")
    print(f"wrote {args.out_md}")

    return 1 if any(not result.ok for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
