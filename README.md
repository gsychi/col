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

## Empty 3 × n theorem

The current mathematical result is that every empty `3 × n` Col board has
value zero. The even-width case uses half-turn pairing; widths `4k+1` use a
periodic certified tiling; widths `4k+3` use finite base cases and a
strong-induction proof with a separator in the middle-row `3 mod 4` opening.
The full argument and its gadget inventory are recorded in
[the all-width proof write-up](proofs/construction/empty_3xn_theorem.md).
The whole theorem, including every finite certificate, is formalised in Lean 4
without external libraries; see [the Lean proof](proofs/lean/README.md)
(`cd proofs/lean && lake build`). Papers for submission and for beginners are
in [`papers/`](papers/).
For the proof's game conventions, the five-row boundary-state program,
documented obstructions, and suggested next research targets, see the
[Col research handoff](proofs/construction/research/col_research_handoff.md).
The five-row and general odd-by-odd problems remain open; the three-row theorem
does not claim to solve them.

## Certified strategies and larger strips

The solver now tries verified one-sided tilings before full-board DFS. The
bundled certificate library proves empty 3×15 and supports arbitrarily long
3×(4k+1) strips, including 3×101. Certificate results retain an executable
strategy and are separate from numerical CGT values and ordinary tablebases.

```bash
./col-solve --m 3 --n 15 --proof-out /tmp/3x15.json
./col-cert verify /tmp/3x15.json
./col-cert verify-python /tmp/3x15.json
./col-cert replay /tmp/3x15.json --moves 0 14
./col-cert --m 3 --n 101 --proof-out /tmp/3x101.json
./col-cert discover --out /tmp/col-tiles --boards 3x19 3x23 5x9 7x7
```

`--proof-mode root` is the default; `off` restores ordinary DFS and `search`
also enables deeper certificate cutoffs. `col-cert` never falls back to DFS:
exit status 2 means **unknown**, not a winning or losing result. Without an
explicit output path, witnesses are saved under `data/proofs/`.

The default library covers 19/20 representative openings on 3×19. The
[checkpoint experiment](reports/weighted-tiling/checkpoint-results.md) closes
the remaining opening by exposing one existing internal certificate state as
a reusable tile. Its separate 26-tile library certifies all 57 openings, with
both checkers agreeing and an executable response strategy:

```bash
./col-cert --m 3 --n 19 --proof-library reports/weighted-tiling/checkpoint-library --proof-out /tmp/3x19.json
./col-cert verify /tmp/3x19.json
./col-cert replay /tmp/3x19.json --moves 26
```

The [weighted experiment](reports/weighted-tiling/README.md) compares signed
bounds on known boards. Run `python3 scripts/benchmark_weighted_tiling.py`
and then `python3 scripts/checkpoint_tiling_probe.py` to reproduce both
experiments. General compensated bounds remain experimental and require a
different gameplay player; the extracted zero-bound tile above works with
the existing player. Production defaults are unchanged. Taller odd-by-odd
boards remain outside the `3 × n` theorem. See
[the integration report](reports/certified-tiling-integration.md) for the
original artifact semantics, budgets, verification, and benchmarks. Its
historical statements that wider `4k+3` strips are unresolved predate the
inductive proof linked above; the certificate explorer still reports unknown
when its finite tile library cannot construct a witness.

The [adaptive search experiment](reports/adaptive-tiling/README.md) adds bounded
multi-round strategies, indexed checkpoint lookup, and targeted local searches.
It admitted 18 additional local certificates; its finite tile library still
returns unknown for 3×23, although the all-width induction proves that board's
outcome. This distinction is between the theorem and this particular witness
search, not an open mathematical case.
Run `python3 scripts/refine_adaptive_tiling.py` to reproduce the experiment;
its separate library is under `reports/adaptive-tiling/final/library`.

The [atlas integration and benchmark](reports/atlas-priority/README.md) adds
role-explicit imports, executable counterstrategies, complete local classification
lookups, and 772 exact-zero upgrades. On matched 3×23 cases the full atlas costs
more time and memory without closing the center opening, so it remains opt-in:

```bash
python3 scripts/adaptive_tiling_research.py --library reports/adaptive-tiling/final/library --atlas proofs/atlas --atlas-review proofs/atlas-review --out /tmp/col-atlas-research
python3 scripts/benchmark_atlas_priority.py --out /tmp/col-atlas-benchmark
```

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

`proof_status.py` tracks the earlier finite-state proof route and still reports
that route's open obligations. It does not evaluate the later gadget-and-
induction proof linked above, so its status is not the current theorem status.

## GUI

```bash
./col-gui
```

Opens the Electron app. Choose a `.pkl` from `data/tablebases/` or any folder. Requires Python 3 and `npm install` in `gui/` (done automatically on first launch).

## Dependencies

- **Solver:** Rust toolchain (`cargo`)
- **GUI:** Node.js, Python 3
- **Predict plots:** `pip install matplotlib` (optional)
