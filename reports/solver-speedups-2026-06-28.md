# Solver Speedup Benchmarks - 2026-06-28

Representative runs used:

- `--threads 12`
- `--memo hash`
- `--no-tablebase`
- `--no-endgame-cache`
- medians of 3 runs

The saved baseline binary was built before these speedup changes from the current
working tree.

## CGT Component Shape Cache + Adaptive High Cutoff

The candidate caches each local component graph by its live-cell mask and caps
generic CGT size 14 evaluation to size 12 until the whole position has at most
14 open cells. This keeps the expensive size-14 exact evaluations for true late
positions without paying that cost throughout the middle game.

| board | cutoff | baseline | candidate | result |
| --- | ---: | ---: | ---: | ---: |
| 3x9 | 12 | 0.044675s | 0.035173s | 1.27x |
| 3x9 | 14 | 0.089659s | 0.043634s | 2.05x |
| 3x11 | 12 | 1.416565s | 1.380964s | 1.03x |
| 3x11 | 14 | 2.258442s | 1.741378s | 1.30x |
| 5x7 | 12 | 2.161503s | 1.967015s | 1.10x |
| 5x7 | 14 | 3.129247s | 2.698675s | 1.16x |

The adaptive cap is consistently faster for size 14, where CGT miss pressure was
worst. Cutoff 10 remains the best default overall.

## Default Move Ordering

Current default `auto` ordering was compared with fixed `heuristic` ordering at
cutoff 10:

| board | auto median | heuristic median | result |
| --- | ---: | ---: | ---: |
| 3x11 | 1.661267s | 1.607398s | 1.03x |
| 5x7 | 1.983095s | 1.752225s | 1.13x |

After changing the default to fixed heuristic except for larger `3xn` strips,
plain default runs measured:

| board | new default median |
| --- | ---: |
| 3x9 | 0.021250s |
| 3x11 | 1.422380s |
| 5x7 | 1.829867s |

Root-split and legacy ordering were slower on these boards, so they were not made
defaults.

## Kept Defaults

- `--endgame-size` default remains `10`.
- Default move ordering is now fixed `heuristic` for common boards.
- Adaptive `auto` ordering remains the default only for `3xn` strips with
  `n >= 13`, where the previous large-strip fallback may still be useful.
- Size 14 CGT now has a built-in adaptive cap so explicit high cutoffs are less
  likely to lose time to generic component evaluation.

## Exact Hot-Path Round - 2026-08-03

Paired cold runs used `--no-tablebase`, `--no-endgame-cache`, cutoff 10, and
heuristic ordering. Every deterministic comparison preserved the winner, state
count, memo hits, and reduction effects unless explicitly noted.

| experiment | workload | baseline | candidate | result |
| --- | --- | ---: | ---: | ---: |
| Pairing-cardinality reject | 3x11, sequential hash | 1.835979s | 1.721541s | 1.066x |
| One-instruction half-turn | 3x11, sequential hash | 1.552010s | 1.504217s | 1.032x |
| Bitwise 3xn symmetries | 3x11, sequential hash | 1.515674s | 1.427198s | 1.062x |
| 64 KiB/worker front cache | 3x11, fixed20/8 | 0.931046s | 0.913698s | 1.019x |
| 64 KiB/worker front cache | 5x7, fixed20/8 | 2.114987s | 2.045740s | 1.034x |
| 64 KiB/worker front cache | 3x11, fixed18/8 | 1.338108s | 1.286498s | 1.040x |
| Evaluator-before-reducer | 3x11, sequential hash | 1.782559s | 1.724186s | 1.034x |
| Evaluator-before-reducer | 5x7, sequential hash | 8.085046s | 7.214359s | 1.121x |

The requested cumulative 3x13 run proved P2 wins in both binaries with exactly
46,509,244 states. The frozen start-of-round binary took 44.536807s; the
hot-path candidate took 34.975342s (1.273x throughput, 21.5% less elapsed
time). The evaluator-before-reducer change added afterward was neutral on 3x13.

The worker-local front cache retains exact values evicted from the bounded
shared table. It reduced states by 2.9% at fixed18 and now reports queries and
hits through the benchmark JSON parser. The evaluator-first path was neutral on
3x13, but useful on 3x11 and 5x7, so it remains enabled.

Rejected experiments were fully reverted: carrying a cell index in the move
iterator (-0.8%), color-orienting tuples before packing the shadow key (-10%),
and a two-phase 64-slot component-classification buffer (-8%).

Verification after the kept changes: 35 Rust unit tests plus doc tests and 19
Python tests passed.

## Exact Mathematical Cutoffs - 2026-08-04

These paired cold runs used one thread, hash memoization, heuristic ordering,
endgame cutoff 10, component reduction, no tablebase, and no endgame cache.
Every run preserved the P2 winner. The cumulative comparison is against the
binary frozen immediately before this round.

- Frozen baseline SHA-256: `5ec381232976fb27f0f310be70707e49df5746ac4cf59dbd54df55743a3136cc`
- Benchmarked candidate SHA-256: `ca35d62a6a4d68c31c034ca6e085ff559308a751c150b6e24d773b2bc52d18c7`
- Final candidate SHA-256 after reusing the already-computed interaction
  neighbor mask: `635ce5204a043cf9d976207009a97c98cb21bfcdc6cf124cff078e09c763567d`

| board | repeats | baseline states | final states | reduction | baseline median | final median | speedup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 3x11 | 5 | 2,718,745 | 1,004,117 | 63.1% | 1.843592s | 0.646165s | 2.85x |
| 5x7 | 5 | 7,754,080 | 2,380,489 | 69.3% | 7.705812s | 1.892757s | 4.07x |
| 3x13 | 3 | 46,509,244 | 19,346,555 | 58.4% | 48.757315s | 15.924657s | 3.06x |

### Kept exact changes

1. **Interaction components.** Components now join adjacent cells only when
   the cells share at least one player's legality mask. This is the actual
   dependency graph: a move cannot change either legality mask in another
   interaction component. The same rule is used by the global evaluator, the
   3xn bit-parallel flood, local recursive CGT evaluation, linear-chain
   detection, and the zero-summand reducer. In isolation this produced 2.42x
   on 3x11, 2.91x on 5x7, and 2.06x on 3x13.

2. **Actor-relative child dominance.** A private move is skipped when another
   move leaves a superset of the actor's legal cells and no extra opponent
   cells. Any possible dominator must lie in the candidate's closed geometric
   neighborhood, so detection examines at most four other cells rather than
   all legal moves. The optimized rule removed 18.9% / 20.7% / 23.7% of the
   remaining states and added 1.12x / 1.17x / 1.15x on 3x11 / 5x7 / 3x13.

3. **Staged private-reserve cutoffs.** Checkerboard and isolated-private lower
   bounds are compared with safe independent-set upper bounds. The upper bound
   stages raw cell count, four fixed domino matchings, then a greedy bipartite
   matching only near a proof. A larger private reserve certifies a win; a
   sufficiently large opponent-private reserve certifies a loss. The plain
   reserve rule added 1.13x / 1.11x / 1.03x, and banking isolated private cells
   added another 1.11x / 1.09x / 1.09x on the three workloads.

The solver now reports dominance nodes/moves and reserve fixed-bound checks,
greedy checks, win hits, and loss hits. The Python benchmark parser retains all
of these counters in JSON output.

### Rejected experiments

- The exact no-shared-cells MIS/matching evaluator was fully reverted. Eager
  evaluation was 1.3% slower on 3x11, 3.8% slower on 5x7, and about 17% slower
  on 3x13; evaluator-staged matching still lost about 3.3% on 3x11.
- A direct edgeless-interaction formula was fully reverted. It hit only 311
  times on 3x11 after interaction decomposition and produced no measurable
  state or time reduction.
- A fixed-domino-only reserve upper bound was 3.2% slower than the greedy
  bound. It remains only as a cheap first stage before greedy matching.
- The original quadratic dominance detector removed many states but was
  timing-neutral on 3x11. Restricting possible dominators to geometric
  neighbors preserved the exact same pruned moves and made the rule profitable.

Verification after this round: 28 library tests, 15 proof-miner tests, doc
tests, and 19 Python tests passed. This includes exhaustive interaction-component
equivalence on all 3x3 legality-mask pairs, exact-value decomposition on all
2x3 legality-mask pairs, and exhaustive reserve-bound soundness on 3x3 masks.

## Evaluator Architecture Experiments - 2026-08-04

These experiments started from the final exact-cutoff binary above (SHA-256
`635ce5204a043cf9d976207009a97c98cb21bfcdc6cf124cff078e09c763567d`).
They used the same one-thread, hash-memo, heuristic-order, cutoff-10, cold-cache
configuration. Candidate and baseline always agreed on the P2 winner.

### Kept: staged reserve-cardinality gate

Before running the full private-reserve evaluator, the solver now applies a
cheap necessary condition when at least eight moves are shared. If `C` and `O`
are the actor and opponent legality masks, respectively, a reserve proof is
possible only if at least one of

```text
|C \ O| > ceil(|O| / 2)
|O \ C| >= ceil(|C| / 2)
```

holds. The first follows because the actor's private independent set cannot be
larger than its private-cell count while the opponent has a checkerboard lower
bound of `ceil(|O|/2)`; the second is symmetric. If neither condition holds,
the existing reserve evaluator must return `(None, 0, 0)`, so skipping it is
exact. The shared-count threshold affects cost only, not correctness. Threshold
7 was 1.25% slower than threshold 8, and applying the condition unconditionally
was 1.6% slower.

The initial paired batch measured:

| board | repeats | baseline | candidate | ratio | reserve calls skipped |
| --- | ---: | ---: | ---: | ---: | ---: |
| 3x11 | 11 | 0.678932s | 0.664414s | 1.022x | 73,217 |
| 5x7 | 7 | 1.710396s | 1.691244s | 1.011x | 113,551 |
| 3x13 | 3 | 15.195052s | 14.860407s | 1.023x | 903,429 |

A second final-binary batch put the short-board effect closer to measurement
noise: 1.004x on 3x11 and 0.999x on 5x7 over 11 repeats. Across all paired
batches, the median within-pair ratios were 1.004x on 3x11, 1.003x on 5x7,
and 1.047x on 3x13. The conservative conclusion is a small 3xn win and neutral
5x7 performance. Every deterministic metric remained identical: states, memo
hits, dominance, reserve proof hits/checks, endgame evaluation, reductions, and
pairing certificates. The solver and Python benchmark JSON now also report the
new skip count.

The cardinality implication is checked on every 3x3 mask pair without the
performance threshold, including explicit tests for the strict win boundary
and non-strict loss boundary.

### Rejected and fully reverted

- **Fixed-height exact MIS DP.** Direct column DP and a compiled transfer
  automaton were both tried. The no-shared evaluator fired 4,728 / 17,580 /
  85,551 times on 3x11 / 5x7 / 3x13, but was timing-neutral because interaction
  decomposition already solves the same states. Using exact DP inside the
  reserve rule reduced 3x11 states by about 0.6% but made it 3-5% slower.
- **Raw-state L0 cache.** A 16K two-way cache hit 12.2% on 3x11 but was 4.5%
  slower; a 4K direct-mapped version was 0.5% slower on 3x11 and 1.7% slower on
  5x7.
- **Self-conjugate parity cancellation.** The theorem is exact and found 5 /
  31 / 57 component pairs, but the 3x13 candidate was 4.1% slower.
- **Incremental symmetry images.** Exhaustive sampled child-key checks passed,
  but carrying four rectangle images made 5x7 5.6% slower.
- **All-axis geometric pairing.** The additional reflection certificates found
  no new hits in a full optimized 3x11 search.
- **Simple shared-cell feature gate.** Skipping reserve analysis whenever the
  shared count exceeded 10 added 55 states and was 1.3% slower on 3x11.

Move-orbit profiling predicted only about 0.2% pruning, so it was not put on the
hot path. Historical-tablebase analysis makes a gated component-bag cache the
most promising next transposition experiment: cutoff-10 states collapsed by
roughly 38-43% by bag identity in the old 3x9 corpus, before accounting for the
cost of constructing component signatures.

Final release binary SHA-256: `8131c159c44ea077e8f4838817ad310b348c2138eae44d01c0a0643721f3acd0`.
Final verification passed 29 library tests, 15 proof-miner tests, doc tests,
19 Python tests, and `cargo clippy --all-targets` (with pre-existing warnings).

## Component-Native Transposition Cache - 2026-08-04

This round used the previous final binary as its frozen architecture baseline:

- Baseline SHA-256: `8131c159c44ea077e8f4838817ad310b348c2138eae44d01c0a0643721f3acd0`
- Final component-native SHA-256: `2fd7b7dcb23b10e1ad78ff9ab3bfd86117bdd5e45e06f41dd209dbe5a527c72b`

All reported comparisons were paired cold runs with hash memoization,
heuristic ordering, endgame cutoff 10, component reduction, no tablebase, and
no endgame cache. Every run preserved the P2 winner.

### Why component bags were the first architectural target

Profiling showed that fragmentation is the common case after the existing
cutoffs miss. Fragmented positions were 75.7% of post-reduction misses on
3x11, 81.8% on 5x7, and 95.0% on 3x13. Their median interaction-component
size was one cell, while exact canonical component reuse was 92.5%, 93.0%,
and 98.6%, respectively. On 3x13, 53.4% of observed fragmented positions
already duplicated a previously seen exact component bag in a non-pruning
profile.

The retained cache is an exact secondary transposition table keyed by the
position's disjoint game sum rather than its board embedding:

1. The existing reducer supplies surviving interaction-component masks, so
   the cache does not rescan the board.
2. Each non-singleton component receives a color-preserving geometric
   canonical ID. Full canonical signatures are stored and equality-checked;
   hash collisions cannot alias components.
3. IDs are interpreted relative to the actor to move, sorted as a multiset,
   and retain multiplicity. Components are never color-swapped independently.
4. Actor-private and opponent-private singleton components aggregate as an
   exact integer score, while shared singletons aggregate by star parity.
5. A bag hit backfills the ordinary board transposition table. A miss is
   inserted only after the recursive search has completed with an exact
   outcome; cancellation never publishes a partial result.

Most bags have at most four non-singleton IDs. The final representation keeps
those IDs inline and uses a fixed stack scratch array during sorting. This
removes a heap allocation from the common lookup and stored-key paths.

### Final results

| workload | repeats | baseline states | final states | reduction | baseline median | final median | speedup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 3x11, 1 thread | 7 | 1,004,117 | 859,377 | 14.4% | 0.598843s | 0.595931s | 1.005x |
| 3x13, 1 thread | 3 | 19,346,555 | 9,358,902 | 51.6% | 16.178261s | 9.958879s | 1.625x |
| 3x13, 8 threads | 5 | 20,543,008 | 11,789,099 | 42.6% | 4.232290s | 3.366470s | 1.257x |

The parallel state counts vary slightly with scheduling, but all paired runs
returned the same winner. The one-thread 3x13 bag table made 2,895,131 queries
and 1,150,966 hits, a 39.8% exact cache-hit rate. Although key construction
reduces raw states per second, halving the searched DAG produces the net 1.63x
speedup.

The trigger is deliberately adaptive:

- Below 33 cells the cache is disabled. Final 3x9 and 5x5 controls have exactly
  the baseline state counts and no bag queries.
- From 33 through 38 cells it runs only on 3-row or 3-column strips and
  requires at least four components. This retains the 3x11 state reduction.
- At 39 cells and above it runs on all shapes and requires at least three
  components. The lower threshold accounts for most of the 3x13 gain.
- The 5x7 control is disabled after a prototype removed 19.9% of states but
  was timing-neutral to slightly slower. Its final state count is again
  exactly the baseline 2,380,489.

Inline component IDs improved the first accepted bag implementation without
changing any deterministic counter. Against that frozen version, it was
1.064x faster on 3x11 over 11 paired runs and 1.243x faster on 3x13 over three
paired runs. At eight threads it remained 1.032x faster over seven runs.

### Rejected or superseded prototypes

- Recomputing and allocating full component signatures removed 16.9% of 3x11
  states but increased elapsed time by 14.1%. Reusing reducer masks,
  allocation-free signatures, raw-component ID caching, and singleton
  aggregation were all necessary before the cache paid for itself.
- A three-component threshold on 3x11 removed more states but was about 1.2%
  slower; four components is the better small-strip threshold.
- A bit-parallel replacement for the generic component flood was neutral on
  3x11 and made a one-run 3x13 rejection screen 10.1% slower. It fully flooded
  oversized components that the current generic path abandons early, so it
  was reverted.
- A full column-symbol strip backend was not built because the current 3xn
  engine already uses two bit masks, constant-time child updates, bitwise
  rectangle symmetries, dead-column interval tests, and bit-parallel floods.
  The remaining promising strip work is fused component classification and
  reduction, not replacing the global state encoding.

The cache maps are currently unbounded and worker-local. Parallel timing is
positive, but peak RSS could not be collected in the sandbox; cache capping or
shared immutable component IDs should be evaluated before substantially larger
boards.

Final verification passed 34 library tests, 20 proof-miner tests, doc tests,
and 19 Python tests. The Rust tests include exhaustive actor-relative bag
outcomes for every 2x4 legality-mask pair with at least three components,
exhaustive agreement between fixed and allocating component signatures on all
3x3 mask pairs, and explicit gate/invariance tests.
