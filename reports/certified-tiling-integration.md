# Certified tiling integration

The supplied 3×15 result now has a production certificate path. The original
package is preserved under `proofs/3x15`; its historical claims and files are
unchanged. This report supersedes the *current status* of 3×15 in older search
reports, without changing those historical experiment records.

## What is trusted

The Rust loader checks compressed-file SHA-256 digests, dimensions, root masks,
counts, every Blue move and White response, successor closure, reachability,
and strict decrease. Local transitions use the production board's move update.
`col-cert verify proofs/3x15` additionally checks the original opening table,
all 45 opening orbits, the demon construction, and the four family roots.

The independent Python implementation uses coordinate sets. It checks generated
proof artifacts without consulting the Rust solver or any outcome tablebase.
Both implementations check all physical cross-block interactions relevant to
the responding player. Tiles are one-sided losses, **not exact CGT zeros**.

The supplied mathematical composition argument remains necessary: checking
finite DAGs alone does not justify arbitrary composition or an all-width claim.
The provided E4/F1 construction supplies the empty 3×(4k+1) family; finite sweeps
of other widths are reported individually.

## Solver behavior and interfaces

`--proof-mode root` is the default. The solver checks for a direct losing
partition, then searches legal responses for a certified losing child. For an
empty board it additionally checks every opening for such a response. This
happens before DFS and before parallel scheduling. Reflected tile variants are
included. Only unresolved opening jobs are scheduled; a separate exact map
retains certified states even if a fixed-size DFS table evicts an entry.

`--proof-mode search` also probes each DFS call before component reduction and
before recursive descent. It records the original permissions and witness for
each actual cutoff. This is opt-in: certificate checking at every state can be
expensive, and the recorded witnesses consume additional memory.

`--proof-mode off` restores the ordinary search path. Existing memo-derived
`--opening-certificate` and `--invariant-report` outputs automatically use that
path to preserve their schemas. They cannot be combined with `--proof-out` or
search-mode certificate cutoffs.

`--proof-library DIRECTORY` selects a manifest and compressed tile DAGs.
`--proof-out FILE` writes a self-contained `col-tiling-proof-v1` JSON artifact;
otherwise the solver saves one under `data/proofs/` with a position-derived
name that also includes the library identity and proof mode, and prints its path. Normal tablebase encoding is unchanged. Fully
certificate-resolved queries store their result in the proof artifact rather
than manufacturing a dense tablebase.

Artifacts contain absolute P1/P2 column permissions, the side to move, a
side-to-move outcome (`win`, `loss`, or `unknown`), complete local DAGs, source
identifiers/digests, tile transformations and placements, and opening replies
where needed. An artifact can instead contain partial opening evidence and
individual DFS-cutoff witnesses. Such an artifact retains outcome `unknown`
even when the surrounding DFS subsequently solves the board: it does not claim
to be a complete independently replayable root proof.

`col-cert` invokes certificate-only solving and never starts full-board DFS.
Exit 0 means a certified outcome, exit 2 means unknown. A verified partial
artifact can also be inspected with `verify`; that inspection does not upgrade
its outcome. Whole boards use column vectors, so 3×101 works without changing
the DFS engine's 63-cell limit. Unsupported heights or oversized unresolved
boards return unknown. Certificate heights 1 through 7 are supported; the
bundled library is height three.

## Commands

```sh
# Production solver: certify 3×15 before starting DFS.
./col-solve --m 3 --n 15 --proof-out /tmp/3x15.json

# Two independent checks of a self-contained artifact.
./col-cert verify /tmp/3x15.json
./col-cert verify-python /tmp/3x15.json

# Supply the opponent's actual moves; the strategy inserts the winner's replies.
./col-cert replay /tmp/3x15.json --moves 0 14

# Beyond the DFS mask limit.
./col-cert --m 3 --n 101 --proof-out /tmp/3x101.json

# The original three-stone position; reports response 12.
./col-cert --m 3 --n 15 --turn P2 \
  --position B.............B/.............../..............W \
  --proof-out /tmp/demon.json

# Bounded local research, with 30 seconds of discovery per board by default.
./col-cert discover --out /tmp/col-tiles \
  --boards 3x19 3x23 3x27 3x31 5x9 7x7

# Import a mined library; Rust independently checks every admitted tile.
./col-cert --m 5 --n 9 --proof-library /tmp/col-tiles/library \
  --proof-out /tmp/5x9.json
```

The shell wrappers invoke Cargo's incremental freshness check, so editing the
engine cannot silently leave an old release binary running. Dependencies must
be fetched once before the wrappers' offline builds.

## Discovery and limits

The miner computes compatible certified prefixes and suffixes around each
candidate opening response. It proposes a missing full-height tile between
them, with the actual local Blue permissions and White endpoint restrictions
that exclude both neighboring White boundaries. It tries wider permitted
bridges first. This is a search for *one missing bridge*, not a complete search
over all possible strategy classes.

For heights five and seven it also enumerates full-Blue seed tiles with
restricted White endpoint rows. This supplies candidates before useful
prefixes and suffixes exist. The local generator uses exact actor-relative
minimax; an independent set-based checker must validate its exported graph
before admission. Rust rechecks every tile when the resulting library is loaded.

Defaults: 21 cells per tile, 100,000 recursive calls per candidate, one second
per candidate, 200 candidates and 30 seconds of discovery per board. All limits
are explicit CLI options; increasing the tile limit is a research setting.
Coverage audits and certificate I/O are additional to the discovery budget.
Completed winning candidates are rejected; exhausted candidates remain unknown.
Libraries and reports are saved separately from the source fixture.

A small pilot and its verified library are in `tiling-discovery-pilot/`. These
bounded experiments do not establish 3×19, 5×9, 7×7, or general odd rectangles.

## Validation

- Original package: 25 tiles, 22,423 checkpoints, 91,789 edges, all 45 openings.
- Exhaustive checks of 8,192 mask/actor combinations on 3×2 against exact search,
  including agreement of column and production legality updates.
- Random 3×3 shadow checks against independent plain recursion.
- 450 actual-board games spanning every 3×15 opening; long-board replay and
  color-swapped strategies; the demon response 12 and rejection of a tiling
  for response 30.
- Rejection of illegal replies, uncovered Blue moves, overlaps, White bridges,
  and false completion claims for incomplete opening coverage.
- Deliberately incomplete libraries exercise sequential DFS, both parallel
  schedulers, and opt-in deeper certificate cutoffs.
- Height-five and height-seven local generation/composition checks and explicit
  budget-exhaustion tests.

Run `cargo test --offline --manifest-path solver/Cargo.toml --lib`, build both
release binaries, then `python3 -m unittest discover -s tests -v`. The preserved
fixture also has its own `verify.py` and `test_proof.py`.

## Completed-run benchmark

Three interleaved cold runs per mode on this development host, one thread,
fixed 2^24-slot memo, legacy move order, CGT cutoff 10. Both modes use the
same release binary; only `--proof-mode off` versus `root` differs. All
12 completed runs agree on P2. Timing is machine-specific.

| Board | DFS states | Certificate states | DFS wall median | Certificate wall median | DFS peak RSS | Certificate peak RSS |
|---|---:|---:|---:|---:|---:|---:|
| 3x11 | 1,047,484 | 0 | 0.764s | 0.099s | 300.1 MiB | 10.0 MiB |
| 3x13 | 7,260,687 | 0 | 6.170s | 0.090s | 459.7 MiB | 10.0 MiB |

Wall measurements include process startup, verification, and proof output.
Because the sandbox blocks the sysctl used by macOS `time -l`, peak RSS is
collected by a fresh Python helper with exactly one solver child. Its startup
also appears in wall time. Timeout handling terminates the whole measurement
process group. The solver-reported time and every tiling counter are retained
separately in [tiling-benchmark.json](tiling-benchmark.json).

This comparison demonstrates completed-search savings on these boards. It
does not estimate an unmodified full-search runtime for 3×15 or any larger
unresolved board. No deeper-DFS tiling speedup is claimed.

Reproduce with:

```sh
python3 scripts/benchmark_compare.py solver/target/release/col-rs solver/target/release/col-rs \
  --baseline-arg=--proof-mode --baseline-arg=off \
  --candidate-arg=--proof-mode --candidate-arg=root \
  --boards 3x11 3x13 --repeats 3 --threads 1 --memo fixed --memo-bits 24 \
  --move-order legacy --out-json reports/tiling-benchmark.json
```
