# Star-stable bounds and a noncircular induction ledger

Status: **proved algebraic rules for arbitrary short games**, plus conditional
applications to the new boundary contracts. This organizes finite induction
obligations; it does not prove an auxiliary family by itself.

## Bundle the two required comparisons

For a dyadic q, define

```math
T_q(G)\quad\Longleftrightarrow\quad G\le q\ \text{and}\ G+*\le q.
```

This notation names two inequalities, not a new kind of game. It applies
without assuming that G is a number or a number plus star.

**Strictness.** `T_q(G)` implies both `G<q` and `G+*<q`. If either were equal
to q, the other inequality would assert `*≤0`, which is false. Thus the
original paired DX targets are exactly `T_0(DX)` and supply the strictness
needed by no-reply cuts. They do not supply any fixed negative numerical
margin independent of width.

**Star stability.** `T_q(G+*)` is equivalent to `T_q(G)`, because `*+*=0`.

**Addition.** If `T_q(G)` and `H≤r`, then `T_(q+r)(G+H)`. Add the second
inequality to each of the two defining comparisons. This remains true with
any number of weakly bounded summands and with an extra separator star.

**Numerical gap.** If `G_i≤q_i` and a finite cap has exact value `c+ε*`,
then `c+sum(q_i)<t` proves `T_t(sum(G_i)+c+ε*)`. The positive numerical gap
absorbs either star parity. No such conclusion follows solely from a
negative-but-unspecified infinitesimal margin.

At equality `c+sum(q_i)=t`, a star-free sum with at least one strict ordinary
bound is strictly below t. If the cap has a star, a strict ordinary bound
alone is insufficient in general. For example `down={*|0}<0`, but
`down+*` is not nonpositive. One T-bound suffices to handle either star parity
at equality.

These rules preserve the distinction between a failed upper-bound calculation
and a positive actual game. A symbolic sum that does not prove the requested
sign is an unresolved obligation, not a counterexample to its components.

## Apply the rules to the new endpoint clauses

The DX investigation proves center-row opening reductions at distance 1, 2
or 3 from the X endpoint of odd-width `(P,X)` strips. For P=X they are:

| Opening column | Applicable width | Upper comparison after Blue |
| --- | --- | --- |
| 1 | odd `n≥5` | `XX_(n−2)` |
| 2 | odd `n≥5` | `DX_(n−3)−1` |
| 3 | odd `n≥7` | `XX_(n−4)+*` |

The local cap identities and permission proofs are supplied by the
round-four DX package. Horizontal reflection supplies the opposite end.
All displayed child widths are positive and strictly smaller.

The natural paired target is `T_1(XX_odd)`. For either external star parity,
the first and third clauses preserve T1 by star stability. In the second,
`DX_even≤0` alone gives a numerical gap of two below the comparison target 1,
so it also works in either parity. White is next after Blue, and the rules
prove a strict upper bound below 1 in each case.

More generally, use `T_1(RX)`, `T_2(VX)` and `T_1(XX)`. The distance-1 and
distance-3 clauses return the same family at smaller odd width, with the
star unchanged or toggled. The distance-2 clause returns `DR−1`, `DV−1` or
`DX−1`, respectively. The original bounds `DR≤−1/4`, `DV≤1/2` and `DX≤0`
leave a positive numerical margin in every case, in both external star
parities. The endpoint cap theorem preserves an arbitrary far endpoint;
it does not rely on the two endpoints both being X.

This proves conditional clauses of the paired targets, not the whole targets. Other Blue
rows, the remaining columns and the White-first comparison below are still
separate obligations. The boundary targets RX and VX do not become star-stable
merely because unstarred finite tests were favorable.

For example the earlier no-reply DX column-2 bound `RX_(n−3)−1<0` follows
from `RX<1`. With an external star present, the analogous comparison needs
`T_1(RX)`, a proved fixed numerical gap below 1, or a different reply. The
unstarred strict target alone does not discharge this stronger obligation.

## The auxiliary-star opening cannot be hidden in a cycle

To prove `T_q(G_n)`, one must prove White wins playing second in both

```math
G_n-q\quad\text{and}\quad G_n-q+*.
```

In the starred game, Blue can take the star immediately. This leaves
`G_n-q` with **White next**, at the same board width. A nonpositive bound
on `G_n-q` alone is insufficient. One needs an independently established
White-first win, equivalently `G_n-q` not nonnegative.

A valid staged proof can first establish the unstarred strict comparison
from its Blue-first and White-first obligations, and then establish the
starred nonpositive comparison. Give these stages ranks 0 and 1 at fixed
width. Ordinary cap transitions decrease width; star consumption goes from
stage 1 to the already proved stage 0 at the same width. The lexicographic
rank `(width,stage)` then decreases. The stage-0 proof must not call the
same-width paired assertion that is only completed at stage 1.

For a nonzero q, legal moves in its auxiliary number must also be covered.
In the concrete `T_1(XX)` test, the auxiliary number is −1 and has no Blue
move, so Blue's options are exactly board moves and, when present, the star.
White may move in the number, and every required White-first witness must
be checked for the whole sum. General q needs its full canonical options.

This exposes rather than solves the strictness dependency. Marked-state
lemmas can supply the White-first witness only after their own induction
has closed with a decreasing rank. A label such as "strict" or "paired"
cannot replace that proof.

## Checkable conditional ledger

`round4_star_bounds_check.py` implements the conservative sum rules and
records which of the displayed conditional clauses meet the White-next
requirement in each star parity. It also deliberately rejects the unsafe
extension from `RX<1` to `RX+*<1` at zero numerical slack, and marks the
same-width star-consumption obligation as requiring an independent witness.

Independent recursive game-order tests exercise the rules on finite short
games, including infinitesimals that are outside the number-plus-star class.
The general rules are proved above, not inferred from that finite sample.
