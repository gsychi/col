#!/usr/bin/env python3
"""Generate and replay finite option-tree certificates for local Col values."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "python"))

from col.cgt import Value, add_values, value_of_options  # noqa: E402
from col.shapes import BLOCK_P1, BLOCK_P2, Cells, live_components, play  # noqa: E402


DEFAULT_PATTERNS = (
    "bow",
    "b/o/w",
    "bw./.bw",
    "wob/.wb",
    "ww/w.",
    "bbw/b..",
)


@dataclass(frozen=True)
class OptionCertificate:
    move: str
    components: tuple[str, ...]
    value: str


@dataclass
class NodeCertificate:
    cells: str
    left: list[OptionCertificate]
    right: list[OptionCertificate]
    value: str


def parse_pattern(pattern: str) -> Cells:
    rows = pattern.split("/")
    if not rows or len({len(row) for row in rows}) != 1:
        raise ValueError(f"pattern must be a rectangular slash-separated grid: {pattern!r}")
    tint_by_char = {"o": 0, "b": BLOCK_P2, "w": BLOCK_P1}
    cells: Cells = {}
    for row, line in enumerate(rows):
        for col, char in enumerate(line):
            if char == ".":
                continue
            if char not in tint_by_char:
                raise ValueError(f"unknown tint {char!r} in {pattern!r}")
            cells[(row, col)] = tint_by_char[char]
    if not cells:
        raise ValueError("pattern has no live cells")
    return cells


def normalize(cells: Cells) -> Cells:
    min_row = min(row for row, _ in cells)
    min_col = min(col for _, col in cells)
    return {
        (row - min_row, col - min_col): tint
        for (row, col), tint in cells.items()
    }


def cells_key(cells: Cells) -> str:
    normalized = normalize(cells)
    return ";".join(
        f"{row},{col},{tint}"
        for (row, col), tint in sorted(normalized.items())
    )


def value_text(value: Value) -> str:
    number, star = value
    return f"{number}{'*' if star else ''}"


def parse_value(text: str) -> Value:
    star = text.endswith("*")
    number = text[:-1] if star else text
    return Fraction(number), star


class CertificateBuilder:
    def __init__(self) -> None:
        self.nodes: dict[str, NodeCertificate] = {}
        self.values: dict[str, Value] = {}

    def position_value(self, cells: Cells) -> tuple[Value, tuple[str, ...]]:
        total: Value = (Fraction(0), False)
        keys = []
        for component in live_components(cells):
            key = cells_key(component)
            keys.append(key)
            total = add_values(total, self.component_value(component))
        return total, tuple(sorted(keys))

    def component_value(self, cells: Cells) -> Value:
        cells = normalize(cells)
        key = cells_key(cells)
        cached = self.values.get(key)
        if cached is not None:
            return cached

        left: list[OptionCertificate] = []
        right: list[OptionCertificate] = []
        for position, tint in sorted(cells.items()):
            move = f"{position[0]},{position[1]}"
            if not tint & BLOCK_P1:
                value, components = self.position_value(play(cells, position, BLOCK_P1))
                left.append(OptionCertificate(move, components, value_text(value)))
            if not tint & BLOCK_P2:
                value, components = self.position_value(play(cells, position, BLOCK_P2))
                right.append(OptionCertificate(move, components, value_text(value)))

        value = value_of_options(
            [parse_value(option.value) for option in left],
            [parse_value(option.value) for option in right],
        )
        self.values[key] = value
        self.nodes[key] = NodeCertificate(key, left, right, value_text(value))
        return value


def verify_nodes(nodes: dict[str, dict[str, object]]) -> list[str]:
    errors: list[str] = []
    parsed_values = {
        key: parse_value(str(node["value"]))
        for key, node in nodes.items()
    }
    for key, node in nodes.items():
        for side in ("left", "right"):
            options = node.get(side)
            if not isinstance(options, list):
                errors.append(f"{key}: {side} options are not a list")
                continue
            for option in options:
                components = option.get("components", [])
                try:
                    total: Value = (Fraction(0), False)
                    for component in components:
                        total = add_values(total, parsed_values[str(component)])
                except KeyError as exc:
                    errors.append(f"{key}: missing child component {exc.args[0]}")
                    continue
                if total != parse_value(str(option["value"])):
                    errors.append(f"{key}: {side} option sum mismatch")
        left_values = [parse_value(str(option["value"])) for option in node["left"]]
        right_values = [parse_value(str(option["value"])) for option in node["right"]]
        actual = value_of_options(left_values, right_values)
        if actual != parsed_values[key]:
            errors.append(f"{key}: option recurrence gives {value_text(actual)}, not {node['value']}")
    return errors


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patterns", nargs="+", default=list(DEFAULT_PATTERNS))
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "reports" / "cgt-component-certificates.json",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=REPO_ROOT / "reports" / "cgt-component-certificates.md",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    builder = CertificateBuilder()
    roots = {}
    for pattern in args.patterns:
        cells = parse_pattern(pattern)
        value = builder.component_value(cells)
        roots[pattern] = {"node": cells_key(cells), "value": value_text(value)}

    nodes = {
        key: {
            "cells": node.cells,
            "left": [option.__dict__ for option in node.left],
            "right": [option.__dict__ for option in node.right],
            "value": node.value,
        }
        for key, node in sorted(builder.nodes.items())
    }
    errors = verify_nodes(nodes)
    payload = {
        "schema_version": 1,
        "roots": roots,
        "nodes": nodes,
        "verification_errors": errors,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Local CGT Component Certificates",
        "",
        "Each value is backed by a finite option recurrence. Every option lists the "
        "resulting live components and their exact disjunctive-sum value.",
        "",
        "| Pattern | Value | Root node |",
        "|---|---:|---|",
    ]
    for pattern, root in roots.items():
        lines.append(f"| `{pattern}` | `{root['value']}` | `{root['node']}` |")
    lines.extend(
        [
            "",
            f"- Recurrence nodes: `{len(nodes):,}`",
            f"- Verification errors: `{len(errors):,}`",
        ]
    )
    if errors:
        lines.extend(["", "## Errors", "", *[f"- {error}" for error in errors]])
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print(f"wrote {args.report}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
