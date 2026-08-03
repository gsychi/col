from __future__ import annotations

import sys
import unittest
from dataclasses import asdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "python"))

from col.boards import odd_boards
from col.core import P1
from col.dfs import DfsSolver
from col.tablebase import Tablebase
from scripts.certify_cgt_components import CertificateBuilder, parse_pattern, value_text
from scripts.mine_3xn_families import extract_state_certificate
from scripts.verify_3xn_certificates import verify


class BoardCatalogTests(unittest.TestCase):
    def test_odd_boards_through_39_are_complete(self) -> None:
        boards = odd_boards(39)
        self.assertEqual(len(boards), 27)
        self.assertEqual(
            [board.label for board in boards if not board.is_path],
            ["3x3", "3x5", "3x7", "5x5", "3x9", "3x11", "5x7", "3x13"],
        )
        self.assertTrue(all(board.m % 2 and board.n % 2 for board in boards))
        self.assertTrue(all(board.cells <= 39 for board in boards))


class LocalCertificateTests(unittest.TestCase):
    def test_known_component_values(self) -> None:
        builder = CertificateBuilder()
        expected = {
            "bow": "0",
            "b/o/w": "0",
            "ww/w.": "-2",
            "bbw/b..": "1",
        }
        for pattern, value in expected.items():
            with self.subTest(pattern=pattern):
                self.assertEqual(
                    value_text(builder.component_value(parse_pattern(pattern))),
                    value,
                )


class TransitionCertificateTests(unittest.TestCase):
    def test_small_root_certificate_replays(self) -> None:
        solver = DfsSolver(
            3,
            3,
            use_symmetry=True,
            tablebase=Tablebase(enabled=False),
            progress=False,
        )
        self.assertFalse(solver.solve())
        board = solver.board
        root_key = board.shadow_key(
            board.all_cells_mask,
            board.all_cells_mask,
            P1,
        )
        certificate = extract_state_certificate(
            solver,
            root_key,
            board.all_cells_mask,
            board.all_cells_mask,
        )
        self.assertIsNotNone(certificate)
        summary, errors, _details = verify([asdict(certificate)], radius=2)
        self.assertEqual(errors, [])
        self.assertEqual(summary.invalid, 0)


if __name__ == "__main__":
    unittest.main()
