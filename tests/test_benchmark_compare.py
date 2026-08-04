from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "python"))

from col.boards import BoardSpec
from scripts.benchmark_compare import (
    build_comparisons,
    parse_args as parse_compare_args,
    winner_mismatches,
)
from scripts.odd_board_experiments import (
    Configuration,
    RunResult,
    parse_output,
    solver_command,
)


class SolverOutputParsingTests(unittest.TestCase):
    def test_parses_every_reduction_metric(self) -> None:
        output = """
3 x 11: P2 wins
states searched: 101
memo hits: 102
front cache queries: 1000
front cache hits: 250
dominance nodes: 80
dominance pruned moves: 160
reserve matching checks: 170
reserve greedy checks: 140
reserve win hits: 30
reserve loss hits: 10
memo entries: 103
memo evictions: 999
memo entries collected: 104
endgame hits: 105
endgame raw cache hits: 106
endgame canonical cache hits: 107
endgame cgt misses: 108
endgame component evals: 109
component reduction calls: 110
component reduction component evals: 209
component reduction column all-small exits: 210
component reduction single-component exits: 111
component reduction all-small exits: 112
component reduction multi-oversized: 113
component reduction changes: 114
conjugate pairs removed: 115
zero components removed: 116
zero-sum cells removed: 117
reductions to empty: 118
pairing certificate hits: 119
pairing certificate checks: 120
states per second: 121
time elapsed (solve): 1.250000s
122 maximum resident set size
"""

        parsed = parse_output(output)

        self.assertEqual(parsed["winner"], "P2")
        self.assertEqual(parsed["states"], 101)
        self.assertEqual(parsed["front_cache_queries"], 1000)
        self.assertEqual(parsed["front_cache_hits"], 250)
        self.assertEqual(parsed["dominance_nodes"], 80)
        self.assertEqual(parsed["dominance_pruned_moves"], 160)
        self.assertEqual(parsed["reserve_matching_checks"], 170)
        self.assertEqual(parsed["reserve_greedy_checks"], 140)
        self.assertEqual(parsed["reserve_win_hits"], 30)
        self.assertEqual(parsed["reserve_loss_hits"], 10)
        self.assertEqual(parsed["memo_entries"], 103)
        self.assertEqual(parsed["memo_evictions"], 999)
        self.assertEqual(parsed["memo_entries_collected"], 104)
        self.assertEqual(parsed["endgame_raw_cache_hits"], 106)
        self.assertEqual(parsed["component_reduction_calls"], 110)
        self.assertEqual(parsed["component_reduction_component_evals"], 209)
        self.assertEqual(parsed["component_reduction_column_all_small_exits"], 210)
        self.assertEqual(parsed["component_reduction_single_component_exits"], 111)
        self.assertEqual(parsed["component_reduction_all_small_exits"], 112)
        self.assertEqual(parsed["component_reduction_multi_oversized"], 113)
        self.assertEqual(parsed["component_reduction_changes"], 114)
        self.assertEqual(parsed["conjugate_pairs_removed"], 115)
        self.assertEqual(parsed["zero_components_removed"], 116)
        self.assertEqual(parsed["zero_sum_cells_removed"], 117)
        self.assertEqual(parsed["reductions_to_empty"], 118)
        self.assertEqual(parsed["solve_seconds"], 1.25)
        self.assertEqual(parsed["peak_rss_bytes"], 122)


class CommandConstructionTests(unittest.TestCase):
    def test_fixed_memo_and_reduction_mode_are_explicit(self) -> None:
        args = argparse.Namespace(solver="candidate", order_stats=False)
        config = Configuration(
            name="candidate",
            threads=8,
            memo="fixed",
            memo_bits=21,
            move_order="heuristic",
            endgame_size=10,
            pairing_certificate=True,
            component_reduction=False,
            cache_state="cold",
        )

        command = solver_command(
            args,
            BoardSpec(3, 9),
            config,
            Path("/tmp/col-bench-test"),
            extra_args=("--root-split",),
        )

        self.assertIn("--memo-bits", command)
        self.assertEqual(command[command.index("--memo-bits") + 1], "21")
        self.assertIn("--no-component-reduction", command)
        self.assertEqual(command[-1], "--root-split")

    def test_comparator_accepts_repeated_side_arguments(self) -> None:
        args = parse_compare_args(
            [
                "baseline",
                "candidate",
                "--baseline-arg=--no-component-reduction",
                "--baseline-arg",
                "value",
                "--candidate-arg=--component-reduction",
            ]
        )

        self.assertEqual(args.baseline_arg, ["--no-component-reduction", "value"])
        self.assertEqual(args.candidate_arg, ["--component-reduction"])


def result(
    config: str,
    repeat: int,
    *,
    winner: str = "P2",
    states: int,
    seconds: float,
) -> RunResult:
    return RunResult(
        board="3x9",
        cells=27,
        config=config,
        repeat=repeat,
        command=[config],
        ok=True,
        returncode=0,
        wall_seconds=seconds + 0.1,
        winner=winner,
        states=states,
        solve_seconds=seconds,
    )


class ComparisonTests(unittest.TestCase):
    def test_uses_medians_for_comparison(self) -> None:
        results = [
            result("baseline", 1, states=300, seconds=3.0),
            result("candidate", 1, states=70, seconds=1.0),
            result("candidate", 2, states=50, seconds=2.0),
            result("baseline", 2, states=100, seconds=5.0),
            result("baseline", 3, states=200, seconds=4.0),
            result("candidate", 3, states=60, seconds=1.5),
        ]

        comparison = build_comparisons(results, [BoardSpec(3, 9)])[0]

        self.assertTrue(comparison["winner_match"])
        self.assertEqual(comparison["baseline"]["medians"]["states"], 200)
        self.assertEqual(comparison["candidate"]["medians"]["states"], 60)
        self.assertAlmostEqual(comparison["solve_speedup"], 4.0 / 1.5)
        self.assertAlmostEqual(comparison["state_reduction"], 0.7)

    def test_reports_paired_winner_mismatch(self) -> None:
        results = [
            result("baseline", 1, states=100, seconds=1.0),
            result("candidate", 1, winner="P1", states=90, seconds=0.9),
        ]

        mismatches = winner_mismatches(results)
        comparison = build_comparisons(results, [BoardSpec(3, 9)])[0]

        self.assertEqual(
            mismatches,
            [
                {
                    "board": "3x9",
                    "repeat": 1,
                    "baseline": "P2",
                    "candidate": "P1",
                }
            ],
        )
        self.assertFalse(comparison["winner_match"])


if __name__ == "__main__":
    unittest.main()
