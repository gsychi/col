#!/usr/bin/env python3
"""Continuously solve Col boards by total cell count and update the tablebase.

Walks odd totals 3, 5, 7, 9, ... For each total, enumerates every factor pair
(m, n) with m * n = total (normalized to m <= n), solves each board, and saves
to the tablebase before moving on.

Examples:
  ./continuous-solve
  ./continuous-solve --max-total 25
  ./continuous-solve --start-total 15 --endgame-size 10
  ./continuous-solve --skip-existing --tablebase-dir data/tablebases
  ./continuous-solve --status-file /data/solver_status.json -- --progress --threads 12
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parent
SOLVER = ROOT / "col-solve"
DEFAULT_TABLEBASE_DIR = ROOT / "data" / "tablebases"

WINNER_RE = re.compile(r"^(\d+)\s+x\s+(\d+):\s+(P[12])\s+wins\s*$", re.MULTILINE)
TIME_RE = re.compile(r"^time elapsed:\s+([0-9.]+)s\s*$", re.MULTILINE)
STATES_RE = re.compile(r"^states searched:\s+(\d+)\s*$", re.MULTILINE)
SAVED_RE = re.compile(r"^tablebase saved:\s+", re.MULTILINE)
LOADED_RE = re.compile(r"^tablebase loaded:\s+(\d+)\s+entries\s*$", re.MULTILINE)
PROGRESS_RE = re.compile(
    r"states searched:\s+(\d+)(?:\s+\|\s+memo:\s+(\d+))?(?:\s+\|\s+([0-9.]+)/s)?(?:\s+\|\s+([0-9.]+)s)?"
)

Board = Tuple[int, int]

_stop_requested = False


def _handle_signal(_signum: int, _frame: object) -> None:
    global _stop_requested
    _stop_requested = True
    print("\nStop requested; finishing current board...", file=sys.stderr, flush=True)


def odd_totals(start: int, max_total: int | None) -> Iterator[int]:
    total = start if start % 2 == 1 else start + 1
    while max_total is None or total <= max_total:
        yield total
        total += 2


def boards_for_total(total: int) -> List[Board]:
    """All distinct m x n boards with m * n = total and m <= n."""
    pairs: List[Board] = []
    limit = int(math.isqrt(total))
    for m in range(1, limit + 1):
        if total % m != 0:
            continue
        n = total // m
        if m <= n:
            pairs.append((m, n))
    return pairs


def tablebase_path(tablebase_dir: Path, m: int, n: int) -> Path:
    if m > n:
        m, n = n, m
    return tablebase_dir / f"{m}x{n}_sym.pkl"


def normalize_stream_line(chunk: str) -> str:
    if "\r" in chunk:
        chunk = chunk.split("\r")[-1]
    return chunk.strip()


class StatusWriter:
    def __init__(self, path: Path, *, start_total: int, max_total: int | None) -> None:
        self.path = path
        self.start_total = start_total
        self.max_total = max_total
        self.finished: List[dict[str, Any]] = []
        self.running = False

    def _write(self, payload: dict[str, Any]) -> None:
        payload = {
            **payload,
            "finished": self.finished,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self.path)

    def set_idle(self, *, boards_done: int) -> None:
        self.running = False
        self._write(
            {
                "running": False,
                "boards_done": boards_done,
                "queue": {
                    "start_total": self.start_total,
                    "max_total": self.max_total,
                },
                "current": None,
            }
        )

    def start_board(
        self,
        *,
        total: int,
        m: int,
        n: int,
        board_index: int,
        boards_on_total: int,
    ) -> None:
        self.running = True
        self._write(
            {
                "running": True,
                "queue": {
                    "start_total": self.start_total,
                    "max_total": self.max_total,
                    "current_total": total,
                    "board_index": board_index,
                    "boards_on_total": boards_on_total,
                },
                "current": {
                    "m": m,
                    "n": n,
                    "states": 0,
                    "memo": None,
                    "rate": None,
                    "elapsed_s": 0.0,
                    "skipped": False,
                },
            }
        )

    def update_progress(
        self,
        *,
        m: int,
        n: int,
        total: int,
        board_index: int,
        boards_on_total: int,
        states: int,
        memo: int | None,
        rate: float | None,
        elapsed_s: float | None,
    ) -> None:
        self._write(
            {
                "running": True,
                "queue": {
                    "start_total": self.start_total,
                    "max_total": self.max_total,
                    "current_total": total,
                    "board_index": board_index,
                    "boards_on_total": boards_on_total,
                },
                "current": {
                    "m": m,
                    "n": n,
                    "states": states,
                    "memo": memo,
                    "rate": rate,
                    "elapsed_s": elapsed_s,
                    "skipped": False,
                },
            }
        )

    def finish_board(self, result: dict[str, Any]) -> None:
        entry = {
            "m": result["m"],
            "n": result["n"],
            "winner": result["winner"],
            "states": result["states"],
            "seconds": result["seconds"],
            "skipped": bool(result.get("skipped")),
            "saved": bool(result.get("saved")),
        }
        self.finished.append(entry)
        self.running = False
        self._write(
            {
                "running": False,
                "queue": {
                    "start_total": self.start_total,
                    "max_total": self.max_total,
                },
                "current": None,
                "last_finished": entry,
            }
        )


def run_solver(
    m: int,
    n: int,
    solver_args: Sequence[str],
) -> subprocess.CompletedProcess[str]:
    cmd = [str(SOLVER), "--m", str(m), "--n", str(n), *solver_args]
    return subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def run_solver_streaming(
    m: int,
    n: int,
    solver_args: Sequence[str],
    *,
    status: StatusWriter | None,
    queue_total: int,
    board_index: int,
    boards_on_total: int,
) -> tuple[str, str, int]:
    cmd = [str(SOLVER), "--m", str(m), "--n", str(n), *solver_args]
    proc = subprocess.Popen(
        cmd,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert proc.stdout is not None
    assert proc.stderr is not None

    stderr_chunks: List[str] = []

    def drain_stderr() -> None:
        for line in proc.stderr:
            stderr_chunks.append(line)
            print(line, end="", file=sys.stderr, flush=True)
            normalized = normalize_stream_line(line)
            match = PROGRESS_RE.search(normalized)
            if match and status is not None:
                status.update_progress(
                    m=m,
                    n=n,
                    total=queue_total,
                    board_index=board_index,
                    boards_on_total=boards_on_total,
                    states=int(match.group(1)),
                    memo=int(match.group(2)) if match.group(2) else None,
                    rate=float(match.group(3)) if match.group(3) else None,
                    elapsed_s=float(match.group(4)) if match.group(4) else None,
                )

    reader = threading.Thread(target=drain_stderr, daemon=True)
    reader.start()
    stdout = proc.stdout.read()
    returncode = proc.wait()
    reader.join()
    stderr = "".join(stderr_chunks)
    if stdout:
        print(stdout, end="")
    return stdout, stderr, returncode


def parse_result(output: str, m: int, n: int) -> dict[str, object]:
    winner = WINNER_RE.search(output)
    elapsed = TIME_RE.search(output)
    states = STATES_RE.search(output)
    loaded = LOADED_RE.search(output)
    return {
        "m": int(winner.group(1)) if winner else m,
        "n": int(winner.group(2)) if winner else n,
        "winner": winner.group(3) if winner else "?",
        "seconds": float(elapsed.group(1)) if elapsed else 0.0,
        "states": int(states.group(1)) if states else 0,
        "cached": bool(loaded)
        and SAVED_RE.search(output) is None
        and int(states.group(1)) == 0
        if states
        else bool(loaded),
        "saved": SAVED_RE.search(output) is not None,
        "loaded_entries": int(loaded.group(1)) if loaded else 0,
    }


def solve_board(
    m: int,
    n: int,
    *,
    tablebase_dir: Path,
    skip_existing: bool,
    solver_args: Sequence[str],
    status: StatusWriter | None = None,
    queue_total: int | None = None,
    board_index: int = 0,
    boards_on_total: int = 1,
) -> dict[str, object] | None:
    norm_m, norm_n = (m, n) if m <= n else (n, m)
    if skip_existing and tablebase_path(tablebase_dir, norm_m, norm_n).is_file():
        print(
            f"  {norm_m} x {norm_n}: skipped (tablebase exists)",
            flush=True,
        )
        result = {
            "m": norm_m,
            "n": norm_n,
            "winner": "?",
            "seconds": 0.0,
            "states": 0,
            "cached": True,
            "saved": False,
            "loaded_entries": 0,
            "skipped": True,
        }
        if status is not None:
            status.finish_board(result)
        return result

    if status is not None and queue_total is not None:
        status.start_board(
            total=queue_total,
            m=norm_m,
            n=norm_n,
            board_index=board_index,
            boards_on_total=boards_on_total,
        )

    started = time.perf_counter()
    stream_progress = "--progress" in solver_args
    if stream_progress:
        stdout, stderr, returncode = run_solver_streaming(
            m,
            n,
            solver_args,
            status=status,
            queue_total=queue_total or norm_m * norm_n,
            board_index=board_index,
            boards_on_total=boards_on_total,
        )
        elapsed = time.perf_counter() - started
        if returncode != 0:
            print(stdout, end="")
            raise RuntimeError(f"solver failed for {m}x{n} (exit {returncode})")
        combined = stdout + stderr
    else:
        proc = run_solver(m, n, solver_args)
        elapsed = time.perf_counter() - started
        if proc.returncode != 0:
            print(proc.stdout, end="")
            print(proc.stderr, end="", file=sys.stderr)
            raise RuntimeError(f"solver failed for {m}x{n} (exit {proc.returncode})")
        combined = proc.stdout
        if proc.stderr:
            print(proc.stderr, end="", file=sys.stderr)

    result = parse_result(combined, norm_m, norm_n)
    result["seconds"] = float(result["seconds"]) or elapsed
    result["skipped"] = False
    status_label = (
        "cached"
        if result["cached"] and not result["saved"]
        else ("saved" if result["saved"] else "solved")
    )
    print(
        f"  {result['m']} x {result['n']}: {result['winner']} wins "
        f"({result['states']} states, {result['seconds']:.3f}s, {status_label})",
        flush=True,
    )
    if status is not None:
        status.finish_board(result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Continuously solve odd-area Col boards (totals 3, 5, 7, ...) "
            "and update the tablebase."
        ),
    )
    parser.add_argument(
        "--start-total",
        type=int,
        default=3,
        help="first total cell count to process (default: 3)",
    )
    parser.add_argument(
        "--max-total",
        type=int,
        default=None,
        help="last total cell count to process (default: run until interrupted)",
    )
    parser.add_argument(
        "--tablebase-dir",
        type=Path,
        default=DEFAULT_TABLEBASE_DIR,
        help="directory for tablebase files",
    )
    parser.add_argument(
        "--status-file",
        type=Path,
        default=None,
        help="write live solver progress JSON for dashboards (optional)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="skip boards whose tablebase file already exists",
    )
    parser.add_argument(
        "solver_args",
        nargs=argparse.REMAINDER,
        help="extra arguments passed to col-solve (prefix with --)",
    )
    return parser


def normalize_solver_args(solver_args: Sequence[str]) -> List[str]:
    args = list(solver_args)
    if args and args[0] == "--":
        args = args[1:]
    return args


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.start_total <= 0:
        parser.error("--start-total must be positive")
    if args.max_total is not None and args.max_total < args.start_total:
        parser.error("--max-total must be >= --start-total")
    if not SOLVER.is_file():
        parser.error(f"solver wrapper not found: {SOLVER}")

    solver_args = normalize_solver_args(args.solver_args)
    if "--tablebase-dir" not in solver_args:
        solver_args = [
            "--tablebase-dir",
            str(args.tablebase_dir),
            *solver_args,
        ]
    if "--no-tablebase" in solver_args:
        parser.error("continuous solve requires tablebase enabled; omit --no-tablebase")

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    args.tablebase_dir.mkdir(parents=True, exist_ok=True)

    status_path = args.status_file
    if status_path is None:
        env_status = os.environ.get("STATUS_FILE")
        if env_status:
            status_path = Path(env_status)

    status = (
        StatusWriter(status_path, start_total=args.start_total, max_total=args.max_total)
        if status_path is not None
        else None
    )

    print(
        "Continuous solve: odd totals "
        f"{args.start_total}"
        f"{f'..{args.max_total}' if args.max_total is not None else '+'}"
        f", tablebase {args.tablebase_dir}",
        flush=True,
    )
    if status_path is not None:
        print(f"Status file: {status_path}", flush=True)

    grand_started = time.perf_counter()
    boards_done = 0

    for total in odd_totals(args.start_total, args.max_total):
        if _stop_requested:
            break

        boards = boards_for_total(total)
        print(f"\n=== total {total} ({len(boards)} board(s)) ===", flush=True)

        for board_index, (m, n) in enumerate(boards):
            if _stop_requested:
                break
            solve_board(
                m,
                n,
                tablebase_dir=args.tablebase_dir,
                skip_existing=args.skip_existing,
                solver_args=solver_args,
                status=status,
                queue_total=total,
                board_index=board_index,
                boards_on_total=len(boards),
            )
            boards_done += 1

    elapsed = time.perf_counter() - grand_started
    print(
        f"\nDone: {boards_done} board(s) in {elapsed:.1f}s",
        flush=True,
    )
    if status is not None:
        status.set_idle(boards_done=boards_done)
    return 0 if not _stop_requested else 130


if __name__ == "__main__":
    raise SystemExit(main())
