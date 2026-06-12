# Col — 2D placement game solver

Three entry points at the repo root:

| Command | Purpose |
|---|---|
| `./col-solve` | Rust solver (builds on first run) |
| `./col-predict` | Estimate state counts and solve times |
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
| `/` | Tablebase explorer |
| `/dashboard` | Live solver progress + finished tablebases |

For a **manual** setup (no Blueprint): create one **Web Service** with Dockerfile `deploy/Dockerfile`, command **`./deploy/start-all.sh`**, disk at **`/data`**, and the env vars below. Do **not** split into a separate Background Worker unless you add external storage (S3, etc.).

| Env var | Default | Purpose |
|---|---|---|
| `TABLEBASE_DIR` | `/data/tablebases` | Shared tablebase storage |
| `STATUS_FILE` | `/data/solver_status.json` | Live progress for dashboard |
| `SOLVER_THREADS` | `auto` (all CPUs) | Worker: `--threads` for col-solve; set a number to cap |
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

## GUI

```bash
./col-gui
```

Opens the Electron app. Choose a `.pkl` from `data/tablebases/` or any folder. Requires Python 3 and `npm install` in `gui/` (done automatically on first launch).

## Dependencies

- **Solver:** Rust toolchain (`cargo`)
- **GUI:** Node.js, Python 3
- **Predict plots:** `pip install matplotlib` (optional)
