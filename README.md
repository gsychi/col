# Col — 2D placement game solver

Three entry points at the repo root:

| Command | Purpose |
|---|---|
| `./col-solve` | Rust solver (builds on first run) |
| `./col-predict` | Estimate state counts and solve times |
| `./col-cgt` | Recommend CGT endgame cutoff for a board |
| `./col-bench` | Compare two solver binaries with paired cold runs |
| `./col-gui` | Desktop tablebase explorer |

## Layout

```
col/
├── col-solve          # solver wrapper
├── col-predict        # complexity / time estimator
├── col-gui            # desktop app wrapper
├── solver/            # Rust solver source
├── python/
│   ├── col/           # shared Python library (tablebase, DFS for GUI analyze)
│   └── gui_server.py  # HTTP backend for the explorer
├── gui/               # Electron shell
├── predict/           # estimation script + saved measurements
└── data/
    └── tablebases/    # .pkl tablebase files ({m}x{n}_sym.pkl)
```

## Solver

```bash
./col-solve --m 5 --n 7 --progress
./col-solve --m 3 --n 11 --no-tablebase --threads 12
```

Tablebases are saved to `data/tablebases/` by default.

With multiple threads the solver uses an **AND-split** scheduler: every
symmetry-distinct P1 opening must be refuted anyway, and within each opening
the P1 continuations of the move-ordered P2 reply must all be refuted too, so
the work splits into hundreds of required subtasks instead of ~20 openings.
Pass `--root-split` for the older opening-level split (useful for comparison).

## Render (cloud)

Deploy continuous solving + web explorer to [Render](https://render.com):

1. Push this repo to GitHub.
2. In Render: **New → Blueprint** → repo `gsychi/col` → blueprint path **`deploy/render.yaml`**.

**Important:** Render disks are **per-service only** — two separate services cannot share one disk. This blueprint runs the solver and web UI in **one** web service (`deploy/start-all.sh`) so they share `/data`.

| URL | Purpose |
|---|---|
| `/` | Research dashboard (solver progress, tablebase corpus) |
| `/explorer` | Interactive position explorer |
| `/dashboard` | Alias for `/` |

For a **manual** setup (no Blueprint): create one **Web Service** with Dockerfile `deploy/Dockerfile`, command **`./deploy/start-all.sh`**, disk at **`/data`**, and the env vars below. Do **not** split into a separate Background Worker unless you add external storage (S3, etc.).

| Env var | Default | Purpose |
|---|---|---|
| `TABLEBASE_DIR` | `/data/tablebases` | Shared tablebase storage |
| `STATUS_FILE` | `/data/solver_status.json` | Live progress for dashboard |
| `SOLVER_THREADS` | `auto` (all CPUs) | Worker: `--threads` for col-solve; set a number to cap |
| `SOLVER_MEMO` | `fixed` | Transposition table: `fixed` (RAM cap), `open`, or `hash` |
| `SOLVER_MEMO_BITS` | auto from RAM | Fixed table size: `2^bits` slots × 16 bytes (~18% of RAM by default) |
| `SOLVER_MEMO_FRACTION` | `0.18` | Share of host RAM for the fixed memo table (leaves headroom for save spikes + web UI) |
| `SOLVER_MEMO_MIN_LEGAL` | (none) | Skip memo below N legal cells (e.g. `8` on huge boards) |
| `CONTINUOUS_START_TOTAL` | `3` | First odd cell total to solve |
| `CONTINUOUS_MAX_TOTAL` | (none) | Optional cap, e.g. `35` for 5×7 era |
| `COL_M` / `COL_N` | `3` / `11` | Default board for explorer UI |

Local smoke test:

```bash
docker build -f deploy/Dockerfile -t col-render .
# worker
docker run --rm -v col-data:/data col-render ./deploy/start-worker.sh
# web (another terminal)
docker run --rm -p 8000:8000 -v col-data:/data -e PORT=8000 col-render ./deploy/start-web.sh
```

## Predict

```bash
./col-predict --estimate              # all odd boards up to 100 cells
./col-predict 7x7 5x9 3x13            # specific boards
./col-predict --estimate --plot       # requires matplotlib
```

Estimates use log-linear extrapolation from measured benchmarks (no solver runs unless `--run`).

## CGT Cutoff Sweeps

```bash
python3 scripts/cgt_size_sweep.py --boards 3x9 3x11 5x7 --cgt-sizes 0,6,8,10,12
```

This runs fresh `--no-tablebase` solves, compares each `--endgame-size` against
CGT disabled, and writes matrix reports to `reports/cgt-size-sweep.md` and
`reports/cgt-size-sweep.json`.

Recommend a cutoff from that data:

```bash
./col-cgt 5x9
./col-cgt 3x13
```

## Reproducible odd-board research

“Odd boards through 39 cells” means every normalized odd-by-odd rectangle
`m <= n` with `m*n <= 39` (excluding `1x1`). The shared catalog contains 27
boards, including these eight non-path boards:

```text
3x3 3x5 3x7 5x5 3x9 3x11 5x7 3x13
```

Run the complete outcome/performance baseline or a controlled experiment:

```bash
python3 scripts/odd_board_experiments.py --experiment baseline
python3 scripts/odd_board_experiments.py --experiment pairing
python3 scripts/odd_board_experiments.py --experiment cgt --boards 3x11 5x7 3x13
python3 scripts/odd_board_experiments.py --experiment threads --boards 3x11 5x7
```

The harness records the command, commit, dirty working tree, platform, winner,
state count, throughput, solve time, and peak RSS in JSON and Markdown under
`reports/odd-board-experiments/`.

Compare two already-built solver binaries with interleaved A/B runs and a
winner-equivalence gate:

```bash
./col-bench /tmp/col-rs-baseline ./solver/target/release/col-rs \
  --boards 3x11 5x7 --repeats 3 --memo fixed --memo-bits 20 \
  --out-json /tmp/col-bench.json
```

Progress goes to stderr and the complete comparison JSON goes to stdout. No
report or cache is retained unless `--out-json` is supplied. Fixed-memo runs
also record full-window TT evictions, making replacement pressure visible.

Proof-oriented tools emit replayable artifacts rather than treating pattern
frequency as a proof:

```bash
python3 scripts/mine_3xn_families.py --boards 3x5 3x7 3x9
python3 scripts/verify_3xn_certificates.py
python3 scripts/build_3xn_strategy_dag.py
python3 scripts/verify_3xn_strategy_dag.py
python3 scripts/audit_3xn_frontier_abstraction.py
python3 scripts/certify_cgt_components.py
python3 scripts/test_odd_invariants.py
python3 scripts/proof_status.py
```

The rooted strategy DAG is an exact finite-board P2 certificate: its verifier
replays every P1 move, checks the selected P2 response, and independently
checks terminal and half-turn-pairing leaves. The frontier audit exits nonzero
when one truncated signature contains both winning and losing exact states;
that is a concrete counterexample to treating the signature as a proof state.

`proof_status.py` exits nonzero while any all-width proof obligation remains
open. In particular, finite verification through a fixed width is not reported
as a proof of all odd `3xn` boards.

## GUI

```bash
./col-gui
```

Opens the Electron app. Choose a `.pkl` from `data/tablebases/` or any folder. Requires Python 3 and `npm install` in `gui/` (done automatically on first launch).

## Dependencies

- **Solver:** Rust toolchain (`cargo`)
- **GUI:** Node.js, Python 3
- **Predict plots:** `pip install matplotlib` (optional)
