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
reserve cardinality skips: 75
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
component bag queries: 200
component bag hits: 201
component bag local hits: 151
component bag inserts: 202
component bag local duplicate inserts: 7
component bag shared queries: 50
component bag shared hits: 25
component bag persistent hits: 15
component bag shared inserts: 20
component bag shared duplicate inserts: 5
component bag raw id hits: 203
component bag signature hits: 204
component signature shared queries: 40
component signature shared hits: 30
component signature shared inserts: 10
component native calls: 90
component native eligible: 80
component native solved: 70
component native states: 600
component native memo hits: 500
component native transition queries: 400
component native transition hits: 300
component native transition builds: 100
component native transition options: 900
component native transition deduplicated: 200
component native value option queries: 75
component native value option hits: 65
component native closure fallbacks: 4
component native cancellations: 3
scheduler subtasks generated: 300
scheduler subtasks released: 280
scheduler subtasks never released: 20
scheduler abandoned published: 8
scheduler stale queued: 5
scheduler stale results: 3
scheduler no-work polls: 12
scheduler ready high-water: 16
component bag db loaded signatures: 500
component bag db loaded bags: 400
component bag db load: 0.125000s
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
        self.assertEqual(parsed["reserve_cardinality_skips"], 75)
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
        self.assertEqual(parsed["component_bag_queries"], 200)
        self.assertEqual(parsed["component_bag_hits"], 201)
        self.assertEqual(parsed["component_bag_local_hits"], 151)
        self.assertEqual(parsed["component_bag_inserts"], 202)
        self.assertEqual(parsed["component_bag_local_duplicate_inserts"], 7)
        self.assertEqual(parsed["component_bag_shared_queries"], 50)
        self.assertEqual(parsed["component_bag_shared_hits"], 25)
        self.assertEqual(parsed["component_bag_persistent_hits"], 15)
        self.assertEqual(parsed["component_bag_shared_inserts"], 20)
        self.assertEqual(parsed["component_bag_shared_duplicate_inserts"], 5)
        self.assertEqual(parsed["component_bag_raw_id_hits"], 203)
        self.assertEqual(parsed["component_bag_signature_hits"], 204)
        self.assertEqual(parsed["component_signature_shared_queries"], 40)
        self.assertEqual(parsed["component_signature_shared_hits"], 30)
        self.assertEqual(parsed["component_signature_shared_inserts"], 10)
        self.assertEqual(parsed["component_native_calls"], 90)
        self.assertEqual(parsed["component_native_eligible"], 80)
        self.assertEqual(parsed["component_native_solved"], 70)
        self.assertEqual(parsed["component_native_states"], 600)
        self.assertEqual(parsed["component_native_memo_hits"], 500)
        self.assertEqual(parsed["component_native_transition_queries"], 400)
        self.assertEqual(parsed["component_native_transition_hits"], 300)
        self.assertEqual(parsed["component_native_transition_builds"], 100)
        self.assertEqual(parsed["component_native_transition_options"], 900)
        self.assertEqual(parsed["component_native_transition_deduplicated"], 200)
        self.assertEqual(parsed["component_native_value_option_queries"], 75)
        self.assertEqual(parsed["component_native_value_option_hits"], 65)
        self.assertEqual(parsed["component_native_closure_fallbacks"], 4)
        self.assertEqual(parsed["component_native_cancellations"], 3)
        self.assertEqual(parsed["scheduler_subtasks_generated"], 300)
        self.assertEqual(parsed["scheduler_subtasks_released"], 280)
        self.assertEqual(parsed["scheduler_subtasks_never_released"], 20)
        self.assertEqual(parsed["scheduler_abandoned_published"], 8)
        self.assertEqual(parsed["scheduler_stale_queued"], 5)
        self.assertEqual(parsed["scheduler_stale_results"], 3)
        self.assertEqual(parsed["scheduler_no_work_polls"], 12)
        self.assertEqual(parsed["scheduler_ready_high_water"], 16)
        self.assertEqual(parsed["component_bag_db_loaded_signatures"], 500)
        self.assertEqual(parsed["component_bag_db_loaded_bags"], 400)
        self.assertEqual(parsed["component_bag_db_load_seconds"], 0.125)
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
