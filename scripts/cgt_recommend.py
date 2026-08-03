#!/usr/bin/env python3
"""Recommend a CGT endgame cutoff for a board using sweep measurements.

Uses family-wise log-linear fits on baseline states, retention ratios, and
solve times from reports/cgt-size-sweep.json. Falls back to measured rows when
the requested board is already in the sweep.

Examples:
  python3 scripts/cgt_recommend.py 5x9
  python3 scripts/cgt_recommend.py 3x13 5x7 --data reports/cgt-size-sweep.json
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = REPO_ROOT / "reports" / "cgt-size-sweep.json"
DEFAULT_CGT_SIZES = (6, 8, 10, 12, 14)
MAX_SUPPORTED_CGT = 14


@dataclass(frozen=True, order=True)
class Board:
    m: int
    n: int

    @classmethod
    def parse(cls, text: str) -> "Board":
        match = re.fullmatch(r"(\d+)x(\d+)", text.strip().lower())
        if not match:
            raise argparse.ArgumentTypeError(f"bad board {text!r}; expected MxN")
        m, n = int(match.group(1)), int(match.group(2))
        if m <= 0 or n <= 0:
            raise argparse.ArgumentTypeError("board dimensions must be positive")
        if m > n:
            m, n = n, m
        return cls(m, n)

    @property
    def cells(self) -> int:
        return self.m * self.n

    @property
    def label(self) -> str:
        return f"{self.m}x{self.n}"


@dataclass
class SweepRow:
    board: Board
    cgt_size: int
    states: int
    time_elapsed: float
    component_evals: int
    measured: bool = True


@dataclass
class Prediction:
    cgt_size: int
    states: float
    component_evals: float
    time_elapsed: float
    source: str
    retention: float | None = None


@dataclass
class Recommendation:
    board: Board
    baseline_states: float
    baseline_time: float | None
    predictions: list[Prediction]
    best: Prediction
    compare_10_12: tuple[float, float, float] | None


def linear_fit(xs: Sequence[float], ys: Sequence[float]) -> tuple[float, float]:
    n = len(xs)
    if n == 0:
        raise ValueError("linear_fit requires at least one point")
    if n == 1:
        return ys[0], 0.0
    sx = sum(xs)
    sy = sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    denom = n * sxx - sx * sx
    if denom == 0:
        return statistics.mean(ys), 0.0
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    return intercept, slope


def log10_fit(points: Sequence[tuple[float, float]]) -> tuple[float, float]:
    xs = [cells for cells, value in points if value > 0]
    ys = [math.log10(value) for cells, value in points if value > 0]
    if not xs:
        return 0.0, 0.0
    return linear_fit(xs, ys)


def predict_log_linear(
    intercept: float, slope: float, cells: float, *, minimum: float = 1.0
) -> float:
    return max(minimum, 10 ** (intercept + slope * cells))


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def load_rows(path: Path) -> list[SweepRow]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows: list[SweepRow] = []
    for item in raw:
        if not item.get("ok"):
            continue
        states = item.get("states_searched")
        elapsed = item.get("time_elapsed")
        if states is None or elapsed is None:
            continue
        board = Board(item["m"], item["n"])
        rows.append(
            SweepRow(
                board=board,
                cgt_size=int(item["cgt_size"]),
                states=int(states),
                time_elapsed=float(elapsed),
                component_evals=int(item.get("endgame_component_evals") or 0),
            )
        )
    return rows


def row_map(rows: Iterable[SweepRow]) -> dict[tuple[str, int], SweepRow]:
    return {(row.board.label, row.cgt_size): row for row in rows}


def family_points(
    rows: Sequence[SweepRow], m: int, cgt_size: int
) -> list[tuple[float, float]]:
    return sorted(
        ((row.board.cells, row.states if cgt_size == 0 else row.time_elapsed) for row in rows if row.board.m == m and row.cgt_size == cgt_size),
        key=lambda item: item[0],
    )


def retention_points(rows: Sequence[SweepRow], m: int, cgt_size: int) -> list[tuple[float, float]]:
    baseline = {
        row.board.label: row.states for row in rows if row.board.m == m and row.cgt_size == 0
    }
    points: list[tuple[float, float]] = []
    for row in rows:
        if row.board.m != m or row.cgt_size != cgt_size:
            continue
        base = baseline.get(row.board.label)
        if not base:
            continue
        points.append((row.board.cells, row.states / base))
    return sorted(points, key=lambda item: item[0])


def eta_points(rows: Sequence[SweepRow], m: int, cgt_size: int) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for row in rows:
        if row.board.m != m or row.cgt_size != cgt_size or row.states <= 0:
            continue
        points.append((row.board.cells, row.component_evals / row.states))
    return sorted(points, key=lambda item: item[0])


def extrapolate_retention(
    points: Sequence[tuple[float, float]], cells: float
) -> tuple[float, str]:
    if not points:
        return 0.5, "default"
    measured_cells = [p[0] for p in points]
    if cells in measured_cells:
        for point_cells, value in points:
            if point_cells == cells:
                return value, "measured"

    if len(points) >= 2 and cells > max(measured_cells):
        tail = points[-2:]
    else:
        tail = points

    if len(tail) == 1:
        return clamp(tail[0][1], 0.01, 1.0), "single-point"

    if len(tail) >= 2 and all(0 < value <= 1 for _, value in tail):
        intercept, slope = log10_fit(tail)
        rho = predict_log_linear(intercept, slope, cells, minimum=0.01)
        return clamp(rho, 0.01, 1.0), "log-linear-rho"

    intercept, slope = linear_fit([p[0] for p in tail], [p[1] for p in tail])
    return clamp(intercept + slope * cells, 0.01, 1.0), "linear-rho"


def extrapolate_log_value(
    points: Sequence[tuple[float, float]], cells: float, *, minimum: float = 1.0
) -> tuple[float, str]:
    if not points:
        return minimum, "default"
    if len(points) == 1:
        only_cells, only_value = points[0]
        if only_cells == cells:
            return max(minimum, only_value), "measured-single"
        ratio = cells / only_cells
        return max(minimum, only_value * ratio), "scaled-single"
    intercept, slope = log10_fit(points)
    return predict_log_linear(intercept, slope, cells, minimum=minimum), "log-linear"


def fit_cost_model(rows: Sequence[SweepRow]) -> tuple[dict[int, float], float]:
    alpha_by_m: dict[int, list[float]] = {}
    residuals: list[tuple[float, int]] = []
    for row in rows:
        if row.cgt_size == 0 and row.states > 0:
            alpha_by_m.setdefault(row.board.m, []).append(row.time_elapsed / row.states)
    alpha = {m: statistics.mean(values) for m, values in alpha_by_m.items()}
    for row in rows:
        if row.cgt_size == 0 or row.component_evals <= 0:
            continue
        base_alpha = alpha.get(row.board.m)
        if base_alpha is None:
            continue
        residual = row.time_elapsed - base_alpha * row.states
        residuals.append((residual, row.component_evals))
    if not residuals:
        return alpha, 0.0
    beta = statistics.median(residual / evals for residual, evals in residuals if evals > 0)
    return alpha, beta


class CgtModel:
    def __init__(self, rows: Sequence[SweepRow]) -> None:
        self.rows = list(rows)
        self.by_key = row_map(self.rows)
        self.alpha_by_m, self.beta = fit_cost_model(self.rows)

    def measured(self, board: Board, cgt_size: int) -> SweepRow | None:
        return self.by_key.get((board.label, cgt_size))

    def predict_baseline(self, board: Board) -> tuple[float, float | None, str]:
        measured = self.measured(board, 0)
        if measured:
            return float(measured.states), measured.time_elapsed, "measured"
        points = family_points(self.rows, board.m, 0)
        states, source = extrapolate_log_value(points, board.cells)
        alpha = self.alpha_by_m.get(board.m)
        time_est = states * alpha if alpha is not None else None
        return states, time_est, source

    def predict_cutoff(self, board: Board, cgt_size: int) -> Prediction:
        measured = self.measured(board, cgt_size)
        baseline_states, _, _ = self.predict_baseline(board)
        if measured:
            retention = measured.states / baseline_states if baseline_states > 0 else None
            return Prediction(
                cgt_size=cgt_size,
                states=float(measured.states),
                component_evals=float(measured.component_evals),
                time_elapsed=measured.time_elapsed,
                source="measured",
                retention=retention,
            )

        rho_points = retention_points(self.rows, board.m, cgt_size)
        rho, rho_source = extrapolate_retention(rho_points, board.cells)
        states = baseline_states * rho

        time_points = [
            (cells, elapsed)
            for cells, elapsed in family_points(self.rows, board.m, cgt_size)
        ]
        time_est, time_source = extrapolate_log_value(time_points, board.cells)

        eta_pts = eta_points(self.rows, board.m, cgt_size)
        if len(eta_pts) >= 2 and board.cells > max(c for c, _ in eta_pts):
            eta_pts = eta_pts[-2:]
        if len(eta_pts) == 1:
            eta = eta_pts[0][1]
        elif len(eta_pts) >= 2:
            intercept, slope = linear_fit([p[0] for p in eta_pts], [p[1] for p in eta_pts])
            eta = max(0.0, intercept + slope * board.cells)
        else:
            eta = 0.0
        component_evals = states * eta if eta > 0 else 0.0

        alpha = self.alpha_by_m.get(board.m)
        if alpha is not None and component_evals > 0:
            cost_est = alpha * states + self.beta * component_evals
            if time_source in {"default", "scaled-single"}:
                time_est = cost_est
                time_source = "cost-model"
            else:
                time_est = statistics.mean([time_est, cost_est])
                time_source = f"{time_source}+cost"

        return Prediction(
            cgt_size=cgt_size,
            states=states,
            component_evals=component_evals,
            time_elapsed=time_est,
            source=f"{rho_source}/{time_source}",
            retention=rho,
        )

    def recommend(
        self, board: Board, cgt_sizes: Sequence[int]
    ) -> Recommendation:
        baseline_states, baseline_time, _ = self.predict_baseline(board)
        predictions = [self.predict_cutoff(board, size) for size in cgt_sizes]
        best = min(predictions, key=lambda item: item.time_elapsed)

        compare: tuple[float, float, float] | None = None
        by_size = {item.cgt_size: item for item in predictions}
        if 10 in by_size and 12 in by_size:
            ten, twelve = by_size[10], by_size[12]
            delta_states = ten.states - twelve.states
            delta_evals = twelve.component_evals - ten.component_evals
            delta_time = twelve.time_elapsed - ten.time_elapsed
            if delta_evals > 0:
                score = delta_states / delta_evals
                alpha = self.alpha_by_m.get(board.m, self.beta)
                threshold = self.beta / alpha if alpha > 0 else 0.0
                compare = (score, threshold, delta_time)
            else:
                compare = (float("nan"), float("nan"), delta_time)

        return Recommendation(
            board=board,
            baseline_states=baseline_states,
            baseline_time=baseline_time,
            predictions=predictions,
            best=best,
            compare_10_12=compare,
        )


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.2f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f} min"
    return f"{seconds / 3600:.1f} hr"


def format_number(value: float) -> str:
    if value < 1e6:
        return f"{value:,.0f}"
    return f"{value:.2e}"


def print_recommendation(rec: Recommendation) -> None:
    print(f"Board: {rec.board.label} ({rec.board.cells} cells, family m={rec.board.m})")
    if rec.baseline_time is not None:
        print(
            f"Baseline (CGT 0): {format_number(rec.baseline_states)} states, "
            f"{format_duration(rec.baseline_time)}"
        )
    else:
        print(f"Baseline (CGT 0): {format_number(rec.baseline_states)} states")

    print()
    print(f"{'CGT':>4} {'Time':>12} {'States':>14} {'Retention':>10} {'Source':>18}")
    for item in rec.predictions:
        retention = "-" if item.retention is None else f"{item.retention * 100:.1f}%"
        marker = " <-- best" if item.cgt_size == rec.best.cgt_size else ""
        print(
            f"{item.cgt_size:4d} {format_duration(item.time_elapsed):>12} "
            f"{format_number(item.states):>14} {retention:>10} {item.source:>18}{marker}"
        )

    print()
    print(
        f"Recommended CGT size: {rec.best.cgt_size} "
        f"({format_duration(rec.best.time_elapsed)}, {rec.best.source})"
    )

    if rec.compare_10_12:
        score, threshold, delta_time = rec.compare_10_12
        verdict = "CGT 12 faster" if delta_time < 0 else "CGT 10 faster"
        if math.isnan(score):
            print(
                f"CGT 10 vs 12: {verdict} by {format_duration(abs(delta_time))} "
                f"(CGT 12 uses fewer states with similar eval cost)"
            )
        else:
            print(
                f"CGT 10 vs 12 crossover score: {score:.3f} states saved per extra eval "
                f"(threshold ~ {threshold:.3f}); {verdict} by {format_duration(abs(delta_time))}"
            )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "boards",
        nargs="+",
        type=Board.parse,
        help="boards to recommend for, e.g. 5x9 3x13",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA,
        help="CGT sweep JSON (default: reports/cgt-size-sweep.json)",
    )
    parser.add_argument(
        "--cgt-sizes",
        type=lambda text: [int(part) for part in re.split(r"[,\s]+", text.strip()) if part],
        default=list(DEFAULT_CGT_SIZES),
        help="candidate cutoffs (default: 6,8,10,12)",
    )
    args = parser.parse_args(argv)
    if any(size <= 0 or size > MAX_SUPPORTED_CGT for size in args.cgt_sizes):
        parser.error(f"CGT sizes must be in 1..{MAX_SUPPORTED_CGT}")
    args.cgt_sizes = sorted(set(args.cgt_sizes))
    return args


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    if not args.data.is_file():
        print(f"missing sweep data: {args.data}", file=sys.stderr)
        print("run: python3 scripts/cgt_size_sweep.py", file=sys.stderr)
        return 1

    rows = load_rows(args.data)
    available_sizes = {row.cgt_size for row in rows}
    missing_sizes = [size for size in args.cgt_sizes if size not in available_sizes]
    if missing_sizes:
        missing = ",".join(str(size) for size in missing_sizes)
        print(
            f"missing CGT cutoff data for: {missing}; run scripts/cgt_size_sweep.py with those sizes",
            file=sys.stderr,
        )
        return 1

    model = CgtModel(rows)

    for index, board in enumerate(args.boards):
        if index:
            print()
        print_recommendation(model.recommend(board, args.cgt_sizes))

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
