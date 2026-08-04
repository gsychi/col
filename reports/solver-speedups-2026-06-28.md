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
