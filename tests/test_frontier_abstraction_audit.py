from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "python"))

from col.boards import BoardSpec
from col.core import ColBoard, P1, P2
from scripts.audit_3xn_frontier_abstraction import (
    StateObservation,
    audit_board,
    audit_boards,
    group_outcomes,
    orient_key_to_p1,
)
from scripts.proof_status import frontier_audit_status
from scripts.verify_3xn_certificates import canonical_signature


class FrontierAbstractionAuditTests(unittest.TestCase):
    def test_pure_toy_grouping(self) -> None:
        groups = group_outcomes(
            [
                StateObservation("left", "state-a", True),
                StateObservation("left", "state-b", True),
                StateObservation("right", "state-c", False),
            ]
        )

        self.assertEqual(
            [group.frontier_signature for group in groups], ["left", "right"]
        )
        self.assertTrue(all(not group.mixed for group in groups))
        self.assertEqual(groups[0].winning_count, 2)
        self.assertEqual(groups[0].losing_count, 0)
        self.assertEqual(groups[1].winning_count, 0)
        self.assertEqual(groups[1].losing_count, 1)

    def test_color_swapped_key_is_oriented_to_p1(self) -> None:
        board = ColBoard(3, 5, use_symmetry=True)
        p1_legal = (1 << 0) | (1 << 7)
        p2_legal = (1 << 4) | (1 << 12)
        key = board.shadow_key(p1_legal, p2_legal, P2)

        oriented = orient_key_to_p1(board, key)

        self.assertEqual(oriented.stored_turn, P2)
        self.assertTrue(oriented.color_swapped)
        self.assertEqual(
            canonical_signature(board, oriented.p1_legal, oriented.p2_legal),
            canonical_signature(board, p2_legal, p1_legal),
        )
        self.assertEqual(
            board.shadow_key(oriented.p1_legal, oriented.p2_legal, P1),
            key,
        )

    def test_radius_two_has_known_mixed_3x5_class(self) -> None:
        result = audit_board(BoardSpec(3, 5), radius=2)

        self.assertFalse(result["outcome_pure"])
        self.assertGreater(result["mixed_frontier_classes"], 0)
        mixed = {
            group["frontier_signature"]: group for group in result["mixed_classes"]
        }
        terminal_frontier = "../../..|*|../../.."
        self.assertIn(terminal_frontier, mixed)
        self.assertGreater(mixed[terminal_frontier]["winning_count"], 0)
        self.assertGreater(mixed[terminal_frontier]["losing_count"], 0)

    def test_cross_width_only_mixture_is_in_top_level_audit(self) -> None:
        pure_result = {
            "outcome_pure": True,
            "mixed_classes": [],
        }
        observations = [
            [StateObservation("shared", "state-a", True, board="3x5")],
            [StateObservation("shared", "state-b", False, board="3x7")],
        ]
        with patch(
            "scripts.audit_3xn_frontier_abstraction._audit_board_with_observations",
            side_effect=[
                ({**pure_result, "board": "3x5"}, observations[0]),
                ({**pure_result, "board": "3x7"}, observations[1]),
            ],
        ):
            result = audit_boards([BoardSpec(3, 5), BoardSpec(3, 7)], radius=2)

        self.assertFalse(result["outcome_pure"])
        self.assertEqual(result["aggregate"]["mixed_frontier_classes"], 1)
        self.assertEqual(
            result["aggregate"]["cross_width_only_mixed_classes"],
            1,
        )
        mixed = result["aggregate"]["mixed_classes"][0]
        self.assertEqual(mixed["winning_examples"][0]["board"], "3x5")
        self.assertEqual(mixed["losing_examples"][0]["board"], "3x7")

    def test_proof_gate_rejects_radius_mismatch_and_empty_evidence(self) -> None:
        frontier = {
            "schema_version": 1,
            "frontier_radius": 2,
            "summary": {"certificates": 1, "transitions": 1},
            "details": {"widths": {"5": 1}},
        }
        audit = {
            "schema_version": 1,
            "audit": "3xn-frontier-outcome-purity",
            "radius": 2,
            "fresh_solve": True,
            "tablebase_enabled": False,
            "outcome_pure": True,
            "aggregate": {
                "observations": 1,
                "mixed_frontier_classes": 0,
                "outcome_pure": True,
            },
            "boards": [
                {
                    "board": "3x5",
                    "radius": 2,
                    "observations": 1,
                    "mixed_frontier_classes": 0,
                    "outcome_pure": True,
                }
            ],
        }

        self.assertTrue(frontier_audit_status(frontier, audit)[0])
        audit["radius"] = 3
        audit["boards"][0]["radius"] = 3
        self.assertFalse(frontier_audit_status(frontier, audit)[0])
        audit["boards"] = []
        audit["aggregate"]["observations"] = 0
        self.assertFalse(frontier_audit_status(frontier, audit)[0])


if __name__ == "__main__":
    unittest.main()
