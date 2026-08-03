#!/usr/bin/env python3
"""Mine finite-state proof candidates for odd 3xn Col strips.

This is an analysis helper, not a solver optimization.  It solves small 3xn
boards in memory, scans the DFS shadow memo, and reports recurring tinted
component/frontier families that could become the finite induction states in a
3xn proof.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Callable, Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "python"))

from col.core import ColBoard, P1, P2  # noqa: E402
from col.dfs import DfsSolver  # noqa: E402
from col.endgame import ShapeValueCache  # noqa: E402
from col.shapes import BLOCK_P1, BLOCK_P2, Cells, live_components  # noqa: E402
from col.tablebase import Tablebase  # noqa: E402


DEAD = BLOCK_P1 | BLOCK_P2
DEFAULT_BOARDS = ("3x5", "3x7", "3x9", "3x11", "3x13")


@dataclass(frozen=True, order=True)
class Board:
    m: int
    n: int

    @classmethod
    def parse(cls, text: str) -> "Board":
        parts = text.lower().split("x")
        if len(parts) != 2:
            raise argparse.ArgumentTypeError(f"bad board {text!r}; expected MxN")
        m, n = int(parts[0]), int(parts[1])
        if m != 3 or n < 3 or n % 2 == 0:
            raise argparse.ArgumentTypeError("this miner expects boards 3xN with odd N >= 3")
        return cls(m, n)

    @property
    def label(self) -> str:
        return f"{self.m}x{self.n}"


@dataclass
class BoardSummary:
    board: Board
    empty_is_p1_win: bool
    seconds: float
    states_searched: int
    memo_entries: int
    pairing_certificate_hits: int


@dataclass
class FamilyStats:
    occurrences: int = 0
    boards: Counter[str] = field(default_factory=Counter)
    widths: Counter[int] = field(default_factory=Counter)
    values: Counter[str] = field(default_factory=Counter)
    samples: Counter[str] = field(default_factory=Counter)
    losing_single_component: int = 0

    def record(
        self,
        *,
        board: str,
        width: int,
        value: str | None,
        sample: str,
        losing_single_component: bool = False,
    ) -> None:
        self.occurrences += 1
        self.boards[board] += 1
        self.widths[width] += 1
        if value is not None:
            self.values[value] += 1
        self.samples[sample] += 1
        if losing_single_component:
            self.losing_single_component += 1

    @property
    def sample(self) -> str:
        return self.samples.most_common(1)[0][0] if self.samples else ""


@dataclass
class Transition:
    p1_move: int
    p2_response: int
    target_key: str
    target_signature: str


@dataclass
class StateCertificate:
    schema_version: int
    board: str
    source_key: str
    source_signature: str
    p1_legal: str
    p2_legal: str
    transitions: list[Transition]


def char_from_legal(p1_legal: bool, p2_legal: bool) -> str:
    """Use proof-miner convention: b = P1-only, w = P2-only."""
    if p1_legal and p2_legal:
        return "o"
    if p1_legal:
        return "b"
    if p2_legal:
        return "w"
    return "."


def char_from_tint(tint: int) -> str:
    if tint == 0:
        return "o"
    if tint == BLOCK_P2:
        return "b"
    if tint == BLOCK_P1:
        return "w"
    return "."


def swap_color(ch: str) -> str:
    if ch == "b":
        return "w"
    if ch == "w":
        return "b"
    return ch


def value_text(value: tuple[Fraction, bool]) -> str:
    number, star = value
    return f"{number}{'*' if star else ''}"


def component_grid(component: Cells) -> list[str]:
    rows = [row for row, _ in component]
    cols = [col for _, col in component]
    min_row, max_row = min(rows), max(rows)
    min_col, max_col = min(cols), max(cols)
    grid = []
    for row in range(min_row, max_row + 1):
        grid.append(
            "".join(
                char_from_tint(component.get((row, col), DEAD))
                for col in range(min_col, max_col + 1)
            )
        )
    return grid


def render_grid(grid: Sequence[str]) -> str:
    return "/".join(grid)


def transform_grid(
    grid: Sequence[str],
    transform: Callable[[int, int, int, int], tuple[int, int, int, int]],
    *,
    color_swap: bool,
) -> list[str]:
    height = len(grid)
    width = len(grid[0]) if grid else 0
    _, _, out_height, out_width = transform(0, 0, height, width)
    out = [["." for _ in range(out_width)] for _ in range(out_height)]
    for row, line in enumerate(grid):
        for col, ch in enumerate(line):
            if ch == ".":
                continue
            next_row, next_col, _, _ = transform(row, col, height, width)
            out[next_row][next_col] = swap_color(ch) if color_swap else ch
    return ["".join(line) for line in out]


def canonical_grid(grid: Sequence[str], *, allow_transpose: bool, allow_color_swap: bool) -> str:
    transforms: list[Callable[[int, int, int, int], tuple[int, int, int, int]]] = [
        lambda r, c, h, w: (r, c, h, w),
        lambda r, c, h, w: (h - 1 - r, c, h, w),
        lambda r, c, h, w: (r, w - 1 - c, h, w),
        lambda r, c, h, w: (h - 1 - r, w - 1 - c, h, w),
    ]
    if allow_transpose:
        transforms.extend(
            [
                lambda r, c, h, w: (c, r, w, h),
                lambda r, c, h, w: (c, h - 1 - r, w, h),
                lambda r, c, h, w: (w - 1 - c, r, w, h),
                lambda r, c, h, w: (w - 1 - c, h - 1 - r, w, h),
            ]
        )
    variants = []
    for transform in transforms:
        for do_swap in ([False, True] if allow_color_swap else [False]):
            variants.append(render_grid(transform_grid(grid, transform, color_swap=do_swap)))
    return min(variants)


def frontier_signature(grid: Sequence[str], radius: int) -> str:
    width = len(grid[0]) if grid else 0
    if width <= 2 * radius + 1:
        return render_grid(grid)
    left = [line[:radius] for line in grid]
    right = [line[-radius:] for line in grid]
    return f"{render_grid(left)} | ...{width - 2 * radius}... | {render_grid(right)}"


def rle_columns(grid: Sequence[str]) -> str:
    if not grid:
        return ""
    columns = ["".join(row[col] for row in grid) for col in range(len(grid[0]))]
    out: list[str] = []
    last = columns[0]
    count = 1
    for column in columns[1:]:
        if column == last:
            count += 1
        else:
            out.append(f"{last}x{count}" if count > 1 else last)
            last = column
            count = 1
    out.append(f"{last}x{count}" if count > 1 else last)
    return " ".join(out)


def whole_position_grid(board: ColBoard, p1_legal: int, p2_legal: int) -> list[str]:
    grid = []
    for row in range(board.m):
        line = []
        for col in range(board.n):
            bit = 1 << (row * board.n + col)
            line.append(char_from_legal(bool(p1_legal & bit), bool(p2_legal & bit)))
        grid.append("".join(line))
    return grid


def child_legals(
    board: ColBoard,
    p1_legal: int,
    p2_legal: int,
    turn: int,
    bit: int,
) -> tuple[int, int]:
    cell = bit.bit_length() - 1
    blocked = bit | board.adjacency_masks[cell]
    if turn == P1:
        return p1_legal & ~blocked, p2_legal & ~bit
    return p1_legal & ~bit, p2_legal & ~blocked


def extract_state_certificate(
    solver: DfsSolver,
    key: int,
    p1_legal: int,
    p2_legal: int,
) -> StateCertificate | None:
    """Certify every P1 move has a P2 reply to another losing P1 state."""
    board = solver.board
    transitions: list[Transition] = []
    remaining_p1 = p1_legal
    while remaining_p1:
        p1_bit = remaining_p1 & -remaining_p1
        remaining_p1 ^= p1_bit
        child_p1, child_p2 = child_legals(board, p1_legal, p2_legal, P1, p1_bit)
        child_key = board.shadow_key(child_p1, child_p2, P2)
        if solver.memo.get(child_key) is not True:
            return None

        response: Transition | None = None
        remaining_p2 = child_p2
        while remaining_p2:
            p2_bit = remaining_p2 & -remaining_p2
            remaining_p2 ^= p2_bit
            target_p1, target_p2 = child_legals(board, child_p1, child_p2, P2, p2_bit)
            target_key = board.shadow_key(target_p1, target_p2, P1)
            if solver.memo.get(target_key) is not False:
                continue
            target_grid = whole_position_grid(board, target_p1, target_p2)
            response = Transition(
                p1_move=p1_bit.bit_length() - 1,
                p2_response=p2_bit.bit_length() - 1,
                target_key=hex(target_key),
                target_signature=canonical_grid(
                    target_grid,
                    allow_transpose=False,
                    allow_color_swap=False,
                ),
            )
            break
        if response is None:
            return None
        transitions.append(response)

    source_grid = whole_position_grid(board, p1_legal, p2_legal)
    return StateCertificate(
        schema_version=1,
        board=f"{board.m}x{board.n}",
        source_key=hex(key),
        source_signature=canonical_grid(
            source_grid,
            allow_transpose=False,
            allow_color_swap=False,
        ),
        p1_legal=hex(p1_legal),
        p2_legal=hex(p2_legal),
        transitions=transitions,
    )


def mine_board(
    board_spec: Board,
    *,
    max_exact_cells: int,
    frontier_radius: int,
    component_families: dict[str, FamilyStats],
    frontier_families: dict[str, FamilyStats],
    losing_state_families: dict[str, FamilyStats],
    certificates: list[StateCertificate],
    max_certificates: int,
) -> BoardSummary:
    solver = DfsSolver(
        board_spec.m,
        board_spec.n,
        use_symmetry=True,
        tablebase=Tablebase(enabled=False),
        progress=False,
        mobility_order=True,
    )
    started_at = time.perf_counter()
    empty_is_p1_win = solver.solve()
    seconds = time.perf_counter() - started_at
    board = solver.board
    value_cache = ShapeValueCache(enabled=False, max_component_size=max_exact_cells)

    for key, side_to_move_wins in solver.memo.items():
        p1_legal, p2_legal, turn = board.unpack_key(key)
        component_masks = board.legal_component_masks(p1_legal, p2_legal)
        single_component = len(component_masks) == 1

        if single_component and not side_to_move_wins:
            grid = whole_position_grid(board, p1_legal, p2_legal)
            canonical = canonical_grid(grid, allow_transpose=False, allow_color_swap=False)
            sample = f"turn=P{turn + 1}; cols={rle_columns(canonical.split('/'))}"
            losing_state_families[canonical].record(
                board=board_spec.label,
                width=board.n,
                value=None,
                sample=sample,
                losing_single_component=True,
            )

        if (
            turn == P1
            and not side_to_move_wins
            and len(certificates) < max_certificates
        ):
            certificate = extract_state_certificate(solver, key, p1_legal, p2_legal)
            if certificate is not None:
                certificates.append(certificate)

        for comp_p1, comp_p2 in component_masks:
            cells = ShapeValueCache.cells_from_legal_masks(board, comp_p1, comp_p2)
            for component in live_components(cells):
                grid = component_grid(component)
                height = len(grid)
                width = len(grid[0]) if grid else 0
                exact_value = None
                if len(component) <= max_exact_cells:
                    exact_value = value_text(value_cache.component_value(component))

                component_key = canonical_grid(
                    grid,
                    allow_transpose=True,
                    allow_color_swap=False,
                )
                component_families[component_key].record(
                    board=board_spec.label,
                    width=width,
                    value=exact_value,
                    sample=render_grid(grid),
                    losing_single_component=single_component and not side_to_move_wins,
                )

                if height == 3 or width >= 3:
                    frontier_key = canonical_grid(
                        grid,
                        allow_transpose=False,
                        allow_color_swap=False,
                    )
                    frontier_families[frontier_key].record(
                        board=board_spec.label,
                        width=width,
                        value=exact_value,
                        sample=frontier_signature(grid, frontier_radius),
                        losing_single_component=single_component and not side_to_move_wins,
                    )

    return BoardSummary(
        board=board_spec,
        empty_is_p1_win=empty_is_p1_win,
        seconds=seconds,
        states_searched=solver.stats.states_searched,
        memo_entries=len(solver.memo),
        pairing_certificate_hits=solver.stats.pairing_certificate_hits,
    )


def top_items(families: dict[str, FamilyStats], limit: int) -> list[tuple[str, FamilyStats]]:
    return sorted(families.items(), key=lambda item: (-item[1].occurrences, item[0]))[:limit]


def counter_text(counter: Counter[object], limit: int = 5) -> str:
    if not counter:
        return "-"
    return ", ".join(f"{key} ({count})" for key, count in counter.most_common(limit))


def write_family_section(
    out: list[str],
    title: str,
    families: dict[str, FamilyStats],
    *,
    limit: int,
) -> None:
    out.append(f"## {title}\n")
    out.append("| Rank | Occurrences | Boards | Widths | Exact values | Sample |")
    out.append("|---:|---:|---|---|---|---|")
    for rank, (signature, stats) in enumerate(top_items(families, limit), start=1):
        sample = stats.sample.replace("|", "\\|")
        out.append(
            f"| {rank} | {stats.occurrences} | {counter_text(stats.boards)} | "
            f"{counter_text(stats.widths)} | {counter_text(stats.values)} | `{sample}` |"
        )
    out.append("")


def write_report(
    path: Path,
    summaries: Sequence[BoardSummary],
    component_families: dict[str, FamilyStats],
    frontier_families: dict[str, FamilyStats],
    losing_state_families: dict[str, FamilyStats],
    *,
    max_exact_cells: int,
    top: int,
) -> None:
    out: list[str] = []
    out.append("# 3xn Finite-State Proof Candidates\n")
    out.append(
        "This report solves small odd `3xn` boards in memory, scans the DFS shadow memo, "
        "and mines tinted state families that could become the finite induction table for "
        "a proof that all odd `3xn` boards are second-player wins.\n"
    )
    out.append(
        "Notation follows the proof miner: `o` is legal for both players, `b` is P1-only, "
        "`w` is P2-only, and `.` is dead/unavailable.\n"
    )
    out.append(f"- Exact component values computed for components with at most `{max_exact_cells}` live cells.")
    out.append("- Tablebase files are not required; all data here comes from fresh in-memory DFS runs.\n")

    out.append("## Board Summary\n")
    out.append("| Board | Empty P1 win? | Seconds | States searched | Memo entries | Pairing cert hits |")
    out.append("|---|---:|---:|---:|---:|---:|")
    for summary in summaries:
        out.append(
            f"| {summary.board.label} | {summary.empty_is_p1_win} | {summary.seconds:.2f} | "
            f"{summary.states_searched:,} | {summary.memo_entries:,} | "
            f"{summary.pairing_certificate_hits:,} |"
        )
    out.append("")

    write_family_section(out, "Most Frequent Local Components", component_families, limit=top)
    write_family_section(out, "Most Frequent 3-Row Frontier Components", frontier_families, limit=top)

    zero_frontiers = {
        key: stats
        for key, stats in frontier_families.items()
        if stats.values and set(stats.values) == {"0"}
    }
    write_family_section(out, "Exact-Zero Frontier Candidates", zero_frontiers, limit=top)

    nonzero_frontiers = {
        key: stats
        for key, stats in frontier_families.items()
        if any(value != "0" for value in stats.values)
    }
    write_family_section(out, "Nonzero Frontier Obstacles", nonzero_frontiers, limit=top)

    write_family_section(
        out,
        "Losing Single-Component Whole-State Candidates",
        losing_state_families,
        limit=top,
    )

    out.append("## How To Use This\n")
    out.append(
        "A plausible `3xn` proof should promote a small subset of the exact-zero "
        "frontier candidates into lemmas, then show every P1 move from each losing "
        "whole-state family has a P2 reply landing back in the family set. Nonzero "
        "frontier obstacles are the states that need cancellation partners or their "
        "own recurrence lemmas."
    )
    out.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--boards",
        nargs="+",
        type=Board.parse,
        default=[Board.parse(text) for text in DEFAULT_BOARDS],
        help="Odd 3xN boards to solve and mine (default: 3x5 through 3x13).",
    )
    parser.add_argument(
        "--max-exact-cells",
        type=int,
        default=12,
        help="Maximum component size for exact CGT value extraction.",
    )
    parser.add_argument(
        "--frontier-radius",
        type=int,
        default=2,
        help="Columns to keep at each end when rendering wide frontier samples.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Number of rows per report section.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "reports" / "3xn-finite-state-candidates.md",
        help="Markdown report path.",
    )
    parser.add_argument(
        "--certificates-out",
        type=Path,
        default=REPO_ROOT / "reports" / "3xn-transition-certificates.jsonl",
        help="Replayable P1-move/P2-response certificates (JSON Lines).",
    )
    parser.add_argument(
        "--max-certificates",
        type=int,
        default=50_000,
        help="Maximum closure certificates to emit across all boards.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    component_families: dict[str, FamilyStats] = defaultdict(FamilyStats)
    frontier_families: dict[str, FamilyStats] = defaultdict(FamilyStats)
    losing_state_families: dict[str, FamilyStats] = defaultdict(FamilyStats)
    certificates: list[StateCertificate] = []

    summaries = [
        mine_board(
            board,
            max_exact_cells=args.max_exact_cells,
            frontier_radius=args.frontier_radius,
            component_families=component_families,
            frontier_families=frontier_families,
            losing_state_families=losing_state_families,
            certificates=certificates,
            max_certificates=args.max_certificates,
        )
        for board in args.boards
    ]
    write_report(
        args.out,
        summaries,
        component_families,
        frontier_families,
        losing_state_families,
        max_exact_cells=args.max_exact_cells,
        top=args.top,
    )
    args.certificates_out.parent.mkdir(parents=True, exist_ok=True)
    with args.certificates_out.open("w", encoding="utf-8") as handle:
        for certificate in certificates:
            handle.write(
                json.dumps(
                    {
                        **{
                            key: value
                            for key, value in asdict(certificate).items()
                            if key != "transitions"
                        },
                        "transitions": [
                            asdict(transition)
                            for transition in certificate.transitions
                        ],
                    },
                    sort_keys=True,
                )
                + "\n"
            )
    print(f"wrote {args.out}")
    print(f"wrote {args.certificates_out} ({len(certificates):,} certificates)")


if __name__ == "__main__":
    main()
