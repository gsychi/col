#!/usr/bin/env python3
"""Replay 3xn transition certificates and measure frontier-family closure."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "python"))

from col.boards import BoardSpec  # noqa: E402
from col.core import ColBoard, P1, P2  # noqa: E402


@dataclass
class VerificationSummary:
    certificates: int = 0
    transitions: int = 0
    invalid: int = 0
    exact_closed: int = 0
    exact_open: int = 0
    frontier_closed: int = 0
    frontier_open: int = 0


def char_from_legal(p1: bool, p2: bool) -> str:
    if p1 and p2:
        return "o"
    if p1:
        return "b"
    if p2:
        return "w"
    return "."


def grid_from_masks(board: ColBoard, p1_legal: int, p2_legal: int) -> tuple[str, ...]:
    return tuple(
        "".join(
            char_from_legal(
                bool(p1_legal & (1 << (row * board.n + col))),
                bool(p2_legal & (1 << (row * board.n + col))),
            )
            for col in range(board.n)
        )
        for row in range(board.m)
    )


def render(grid: Sequence[str]) -> str:
    return "/".join(grid)


def symmetries(grid: Sequence[str]) -> tuple[str, ...]:
    horizontal = tuple(line[::-1] for line in grid)
    vertical = tuple(reversed(grid))
    both = tuple(line[::-1] for line in reversed(grid))
    return tuple(sorted({render(grid), render(horizontal), render(vertical), render(both)}))


def canonical_signature(board: ColBoard, p1_legal: int, p2_legal: int) -> str:
    return symmetries(grid_from_masks(board, p1_legal, p2_legal))[0]


def frontier_signature(signature: str, radius: int) -> str:
    rows = signature.split("/")
    width = len(rows[0])
    variants = []
    for variant in symmetries(rows):
        grid = variant.split("/")
        if width <= radius * 2:
            variants.append(variant)
        else:
            left = "/".join(row[:radius] for row in grid)
            right = "/".join(row[-radius:] for row in grid)
            variants.append(f"{left}|*|{right}")
    return min(variants)


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


def load_certificates(path: Path) -> list[dict[str, object]]:
    certificates = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                certificates.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: {exc}") from exc
    return certificates


def verify(
    certificates: Sequence[dict[str, object]],
    radius: int,
) -> tuple[VerificationSummary, list[str], dict[str, object]]:
    summary = VerificationSummary(certificates=len(certificates))
    errors: list[str] = []
    exact_sources = {str(certificate["source_signature"]) for certificate in certificates}
    frontier_sources = {
        frontier_signature(str(certificate["source_signature"]), radius)
        for certificate in certificates
    }
    widths: Counter[int] = Counter()
    source_frontiers_by_width: dict[int, set[str]] = defaultdict(set)

    for certificate in certificates:
        board_spec = BoardSpec.parse(str(certificate["board"]))
        board = ColBoard(board_spec.m, board_spec.n, use_symmetry=True)
        p1_legal = int(str(certificate["p1_legal"]), 16)
        p2_legal = int(str(certificate["p2_legal"]), 16)
        source = canonical_signature(board, p1_legal, p2_legal)
        widths[board.n] += 1
        source_frontiers_by_width[board.n].add(frontier_signature(source, radius))
        if source != certificate["source_signature"]:
            errors.append(f"{board_spec.label}/{certificate['source_key']}: source signature mismatch")
            summary.invalid += 1
            continue

        transitions = certificate.get("transitions")
        if not isinstance(transitions, list):
            errors.append(f"{board_spec.label}/{certificate['source_key']}: transitions not a list")
            summary.invalid += 1
            continue
        expected_moves = {cell for cell in range(board.num_cells) if p1_legal & (1 << cell)}
        actual_moves = {int(transition["p1_move"]) for transition in transitions}
        if actual_moves != expected_moves:
            errors.append(f"{board_spec.label}/{certificate['source_key']}: incomplete P1 move coverage")
            summary.invalid += 1
            continue

        for transition in transitions:
            summary.transitions += 1
            p1_move = int(transition["p1_move"])
            p2_response = int(transition["p2_response"])
            if p1_legal & (1 << p1_move) == 0:
                errors.append(f"{board_spec.label}: illegal P1 move {p1_move}")
                summary.invalid += 1
                continue
            child_p1, child_p2 = child_legals(board, p1_legal, p2_legal, P1, p1_move)
            if child_p2 & (1 << p2_response) == 0:
                errors.append(f"{board_spec.label}: illegal P2 response {p2_response}")
                summary.invalid += 1
                continue
            target_p1, target_p2 = child_legals(
                board,
                child_p1,
                child_p2,
                P2,
                p2_response,
            )
            target_key = board.shadow_key(target_p1, target_p2, P1)
            target = canonical_signature(board, target_p1, target_p2)
            if hex(target_key) != transition["target_key"] or target != transition["target_signature"]:
                errors.append(f"{board_spec.label}: target replay mismatch")
                summary.invalid += 1
                continue
            if target in exact_sources:
                summary.exact_closed += 1
            else:
                summary.exact_open += 1
            if frontier_signature(target, radius) in frontier_sources:
                summary.frontier_closed += 1
            else:
                summary.frontier_open += 1

    held_out: dict[str, object] = {}
    if source_frontiers_by_width:
        held_width = max(source_frontiers_by_width)
        discovered = set().union(
            *(
                frontiers
                for width, frontiers in source_frontiers_by_width.items()
                if width != held_width
            )
        )
        held_frontiers = source_frontiers_by_width[held_width]
        held_out = {
            "width": held_width,
            "frontiers": len(held_frontiers),
            "seen_at_smaller_width": len(held_frontiers & discovered),
            "novel": sorted(held_frontiers - discovered),
        }
    details = {
        "widths": dict(sorted(widths.items())),
        "exact_family_size": len(exact_sources),
        "frontier_family_size": len(frontier_sources),
        "held_out": held_out,
    }
    return summary, errors, details


def write_report(
    path: Path,
    summary: VerificationSummary,
    errors: Sequence[str],
    details: dict[str, object],
    radius: int,
) -> None:
    total = summary.frontier_closed + summary.frontier_open
    closure = summary.frontier_closed / total if total else 0.0
    held_out = details.get("held_out", {})
    held_novel = held_out.get("novel", []) if isinstance(held_out, dict) else []
    held_summary = {
        "width": held_out.get("width") if isinstance(held_out, dict) else None,
        "frontiers": held_out.get("frontiers") if isinstance(held_out, dict) else None,
        "seen_at_smaller_width": (
            held_out.get("seen_at_smaller_width")
            if isinstance(held_out, dict)
            else None
        ),
        "novel_count": len(held_novel),
        "novel_examples": held_novel[:20],
    }
    lines = [
        "# 3xn Frontier Certificate Verification",
        "",
        f"- Certificates: `{summary.certificates:,}`",
        f"- Replayed transitions: `{summary.transitions:,}`",
        f"- Invalid records: `{summary.invalid:,}`",
        f"- Exact whole-state family size: `{details['exact_family_size']:,}`",
        f"- Radius-{radius} frontier family size: `{details['frontier_family_size']:,}`",
        f"- Empirical frontier target coverage: `{summary.frontier_closed:,}/{total:,}` (`{closure:.2%}`)",
        f"- Width coverage: `{details['widths']}`",
        "- Quotient soundness: `not checked here` (run `audit_3xn_frontier_abstraction.py`)",
        "",
        "## Held-out widest strip",
        "",
        f"`{held_summary}`",
        "",
        "These coverage counts do not establish a finite-state induction. A proof also needs an "
        "outcome-pure, response-congruent quotient and a symbolic all-width extension theorem. "
        "Replay errors, open targets, and held-out novel signatures remain concrete gaps.",
    ]
    if errors:
        lines.extend(["", "## Replay errors", ""])
        lines.extend(f"- {error}" for error in errors[:100])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--certificates",
        type=Path,
        default=REPO_ROOT / "reports" / "3xn-transition-certificates.jsonl",
    )
    parser.add_argument("--frontier-radius", type=int, default=2)
    parser.add_argument(
        "--out-json",
        type=Path,
        default=REPO_ROOT / "reports" / "3xn-frontier-closure.json",
    )
    parser.add_argument(
        "--out-md",
        type=Path,
        default=REPO_ROOT / "reports" / "3xn-frontier-closure.md",
    )
    args = parser.parse_args(argv)
    if args.frontier_radius <= 0:
        parser.error("--frontier-radius must be positive")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    certificates = load_certificates(args.certificates)
    summary, errors, details = verify(certificates, args.frontier_radius)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "frontier_radius": args.frontier_radius,
                "summary": summary.__dict__,
                "details": details,
                "errors": errors,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    write_report(args.out_md, summary, errors, details, args.frontier_radius)
    print(f"wrote {args.out_json}")
    print(f"wrote {args.out_md}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
