#!/usr/bin/env python3
"""Reproducible Col benchmarks on every odd board up to an area cap."""

from __future__ import annotations

import argparse
import functools
import json
import os
import platform
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "python"))

from col.boards import BoardSpec, odd_boards  # noqa: E402


METRIC_PATTERNS = {
    "winner": re.compile(r"^\d+\s+x\s+\d+:\s+(P[12])\s+wins$"),
    "states": re.compile(r"^states searched:\s+(\d+)$"),
    "memo_hits": re.compile(r"^memo hits:\s+(\d+)$"),
    "front_cache_queries": re.compile(r"^front cache queries:\s+(\d+)$"),
    "front_cache_hits": re.compile(r"^front cache hits:\s+(\d+)$"),
    "dominance_nodes": re.compile(r"^dominance nodes:\s+(\d+)$"),
    "dominance_pruned_moves": re.compile(r"^dominance pruned moves:\s+(\d+)$"),
    "reserve_cardinality_skips": re.compile(r"^reserve cardinality skips:\s+(\d+)$"),
    "reserve_matching_checks": re.compile(r"^reserve matching checks:\s+(\d+)$"),
    "reserve_greedy_checks": re.compile(r"^reserve greedy checks:\s+(\d+)$"),
    "reserve_win_hits": re.compile(r"^reserve win hits:\s+(\d+)$"),
    "reserve_loss_hits": re.compile(r"^reserve loss hits:\s+(\d+)$"),
    "memo_entries": re.compile(r"^memo entries:\s+(\d+)$"),
    "memo_evictions": re.compile(r"^memo evictions:\s+(\d+)$"),
    "memo_entries_collected": re.compile(r"^memo entries collected:\s+(\d+)$"),
    "endgame_hits": re.compile(r"^endgame hits:\s+(\d+)$"),
    "endgame_raw_cache_hits": re.compile(r"^endgame raw cache hits:\s+(\d+)$"),
    "endgame_canonical_cache_hits": re.compile(
        r"^endgame canonical cache hits:\s+(\d+)$"
    ),
    "endgame_cgt_misses": re.compile(r"^endgame cgt misses:\s+(\d+)$"),
    "endgame_component_evals": re.compile(r"^endgame component evals:\s+(\d+)$"),
    "component_reduction_calls": re.compile(r"^component reduction calls:\s+(\d+)$"),
    "component_reduction_component_evals": re.compile(
        r"^component reduction component evals:\s+(\d+)$"
    ),
    "component_reduction_column_all_small_exits": re.compile(
        r"^component reduction column all-small exits:\s+(\d+)$"
    ),
    "component_reduction_single_component_exits": re.compile(
        r"^component reduction single-component exits:\s+(\d+)$"
    ),
    "component_reduction_all_small_exits": re.compile(
        r"^component reduction all-small exits:\s+(\d+)$"
    ),
    "component_reduction_multi_oversized": re.compile(
        r"^component reduction multi-oversized:\s+(\d+)$"
    ),
    "component_reduction_changes": re.compile(
        r"^component reduction changes:\s+(\d+)$"
    ),
    "conjugate_pairs_removed": re.compile(r"^conjugate pairs removed:\s+(\d+)$"),
    "zero_components_removed": re.compile(r"^zero components removed:\s+(\d+)$"),
    "zero_sum_cells_removed": re.compile(r"^zero-sum cells removed:\s+(\d+)$"),
    "reductions_to_empty": re.compile(r"^reductions to empty:\s+(\d+)$"),
    "component_bag_queries": re.compile(r"^component bag queries:\s+(\d+)$"),
    "component_bag_hits": re.compile(r"^component bag hits:\s+(\d+)$"),
    "component_bag_local_hits": re.compile(r"^component bag local hits:\s+(\d+)$"),
    "component_bag_inserts": re.compile(r"^component bag inserts:\s+(\d+)$"),
    "component_bag_local_duplicate_inserts": re.compile(
        r"^component bag local duplicate inserts:\s+(\d+)$"
    ),
    "component_bag_shared_queries": re.compile(
        r"^component bag shared queries:\s+(\d+)$"
    ),
    "component_bag_shared_hits": re.compile(
        r"^component bag shared hits:\s+(\d+)$"
    ),
    "component_bag_persistent_hits": re.compile(
        r"^component bag persistent hits:\s+(\d+)$"
    ),
    "component_bag_shared_inserts": re.compile(
        r"^component bag shared inserts:\s+(\d+)$"
    ),
    "component_bag_shared_duplicate_inserts": re.compile(
        r"^component bag shared duplicate inserts:\s+(\d+)$"
    ),
    "component_bag_raw_id_hits": re.compile(r"^component bag raw id hits:\s+(\d+)$"),
    "component_bag_signature_hits": re.compile(
        r"^component bag signature hits:\s+(\d+)$"
    ),
    "component_signature_shared_queries": re.compile(
        r"^component signature shared queries:\s+(\d+)$"
    ),
    "component_signature_shared_hits": re.compile(
        r"^component signature shared hits:\s+(\d+)$"
    ),
    "component_signature_shared_inserts": re.compile(
        r"^component signature shared inserts:\s+(\d+)$"
    ),
    "component_native_calls": re.compile(r"^component native calls:\s+(\d+)$"),
    "component_native_eligible": re.compile(
        r"^component native eligible:\s+(\d+)$"
    ),
    "component_native_solved": re.compile(r"^component native solved:\s+(\d+)$"),
    "component_native_states": re.compile(r"^component native states:\s+(\d+)$"),
    "component_native_memo_hits": re.compile(
        r"^component native memo hits:\s+(\d+)$"
    ),
    "component_native_transition_queries": re.compile(
        r"^component native transition queries:\s+(\d+)$"
    ),
    "component_native_transition_hits": re.compile(
        r"^component native transition hits:\s+(\d+)$"
    ),
    "component_native_transition_builds": re.compile(
        r"^component native transition builds:\s+(\d+)$"
    ),
    "component_native_transition_options": re.compile(
        r"^component native transition options:\s+(\d+)$"
    ),
    "component_native_transition_deduplicated": re.compile(
        r"^component native transition deduplicated:\s+(\d+)$"
    ),
    "component_native_value_option_queries": re.compile(
        r"^component native value option queries:\s+(\d+)$"
    ),
    "component_native_value_option_hits": re.compile(
        r"^component native value option hits:\s+(\d+)$"
    ),
    "component_native_closure_fallbacks": re.compile(
        r"^component native closure fallbacks:\s+(\d+)$"
    ),
    "component_native_cancellations": re.compile(
        r"^component native cancellations:\s+(\d+)$"
    ),
    "scheduler_subtasks_generated": re.compile(
        r"^scheduler subtasks generated:\s+(\d+)$"
    ),
    "scheduler_subtasks_released": re.compile(
        r"^scheduler subtasks released:\s+(\d+)$"
    ),
    "scheduler_subtasks_never_released": re.compile(
        r"^scheduler subtasks never released:\s+(\d+)$"
    ),
    "scheduler_abandoned_published": re.compile(
        r"^scheduler abandoned published:\s+(\d+)$"
    ),
    "scheduler_stale_queued": re.compile(r"^scheduler stale queued:\s+(\d+)$"),
    "scheduler_stale_results": re.compile(r"^scheduler stale results:\s+(\d+)$"),
    "scheduler_no_work_polls": re.compile(r"^scheduler no-work polls:\s+(\d+)$"),
    "scheduler_ready_high_water": re.compile(
        r"^scheduler ready high-water:\s+(\d+)$"
    ),
    "component_bag_db_loaded_signatures": re.compile(
        r"^component bag db loaded signatures:\s+(\d+)$"
    ),
    "component_bag_db_loaded_bags": re.compile(
        r"^component bag db loaded bags:\s+(\d+)$"
    ),
    "component_bag_db_load_seconds": re.compile(
        r"^component bag db load:\s+([0-9.]+)s$"
    ),
    "pairing_certificate_hits": re.compile(r"^pairing certificate hits:\s+(\d+)$"),
    "pairing_certificate_checks": re.compile(r"^pairing certificate checks:\s+(\d+)$"),
    "states_per_second": re.compile(r"^states per second:\s+(\d+)$"),
    "solve_seconds": re.compile(r"^time elapsed(?: \(solve\))?:\s+([0-9.]+)s$"),
    "peak_rss_bytes": re.compile(r"^\s*(\d+)\s+maximum resident set size$"),
}


@dataclass(frozen=True)
class Configuration:
    name: str
    threads: int
    memo: str
    memo_bits: int
    move_order: str
    endgame_size: int
    pairing_certificate: bool
    component_reduction: bool
    cache_state: str


@dataclass
class RunResult:
    board: str
    cells: int
    config: str
    repeat: int
    command: list[str]
    ok: bool
    returncode: int
    wall_seconds: float
    winner: str | None = None
    states: int | None = None
    memo_hits: int | None = None
    front_cache_queries: int | None = None
    front_cache_hits: int | None = None
    dominance_nodes: int | None = None
    dominance_pruned_moves: int | None = None
    reserve_cardinality_skips: int | None = None
    reserve_matching_checks: int | None = None
    reserve_greedy_checks: int | None = None
    reserve_win_hits: int | None = None
    reserve_loss_hits: int | None = None
    memo_entries: int | None = None
    memo_evictions: int | None = None
    memo_entries_collected: int | None = None
    endgame_hits: int | None = None
    endgame_raw_cache_hits: int | None = None
    endgame_canonical_cache_hits: int | None = None
    endgame_cgt_misses: int | None = None
    endgame_component_evals: int | None = None
    component_reduction_calls: int | None = None
    component_reduction_component_evals: int | None = None
    component_reduction_column_all_small_exits: int | None = None
    component_reduction_single_component_exits: int | None = None
    component_reduction_all_small_exits: int | None = None
    component_reduction_multi_oversized: int | None = None
    component_reduction_changes: int | None = None
    conjugate_pairs_removed: int | None = None
    zero_components_removed: int | None = None
    zero_sum_cells_removed: int | None = None
    reductions_to_empty: int | None = None
    component_bag_queries: int | None = None
    component_bag_hits: int | None = None
    component_bag_local_hits: int | None = None
    component_bag_inserts: int | None = None
    component_bag_local_duplicate_inserts: int | None = None
    component_bag_shared_queries: int | None = None
    component_bag_shared_hits: int | None = None
    component_bag_persistent_hits: int | None = None
    component_bag_shared_inserts: int | None = None
    component_bag_shared_duplicate_inserts: int | None = None
    component_bag_raw_id_hits: int | None = None
    component_bag_signature_hits: int | None = None
    component_signature_shared_queries: int | None = None
    component_signature_shared_hits: int | None = None
    component_signature_shared_inserts: int | None = None
    component_native_calls: int | None = None
    component_native_eligible: int | None = None
    component_native_solved: int | None = None
    component_native_states: int | None = None
    component_native_memo_hits: int | None = None
    component_native_transition_queries: int | None = None
    component_native_transition_hits: int | None = None
    component_native_transition_builds: int | None = None
    component_native_transition_options: int | None = None
    component_native_transition_deduplicated: int | None = None
    component_native_value_option_queries: int | None = None
    component_native_value_option_hits: int | None = None
    component_native_closure_fallbacks: int | None = None
    component_native_cancellations: int | None = None
    scheduler_subtasks_generated: int | None = None
    scheduler_subtasks_released: int | None = None
    scheduler_subtasks_never_released: int | None = None
    scheduler_abandoned_published: int | None = None
    scheduler_stale_queued: int | None = None
    scheduler_stale_results: int | None = None
    scheduler_no_work_polls: int | None = None
    scheduler_ready_high_water: int | None = None
    component_bag_db_loaded_signatures: int | None = None
    component_bag_db_loaded_bags: int | None = None
    component_bag_db_load_seconds: float | None = None
    pairing_certificate_hits: int | None = None
    pairing_certificate_checks: int | None = None
    states_per_second: int | None = None
    solve_seconds: float | None = None
    peak_rss_bytes: int | None = None
    error: str | None = None


def parse_board(text: str) -> BoardSpec:
    try:
        board = BoardSpec.parse(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if board.m % 2 == 0 or board.n % 2 == 0:
        raise argparse.ArgumentTypeError("experiment boards must have odd dimensions")
    return board


def parse_int_list(text: str) -> list[int]:
    try:
        values = [int(value) for value in re.split(r"[,\s]+", text) if value]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected comma-separated integers") from exc
    if not values or any(value <= 0 for value in values):
        raise argparse.ArgumentTypeError("values must be positive")
    return values


def parse_nonnegative_int_list(text: str) -> list[int]:
    try:
        values = [int(value) for value in re.split(r"[,\s]+", text) if value]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected comma-separated integers") from exc
    if not values or any(value < 0 for value in values):
        raise argparse.ArgumentTypeError("values must be nonnegative")
    return values


def configurations(args: argparse.Namespace) -> list[Configuration]:
    base = {
        "threads": args.threads,
        "memo": args.memo,
        "memo_bits": args.memo_bits,
        "move_order": args.move_order,
        "endgame_size": args.endgame_size,
        "pairing_certificate": not args.no_pairing_certificate,
        "component_reduction": args.component_reduction and args.endgame_size > 0,
        "cache_state": args.cache_state,
    }
    if args.experiment == "baseline":
        return [Configuration("baseline", **base)]
    if args.experiment == "threads":
        return [
            Configuration(f"threads-{threads}", **{**base, "threads": threads})
            for threads in args.thread_values
        ]
    if args.experiment == "cgt":
        return [
            Configuration(
                f"cgt-{size}",
                **{
                    **base,
                    "endgame_size": size,
                    "component_reduction": args.component_reduction and size > 0,
                },
            )
            for size in args.cgt_sizes
        ]
    if args.experiment == "move-order":
        return [
            Configuration(f"order-{order}", **{**base, "move_order": order})
            for order in ("legacy", "heuristic", "auto")
        ]
    return [
        Configuration("pairing-off", **{**base, "pairing_certificate": False}),
        Configuration("pairing-on", **{**base, "pairing_certificate": True}),
    ]


def git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.stdout.strip()


def manifest(
    args: argparse.Namespace, configs: Sequence[Configuration]
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "area_cap": args.max_cells,
        "experiment": args.experiment,
        "repeats": args.repeats,
        "timeout_seconds": args.timeout,
        "git_commit": git_output("rev-parse", "HEAD"),
        "git_status": git_output("status", "--short").splitlines(),
        "platform": platform.platform(),
        "python": sys.version,
        "cpu_count": os.cpu_count(),
        "configurations": [asdict(config) for config in configs],
    }


def solver_command(
    args: argparse.Namespace,
    board: BoardSpec,
    config: Configuration,
    cache_dir: Path,
    extra_args: Sequence[str] = (),
) -> list[str]:
    command = [
        str(args.solver),
        "--m",
        str(board.m),
        "--n",
        str(board.n),
        "--threads",
        str(config.threads),
        "--memo",
        config.memo,
        "--move-order",
        config.move_order,
        "--endgame-size",
        str(config.endgame_size),
        "--tablebase-dir",
        str(cache_dir),
        "--no-tablebase",
    ]
    if config.memo == "fixed":
        command.extend(("--memo-bits", str(config.memo_bits)))
    if not config.pairing_certificate:
        command.append("--no-pairing-certificate")
    command.append(
        "--component-reduction"
        if config.component_reduction
        else "--no-component-reduction"
    )
    if config.cache_state == "cold":
        command.append("--no-endgame-cache")
    if args.order_stats:
        command.append("--order-stats")
    command.extend(extra_args)
    return command


def parse_output(output: str) -> dict[str, int | float | str]:
    parsed: dict[str, int | float | str] = {}
    for line in output.splitlines():
        for name, pattern in METRIC_PATTERNS.items():
            match = pattern.match(line.strip())
            if match is None:
                continue
            value = match.group(1)
            if name == "winner":
                parsed[name] = value
            elif name in {"solve_seconds", "component_bag_db_load_seconds"}:
                parsed[name] = float(value)
            else:
                parsed[name] = int(value)
            break
    return parsed


@functools.lru_cache(maxsize=1)
def darwin_extended_time_available() -> bool:
    if platform.system() != "Darwin" or not Path("/usr/bin/time").is_file():
        return False
    probe = subprocess.run(
        ["/usr/bin/time", "-l", "/usr/bin/true"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return probe.returncode == 0 and "maximum resident set size" in probe.stdout


def run_one(
    args: argparse.Namespace,
    board: BoardSpec,
    config: Configuration,
    repeat: int,
    extra_args: Sequence[str] = (),
) -> RunResult:
    cache_dir = args.out_dir / "cache" / config.name
    cache_dir.mkdir(parents=True, exist_ok=True)
    command = solver_command(args, board, config, cache_dir, extra_args)
    timed_command = command
    if darwin_extended_time_available():
        timed_command = ["/usr/bin/time", "-l", *command]

    started = time.perf_counter()
    try:
        completed = subprocess.run(
            timed_command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=args.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return RunResult(
            board=board.label,
            cells=board.cells,
            config=config.name,
            repeat=repeat,
            command=command,
            ok=False,
            returncode=124,
            wall_seconds=time.perf_counter() - started,
            error=f"timeout after {exc.timeout}s",
        )

    output = completed.stdout
    parsed = parse_output(output)
    result = RunResult(
        board=board.label,
        cells=board.cells,
        config=config.name,
        repeat=repeat,
        command=command,
        ok=completed.returncode == 0 and parsed.get("winner") in {"P1", "P2"},
        returncode=completed.returncode,
        wall_seconds=time.perf_counter() - started,
        error=None,
    )
    for name, value in parsed.items():
        setattr(result, name, value)
    if not result.ok:
        result.error = output[-4000:]
    return result


def fmt_int(value: int | None) -> str:
    return "-" if value is None else f"{value:,}"


def write_report(
    path: Path, metadata: dict[str, object], results: Sequence[RunResult]
) -> None:
    lines = [
        "# Odd-board Experiment",
        "",
        f"- Created: `{metadata['created_at']}`",
        f"- Experiment: `{metadata['experiment']}`",
        f"- Area cap: `{metadata['area_cap']}`",
        f"- Commit: `{metadata['git_commit']}`",
        "",
        "| Board | Cells | Configuration | Repeat | Winner | States | States/s | Solve time | Peak RSS | OK |",
        "|---|---:|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        rss = (
            "-"
            if result.peak_rss_bytes is None
            else f"{result.peak_rss_bytes / (1024 * 1024):.1f} MiB"
        )
        lines.append(
            f"| {result.board} | {result.cells} | {result.config} | {result.repeat} | "
            f"{result.winner or '-'} | {fmt_int(result.states)} | "
            f"{fmt_int(result.states_per_second)} | "
            f"{'-' if result.solve_seconds is None else f'{result.solve_seconds:.6f}s'} | "
            f"{rss} | {result.ok} |"
        )
    failures = [result for result in results if not result.ok]
    if failures:
        lines.extend(["", "## Failures", ""])
        for result in failures:
            lines.append(
                f"- `{result.board}/{result.config}`: {result.error or 'unknown error'}"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--experiment",
        choices=("baseline", "threads", "cgt", "move-order", "pairing"),
        default="baseline",
    )
    parser.add_argument("--max-cells", type=int, default=39)
    parser.add_argument("--boards", nargs="+", type=parse_board)
    parser.add_argument("--threads", type=int, default=min(os.cpu_count() or 1, 12))
    parser.add_argument(
        "--thread-values", type=parse_int_list, default=[1, 4, 8, 12, 16]
    )
    parser.add_argument(
        "--cgt-sizes",
        type=parse_nonnegative_int_list,
        default=[0, 8, 10, 12, 14],
    )
    parser.add_argument("--endgame-size", type=int, default=10)
    parser.add_argument("--memo", choices=("hash", "open", "fixed"), default="hash")
    parser.add_argument("--memo-bits", type=int, default=24)
    parser.add_argument(
        "--move-order", choices=("legacy", "heuristic", "auto"), default="heuristic"
    )
    parser.add_argument("--cache-state", choices=("cold", "warm"), default="cold")
    parser.add_argument("--no-pairing-certificate", action="store_true")
    component_reduction = parser.add_mutually_exclusive_group()
    component_reduction.add_argument(
        "--component-reduction",
        dest="component_reduction",
        action="store_true",
    )
    component_reduction.add_argument(
        "--no-component-reduction",
        dest="component_reduction",
        action="store_false",
    )
    parser.set_defaults(component_reduction=True)
    parser.add_argument("--order-stats", action="store_true")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--solver", type=Path, default=REPO_ROOT / "col-solve")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT / "reports" / "odd-board-experiments",
    )
    args = parser.parse_args(argv)
    if args.max_cells <= 0 or args.repeats <= 0:
        parser.error("--max-cells and --repeats must be positive")
    if args.memo == "fixed" and not 16 <= args.memo_bits <= 34:
        parser.error("--memo fixed requires --memo-bits between 16 and 34")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.skip_build:
        build_env = {
            **os.environ,
            "CARGO_TARGET_DIR": str(REPO_ROOT / "solver" / "target"),
        }
        subprocess.run(
            ["cargo", "build", "--release"],
            cwd=REPO_ROOT / "solver",
            env=build_env,
            check=True,
        )

    boards = sorted(
        set(args.boards or odd_boards(args.max_cells)),
        key=lambda board: (board.cells, board.m, board.n),
    )
    configs = configurations(args)
    metadata = manifest(args, configs)
    results: list[RunResult] = []
    total = len(boards) * len(configs) * args.repeats
    completed_count = 0
    for config in configs:
        for board in boards:
            for repeat in range(1, args.repeats + 1):
                completed_count += 1
                print(
                    f"[{completed_count}/{total}] {board.label} {config.name} repeat={repeat}",
                    flush=True,
                )
                result = run_one(args, board, config, repeat)
                print(
                    f"  {'ok' if result.ok else 'failed'}: "
                    f"{result.states or 0:,} states, {result.solve_seconds or result.wall_seconds:.3f}s",
                    flush=True,
                )
                results.append(result)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{args.experiment}-{args.cache_state}-{args.max_cells}"
    json_path = args.out_dir / f"{stem}.json"
    md_path = args.out_dir / f"{stem}.md"
    payload = {**metadata, "results": [asdict(result) for result in results]}
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_report(md_path, metadata, results)
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    return 1 if any(not result.ok for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
