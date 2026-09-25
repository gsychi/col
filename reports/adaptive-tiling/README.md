# Adaptive certificate search experiment

Outcome: faster certificate lookup and 18 new independently checked local strategies. Empty 3x23 remains unresolved: 68/69 opening cases are covered, with the center cell 34 still missing. Production defaults and tablebases are unchanged.

The experiment searches for a short White strategy whose every Blue continuation eventually reaches an ordinary safe tiling. The tiling may differ between branches. Iterative AND/OR search checks all immediate certified White responses before exploring descendants, reuses solved states, and prioritizes Blue moves that defeated earlier candidates. This is a bounded baseline; a proof-number scheduler and a parametric extension theorem were not implemented.

## What changed

- All checked grid-only DAG checkpoints are available as tile roots. Per-cell bitset indexes answer the two legality-inclusion tests; boundary groups choose compatible continuations. Local-mask caches avoid repeating matching work.
- A standalone adaptive proof format stores the short prefix and ordinary tile leaves. Its independent set-based checker requires every legal opponent move, legal winner choices, closed successors, and strict progress. A replay player follows the prefix and then the existing tile strategy.
- A failed tiling returns candidate intervals with certified prefixes and suffixes. Local exact searches use the required endpoint restrictions. The focused experiment considers intervals containing the unresolved center column. Failed bounded searches remain Unknown.
- The refinement loop verifies each admitted DAG and its concrete board context, then retries the adaptive search. Resolved local contracts are not searched again.

## Fixed-query comparison

The compared palettes contain the identical 63,080 reflected original-checkpoint states. The 25 queries comprise empty 3x13, the successful 3x19 response at cell 8 after opening 26, and all 23 symmetry-distinct White responses to the 3x23 center. Both implementations find exactly the same two covers.

| Measurement | Linear scan | Indexed lookup |
|---|---:|---:|
| Index construction | 0.524s | 0.847s |
| First query pass, 25 checks | 1.8911s | 0.0032s |
| Median of three passes, 25 checks | 2.1955s | 0.0019s |

The measured median lookup speedup is 1181x. This is a small fixed-query Python benchmark with caches retained across passes. It excludes source verification and preprocessing, and does not measure a full-game solving speedup. The first-pass speedup is 591x.

## Proof discovery

| Refinement round | Completed White-turn depths | Search time | Local candidates searched | New tiles |
|---|---|---:|---:|---:|
| 1 | [1, 2, 3] | 2.419s | 1380 | 15 |
| 2 | [1, 2, 3] | 3.849s | 401 | 3 |
| 3 | [1, 2, 3] | 7.613s | 122 | 0 |

The 18 admitted tiles contain 4,169 checkpoints and 13,917 response edges. They expand the separate library from 26 to 44 roots (69,484 reflected checkpoint variants). All tile dimensions are at most 3x7 (21 cells).

After refinement, the search completed depths 1, 2, and 3 White turns. The fourth-turn attempt stopped after 30.000s and 41,413 visited search states, returning Unknown. A three-White-turn proof would have at most five prefix plies after the initial Blue opening. Every opponent continuation must be handled.

Local-discovery limits: up to three rounds; 20 seconds and 4,000 candidates per round; 500,000 search calls and one second per local game. Each short strategy search has 150,000 visited-state and time limits. The method searches a restricted certificate language; failure is not a game-theoretic result.

## Verification and controls

- All 43 Python regression tests passed, including indexed-versus-linear matching/frontier checks, independent exact small-game outcomes, both color orientations, budget exhaustion, illegal replies, and omitted opponent branches.
- The independent Python checker validates the complete adaptive prefix. The existing Rust checker independently validates local DAGs and tile-leaf assemblies. Rust does not yet check the new prefix format.
- Every one of the 18 mined contracts was reconstructed on the actual 3x23 board, checked as a valid tiled leaf, and replayed in both color orientations: 180 completed games in total.
- The Rust whole-board checks validate all 44 local DAGs. Empty 3x13 and 3x19 remain certified; 3x23 remains unknown.

| Whole board | Result | Opening assemblies | Uncovered cells |
|---|---|---:|---|
| 3x13 | loss | Direct tiling | [] |
| 3x19 | loss | 57 | [] |
| 3x23 | unknown | 68 | [34] |

`loss` in these artifacts means the side to move loses. No new whole-board or all-width result is claimed.

## Reproduce

```sh
cargo build --release --offline --manifest-path solver/Cargo.toml --bin col-cert
python3 scripts/refine_adaptive_tiling.py
python3 scripts/benchmark_adaptive_index.py
python3 -m unittest discover -s tests
python3 scripts/adaptive_tiling_research.py --verify reports/adaptive-tiling/final/contract-0.json
./col-cert --m 3 --n 23 --proof-library reports/adaptive-tiling/final/library --proof-out /tmp/3x23-adaptive-library.json
```

The configurable single-round driver is `scripts/adaptive_tiling_research.py`. The fixed refinement experiment is `scripts/refine_adaptive_tiling.py`. Earlier pilot outputs are retained separately from `final/`.

Raw results: [refinement and certificate provenance](final/summary.json), [lookup benchmark](index-benchmark.json), [whole-board checks](final/whole-board-checks.json).
