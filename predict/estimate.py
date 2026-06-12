#!/usr/bin/env python3
"""Estimate Col solver state counts and solve times.

Examples:
  ./col-predict --estimate
  ./col-predict 7x7 5x9 3x13
  ./col-predict --estimate --plot --save predict/complexity.png
  ./col-predict --run --boards 3x13 --threads 12
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
SOLVER = ROOT / "col-solve"
DATA_PATH = ROOT / "predict" / "measurements.json"

STATES_RE = re.compile(r"^states searched:\s+(\d+)\s*$", re.MULTILINE)
TIME_RE = re.compile(r"^time elapsed:\s+([0-9.]+)s\s*$", re.MULTILINE)
WINNER_RE = re.compile(r"^(\d+)\s+x\s+(\d+):\s+(P[12])\s+wins\s*$", re.MULTILINE)


@dataclass
class BoardResult:
    m: int
    n: int
    cells: int
    family: str
    states: int
    seconds: float
    winner: str
    source: str = "measured"


@dataclass
class Estimate:
    m: int
    n: int
    cells: int
    states: float
    measured: bool
    seconds: Optional[float] = None


def board_family(m: int, n: int) -> str:
    if m == 1 or n == 1:
        return "path"
    return "area"


def normalize(m: int, n: int) -> Tuple[int, int]:
    return (m, n) if m <= n else (n, m)


def default_boards(max_cells: int = 45) -> List[Tuple[int, int]]:
    boards: List[Tuple[int, int]] = []

    for n in range(9, max_cells + 1, 2):
        if n <= max_cells:
            boards.append((1, n))

    for n in range(3, 15, 2):
        cells = 3 * n
        if cells <= max_cells:
            boards.append((3, n))

    for n in range(3, 11, 2):
        cells = 5 * n
        if cells <= max_cells:
            boards.append((5, n))

    for side in (7, 9):
        if side * side <= max_cells:
            boards.append((side, side))

    seen = set()
    unique: List[Tuple[int, int]] = []
    for board in boards:
        key = normalize(*board)
        if key not in seen:
            seen.add(key)
            unique.append(key)
    return sorted(unique, key=lambda item: item[0] * item[1])


def seed_results() -> List[BoardResult]:
    """Previously measured points (12 threads unless noted)."""
    raw = [
        (1, 9, 77, 0.000177, "P2"),
        (1, 11, 222, 0.000209, "P2"),
        (1, 13, 491, 0.000228, "P2"),
        (1, 15, 1208, 0.000379, "P2"),
        (1, 17, 3086, 0.000484, "P2"),
        (1, 19, 7261, 0.000725, "P2"),
        (1, 21, 17899, 0.001625, "P2"),
        (1, 23, 43732, 0.004235, "P2"),
        (1, 25, 107356, 0.008679, "P2"),
        (1, 27, 256080, 0.023819, "P2"),
        (1, 29, 627319, 0.064367, "P2"),
        (1, 31, 1529401, 0.172446, "P2"),
        (1, 33, 3752737, 0.443554, "P2"),
        (1, 35, 8991885, 1.199861, "P2"),
        (1, 37, 21874474, 2.896966, "P2"),
        (3, 3, 35, 0.000173, "P2"),
        (3, 5, 594, 0.000199, "P2"),
        (3, 7, 16806, 0.001930, "P2"),
        (3, 9, 144509, 0.015383, "P2"),
        (5, 5, 85380, 0.016575, "P2"),
        (3, 11, 16770392, 4.276387, "P2"),
        (5, 7, 80569940, 44.198694, "P2"),
    ]
    out: List[BoardResult] = []
    for m, n, states, seconds, winner in raw:
        m, n = normalize(m, n)
        out.append(
            BoardResult(
                m=m,
                n=n,
                cells=m * n,
                family=board_family(m, n),
                states=states,
                seconds=seconds,
                winner=winner,
                source="seed",
            )
        )
    return out


def run_board(m: int, n: int, threads: int, timeout: Optional[float]) -> BoardResult:
    if not SOLVER.is_file():
        raise FileNotFoundError(f"Solver not found: {SOLVER}")

    cmd = [str(SOLVER), "--m", str(m), "--n", str(n), "--no-tablebase"]
    if threads:
        cmd.extend(["--threads", str(threads)])

    started = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    elapsed = time.perf_counter() - started
    output = proc.stdout + "\n" + proc.stderr

    if proc.returncode != 0:
        raise RuntimeError(f"{m}x{n} failed ({proc.returncode}):\n{output.strip()}")

    states_match = STATES_RE.search(output)
    time_match = TIME_RE.search(output)
    winner_match = WINNER_RE.search(output)
    if not states_match or not winner_match:
        raise RuntimeError(f"Could not parse solver output for {m}x{n}:\n{output.strip()}")

    m_out, n_out = normalize(int(winner_match.group(1)), int(winner_match.group(2)))
    return BoardResult(
        m=m_out,
        n=n_out,
        cells=m_out * n_out,
        family=board_family(m_out, n_out),
        states=int(states_match.group(1)),
        seconds=float(time_match.group(1)) if time_match else elapsed,
        winner=winner_match.group(3),
        source="measured",
    )


def merge_results(existing: Sequence[BoardResult], fresh: Sequence[BoardResult]) -> List[BoardResult]:
    by_key = {(item.m, item.n): item for item in existing}
    for item in fresh:
        by_key[(item.m, item.n)] = item
    return sorted(by_key.values(), key=lambda item: item.cells)


def load_results() -> List[BoardResult]:
    if not DATA_PATH.exists():
        return seed_results()
    payload = json.loads(DATA_PATH.read_text())
    return [
        BoardResult(
            m=entry["m"],
            n=entry["n"],
            cells=entry["cells"],
            family=entry["family"],
            states=entry["states"],
            seconds=entry["seconds"],
            winner=entry["winner"],
            source=entry.get("source", "saved"),
        )
        for entry in payload
    ]


def save_results(results: Sequence[BoardResult]) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps([asdict(item) for item in results], indent=2) + "\n")


def print_table(results: Sequence[BoardResult]) -> None:
    print(f"{'board':>8} {'cells':>5} {'family':>5} {'states':>12} {'seconds':>10} {'winner':>6}")
    for item in results:
        label = f"{item.m}x{item.n}"
        print(
            f"{label:>8} {item.cells:5d} {item.family:>5} "
            f"{item.states:12,} {item.seconds:10.3f} {item.winner:>6}"
        )


def linear_fit(xs: Sequence[float], ys: Sequence[float]) -> Tuple[float, float]:
    """Least-squares fit returning (intercept, slope) for y = intercept + slope * x."""
    if len(xs) < 2:
        return (ys[0] if ys else 0.0), 0.0
    n = len(xs)
    sx = sum(xs)
    sy = sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    denom = n * sxx - sx * sx
    if denom == 0:
        return ys[0], 0.0
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    return intercept, slope


def fit_log_line(points: Sequence[BoardResult]) -> Tuple[float, float]:
    """Return (intercept, slope) for log10(states) = intercept + slope * cells."""
    xs = [float(p.cells) for p in points]
    ys = [math.log10(max(p.states, 1)) for p in points]
    return linear_fit(xs, ys)


def family_fits(results: Sequence[BoardResult]) -> dict:
    """Fit log10(states) = a_m + b_m * cells for each measured min-dimension m."""
    groups: dict = {}
    for item in results:
        groups.setdefault(item.m, []).append(item)
    fits = {}
    for m, points in groups.items():
        if len(points) >= 2:
            fits[m] = fit_log_line(points)
    return fits


def predict_fit(fits: dict, m: int) -> Tuple[float, float]:
    """Fit parameters for row count m, extrapolating (a_m, b_m) linearly in m if unmeasured."""
    if m in fits:
        return fits[m]
    ms = sorted(fits)
    intercepts = [fits[k][0] for k in ms]
    slopes = [fits[k][1] for k in ms]
    ia, ib = linear_fit([float(k) for k in ms], intercepts)
    sa, sb = linear_fit([float(k) for k in ms], slopes)
    return ia + ib * m, sa + sb * m


def throughput_by_row(results: Sequence[BoardResult]) -> dict:
    """Average measured states/sec for each row count m."""
    by_m: dict = {}
    for item in results:
        if item.seconds <= 0:
            continue
        by_m.setdefault(item.m, []).append(item.states / item.seconds)
    return {m: statistics.mean(rates) for m, rates in by_m.items() if rates}


def predict_throughput(rates: dict, m: int) -> float:
    if m in rates:
        return rates[m]
    ms = sorted(rates)
    xs = [float(k) for k in ms]
    ys = [math.log10(rates[k]) for k in ms]
    intercept, slope = linear_fit(xs, ys)
    return 10 ** (intercept + slope * m)


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f} min"
    if seconds < 86400:
        return f"{seconds / 3600:.1f} hr"
    if seconds < 86400 * 365:
        return f"{seconds / 86400:.1f} days"
    return f"{seconds / 86400 / 365:.1f} years"


def format_states(states: float) -> str:
    if states < 1e12:
        return f"{states:,.0f}"
    return f"{states:.2e}"


def estimate_boards(
    results: Sequence[BoardResult], max_cells: int, boards: Optional[Sequence[Tuple[int, int]]] = None
) -> List[Estimate]:
    """Estimate states for odd m x n boards (m <= n) up to max_cells or explicit list."""
    measured = {(item.m, item.n): item for item in results}
    fits = family_fits(results)
    rates = throughput_by_row(results)
    estimates: List[Estimate] = []

    if boards is None:
        targets: List[Tuple[int, int]] = []
        for m in range(1, max_cells + 1, 2):
            if m * m > max_cells:
                break
            for n in range(m, max_cells // m + 1, 2):
                targets.append((m, n))
    else:
        targets = [normalize(m, n) for m, n in boards]

    for m, n in sorted(set(targets), key=lambda item: (item[0], item[0] * item[1])):
        cells = m * n
        key = (m, n)
        if key in measured:
            item = measured[key]
            estimates.append(
                Estimate(m, n, cells, float(item.states), True, item.seconds)
            )
        else:
            intercept, slope = predict_fit(fits, m)
            states = 10 ** (intercept + slope * cells)
            rate = predict_throughput(rates, m)
            estimates.append(Estimate(m, n, cells, states, False, states / rate))

    return estimates


def print_estimates(results: Sequence[BoardResult], max_cells: int, boards: Optional[List[Tuple[int, int]]]) -> None:
    estimates = estimate_boards(results, max_cells, boards)
    print(f"{'board':>8} {'cells':>5} {'est. states':>14} {'est. time':>12} {'source':>12}")
    for e in estimates:
        source = "measured" if e.measured else "extrapolated"
        duration = format_duration(e.seconds) if e.seconds is not None else "?"
        print(
            f"{e.m}x{e.n:>6} {e.cells:5d} {format_states(e.states):>14} "
            f"{duration:>12} {source:>12}"
        )


def plot_estimates(
    results: Sequence[BoardResult], max_cells: int, save_path: Optional[Path]
) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise SystemExit(
            "matplotlib is required for --plot. Install with: pip install matplotlib"
        ) from exc

    estimates = estimate_boards(results, max_cells)
    families = sorted({e.m for e in estimates})
    cmap = plt.get_cmap("viridis")
    colors = {m: cmap(i / max(len(families) - 1, 1)) for i, m in enumerate(families)}

    fig, ax = plt.subplots(figsize=(11, 6.5))

    for m in families:
        series = [e for e in estimates if e.m == m]
        ax.plot(
            [e.cells for e in series],
            [e.states for e in series],
            "-",
            color=colors[m],
            alpha=0.6,
            linewidth=1.4,
            label=f"{m}×N",
            zorder=2,
        )
        meas = [e for e in series if e.measured]
        est = [e for e in series if not e.measured]
        if meas:
            ax.scatter(
                [e.cells for e in meas],
                [e.states for e in meas],
                color=colors[m],
                s=45,
                zorder=3,
            )
        if est:
            ax.scatter(
                [e.cells for e in est],
                [e.states for e in est],
                facecolors="none",
                edgecolors=colors[m],
                s=40,
                zorder=3,
            )

    for e in estimates:
        if e.n == max(x.n for x in estimates if x.m == e.m):
            ax.annotate(
                f"{e.m}×{e.n}",
                (e.cells, e.states),
                textcoords="offset points",
                xytext=(5, -3),
                fontsize=8,
                color=colors[e.m],
            )

    ax.set_yscale("log")
    ax.set_xlabel("Board cells (m × n)")
    ax.set_ylabel("States (log scale)")
    ax.set_title(
        f"Col solver: estimated state complexity up to {max_cells} cells\n"
        "filled = measured, hollow = extrapolated (log-linear fit per row count)"
    )
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(title="rows", loc="upper left")
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=160)
        print(f"Saved plot to {save_path}")
    else:
        plt.show()


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "boards",
        nargs="*",
        help="boards to estimate as MxN (e.g. 7x7 5x9). Implies --estimate.",
    )
    parser.add_argument("--run", action="store_true", help="run fresh benchmarks with col-solve")
    parser.add_argument("--plot", action="store_true", help="plot with matplotlib")
    parser.add_argument(
        "--estimate",
        action="store_true",
        help="extrapolate states/times for odd m x n boards up to --max-cells",
    )
    parser.add_argument("--save", type=Path, help="save plot image instead of showing window")
    parser.add_argument("--max-cells", type=int, default=100, help="largest board area to include")
    parser.add_argument("--timeout", type=float, default=None, help="per-board timeout in seconds")
    parser.add_argument("--threads", type=int, default=1, help="solver thread count (1 = exact counts)")
    parser.add_argument(
        "--boards",
        nargs="*",
        dest="run_boards",
        help="explicit boards for --run as MxN (e.g. 3x11 5x7)",
    )
    return parser.parse_args(argv)


def parse_boards_arg(values: Iterable[str]) -> List[Tuple[int, int]]:
    boards: List[Tuple[int, int]] = []
    for token in values:
        if "x" not in token:
            raise ValueError(f"Expected MxN, got {token!r}")
        m_text, n_text = token.lower().split("x", 1)
        boards.append(normalize(int(m_text), int(n_text)))
    return boards


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    results = load_results()

    if args.run:
        if args.run_boards:
            boards = parse_boards_arg(args.run_boards)
        else:
            boards = default_boards(min(args.max_cells, 45))

        fresh: List[BoardResult] = []
        for m, n in boards:
            label = f"{m}x{n}"
            print(f"Running {label}...", flush=True)
            try:
                result = run_board(m, n, threads=args.threads, timeout=args.timeout)
            except subprocess.TimeoutExpired:
                print(f"  timeout on {label}", file=sys.stderr)
                continue
            except RuntimeError as exc:
                print(f"  {exc}", file=sys.stderr)
                continue
            fresh.append(result)
            print(f"  {result.states:,} states in {result.seconds:.3f}s")

        results = merge_results(results, fresh)
        save_results(results)

    estimate = args.estimate or bool(args.boards)
    if estimate:
        boards = parse_boards_arg(args.boards) if args.boards else None
        print_estimates(results, args.max_cells, boards)
        if args.plot:
            plot_estimates(results, args.max_cells, args.save)
        return 0

    print_table(results)

    if args.plot:
        plot_estimates(results, args.max_cells, args.save)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
