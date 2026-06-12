"""Estimate solver state counts from tablebase files and extrapolate by board shape."""

from __future__ import annotations

import math
import pickle
import re
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

TABLEBASE_NAME_RE = re.compile(r"^(\d+)x(\d+)_sym\.pkl$")


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


def fit_log_line(points: Sequence[Dict[str, Any]]) -> Tuple[float, float]:
    """Return (intercept, slope) for log10(states) = intercept + slope * cells."""
    xs = [float(point["cells"]) for point in points]
    ys = [math.log10(max(float(point["states"]), 1.0)) for point in points]
    return linear_fit(xs, ys)


def family_fits(points: Sequence[Dict[str, Any]]) -> Dict[int, Tuple[float, float]]:
    groups: Dict[int, List[Dict[str, Any]]] = {}
    for point in points:
        groups.setdefault(int(point["m"]), []).append(point)
    fits: Dict[int, Tuple[float, float]] = {}
    for m, family in groups.items():
        if len(family) >= 2:
            fits[m] = fit_log_line(family)
    return fits


def predict_fit(fits: Dict[int, Tuple[float, float]], m: int) -> Tuple[float, float]:
    if m in fits:
        return fits[m]
    if not fits:
        return 0.0, 0.0
    ms = sorted(fits)
    intercepts = [fits[key][0] for key in ms]
    slopes = [fits[key][1] for key in ms]
    ia, ib = linear_fit([float(key) for key in ms], intercepts)
    sa, sb = linear_fit([float(key) for key in ms], slopes)
    return ia + ib * m, sa + sb * m


def read_tablebase_count(path: Path) -> Optional[int]:
    try:
        with path.open("rb") as handle:
            payload = pickle.load(handle)
    except (OSError, pickle.UnpicklingError, EOFError):
        return None
    if not isinstance(payload, dict):
        return None
    count = payload.get("count")
    return count if isinstance(count, int) and count > 0 else None


def normalize_board(m: int, n: int) -> Tuple[int, int]:
    return (m, n) if m <= n else (n, m)


def corpus_points(tablebase_dir: Path) -> Tuple[List[Dict[str, Any]], Optional[float]]:
    """Return measured points and median bytes per stored state from pkl files."""
    if not tablebase_dir.is_dir():
        return [], None

    raw: List[Dict[str, Any]] = []
    ratios: List[float] = []
    for path in sorted(tablebase_dir.glob("*_sym.pkl")):
        match = TABLEBASE_NAME_RE.match(path.name)
        if not match:
            continue
        m, n = normalize_board(int(match.group(1)), int(match.group(2)))
        size_bytes = path.stat().st_size
        count = read_tablebase_count(path)
        if count is not None:
            ratios.append(size_bytes / count)
        raw.append(
            {
                "m": m,
                "n": n,
                "cells": m * n,
                "size_bytes": size_bytes,
                "count": count,
            }
        )

    bytes_per_state = statistics.median(ratios) if ratios else None
    points: List[Dict[str, Any]] = []
    for row in raw:
        states = row["count"]
        if states is None and bytes_per_state and bytes_per_state > 0:
            states = max(1, int(row["size_bytes"] / bytes_per_state))
        if states is None:
            continue
        points.append(
            {
                "m": row["m"],
                "n": row["n"],
                "cells": row["cells"],
                "states": float(states),
                "size_bytes": row["size_bytes"],
                "measured": row["count"] is not None,
                "from_size": row["count"] is None,
            }
        )
    points.sort(key=lambda item: (item["m"], item["cells"]))
    return points, bytes_per_state


def target_boards(max_cells: int) -> List[Tuple[int, int]]:
    targets: List[Tuple[int, int]] = []
    for m in range(1, max_cells + 1, 2):
        if m * m > max_cells:
            break
        for n in range(m, max_cells // m + 1, 2):
            targets.append((m, n))
    return sorted(set(targets), key=lambda item: (item[0], item[0] * item[1]))


def build_complexity_forecast(
    tablebase_dir: Path,
    *,
    max_cells: int = 100,
) -> Dict[str, Any]:
    measured_points, bytes_per_state = corpus_points(tablebase_dir)
    if not measured_points:
        return {
            "available": False,
            "bytes_per_state": bytes_per_state,
            "max_cells": max_cells,
            "series": [],
            "note": "Need at least one tablebase file to estimate complexity.",
        }

    measured_keys = {(int(p["m"]), int(p["n"])) for p in measured_points}
    max_measured_cells = max(int(p["cells"]) for p in measured_points)
    forecast_cells = max(max_cells, max_measured_cells + 10)

    fits = family_fits(measured_points)
    if not fits:
        return {
            "available": True,
            "bytes_per_state": bytes_per_state,
            "max_cells": forecast_cells,
            "series": [
                {
                    "m": int(point["m"]),
                    "points": [
                        {
                            "m": int(point["m"]),
                            "n": int(point["n"]),
                            "cells": int(point["cells"]),
                            "states": float(point["states"]),
                            "measured": True,
                            "from_size": bool(point.get("from_size")),
                            "size_bytes": int(point["size_bytes"]),
                        }
                    ],
                }
                for point in measured_points
            ],
            "note": "Only one board shape in corpus — add more tablebases to extrapolate.",
        }

    by_m: Dict[int, List[Dict[str, Any]]] = {}
    for m, n in target_boards(forecast_cells):
        cells = m * n
        key = (m, n)
        if key in measured_keys:
            source = next(p for p in measured_points if p["m"] == m and p["n"] == n)
            point = {
                "m": m,
                "n": n,
                "cells": cells,
                "states": float(source["states"]),
                "measured": True,
                "from_size": bool(source.get("from_size")),
                "size_bytes": int(source["size_bytes"]),
            }
        else:
            intercept, slope = predict_fit(fits, m)
            point = {
                "m": m,
                "n": n,
                "cells": cells,
                "states": float(10 ** (intercept + slope * cells)),
                "measured": False,
                "from_size": False,
                "size_bytes": None,
            }
        by_m.setdefault(m, []).append(point)

    series = [
        {"m": m, "points": points}
        for m, points in sorted(by_m.items(), key=lambda item: item[0])
    ]
    return {
        "available": True,
        "bytes_per_state": bytes_per_state,
        "max_cells": forecast_cells,
        "series": series,
        "note": (
            "States estimated from tablebase entry counts (read from each .pkl, "
            "or inferred from file size when needed). Extrapolation uses a "
            "log-linear fit per row count m."
        ),
    }
