#!/usr/bin/env python3
"""Compare two Col solver executables with paired, cold benchmark runs."""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "python"))

from col.boards import BoardSpec  # noqa: E402
from scripts.odd_board_experiments import (  # noqa: E402
    Configuration,
    RunResult,
    git_output,
    parse_board,
    run_one,
)


DEFAULT_BOARDS = tuple(
    BoardSpec.parse(label) for label in ("3x9", "3x11", "3x13", "5x5", "5x7")
)

MEDIAN_FIELDS = (
    "wall_seconds",
    "solve_seconds",
    "states",
    "memo_hits",
    "front_cache_queries",
    "front_cache_hits",
    "dominance_nodes",
    "dominance_pruned_moves",
    "reserve_cardinality_skips",
    "reserve_matching_checks",
    "reserve_greedy_checks",
    "reserve_win_hits",
    "reserve_loss_hits",
    "memo_entries",
    "memo_evictions",
    "memo_entries_collected",
    "endgame_hits",
    "endgame_raw_cache_hits",
    "endgame_canonical_cache_hits",
    "endgame_cgt_misses",
    "endgame_component_evals",
    "component_reduction_calls",
    "component_reduction_component_evals",
    "component_reduction_column_all_small_exits",
    "component_reduction_single_component_exits",
    "component_reduction_all_small_exits",
    "component_reduction_multi_oversized",
    "component_reduction_changes",
    "conjugate_pairs_removed",
    "zero_components_removed",
    "zero_sum_cells_removed",
    "reductions_to_empty",
    "component_bag_queries",
    "component_bag_hits",
    "component_bag_inserts",
    "component_bag_raw_id_hits",
    "component_bag_signature_hits",
    "pairing_certificate_hits",
    "pairing_certificate_checks",
    "states_per_second",
    "peak_rss_bytes",
)


def median_present(results: Sequence[RunResult], field: str) -> int | float | None:
    values = [
        value
        for result in results
        if result.ok and (value := getattr(result, field)) is not None
    ]
    return statistics.median(values) if values else None


def aggregate_results(
    results: Sequence[RunResult],
) -> dict[tuple[str, str], dict[str, object]]:
    groups: dict[tuple[str, str], list[RunResult]] = {}
    for result in results:
        groups.setdefault((result.board, result.config), []).append(result)

    aggregates: dict[tuple[str, str], dict[str, object]] = {}
    for key, group in groups.items():
        winners = sorted(
            {
                result.winner
                for result in group
                if result.ok and result.winner is not None
            }
        )
        aggregates[key] = {
            "runs": len(group),
            "ok_runs": sum(result.ok for result in group),
            "winner": winners[0] if len(winners) == 1 else None,
            "observed_winners": winners,
            "medians": {field: median_present(group, field) for field in MEDIAN_FIELDS},
        }
    return aggregates


def safe_ratio(numerator: object, denominator: object) -> float | None:
    if not isinstance(numerator, (int, float)) or not isinstance(
        denominator, (int, float)
    ):
        return None
    if denominator == 0:
        return None
    return numerator / denominator


def winner_mismatches(results: Sequence[RunResult]) -> list[dict[str, object]]:
    paired: dict[tuple[str, int], dict[str, str]] = {}
    for result in results:
        if result.winner is not None:
            paired.setdefault((result.board, result.repeat), {})[
                result.config
            ] = result.winner

    mismatches = []
    for (board, repeat), winners in paired.items():
        baseline = winners.get("baseline")
        candidate = winners.get("candidate")
        if baseline is not None and candidate is not None and baseline != candidate:
            mismatches.append(
                {
                    "board": board,
                    "repeat": repeat,
                    "baseline": baseline,
                    "candidate": candidate,
                }
            )
    return mismatches


def build_comparisons(
    results: Sequence[RunResult], boards: Sequence[BoardSpec]
) -> list[dict[str, object]]:
    aggregates = aggregate_results(results)
    comparisons = []
    for board in boards:
        baseline = aggregates.get((board.label, "baseline"), {})
        candidate = aggregates.get((board.label, "candidate"), {})
        baseline_medians = baseline.get("medians", {})
        candidate_medians = candidate.get("medians", {})
        assert isinstance(baseline_medians, dict)
        assert isinstance(candidate_medians, dict)

        baseline_states = baseline_medians.get("states")
        candidate_states = candidate_medians.get("states")
        state_ratio = safe_ratio(candidate_states, baseline_states)
        comparisons.append(
            {
                "board": board.label,
                "winner_match": baseline.get("winner") is not None
                and baseline.get("winner") == candidate.get("winner"),
                "baseline": baseline,
                "candidate": candidate,
                "solve_speedup": safe_ratio(
                    baseline_medians.get("solve_seconds"),
                    candidate_medians.get("solve_seconds"),
                ),
                "wall_speedup": safe_ratio(
                    baseline_medians.get("wall_seconds"),
                    candidate_medians.get("wall_seconds"),
                ),
                "state_reduction": None if state_ratio is None else 1.0 - state_ratio,
            }
        )
    return comparisons


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", help="baseline solver executable")
    parser.add_argument("candidate", help="candidate solver executable")
    parser.add_argument(
        "--baseline-arg",
        action="append",
        default=[],
        metavar="ARG",
        help="extra baseline argument; repeat as needed (use = for values starting --)",
    )
    parser.add_argument(
        "--candidate-arg",
        action="append",
        default=[],
        metavar="ARG",
        help="extra candidate argument; repeat as needed (use = for values starting --)",
    )
    parser.add_argument(
        "--boards", nargs="+", type=parse_board, default=list(DEFAULT_BOARDS)
    )
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--memo", choices=("hash", "open", "fixed"), default="hash")
    parser.add_argument("--memo-bits", type=int, default=24)
    parser.add_argument(
        "--move-order", choices=("legacy", "heuristic", "auto"), default="heuristic"
    )
    parser.add_argument("--endgame-size", type=int, default=10)
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
    parser.add_argument("--out-json", type=Path)
    args = parser.parse_args(argv)

    if args.threads <= 0 or args.repeats <= 0 or args.timeout <= 0:
        parser.error("--threads, --repeats, and --timeout must be positive")
    if args.memo == "fixed" and not 16 <= args.memo_bits <= 34:
        parser.error("--memo fixed requires --memo-bits between 16 and 34")
    return args


def benchmark_configuration(args: argparse.Namespace, name: str) -> Configuration:
    return Configuration(
        name=name,
        threads=args.threads,
        memo=args.memo,
        memo_bits=args.memo_bits,
        move_order=args.move_order,
        endgame_size=args.endgame_size,
        pairing_certificate=not args.no_pairing_certificate,
        component_reduction=args.component_reduction and args.endgame_size > 0,
        cache_state="cold",
    )


def run_benchmarks(args: argparse.Namespace) -> list[RunResult]:
    boards = list(dict.fromkeys(args.boards))
    baseline_config = benchmark_configuration(args, "baseline")
    candidate_config = benchmark_configuration(args, "candidate")
    total = len(boards) * args.repeats * 2
    completed_count = 0
    results: list[RunResult] = []

    with tempfile.TemporaryDirectory(prefix="col-bench-") as temp_dir:
        common = {
            "out_dir": Path(temp_dir),
            "timeout": args.timeout,
            "order_stats": args.order_stats,
        }
        for board in boards:
            for repeat in range(1, args.repeats + 1):
                configurations = [
                    (
                        "baseline",
                        args.baseline,
                        baseline_config,
                        args.baseline_arg,
                    ),
                    (
                        "candidate",
                        args.candidate,
                        candidate_config,
                        args.candidate_arg,
                    ),
                ]
                if repeat % 2 == 0:
                    configurations.reverse()
                for name, solver, config, extra_args in configurations:
                    completed_count += 1
                    print(
                        f"[{completed_count}/{total}] {board.label} {name} repeat={repeat}",
                        file=sys.stderr,
                        flush=True,
                    )
                    runner_args = argparse.Namespace(solver=solver, **common)
                    result = run_one(
                        runner_args,
                        board,
                        config,
                        repeat,
                        extra_args=extra_args,
                    )
                    elapsed = (
                        result.solve_seconds
                        if result.solve_seconds is not None
                        else result.wall_seconds
                    )
                    print(
                        f"  {'ok' if result.ok else 'failed'}: "
                        f"{result.states or 0:,} states, {elapsed:.3f}s",
                        file=sys.stderr,
                        flush=True,
                    )
                    results.append(result)
    return results


def build_payload(
    args: argparse.Namespace, results: Sequence[RunResult]
) -> dict[str, object]:
    boards = list(dict.fromkeys(args.boards))
    comparisons = build_comparisons(results, boards)
    mismatches = winner_mismatches(results)
    failures = [
        {
            "board": result.board,
            "config": result.config,
            "repeat": result.repeat,
            "returncode": result.returncode,
            "error": result.error,
        }
        for result in results
        if not result.ok
    ]
    winner_gate_passed = not mismatches and all(
        comparison["winner_match"] for comparison in comparisons
    )
    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_output("rev-parse", "HEAD"),
        "git_dirty": bool(git_output("status", "--short")),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "boards": [board.label for board in boards],
        "repeats": args.repeats,
        "timeout_seconds": args.timeout,
        "baseline": {
            "solver": args.baseline,
            "extra_args": args.baseline_arg,
            "configuration": asdict(benchmark_configuration(args, "baseline")),
        },
        "candidate": {
            "solver": args.candidate,
            "extra_args": args.candidate_arg,
            "configuration": asdict(benchmark_configuration(args, "candidate")),
        },
        "ok": not failures and winner_gate_passed,
        "winner_gate_passed": winner_gate_passed,
        "winner_mismatches": mismatches,
        "failures": failures,
        "comparisons": comparisons,
        "runs": [asdict(result) for result in results],
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    results = run_benchmarks(args)
    payload = build_payload(args, results)
    rendered = json.dumps(payload, indent=2, allow_nan=False) + "\n"
    if args.out_json is not None:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(rendered, encoding="utf-8")
        print(f"wrote {args.out_json}", file=sys.stderr)
    sys.stdout.write(rendered)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
