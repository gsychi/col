from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "python"))

from col.core import ColBoard, P1
from scripts.build_3xn_strategy_dag import (
    Board,
    build_artifact,
    canonical_signature,
)
from scripts.verify_3xn_strategy_dag import verify_artifact


class RootedStrategyDagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.artifact = build_artifact([Board.parse("3x5")])

    def test_fresh_rooted_strategy_replays(self) -> None:
        result = verify_artifact(self.artifact)
        self.assertEqual(result.errors, [])
        self.assertTrue(result.ok)
        board = self.artifact["boards"][0]
        self.assertGreater(board["summary"]["transition_nodes"], 0)
        self.assertGreater(board["summary"]["pairing_leaves"], 0)
        self.assertEqual(
            result.boards[0]["nodes"],
            result.boards[0]["reachable_nodes"],
        )

    def test_missing_move_is_rejected(self) -> None:
        artifact = copy.deepcopy(self.artifact)
        board = artifact["boards"][0]
        node = next(node for node in board["nodes"] if node["kind"] == "transitions")
        node["transitions"].pop()
        board["summary"]["transitions"] -= 1

        result = verify_artifact(artifact)
        self.assertFalse(result.ok)
        self.assertTrue(
            any("incomplete P1 move coverage" in error for error in result.errors),
            result.errors,
        )

    def test_mutated_pairing_leaf_is_rejected(self) -> None:
        artifact = copy.deepcopy(self.artifact)
        board = artifact["boards"][0]
        node = next(
            node for node in board["nodes"] if node["kind"] == "half_turn_pairing"
        )
        node["p2_legal"] = hex(int(node["p2_legal"], 16) ^ 1)

        result = verify_artifact(artifact)
        self.assertFalse(result.ok)
        self.assertTrue(
            any("half-turn pairing predicate" in error for error in result.errors),
            result.errors,
        )

    def test_unreachable_extra_node_is_rejected(self) -> None:
        artifact = copy.deepcopy(self.artifact)
        record = artifact["boards"][0]
        board = ColBoard(3, 5, use_symmetry=True)
        existing = {node["id"] for node in record["nodes"]}
        for p2_legal in range(1, board.all_cells_mask + 1):
            node_id = hex(board.shadow_key(0, p2_legal, P1))
            if node_id not in existing:
                break
        else:  # pragma: no cover - the finite search above always finds one
            self.fail("could not construct a distinct terminal node")
        record["nodes"].append(
            {
                "id": node_id,
                "p1_legal": "0x0",
                "p2_legal": hex(p2_legal),
                "signature": canonical_signature(board, 0, p2_legal),
                "kind": "terminal",
                "transitions": [],
            }
        )
        record["summary"]["nodes"] += 1
        record["summary"]["terminal_leaves"] += 1

        result = verify_artifact(artifact)
        self.assertFalse(result.ok)
        self.assertTrue(
            any("unreachable node" in error for error in result.errors),
            result.errors,
        )

    def test_noncanonical_duplicate_board_is_rejected(self) -> None:
        artifact = copy.deepcopy(self.artifact)
        duplicate = copy.deepcopy(artifact["boards"][0])
        duplicate["board"] = "5x3"
        artifact["boards"].append(duplicate)

        result = verify_artifact(artifact)
        self.assertFalse(result.ok)
        self.assertTrue(
            any("board label is not canonical" in error for error in result.errors),
            result.errors,
        )
        self.assertIn("artifact contains duplicate board records", result.errors)

    def test_boolean_schema_version_is_rejected(self) -> None:
        artifact = copy.deepcopy(self.artifact)
        artifact["schema_version"] = True

        result = verify_artifact(artifact)
        self.assertFalse(result.ok)
        self.assertTrue(
            any("unsupported schema_version" in error for error in result.errors),
            result.errors,
        )


if __name__ == "__main__":
    unittest.main()
