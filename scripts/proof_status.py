#!/usr/bin/env python3
"""Evaluate generated certificates against the 3xn proof obligations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "python"))

from col.core import ColBoard, P1, P2  # noqa: E402


def positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def nonnegative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def child_legals(
    board: ColBoard,
    p1_legal: int,
    p2_legal: int,
    turn: int,
    cell: int,
) -> tuple[int, int]:
    bit = 1 << cell
    blocked = bit | board.adjacency_masks[cell]
    if turn == P1:
        return p1_legal & ~blocked, p2_legal & ~bit
    return p1_legal & ~bit, p2_legal & ~blocked


def opening_certificate_replays(payload: dict[str, object], width: int) -> bool:
    openings = payload.get("openings")
    if payload.get("board") != f"3x{width}" or not isinstance(openings, list):
        return False
    board = ColBoard(3, width, use_symmetry=True)
    if len(openings) != board.num_cells:
        return False
    seen = set()
    for opening in openings:
        if not isinstance(opening, dict):
            return False
        p1_move = opening.get("p1_move")
        p2_response = opening.get("p2_response")
        if not isinstance(p1_move, int) or not isinstance(p2_response, int):
            return False
        seen.add(p1_move)
        child_p1, child_p2 = child_legals(
            board,
            board.all_cells_mask,
            board.all_cells_mask,
            P1,
            p1_move,
        )
        child_key = board.shadow_key(child_p1, child_p2, P2)
        if opening.get("child_key") != hex(child_key):
            return False
        if child_p2 & (1 << p2_response) == 0:
            return False
        target_p1, target_p2 = child_legals(
            board,
            child_p1,
            child_p2,
            P2,
            p2_response,
        )
        target_key = board.shadow_key(target_p1, target_p2, P1)
        if opening.get("target_key") != hex(target_key):
            return False
    return seen == set(range(board.num_cells))


def frontier_audit_status(
    frontier: dict[str, object],
    audit: dict[str, object],
) -> tuple[bool, str]:
    """Check that purity evidence describes the same nonempty frontier quotient."""

    details = frontier.get("details", {})
    summary = frontier.get("summary", {})
    widths = details.get("widths", {}) if isinstance(details, dict) else {}
    certificate_boards = (
        {f"3x{width}" for width in widths} if isinstance(widths, dict) else set()
    )
    audit_boards = audit.get("boards", [])
    audited_labels = (
        {
            str(board.get("board"))
            for board in audit_boards
            if isinstance(board, dict) and isinstance(board.get("board"), str)
        }
        if isinstance(audit_boards, list)
        else set()
    )
    aggregate = audit.get("aggregate", {})
    mixed_classes = (
        aggregate.get("mixed_frontier_classes") if isinstance(aggregate, dict) else None
    )
    frontier_radius = frontier.get("frontier_radius")
    audit_radius = audit.get("radius")
    board_records_valid = (
        isinstance(audit_boards, list)
        and bool(audit_boards)
        and all(
            isinstance(board, dict)
            and board.get("radius") == audit_radius
            and positive_int(board.get("observations"))
            and nonnegative_int(board.get("mixed_frontier_classes"))
            and isinstance(board.get("outcome_pure"), bool)
            for board in audit_boards
        )
    )
    metadata_matches = (
        type(frontier.get("schema_version")) is int
        and frontier.get("schema_version") == 1
        and type(audit.get("schema_version")) is int
        and audit.get("schema_version") == 1
        and audit.get("audit") == "3xn-frontier-outcome-purity"
        and audit.get("fresh_solve") is True
        and audit.get("tablebase_enabled") is False
        and positive_int(frontier_radius)
        and positive_int(audit_radius)
        and audit_radius == frontier_radius
        and isinstance(summary, dict)
        and positive_int(summary.get("certificates"))
        and positive_int(summary.get("transitions"))
        and bool(certificate_boards)
        and all(positive_int(count) for count in widths.values())
        and certificate_boards <= audited_labels
        and board_records_valid
        and isinstance(aggregate, dict)
        and positive_int(aggregate.get("observations"))
        and nonnegative_int(mixed_classes)
    )
    pure = (
        metadata_matches
        and mixed_classes == 0
        and aggregate.get("outcome_pure") is True
        and audit.get("outcome_pure") is True
        and all(
            isinstance(board, dict)
            and board.get("mixed_frontier_classes") == 0
            and board.get("outcome_pure") is True
            for board in audit_boards
        )
    )
    evidence = (
        f"closure_radius={frontier_radius}; audit_radius={audit_radius}; "
        f"certificate_boards={sorted(certificate_boards)}; "
        f"audited_boards={sorted(audited_labels)}; "
        f"mixed_classes={mixed_classes}; compatible={metadata_matches}"
    )
    return pure, evidence


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--frontier",
        type=Path,
        default=REPO_ROOT / "reports" / "3xn-frontier-closure.json",
    )
    parser.add_argument(
        "--cgt",
        type=Path,
        default=REPO_ROOT / "reports" / "cgt-component-certificates.json",
    )
    parser.add_argument(
        "--frontier-audit",
        type=Path,
        default=REPO_ROOT / "reports" / "3xn-frontier-abstraction-audit.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "reports" / "formal-proof-handoff.md",
    )
    parser.add_argument(
        "--opening-dir",
        type=Path,
        default=REPO_ROOT / "reports" / "opening-certificates",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    frontier = read_json(args.frontier)
    cgt = read_json(args.cgt)
    frontier_audit = read_json(args.frontier_audit)
    opening_widths = []
    for width in (3, 5, 7, 9, 11, 13):
        path = args.opening_dir / f"3x{width}.json"
        if not path.is_file():
            continue
        payload = read_json(path)
        if opening_certificate_replays(payload, width):
            opening_widths.append(width)
    summary = frontier.get("summary", {})
    details = frontier.get("details", {})
    if not isinstance(summary, dict):
        summary = {}
    if not isinstance(details, dict):
        details = {}
    held_out = details.get("held_out", {})
    held_out_summary = (
        {
            "width": held_out.get("width"),
            "frontiers": held_out.get("frontiers"),
            "seen_at_smaller_width": held_out.get("seen_at_smaller_width"),
            "novel_count": len(held_out.get("novel", [])),
        }
        if isinstance(held_out, dict)
        else held_out
    )
    cgt_errors = cgt.get("verification_errors", [])
    purity_passed, purity_evidence = frontier_audit_status(frontier, frontier_audit)

    obligations = [
        (
            "Transition replay",
            positive_int(summary.get("certificates"))
            and positive_int(summary.get("transitions"))
            and summary.get("invalid") == 0,
            f"invalid={summary.get('invalid')}",
        ),
        (
            "Empirical frontier target coverage",
            positive_int(summary.get("transitions"))
            and summary.get("frontier_open") == 0,
            f"open={summary.get('frontier_open')}",
        ),
        (
            "Matching sampled frontier outcome purity",
            purity_passed,
            purity_evidence,
        ),
        (
            "Frontier response congruence",
            False,
            "no checker proves one abstract response rule works for every concretization",
        ),
        (
            "Held-out width prediction",
            isinstance(held_out, dict)
            and positive_int(held_out.get("frontiers"))
            and held_out.get("width") is not None
            and not held_out.get("novel", []),
            f"held_out={held_out_summary}",
        ),
        (
            "Local CGT recurrences",
            isinstance(cgt_errors, list) and not cgt_errors,
            f"errors={len(cgt_errors) if isinstance(cgt_errors, list) else 'invalid'}",
        ),
        (
            "Opening reduction through width 13",
            opening_widths == [3, 5, 7, 9, 11, 13],
            f"widths={opening_widths}",
        ),
        (
            "Evidence reaches width 13",
            isinstance(details, dict) and "13" in details.get("widths", {}),
            f"widths={details.get('widths') if isinstance(details, dict) else None}",
        ),
        (
            "Symbolic two-column extension",
            False,
            "no generated certificate currently quantifies over arbitrary neutral middle length",
        ),
    ]
    proved = all(passed for _, passed, _ in obligations)
    lines = [
        "# Formal Proof Handoff",
        "",
        f"Status: **{'PROVED' if proved else 'NOT PROVED'}**",
        "",
        "This gate intentionally distinguishes finite computational evidence from an "
        "all-width theorem. It exits successfully only after every finite certificate "
        "replays, the proposed frontier quotient passes finite soundness checks, width "
        "13 is covered, and a symbolic two-column extension certificate exists.",
        "",
        "| Obligation | Passed | Evidence |",
        "|---|---:|---|",
    ]
    for name, passed, evidence in obligations:
        lines.append(f"| {name} | {passed} | `{evidence}` |")
    lines.extend(
        [
            "",
            "## Formalization order",
            "",
            "1. Define legal-mask shadow states and prove stone histories with the same masks have identical options.",
            "2. Prove termination by strict decrease of the union of legal masks.",
            "3. Prove disconnected live components form a disjunctive sum.",
            "4. Import and check the finite local CGT option recurrences.",
            "5. Import and replay the frontier response table.",
            "6. Prove the symbolic `n → n+2` extension and conclude all odd `3×n` by induction.",
            "",
            "The generated JSON files are explicit audit artifacts. They are not treated as "
            "axioms: an eventual Lean development should parse or regenerate them and use "
            "finite decision procedures for steps 4 and 5.",
        ]
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    return 0 if proved else 2


if __name__ == "__main__":
    raise SystemExit(main())
