#!/usr/bin/env python3
"""Independently replay and verify rooted 3xn P2 strategy DAG artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "python"))

from col.boards import BoardSpec  # noqa: E402
from col.core import ColBoard, P1, P2  # noqa: E402


SCHEMA_VERSION = 1
ARTIFACT_KIND = "col-3xn-rooted-strategy-dag"
NODE_KINDS = {"transitions", "terminal", "half_turn_pairing"}


@dataclass
class VerificationResult:
    errors: list[str] = field(default_factory=list)
    boards: list[dict[str, object]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, object]:
        return {"ok": self.ok, "boards": self.boards, "errors": self.errors}


@dataclass
class ParsedNode:
    raw: dict[str, object]
    node_id: str
    p1_legal: int
    p2_legal: int
    signature: str
    kind: str


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


def grid_from_masks(
    board: ColBoard,
    p1_legal: int,
    p2_legal: int,
) -> tuple[str, ...]:
    rows = []
    for row in range(board.m):
        chars = []
        for col in range(board.n):
            bit = 1 << (row * board.n + col)
            p1 = bool(p1_legal & bit)
            p2 = bool(p2_legal & bit)
            chars.append("o" if p1 and p2 else "b" if p1 else "w" if p2 else ".")
        rows.append("".join(chars))
    return tuple(rows)


def grid_symmetries(grid: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    horizontal = tuple(row[::-1] for row in grid)
    vertical = tuple(reversed(grid))
    both = tuple(row[::-1] for row in reversed(grid))
    variants = {grid, horizontal, vertical, both}
    if len(grid) == len(grid[0]):
        transpose = tuple(
            "".join(grid[row][col] for row in range(len(grid)))
            for col in range(len(grid[0]))
        )
        variants.update(
            {
                transpose,
                tuple(row[::-1] for row in transpose),
                tuple(reversed(transpose)),
                tuple(row[::-1] for row in reversed(transpose)),
            }
        )
    return tuple(variants)


def canonical_signature(board: ColBoard, p1_legal: int, p2_legal: int) -> str:
    grids = grid_symmetries(grid_from_masks(board, p1_legal, p2_legal))
    return min("/".join(grid) for grid in grids)


def parse_hex(value: object) -> int:
    if not isinstance(value, str) or not value.startswith("0x"):
        raise ValueError("expected a hexadecimal string")
    parsed = int(value, 16)
    if parsed < 0:
        raise ValueError("mask must be nonnegative")
    return parsed


def parse_move(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("move must be an integer")
    return value


def verify_pairing_leaf(
    board: ColBoard,
    node: ParsedNode,
    errors: list[str],
    prefix: str,
) -> None:
    p1_legal = node.p1_legal
    p2_legal = node.p2_legal
    if p1_legal & board.fixed_reflection_mask:
        errors.append(f"{prefix}: half-turn pairing has a fixed legal P1 move")
    if board.reflect_mask(p1_legal) != p2_legal:
        errors.append(f"{prefix}: half-turn pairing predicate does not hold")
        return

    remaining = p1_legal
    while remaining:
        bit = remaining & -remaining
        remaining ^= bit
        p1_move = bit.bit_length() - 1
        p2_response = board.reflected_cells[p1_move]
        child_p1, child_p2 = child_legals(board, p1_legal, p2_legal, P1, p1_move)
        response_bit = 1 << p2_response
        if child_p2 & response_bit == 0:
            errors.append(
                f"{prefix}: reflected response {p2_response} is illegal after {p1_move}"
            )
            continue
        target_p1, target_p2 = child_legals(board, child_p1, child_p2, P2, p2_response)
        if board.reflect_mask(target_p1) != target_p2:
            errors.append(
                f"{prefix}: reflected response after {p1_move} does not restore pairing"
            )


def verify_board(
    record: object,
    result: VerificationResult,
) -> None:
    if not isinstance(record, dict):
        result.errors.append("board record is not an object")
        return
    label = record.get("board")
    if not isinstance(label, str):
        result.errors.append("board record has no string board label")
        return
    prefix = label
    try:
        board_spec = BoardSpec.parse(label)
    except ValueError as exc:
        result.errors.append(f"{prefix}: invalid board label: {exc}")
        return
    if label != board_spec.label:
        result.errors.append(
            f"{prefix}: board label is not canonical (expected {board_spec.label})"
        )
    if board_spec.m != 3 or board_spec.n < 3 or board_spec.n % 2 == 0:
        result.errors.append(f"{prefix}: expected 3xN with odd N >= 3")
        return
    board = ColBoard(board_spec.m, board_spec.n, use_symmetry=True)

    if record.get("empty_p1_wins") is not False:
        result.errors.append(
            f"{prefix}: artifact does not declare an empty-board P2 win"
        )

    raw_nodes = record.get("nodes")
    if not isinstance(raw_nodes, list):
        result.errors.append(f"{prefix}: nodes is not a list")
        return

    nodes: dict[str, ParsedNode] = {}
    for index, raw_node in enumerate(raw_nodes):
        node_prefix = f"{prefix}/node[{index}]"
        if not isinstance(raw_node, dict):
            result.errors.append(f"{node_prefix}: node is not an object")
            continue
        try:
            node_id_value = raw_node["id"]
            if not isinstance(node_id_value, str):
                raise ValueError("id must be a hexadecimal string")
            node_id = node_id_value
            if hex(parse_hex(node_id)) != node_id:
                raise ValueError("id is not canonical hexadecimal")
            p1_legal = parse_hex(raw_node["p1_legal"])
            p2_legal = parse_hex(raw_node["p2_legal"])
            signature_value = raw_node["signature"]
            kind_value = raw_node["kind"]
            if not isinstance(signature_value, str) or not isinstance(kind_value, str):
                raise ValueError("signature and kind must be strings")
            signature = signature_value
            kind = kind_value
        except (KeyError, TypeError, ValueError) as exc:
            result.errors.append(f"{node_prefix}: malformed node: {exc}")
            continue
        node_prefix = f"{prefix}/{node_id}"
        if node_id in nodes:
            result.errors.append(f"{node_prefix}: duplicate node id")
            continue
        if p1_legal & ~board.all_cells_mask or p2_legal & ~board.all_cells_mask:
            result.errors.append(f"{node_prefix}: legal mask extends outside the board")
            continue
        expected_id = hex(board.shadow_key(p1_legal, p2_legal, P1))
        if node_id != expected_id:
            result.errors.append(
                f"{node_prefix}: node id mismatch (expected {expected_id})"
            )
        expected_signature = canonical_signature(board, p1_legal, p2_legal)
        if signature != expected_signature:
            result.errors.append(f"{node_prefix}: signature mismatch")
        if kind not in NODE_KINDS:
            result.errors.append(f"{node_prefix}: unknown node kind {kind!r}")
        nodes[node_id] = ParsedNode(
            raw=raw_node,
            node_id=node_id,
            p1_legal=p1_legal,
            p2_legal=p2_legal,
            signature=signature,
            kind=kind,
        )

    root = record.get("root")
    expected_root = hex(
        board.shadow_key(board.all_cells_mask, board.all_cells_mask, P1)
    )
    if root != expected_root:
        result.errors.append(
            f"{prefix}: root mismatch (expected {expected_root}, got {root!r})"
        )
    root_node = nodes.get(str(root))
    if root_node is None:
        result.errors.append(f"{prefix}: root node is missing")
    elif (
        root_node.p1_legal != board.all_cells_mask
        or root_node.p2_legal != board.all_cells_mask
    ):
        result.errors.append(
            f"{prefix}: root masks are not the empty-board legal masks"
        )

    edges: dict[str, set[str]] = {node_id: set() for node_id in nodes}
    transition_count = 0
    kind_counts = {kind: 0 for kind in NODE_KINDS}
    for node in nodes.values():
        node_prefix = f"{prefix}/{node.node_id}"
        if node.kind in kind_counts:
            kind_counts[node.kind] += 1
        transitions = node.raw.get("transitions")
        if not isinstance(transitions, list):
            result.errors.append(f"{node_prefix}: transitions is not a list")
            continue

        if node.kind == "terminal":
            if node.p1_legal != 0:
                result.errors.append(f"{node_prefix}: terminal leaf has legal P1 moves")
            if transitions:
                result.errors.append(f"{node_prefix}: terminal leaf has transitions")
            continue

        if node.kind == "half_turn_pairing":
            if not node.p1_legal:
                result.errors.append(
                    f"{node_prefix}: zero-move node must use the terminal leaf kind"
                )
            if transitions:
                result.errors.append(f"{node_prefix}: pairing leaf has transitions")
            verify_pairing_leaf(board, node, result.errors, node_prefix)
            continue

        if node.kind != "transitions":
            continue
        if node.p1_legal == 0:
            result.errors.append(f"{node_prefix}: transition node has no P1 moves")

        expected_moves = {
            cell for cell in range(board.num_cells) if node.p1_legal & (1 << cell)
        }
        actual_moves: list[int] = []
        for transition_index, transition in enumerate(transitions):
            transition_count += 1
            transition_prefix = f"{node_prefix}/transition[{transition_index}]"
            if not isinstance(transition, dict):
                result.errors.append(
                    f"{transition_prefix}: transition is not an object"
                )
                continue
            try:
                p1_move = parse_move(transition["p1_move"])
                p2_response = parse_move(transition["p2_response"])
                child_id = str(transition["child"])
                target_id = str(transition["target"])
            except (KeyError, TypeError, ValueError) as exc:
                result.errors.append(
                    f"{transition_prefix}: malformed transition: {exc}"
                )
                continue
            actual_moves.append(p1_move)
            if not 0 <= p1_move < board.num_cells or not (
                node.p1_legal & (1 << p1_move)
            ):
                result.errors.append(f"{transition_prefix}: illegal P1 move {p1_move}")
                continue
            child_p1, child_p2 = child_legals(
                board, node.p1_legal, node.p2_legal, P1, p1_move
            )
            expected_child = hex(board.shadow_key(child_p1, child_p2, P2))
            if child_id != expected_child:
                result.errors.append(
                    f"{transition_prefix}: child key mismatch (expected {expected_child})"
                )
            if not 0 <= p2_response < board.num_cells or not (
                child_p2 & (1 << p2_response)
            ):
                result.errors.append(
                    f"{transition_prefix}: illegal P2 response {p2_response}"
                )
                continue
            target_p1, target_p2 = child_legals(
                board, child_p1, child_p2, P2, p2_response
            )
            expected_target = hex(board.shadow_key(target_p1, target_p2, P1))
            if target_id != expected_target:
                result.errors.append(
                    f"{transition_prefix}: target key mismatch (expected {expected_target})"
                )
                continue
            target_node = nodes.get(target_id)
            if target_node is None:
                result.errors.append(
                    f"{transition_prefix}: target {target_id} is not in the DAG"
                )
                continue
            target_signature = canonical_signature(board, target_p1, target_p2)
            if target_signature != target_node.signature:
                result.errors.append(
                    f"{transition_prefix}: target masks do not match target node"
                )
            if (target_p1 | target_p2).bit_count() >= (
                node.p1_legal | node.p2_legal
            ).bit_count():
                result.errors.append(
                    f"{transition_prefix}: target does not strictly decrease open cells"
                )
            edges[node.node_id].add(target_id)

        if len(actual_moves) != len(set(actual_moves)):
            result.errors.append(f"{node_prefix}: duplicate P1 move transitions")
        if set(actual_moves) != expected_moves:
            result.errors.append(f"{node_prefix}: incomplete P1 move coverage")

    reachable: set[str] = set()
    if isinstance(root, str) and root in nodes:
        pending = deque([root])
        while pending:
            node_id = pending.popleft()
            if node_id in reachable:
                continue
            reachable.add(node_id)
            pending.extend(edges.get(node_id, ()))
    unreachable = sorted(set(nodes) - reachable, key=lambda item: int(item, 16))
    if unreachable:
        result.errors.append(
            f"{prefix}: {len(unreachable)} unreachable node(s): "
            + ", ".join(unreachable[:10])
        )

    computed_summary = {
        "nodes": len(nodes),
        "transition_nodes": kind_counts["transitions"],
        "terminal_leaves": kind_counts["terminal"],
        "pairing_leaves": kind_counts["half_turn_pairing"],
        "transitions": transition_count,
    }
    supplied_summary = record.get("summary")
    if not isinstance(supplied_summary, dict):
        result.errors.append(f"{prefix}: summary is not an object")
    else:
        for key, expected in computed_summary.items():
            if supplied_summary.get(key) != expected:
                result.errors.append(
                    f"{prefix}: summary {key} mismatch "
                    f"(expected {expected}, got {supplied_summary.get(key)!r})"
                )

    result.boards.append(
        {
            "board": label,
            **computed_summary,
            "reachable_nodes": len(reachable),
        }
    )


def verify_artifact(payload: object) -> VerificationResult:
    result = VerificationResult()
    if not isinstance(payload, dict):
        result.errors.append("artifact is not a JSON object")
        return result
    schema_version = payload.get("schema_version")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version != SCHEMA_VERSION
    ):
        result.errors.append(f"unsupported schema_version {schema_version!r}")
    if payload.get("kind") != ARTIFACT_KIND:
        result.errors.append(f"unexpected artifact kind {payload.get('kind')!r}")
    boards = payload.get("boards")
    if not isinstance(boards, list) or not boards:
        result.errors.append("boards must be a nonempty list")
        return result
    canonical_labels = []
    for record in boards:
        if not isinstance(record, dict) or not isinstance(record.get("board"), str):
            continue
        try:
            canonical_labels.append(BoardSpec.parse(str(record["board"])).label)
        except ValueError:
            continue
    if len(canonical_labels) != len(set(canonical_labels)):
        result.errors.append("artifact contains duplicate board records")
    for record in boards:
        verify_board(record, result)
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact",
        type=Path,
        default=REPO_ROOT / "reports" / "3xn-rooted-strategy-dag.json",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        payload = json.loads(args.artifact.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "boards": [], "errors": [str(exc)]}, indent=2))
        return 1
    result = verify_artifact(payload)
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
