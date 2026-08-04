#!/usr/bin/env python3
"""Audit whether a radius-N 3xn frontier quotient is outcome-pure.

The audit performs fresh, tablebase-free exact solves.  Every memo key is
oriented so the side to move is called P1, which removes the ambiguity caused
by global color-swap canonicalization.  It then groups all memo states by the
same frontier signature used by ``verify_3xn_certificates.py`` and reports any
class containing both winning and losing concrete states.

Finding a mixed class proves that the quotient is not a sound losing-state
abstraction.  Finding none is only finite evidence from the searched boards;
it is not an all-width proof.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "python"))

from col.boards import BoardSpec  # noqa: E402
from col.core import ColBoard, P1, P2, StateKey  # noqa: E402
from col.dfs import DfsSolver  # noqa: E402
from col.tablebase import Tablebase  # noqa: E402
from scripts.verify_3xn_certificates import (  # noqa: E402
    canonical_signature,
    frontier_signature,
)


DEFAULT_BOARDS = ("3x5", "3x7", "3x9")
MARKDOWN_MIXED_CLASS_LIMIT = 10


@dataclass(frozen=True)
class OrientedMasks:
    """Legal masks with the side to move consistently represented as P1."""

    p1_legal: int
    p2_legal: int
    stored_turn: int
    color_swapped: bool


@dataclass(frozen=True)
class StateObservation:
    """One memo entry labeled by its exact and quotient signatures."""

    frontier_signature: str
    exact_signature: str
    side_to_move_wins: bool
    board: str = ""
    memo_key: str = ""
    p1_legal: str = "0x0"
    p2_legal: str = "0x0"
    stored_turn: int = P1
    color_swapped: bool = False

    def example_payload(self) -> dict[str, object]:
        return {
            "board": self.board,
            "memo_key": self.memo_key,
            "stored_turn": f"P{self.stored_turn + 1}",
            "color_swapped_to_p1": self.color_swapped,
            "oriented_p1_legal": self.p1_legal,
            "oriented_p2_legal": self.p2_legal,
            "exact_signature": self.exact_signature,
            "side_to_move_wins": self.side_to_move_wins,
        }


@dataclass(frozen=True)
class OutcomeGroup:
    """Outcome counts and witnesses for one quotient class."""

    frontier_signature: str
    winning_count: int
    losing_count: int
    winning_examples: tuple[StateObservation, ...]
    losing_examples: tuple[StateObservation, ...]

    @property
    def state_count(self) -> int:
        return self.winning_count + self.losing_count

    @property
    def mixed(self) -> bool:
        return self.winning_count > 0 and self.losing_count > 0

    def payload(self) -> dict[str, object]:
        return {
            "frontier_signature": self.frontier_signature,
            "state_count": self.state_count,
            "winning_count": self.winning_count,
            "losing_count": self.losing_count,
            "winning_examples": [
                observation.example_payload() for observation in self.winning_examples
            ],
            "losing_examples": [
                observation.example_payload() for observation in self.losing_examples
            ],
        }


def parse_board(text: str) -> BoardSpec:
    """Parse an odd 3xN board for argparse."""

    try:
        board = BoardSpec.parse(text)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if board.m != 3 or board.n < 3 or board.n % 2 == 0:
        raise argparse.ArgumentTypeError(
            f"{text!r} is not an odd 3xN board with N >= 3"
        )
    return board


def orient_key_to_p1(board: ColBoard, key: StateKey) -> OrientedMasks:
    """Decode ``key`` with its actor represented as P1.

    ``ColBoard.shadow_key`` identifies ``(p1, p2, P1)`` with
    ``(p2, p1, P2)``.  Consequently the stored turn is a canonicalization
    detail, not a stable player label.  Swapping masks for stored P2 keys gives
    every observation the same actor-relative meaning.
    """

    p1_legal, p2_legal, stored_turn = board.unpack_key(key)
    if stored_turn == P1:
        oriented = OrientedMasks(p1_legal, p2_legal, stored_turn, False)
    elif stored_turn == P2:
        oriented = OrientedMasks(p2_legal, p1_legal, stored_turn, True)
    else:  # Defensive: packed keys currently use exactly one turn bit.
        raise ValueError(f"invalid stored turn {stored_turn} for key {key}")

    if board.shadow_key(oriented.p1_legal, oriented.p2_legal, P1) != key:
        raise ValueError(f"actor-oriented masks do not reproduce memo key {hex(key)}")
    return oriented


def observe_memo(
    board: ColBoard,
    memo: Mapping[StateKey, bool],
    radius: int,
) -> list[StateObservation]:
    """Convert every memo entry to an actor-relative frontier observation."""

    if radius <= 0:
        raise ValueError("radius must be positive")

    observations: list[StateObservation] = []
    for key, side_to_move_wins in memo.items():
        oriented = orient_key_to_p1(board, key)
        exact = canonical_signature(
            board,
            oriented.p1_legal,
            oriented.p2_legal,
        )
        observations.append(
            StateObservation(
                frontier_signature=frontier_signature(exact, radius),
                exact_signature=exact,
                side_to_move_wins=bool(side_to_move_wins),
                board=f"{board.m}x{board.n}",
                memo_key=hex(key),
                p1_legal=hex(oriented.p1_legal),
                p2_legal=hex(oriented.p2_legal),
                stored_turn=oriented.stored_turn,
                color_swapped=oriented.color_swapped,
            )
        )
    return observations


def group_outcomes(
    observations: Iterable[StateObservation],
    *,
    max_examples_per_outcome: int = 1,
) -> list[OutcomeGroup]:
    """Group observations by quotient signature and retain concrete witnesses."""

    if max_examples_per_outcome <= 0:
        raise ValueError("max_examples_per_outcome must be positive")

    grouped: dict[str, list[StateObservation]] = defaultdict(list)
    for observation in observations:
        grouped[observation.frontier_signature].append(observation)

    summaries: list[OutcomeGroup] = []
    for signature in sorted(grouped):
        ordered = sorted(
            grouped[signature],
            key=lambda observation: (
                observation.exact_signature,
                observation.memo_key,
                observation.p1_legal,
                observation.p2_legal,
            ),
        )
        winning = [
            observation for observation in ordered if observation.side_to_move_wins
        ]
        losing = [
            observation for observation in ordered if not observation.side_to_move_wins
        ]
        summaries.append(
            OutcomeGroup(
                frontier_signature=signature,
                winning_count=len(winning),
                losing_count=len(losing),
                winning_examples=tuple(winning[:max_examples_per_outcome]),
                losing_examples=tuple(losing[:max_examples_per_outcome]),
            )
        )
    return summaries


def _audit_board_with_observations(
    board_spec: BoardSpec,
    radius: int,
    *,
    max_examples_per_outcome: int = 1,
) -> tuple[dict[str, object], list[StateObservation]]:
    """Fresh-solve one board and audit its complete produced memo."""

    solver = DfsSolver(
        board_spec.m,
        board_spec.n,
        use_symmetry=True,
        tablebase=Tablebase(enabled=False),
        progress=False,
        mobility_order=True,
    )
    started_at = time.perf_counter()
    empty_p1_wins = solver.solve()
    solve_seconds = time.perf_counter() - started_at

    observations = observe_memo(solver.board, solver.memo, radius)
    groups = group_outcomes(
        observations,
        max_examples_per_outcome=max_examples_per_outcome,
    )
    mixed_groups = [group for group in groups if group.mixed]
    outcome_counts = Counter(
        observation.side_to_move_wins for observation in observations
    )
    stored_turn_counts = Counter(
        observation.stored_turn for observation in observations
    )

    result = {
        "board": board_spec.label,
        "radius": radius,
        "empty_p1_wins": empty_p1_wins,
        "solve_seconds": solve_seconds,
        "states_searched": solver.stats.states_searched,
        "memo_entries": len(solver.memo),
        "observations": len(observations),
        "frontier_classes": len(groups),
        "pure_frontier_classes": len(groups) - len(mixed_groups),
        "mixed_frontier_classes": len(mixed_groups),
        "states_in_mixed_classes": sum(group.state_count for group in mixed_groups),
        "side_to_move_winning_states": outcome_counts[True],
        "side_to_move_losing_states": outcome_counts[False],
        "stored_p1_turn_states": stored_turn_counts[P1],
        "stored_p2_turn_states": stored_turn_counts[P2],
        "color_swapped_to_p1_states": sum(
            observation.color_swapped for observation in observations
        ),
        "outcome_pure": not mixed_groups,
        "mixed_classes": [group.payload() for group in mixed_groups],
    }
    return result, observations


def audit_board(
    board_spec: BoardSpec,
    radius: int,
    *,
    max_examples_per_outcome: int = 1,
) -> dict[str, object]:
    """Fresh-solve one board and return its within-width purity audit."""

    result, _ = _audit_board_with_observations(
        board_spec,
        radius,
        max_examples_per_outcome=max_examples_per_outcome,
    )
    return result


def audit_boards(
    boards: Sequence[BoardSpec],
    radius: int,
    *,
    max_examples_per_outcome: int = 1,
) -> dict[str, object]:
    board_audits = [
        _audit_board_with_observations(
            board,
            radius,
            max_examples_per_outcome=max_examples_per_outcome,
        )
        for board in boards
    ]
    board_results = [result for result, _ in board_audits]
    observations = [
        observation
        for _, board_observations in board_audits
        for observation in board_observations
    ]
    aggregate_groups = group_outcomes(
        observations,
        max_examples_per_outcome=max_examples_per_outcome,
    )
    aggregate_mixed = [group for group in aggregate_groups if group.mixed]
    within_board_mixed_signatures = {
        str(group["frontier_signature"])
        for result in board_results
        for group in result["mixed_classes"]
        if isinstance(group, dict)
    }
    cross_width_only = [
        group
        for group in aggregate_mixed
        if group.frontier_signature not in within_board_mixed_signatures
    ]
    aggregate = {
        "observations": len(observations),
        "frontier_classes": len(aggregate_groups),
        "pure_frontier_classes": len(aggregate_groups) - len(aggregate_mixed),
        "mixed_frontier_classes": len(aggregate_mixed),
        "states_in_mixed_classes": sum(group.state_count for group in aggregate_mixed),
        "cross_width_only_mixed_classes": len(cross_width_only),
        "outcome_pure": not aggregate_mixed,
        "mixed_classes": [group.payload() for group in aggregate_mixed],
    }
    return {
        "schema_version": 1,
        "audit": "3xn-frontier-outcome-purity",
        "radius": radius,
        "fresh_solve": True,
        "tablebase_enabled": False,
        "perspective": "side to move is oriented as P1",
        "outcome_pure": not aggregate_mixed,
        "aggregate": aggregate,
        "boards": board_results,
    }


def write_markdown(path: Path, payload: Mapping[str, object]) -> None:
    board_results = payload.get("boards", [])
    if not isinstance(board_results, list):
        raise ValueError("audit payload boards must be a list")

    aggregate = payload.get("aggregate")
    if not isinstance(aggregate, dict):
        raise ValueError("audit payload aggregate must be an object")
    report_results = [
        {
            **aggregate,
            "board": "Across requested boards",
            "memo_entries": aggregate["observations"],
        },
        *board_results,
    ]

    lines = [
        "# 3xn Frontier Outcome-Purity Audit",
        "",
        "This report comes from fresh, tablebase-free exact solves. Memo keys are",
        "oriented so the side to move is represented as P1 before applying the same",
        "frontier signature used by `verify_3xn_certificates.py`.",
        "",
        "A mixed class is a concrete proof that the quotient is not outcome-pure.",
        "No mixed class would only be finite evidence for the boards searched, not an",
        "all-width proof.",
        "",
        "| Board | Memo states | Frontier classes | Mixed classes | Mixed states | Pure? |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for result in report_results:
        if not isinstance(result, dict):
            raise ValueError("board result must be an object")
        lines.append(
            f"| {result['board']} | {int(result['memo_entries']):,} | "
            f"{int(result['frontier_classes']):,} | "
            f"{int(result['mixed_frontier_classes']):,} | "
            f"{int(result['states_in_mixed_classes']):,} | "
            f"{result['outcome_pure']} |"
        )

    for result in report_results:
        if not isinstance(result, dict):
            continue
        lines.extend(["", f"## {result['board']}", ""])
        mixed_classes = result.get("mixed_classes", [])
        if not isinstance(mixed_classes, list) or not mixed_classes:
            lines.append("No mixed class was observed.")
            continue
        lines.append(
            f"Showing {min(len(mixed_classes), MARKDOWN_MIXED_CLASS_LIMIT):,} of "
            f"{len(mixed_classes):,} mixed classes. The JSON artifact contains every mixed class."
        )
        for mixed in mixed_classes[:MARKDOWN_MIXED_CLASS_LIMIT]:
            if not isinstance(mixed, dict):
                continue
            lines.extend(
                [
                    "",
                    f"### `{mixed['frontier_signature']}`",
                    "",
                    f"- Winning states: `{mixed['winning_count']}`",
                    f"- Losing states: `{mixed['losing_count']}`",
                ]
            )
            for label, field in (
                ("Winning example", "winning_examples"),
                ("Losing example", "losing_examples"),
            ):
                examples = mixed.get(field, [])
                if not isinstance(examples, list) or not examples:
                    continue
                example = examples[0]
                if not isinstance(example, dict):
                    continue
                lines.append(
                    f"- {label} ({example.get('board', '?')}): `{example['exact_signature']}` "
                    f"(key `{example['memo_key']}`)"
                )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--boards",
        nargs="+",
        type=parse_board,
        default=[parse_board(text) for text in DEFAULT_BOARDS],
        help="Odd 3xN boards to solve (default: 3x5 3x7 3x9).",
    )
    parser.add_argument(
        "--radius",
        type=int,
        default=2,
        help="Columns retained at each frontier (default: 2).",
    )
    parser.add_argument(
        "--max-examples-per-outcome",
        type=int,
        default=1,
        help="Concrete winning and losing witnesses retained per mixed class.",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=REPO_ROOT / "reports" / "3xn-frontier-abstraction-audit.json",
    )
    parser.add_argument(
        "--out-md",
        type=Path,
        default=REPO_ROOT / "reports" / "3xn-frontier-abstraction-audit.md",
    )
    args = parser.parse_args(argv)
    if args.radius <= 0:
        parser.error("--radius must be positive")
    if args.max_examples_per_outcome <= 0:
        parser.error("--max-examples-per-outcome must be positive")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    payload = audit_boards(
        args.boards,
        args.radius,
        max_examples_per_outcome=args.max_examples_per_outcome,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_markdown(args.out_md, payload)
    print(f"wrote {args.out_json}")
    print(f"wrote {args.out_md}")
    return 0 if payload["outcome_pure"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
