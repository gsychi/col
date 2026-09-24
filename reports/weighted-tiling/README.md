# Weighted tile experiment

This compares three palettes using the same experimental Python DP and move order. Production Rust search and its defaults are unchanged.

`original` uses the 25 original safe roots. `nonpositive` adds signed certificates but excludes positive bounds. `weighted` permits positive tiles compensated elsewhere. All arithmetic is exact dyadic arithmetic.

| Board | Opening probes | Original | Nonpositive | Weighted |
|---|---:|---:|---:|---:|
| 3x3 | 4 | 4 | 4 | 4 |
| 3x5 | 6 | 3 | 6 | 6 |
| 3x7 | 8 | 8 | 8 | 8 |
| 3x9 | 10 | 6 | 10 | 10 |
| 3x11 | 12 | 12 | 12 | 12 |
| 3x13 | 14 | 7 | 13 | 13 |
| 3x15 | 16 | 16 | 16 | 16 |
| 5x5 | 9 | 0 | 0 | 0 |
| 5x7 | 12 | 0 | 0 | 0 |
| 3x19 | 20 | 19 | 19 | 19 |

Opening probes ask for a fresh proof after a representative first move. They do not restrict or invalidate an already verified empty-board strategy. The root-only palettes leave 3x19 unresolved; the other boards have known second-player results. Checkpoint reuse is tested separately below.

New accepted positions versus the original palette: **13**. Positions requiring positive-tile compensation versus the nonpositive control: **0**.

| Mode | Variants | Bound queries | Median query wall time |
|---|---:|---:|---:|
| original | 71 | 3387 | 0.340s |
| nonpositive | 97 | 3302 | 0.373s |
| weighted | 113 | 3127 | 0.370s |

Timings cover the same 330 positions, repeated 3 times, excluding source and assembly verification. They compare Python palettes, not Python against production Rust. Process peak memory was 105.6 MiB including source checking, all modes, evidence, and checkpoint expansion; it is not a per-mode measurement.

Independent exact minimax checked both actors on 210 late-position probes (at most 10 live cells). Every accepted result agrees. Accepted late probes: original 25/210, nonpositive 25/210, weighted 25/210.

The remaining 3x19 opening (row 1, column 7, zero-based) returns **win** for White after enabling 5012 reflected checked-checkpoint variants. That separate probe took 0.084s.

The evidence recheck validates 44 source DAGs and 336 assembled results. Local checking took 2.346s; first-pass assembly checking took 0.014s.

**Limits:** No production DFS cutoffs were measured or enabled. This exports checkable numerical bounds, not an executable weighted game player. The old same-tile reply rule is insufficient for compensated sums. For the independently checked, executable 3x19 follow-up, see [checkpoint results](checkpoint-results.md). No all-odd-width theorem is claimed.

Reproduce:

```sh
python3 scripts/benchmark_weighted_tiling.py --repeats 3
python3 scripts/benchmark_weighted_tiling.py --verify reports/weighted-tiling/evidence.json.gz
```
