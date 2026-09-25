# A height-independent obstruction to cancellation across a fixed column

Status: **proved obstruction to a specified upper-comparison construction**.
This is not a counterexample to any empty rectangle of height at least three.
It follows the [research handoff](col_research_handoff.md), including its warning
that zero fixed paths and two reflection axes do not prove a zero whole game.

The literal conjecture over all positive odd dimensions requires an exception:
the empty `1×1` board is `*={0|0}`, so it is not zero. The discussion below
concerns height `m≥5` and odd width `n≥3`; it makes no unproved assertion about
all one-dimensional boards.

## The candidate construction

Let `n=2k+1`, `k≥1`, and let reflection across the middle column exchange the
left and right full-height half-rectangles `L` and `R`. Write `F` for the fixed
middle column and `τ` for reflection. The actual position is obtained from an
ordinary empty rectangle by legal Col play.

Consider an upper comparison that separates `L`, `F`, and `R`, using arbitrary
virtual permission masks satisfying

```math
A_{actual}\subseteq A_{virtual},\qquad
B_{virtual}\subseteq B_{actual},
```

and the required absence of a crossing edge with two virtual White-legal
endpoints. Suppose the half-rectangle games are made **color-conjugate under
reflection**:

```math
A_R^*=\tau(B_L^*),\qquad B_R^*=\tau(A_L^*).
```

The two halves then have values `Q` and `−Q`, so their virtual sum is zero.
The intended conclusion would come from a nonpositive middle-column game.
This includes exact empty-half cancellation as a special case; it permits
arbitrary extra virtual Blue permissions and arbitrary White restrictions.

The theorem below eliminates this construction after a single Blue opening
and a single White reply at every height `m≥5`. It does not eliminate a
reflection strategy with adaptive departures, unequal half-games compensated
by other values, or another partition of the board.

## A necessary support condition

For a middle-column vertex `f=(r,k)`, denote its neighbors in the two halves by
`u=(r,k−1)` and `v=(r,k+1)=τ(u)`.

**Lemma.** If `f` is virtually White-legal in the construction above, then
both `u` and `v` must be actually Blue-illegal.

Proof: seam safety makes `u` and `v` virtually White-illegal. The conjugacy
identities then make the opposite vertices virtually Blue-illegal as well.
Actual Blue permissions must be retained virtually, so both are actually
Blue-illegal. Also, `f` must be actually White-legal by the comparison
direction. These are necessary conditions before assigning any numerical
value to a region.

**Single-Blue-stone consequence.** If the actual position has exactly one Blue
stone, then no vertex of `F` can be virtually White-legal, regardless of how
many White stones are present.

Proof: suppose `f` is actually White-legal and both `u,v` are actually
Blue-illegal. White legality of `f` rules out a White stone at `f`, `u`, or
`v`. Therefore the Blue illegality of each of `u,v` must be caused by the
unique Blue stone `p`, meaning

```math
p\in N[u]\cap N[v].
```

For these two vertices of a rectangular grid, `N[u]∩N[v]={f}`. Hence `p=f`,
which would make `f` occupied and White-illegal, a contradiction. This uses
closed neighborhoods and remains valid at the top and bottom boundaries.

## Immediate cancellation is impossible at height five and above

**Theorem.** Start with an empty `m×(2k+1)` rectangle, where `m≥5` and `k≥1`.
After any Blue opening and any legal White reply, every valid comparison in
the stated class has a strictly positive virtual sum. In particular, it
cannot certify the required nonpositive child after White's reply.

Proof: the single-Blue-stone consequence makes the entire virtual middle
column White-unavailable. One Blue move removes Blue legality from at most
three cells of that column: this maximum occurs when the Blue stone is
itself on the column. The White reply removes Blue legality only from its
occupied cell, so at most one further middle-column cell is removed. Thus
at least `m−4≥1` actual Blue-legal middle-column cell survives, and it must
survive virtually.

The middle-column game therefore has no White move and has at least one Blue
move. It is strictly positive. More explicitly, a Blue-only Col game on a
graph has integer value equal to the maximum size of an independent set of
its Blue-legal induced subgraph; here that integer is at least one. The
color-conjugate half-games cancel, so the whole virtual sum is positive.

This is **not** a claim that the actual child is positive. The comparison is
`G_actual≤V`, and `V>0` does not determine `G_actual`'s sign. The theorem
eliminates this exact cancellation construction as a way to prove `≤0`.

The height threshold has geometric content. At height three, a Blue center
move can eliminate all actual Blue moves in the middle column. The above
argument then supplies no positive surviving middle game; it therefore does
not obstruct the established three-row separator mechanism.

## A bounded dialogue cannot remove the height obstruction uniformly

The same support argument gives a coarse but useful quantitative extension.
Suppose the actual position has `b` Blue stones and `w` White stones. Let `S`
be the set of virtually White-legal middle-column vertices and `s=|S|`.

For every `f∈S`, the two neighboring half-vertices must be Blue-illegal and
cannot contain White stones. Some Blue stone in `L` must block the left
neighbor and some Blue stone in `R` must block the right one. A Blue stone on
the fixed column cannot do either job for such `f`: the only candidate is
`f` itself, which must be White-legal. A Blue stone within a half can block
the neighbor of at most three different middle-column vertices. Consequently,
with `b_L,b_R` the Blue stone counts in the two halves,

```math
s\le 3\min(b_L,b_R)\le \frac{3b}{2}.
```

Meanwhile at most `3b+w` actual Blue permissions have been removed from the
middle column. Its virtual Blue-legal set therefore contains an independent
subset `I` of size at least

```math
|I|\ge\left\lceil\frac{m-3b-w}{2}\right\rceil.
```

**Counting lemma.** A Col position with an independent set of `t` Blue-legal
vertices and at most `s` White-legal vertices is strictly positive if
`t>2s`.

Proof: Blue always plays in that fixed independent set. Blue moves do not
block another member. Each White move can remove at most its own occupied
vertex from the set, and White can make at most `s` moves in total. With
`t>2s`, Blue always has a move on every turn needed to outlast White, whether
Blue or White starts. Thus Blue wins with either starting player, which is
exactly strict positivity.

It follows that the fixed-column virtual game is positive whenever

```math
m>9b+w.
```

The conjugate halves again cancel. Thus a dialogue allowing at most `t` Blue
and `t` White moves before applying this construction cannot work uniformly
over all heights: every height `m>10t` is obstructed. This bound is deliberately
coarse. It is a proved necessary limitation of the candidate construction,
not a search cutoff or a claim about the actual game's outcome.

## Consequences for a height-lifting program

The empty fixed path cannot simply be evaluated in isolation while the two
sides are made color-conjugate. The comparison's support conditions link that
path to the two neighboring columns and can remove all of its White moves.
An interface description must retain this information.

The precise remaining choices include:

- preserve some interaction across the fixed column rather than cutting both
  seams;
- replace exact conjugate-half cancellation by unequal games with an explicit
  compensating inequality;
- create enough Blue support on both sides of the column, with a strategy
  handling every intervening Blue move, and let its length grow with height;
- use a different partition or recursive geometry.

These are dependencies, not established strategies. The argument does not
rule out a four-sided interface algebra or exact shared-leaf deletion; it
rules out treating a zero fixed-axis path as an independent free component
in the specified one-sided cancellation proof.

## Reproduction

```sh
python3 proofs/construction/research/round2_height_reflection_check.py
```

The checker has no game search. It checks closed-neighborhood intersections,
all opening/reply placements on a finite selection of rectangles, and the
quantitative support inequalities on all disjoint three-state assignments of
a `3×3` board. Those checks are regression evidence for the implementation.
The unbounded results follow from the neighborhood and counting proofs above,
not from the finite ranges.
