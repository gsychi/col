# Faster Search and Proof Program Results

## Outcome

The exact solver still reports P2 on every odd-by-odd board through 39 cells.
The search is measurably faster, but the all-odd theorem is **not proved**.
The generated proof gate records the remaining obligations instead of treating
finite computation as an induction.

## Search results

All results below are cold-cache, no-tablebase runs. They are single trials and
should be repeated before making small percentage claims.

### Shadow reflection certificate

The Rust solver now recognizes an exact legal-mask certificate: if a 180-degree
rotation swaps the two players' legal masks and the actor cannot play the fixed
center, every move has a reflected response that restores the relation.

| Board | Disabled | Enabled | Speedup | State change |
|---|---:|---:|---:|---:|
| 3x11 | 1.658s | 1.557s | 1.06x | -0.64% |
| 5x7 | 2.121s | 2.106s | 1.01x | -1.47% |
| 3x13 | 67.285s | 58.755s | 1.15x | -0.99% |

On 3x13 the certificate fired 198,274 times. Full data:
[`odd-board-experiments/pairing-cold-39.json`](odd-board-experiments/pairing-cold-39.json).

### CGT cutoff

There is no single best cutoff even within the small corpus:

- 3x9: cutoff 8 was fastest (0.0136s).
- 3x11: cutoff 10 was fastest (1.328s), with 12 nearly tied (1.352s).
- 5x7: cutoff 10 was fastest (1.865s).
- Cutoff 14 searched fewer states but lost throughput and memory efficiency.

Compared with CGT disabled, cutoff 10 was 4.43x faster on 3x11 and 3.49x on
5x7. Full data:
[`odd-board-experiments/cgt-cold-39.json`](odd-board-experiments/cgt-cold-39.json).

### Parallel scaling

On this 12-logical-CPU host, 16 workers was fastest in the tested 1/4/8/12/16
matrix, though it searched slightly more states:

- 3x11: 7.887s at one thread, 2.956s at 16 (2.67x).
- 5x7: 27.314s at one thread, 5.794s at 16 (4.71x).

This does not demonstrate unlimited scaling; it only says shared-memo
contention had not erased gains by 16 workers on these two boards. Full data:
[`odd-board-experiments/threads-cold-39.json`](odd-board-experiments/threads-cold-39.json).

### Move ordering

Legacy ordering was decisively worse on 5x7 (10.61s versus 2.25–2.47s).
Auto and fixed heuristic were close enough that repeated trials are needed;
auto won these single trials. Full data:
[`odd-board-experiments/move-order-cold-39.json`](odd-board-experiments/move-order-cold-39.json).

## Proof-oriented results

### Opening reduction through width 13

The solver emitted replayable first-move certificates for every opening on
3x3, 3x5, 3x7, 3x9, 3x11, and 3x13. Each record gives a legal P2 reply and the
exact losing target shadow key:
[`opening-certificates/`](opening-certificates/).

This proves each listed finite board once the solver's memo outcomes are
trusted; it is not an all-width opening lemma.

### Frontier closure experiment

Fresh Python searches on 3x5, 3x7, and 3x9 emitted 44,266 losing-state
certificates covering 230,632 P1 moves. Independent replay found zero malformed
or illegal transitions.

The observed radius-2 frontier family closed on all recorded transitions, but
withholding width 9 exposed 77 frontier signatures absent from widths 5 and 7.
Thus the current projection overfits smaller widths and does not supply the
required `n -> n+2` recurrence. See
[`3xn-frontier-closure.md`](3xn-frontier-closure.md).

### Local CGT certificates

Twenty-four finite recurrence nodes certify the six requested local shapes:
four zero families, the bent `-2` triomino, and the `+1` obstacle. Every option
sum and `{L|R}` recurrence replays without error. See
[`cgt-component-certificates.md`](cgt-component-certificates.md).

The previously mentioned `-3/4` obstacle was not included because no concrete
shape for it exists in the repository artifacts; assigning that value without
the shape would not be a certificate.

### General odd-board invariant

The naive “symmetric wings plus isolated zero middle column” claim has 280
counterexamples across every non-path odd board through 39 cells (100 examples
are retained in the combined JSON report). The stronger statement for
genuinely disconnected components whose exact values cancel had no
counterexample in 19,274 applicable states. That stronger result is component
decomposition, not a theorem about attached wings. See
[`odd-invariant-search.md`](odd-invariant-search.md).

## Remaining proof blocker

The current finite data does not quantify over an arbitrary neutral middle
length. A proof still needs either:

1. a bounded frontier representation that predicts new widths with no novel
   signatures and a symbolic two-column extension, or
2. a local cancellation theorem that remains valid when the middle column is
   attached to symmetric wings.

[`formal-proof-handoff.md`](formal-proof-handoff.md) is the executable proof
gate. It remains `NOT PROVED` until those obligations are discharged.
