# Atlas import and two-direction checks

Implemented and benchmarked on September 5, 2026. **The new proof machinery works, but the full atlas does not make these 3×23 searches faster. The center opening remains Unknown.** Atlas expansion and the additional adaptive checks remain opt-in; production DFS, default tile libraries, and tablebases retain their existing behavior.

## Changes

- `python/col/atlas.py` checks source hashes, every grid response DAG, the completeness and irredundancy of each classification frontier, checkpoint references, boundary masks, and all exported zero upgrades. Source first/responder roles remain explicit even when a source starts with the original physical White player. Transposition transforms masks and reorders replies; reflection remains in the ordinary index.
- `python/col/certificate_types.py` separates actual outcome proofs, local construction rejections, and incomplete Unknowns. A local unsafe result has no API that converts it into an enclosing-board outcome.
- `AdaptiveSearch` can check actual White-turn positions by passing `(White, Blue)` into the same tiling evaluator. The protected seam player changes with that orientation. Verified counterproofs have their own DAG store; bounded failures remain separate. Blue can refute a proposed defense with one proved branch. Proving a White loss by exhausting White responses requires every legal move; omitted symmetry representatives never count as covered responses.
- Both winners' proofs export through the existing adaptive artifact format and execute with `AdaptivePlayer`. The Python checker checks the entire prefix. Rust independently checks source DAGs and ordinary tiling leaves; it does not check the adaptive prefix or the classification lattice.
- Complete classifications scan only minimal safe supports. An explicit unsafe-witness request searches the maximal unsafe frontier lazily and returns its local opening and opposite-role response certificate. Damaged first-player masks can use safe inclusions, but cannot use the unsafe direction of the full-first classification.
- All **772** exported subset-zero checkpoints are imported as typed exact-zero entries. Promotion also checks the **actual** masks after a valid cover. If actual responder permissions are contained in actual first permissions, the same cover embeds in both actor orientations. Each exported outcome still carries an ordinary executable witness checked in its actual orientation. Holes stay absent.
- `resolve_contract` and `discover_contracts` consult classifications before bounded local minimax when an atlas is supplied. Rejected local obligations stay local. Admitting a tile rebuilds the matching index and clears its cached matches.

Fixtures are preserved under `proofs/atlas` and `proofs/atlas-review`. The new importer admits grid upper-zero sources only. The atlas's 26 numeric certificates are not imported into this path; existing signed-bound research remains separate. Exact-zero metadata is not written to the production CGT cache or ordinary tablebases.

## Matched 3×23 measurements

The immutable case selection is in [cases.json](cases.json), with a hash of the historical input report. It contains the center opening at two depths and 16 distinct recorded White-turn positions from the three earlier rounds and final search. Every path was replayed to confirm its masks and actor. Each arm ran every case three times, with the same depth, time and 150,000-visit limits. Each case starts with a fresh adaptive memo and an empty 100,000-entry local-match LRU. Workers run sequentially in separate processes.

The baseline uses the existing 44-source library. The atlas arms combine it with 94 applicable/transposed atlas source DAGs. All their checkpoints are available to the index.

| Measurement | Existing library, original checks | + atlas, original checks | + atlas, both directions and zero promotion |
|---|---:|---:|---:|
| Reflected checkpoint variants | 69,484 | 218,310 | 218,310 |
| Preparation: verification and indexing | 1.65 s | 20.09 s | 19.91 s |
| Center, completed depth 3: median search time | **2.697 s** | 4.931 s | 5.380 s |
| Center, completed depth 3: visits | 3,004 | 3,004 | 3,004 |
| Center, completed depth 3: successful cover queries | 90 | 90 | 91 |
| Center, completed depth 3: genuine refutation cutoffs | 0 | 0 | 1 |
| Center, depth 4 under 10 s: median visits | **16,103** | 5,353 | 4,955 |
| Center, depth 4 under 10 s: genuine refutation cutoffs | 0 | 0 | 24 |
| Peak worker memory | 156 MiB | 420 MiB | 461 MiB |

The completed depth-3 search is about **2× slower** with the atlas and both directions, with no reduction in visits. Under the deeper time limit, the dual arm finds 18 distinct White-loss tile leaves and records 24 refutation cutoffs including reuse. It still completes only depths 1–3. Its lower visit count measures lower throughput under a fixed budget, **not** a smaller completed proof search.

All three arms certify the same two recorded White-turn positions; the remaining 16 cases, including both center runs, stay Unknown. None of the selected previously unresolved roots gains an outcome from the atlas. Two snapshots from earlier rounds were already resolved by the baseline's later 44-source library.

The table separates preprocessing from search time. Peak memory includes source checking, indexing, search, and Python artifact checking in the worker; it excludes Rust child processes. It is not an isolated measurement of index memory. One-source preparation timings were measured once per worker; search timings are medians of three repetitions.

Raw results and all per-case metrics: [summary.json](summary.json). Example executable proof of an internal actual counterstrategy: [center-depth3-counterstrategy.json](atlas-dual/center-depth3-counterstrategy.json). This is a branch proof, not a solution of the empty board.

## Local classifications

All **1,903** distinct recorded local obligations have damaged first-player masks. None contains a certified minimal safe support under the required inclusions. The correct result for every classification query is therefore **Unknown**, and **zero local minimax calls are avoidable** on this corpus. No unsafe frontier is scanned.

A matched replay of the first 64 local obligations, with 25,000-state and 0.05-second limits per obligation, finishes in about 0.009 seconds in every arm: 63 local first-player wins and one safe tile. These are local construction results, not whole-board outcomes. Local minimax was already cheap for this sample; atlas matching is the larger measured cost.

Complete classifications do avoid minimax on eligible full-first inputs, as the exhaustive small-shape tests verify. That capability should not be presented as a measured speedup on the recorded center-focused obligations.

## Verification

- Imported and checked **467 grid DAGs, 436,703 states, 1,861,429 response edges**, **152,473** indexed checkpoints, and **772** exact-zero upgrades. Verified all **3,598,668** masks across 21 complete classifications and all source hashes.
- Rust independently checked every imported grid DAG. Both checkers checked all **695** accepted tiling leaves across the first benchmark repetition's three arms. The later repetitions are timing repetitions; their proof checks are not included in that count.
- Checked and replayed exported root and internal counterstrategies in both color orientations: 280 benchmark replay games. Independently tested small-board outcomes against exact minimax, including both actors, reflections, induced holes, lazy unsafe witnesses, malformed DAGs, and invalid swapped-actor seams.
- Known-board controls retain executable strategies: empty **3×13**, the difficult **3×19 opening 26**, and empty **3×101**. Both checkers validate their leaves; 120 additional replay games cover both color orientations. These controls reuse existing solved results and are not new width theorems. See [validation/summary.json](validation/summary.json).
- Rechecked all four proposed bare L remainders: **512 states and 1,469 response edges**. The coordinate verifier checks the bulk interface and induced-path geometry; Rust checks both resulting path-root DAGs. These counterproofs exclude only the specified unopened checkerboard bulk plus independently safe unopened L. They do not settle physical 5×9 or 7×7, or opened/adaptive variants.
- Full Python suite: **49 tests pass**. Rust source code was unchanged by this patch; its production verifier was exercised on all sources and the accepted leaves above.

The next performance experiment should reduce the cost of the larger checkpoint index or select atlas sources that discharge observed obligations. This benchmark does not justify enabling every atlas checkpoint deeper in the default search. The four bare L constructions have been removed from the immediate research queue; opening-dependent constructions remain open.

## Reproduction

```bash
# Build the independent checker used by the benchmark and validation scripts.
cargo build --release --manifest-path solver/Cargo.toml --bin col-cert

# Matched ablations; writes new reports to the selected directory.
python3 scripts/benchmark_atlas_priority.py --out /tmp/col-atlas-benchmark --repeats 3

# Independently checked atlas and known-strip/L controls.
python3 scripts/verify_atlas_integration.py

# Opt into both-direction atlas search and classification-assisted discovery.
python3 scripts/adaptive_tiling_research.py \
  --library reports/adaptive-tiling/final/library \
  --atlas proofs/atlas --atlas-review proofs/atlas-review \
  --out /tmp/col-atlas-research

# Verify an exported adaptive strategy.
python3 scripts/adaptive_tiling_research.py \
  --verify reports/atlas-priority/atlas-dual/center-depth3-counterstrategy.json

PYTHONPATH=python python3 -m unittest discover -s tests
```

The adaptive command's `--atlas` option enables both-direction checks and actual subset-zero promotion together. `--two-direction` enables those checks with an existing library alone. Calls without either option retain the earlier search defaults. `Unknown` retains its depth/time/state-budget reason and is never entered as an exact game outcome.
