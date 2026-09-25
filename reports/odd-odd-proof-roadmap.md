# Odd x Odd Col Proof Roadmap

This note summarizes what we currently know about empty `m x n` Col boards
when both `m` and `n` are odd, and what is still missing for a proof.  The
notation follows the proof-miner reports:

- `o`: legal for both players
- `b`: P1-only
- `w`: P2-only
- `.`: dead or absent inside a bounding box

The target conjecture is:

> For all odd `m,n >= 3`, the empty `m x n` Col board has CGT value `0`.

Equivalently, the second player wins under normal play.

## What Is Already Solid

### Rules and finite termination

Col is a finite partisan placement game on a graph.  P1 places black stones,
P2 places white stones, and a player may not place next to a stone of their own
color.  Every move occupies one previously empty cell, so every play line has
length at most `m*n`.

For proof work, it is usually better to reason about shadow states:

- `legal_p1`: cells P1 may still play
- `legal_p2`: cells P2 may still play

The game outcome depends only on these legal masks and the side to move, not on
the exact prior stone history.

### Even-dimension theorem

If `m` or `n` is even, the empty `m x n` board is a second-player win.  P2 uses
central reflection: after every P1 move, P2 plays the reflected cell.  Because
the reflected cell is never fixed and same-color adjacency is preserved by the
reflection, P2 always has a legal reply.

This theorem does not solve odd x odd boards because the center cell is fixed.

### Linear Col theorem

For `1 x n` Linear Col:

- `o` has value `*`
- `o...o` has value `0` for length `>= 2`
- `b...o` and `o...b` have value `1/2`
- `w...o` and `o...w` have value `-1/2`
- `b...b` has value `1`
- `w...w` has value `-1`
- `b...w` and `w...b` have value `0`

This is the Uiterwijk theorem.  It gives the right flavor of induction, but it
does not directly extend to two-dimensional components.

### Computational evidence

The current evidence supports the odd x odd conjecture:

- Demeur verified `3x3`, `3x5`, `3x7`, `3x9`, and `5x5`.
- Current solver/tablebase evidence covers `3x11`, `3x13`, and `5x7`.
- The proof-miner report scans solved odd boards and finds many repeated local
  tinted components with exact values.

The current in-memory `3xn` miner also verifies:

- `3x5`: P2 win, 537 searched states
- `3x7`: P2 win, 12,473 searched states
- `3x9`: P2 win, 160,636 searched states

These are evidence, not proof.

## Why Linear Col Is Not Enough

A direct proof attempt would hope that every 2D component either reduces to a
Linear Col chain, has value `0`, or appears with an opposite-color partner.
This fails as a standalone lemma.

The smallest obstruction is the bent triomino:

```text
ww
w.
```

All live cells are P2-only.  P1 has no moves.  P2 has either:

- a corner move to `0`, or
- an arm move leaving one P2-only singleton of value `-1`.

So the value is:

```text
{ | 0, -1 } = { | -1 } = -2
```

This component is reachable from empty `3x3`, for example in the semantic state:

```text
B.W
wwB
wBW
```

Therefore a proof needs a real 2D component algebra or a cancellation theorem.
Linear Col can still be used for terminal chains, but not as the only component
classification.

## Best Smaller Target: All Odd 3xn

The most plausible smaller theorem is:

> For all odd `n >= 3`, empty `3 x n` Col is a second-player win.

This is much more approachable than full odd x odd because height is fixed.
Instead of arbitrary 2D geometry, a proof can use a finite set of height-3
frontier states.

The current miner in `scripts/mine_3xn_families.py` points to candidate exact
zero frontier lemmas such as:

```text
b
o
w
```

```text
bow
```

```text
bw.
.bw
```

```text
wob
.wb
```

and also highlights nonzero obstacles that the recurrence must handle:

```text
bbw
b..
```

has value `1`, while

```text
wow
.w.
```

has value `-2`.

The likely proof shape is a finite-state induction on `n`, not a simple mirror
strategy.  A naive plan such as "P2 always takes center unless P1 does" is false
on small solved strips.

### Opening evidence for 3xn

For canonical first moves in `3x3`, `3x5`, `3x7`, `3x9`, and `3x11`, at
least one corner reply is enough in the solved search tree.

Through `3x9`, the simpler deterministic rule held:

- If P1 opens in the top-left corner, P2 can reply in the top-right corner.
- For all other canonical first moves checked through `3x9`, P2 can reply in
  the top-left corner.

That deterministic rule fails on `3x11`: after P1 opens at `(0,2)`, P2 replying
at `(0,0)` is a P1 win.  However the weaker corner-reply lemma still survives;
for that opening, the other three corners are all P2 wins.

This suggests a smaller opening lemma worth proving:

> Every first move on empty odd `3xn` has a P2 corner reply that lands in a
> losing finite-state strip family.

This is only evidence so far, but it now holds through `3x11` by direct Rust
position queries.

## What Lean Could Prove Now

Lean could get surprisingly far if we aim first at outcomes rather than full
canonical CGT values.

### Straightforward Lean definitions

These are routine:

1. Define rectangular boards as finite types:

   ```lean
   Fin m x Fin n
   ```

2. Define orthogonal adjacency.

3. Define positions as two finite sets, `black` and `white`, with disjointness.

4. Define legal moves for each player.

5. Define `move` and prove it strictly decreases the number of empty cells.

6. Define recursive outcome:

   ```lean
   Winning p turn := exists legal move, not (Winning (move p turn move) otherTurn)
   ```

   using well-founded recursion on remaining cells.

7. Prove shadow-state equivalence: outcome depends only on `legal_p1`,
   `legal_p2`, and turn.

### Easy theorem in Lean

The even-dimension theorem should be very formalizable:

- define central reflection,
- prove it is fixed-point-free when one dimension is even,
- prove it preserves adjacency,
- prove reflected replies are legal,
- conclude P2 has a copy strategy.

This is probably the first serious Lean milestone.

### Linear Col in Lean

Uiterwijk's theorem is also formalizable, but more laborious.  The proof needs:

- a syntax for tinted chains,
- a recursive evaluator or CGT value type for dyadic numbers plus `*`,
- proofs of the seven boundary families by induction on chain length.

For outcome-only results, this can be shortened.  For exact CGT values like
`1/2`, `-1/2`, and `*`, Lean needs more CGT infrastructure.

### Finite board certificates

Lean can prove fixed boards like `3x5`, `3x7`, or `5x5` by reflection of an
executable search certificate:

- define the recursive outcome function,
- run it by computation for a fixed finite board,
- prove the result with `native_decide` or a generated certificate.

This gives certified examples, but not a general theorem.

## What Lean Would Not Solve Yet

Lean will not invent the missing proof.  It can check a finite-state induction
once we have the right finite state table, but it will not make the odd x odd
conjecture easy.

The missing mathematical lemmas are below.

## Missing Lemmas

### 0. Fixed-column interaction lemma

This is the most tempting route to the full odd x odd conjecture.

For any odd `m x n` board, vertical reflection fixes the middle `m x 1`
column.  By Linear Col, that fixed column has value `0` when `m > 1`.  If we
could prove a theorem of the following shape, the full conjecture would follow:

> If a Col board has a color-swap reflection symmetry and the fixed subgraph has
> value `0`, then the whole board has value `0`.

This simple theorem is false.  A direct search of reachable shadow states found
color-swap-symmetric `3x5` and `3x7` states whose fixed middle column has value
`0`, but whose side-to-move outcome is winning.  For example, in `3x5` the
following semantic shadow states are P1 wins even though the middle column is a
single `o` plus dead cells:

```text
.wob.
.....
..o..
```

```text
.bow.
.....
..o..
```

The obstacle is that the fixed column is not independent from the reflected
wings.  Moves inside the fixed column tint neighboring wing cells, and those
tints do not preserve naive color-swap symmetry.  A simple hybrid strategy --
mirror all off-column moves and play a Linear Col response inside the fixed
column -- also fails on small `3xn` searches.

So the missing lemma is subtler:

> The zero-valued fixed column must remain a zero *relative to symmetric wing
> attachments*, not merely as an isolated Linear Col chain.

This would be the cleanest proof if true.  It is also the highest-leverage place
to search for either a proof or a counterexample to this proof strategy.

### 1. Component decomposition lemma

Statement:

> If the live cells split into 4-connected components, then the position is the
> disjoint sum of those component games.

This is true and should be easy, but needs to be formalized carefully.  Moves in
one component must not change legality in another.

### 2. Shadow-state sufficiency

Statement:

> Two positions with the same `legal_p1` and `legal_p2` masks have the same game.

The solver uses this constantly.  A proof needs to show that future legality is
computed entirely by removing the played cell and tinting its neighbors.

### 3. 2D local value library

Statement:

> A finite set of small tinted components has the claimed CGT values.

This includes both zero candidates and nonzero obstacles:

```text
b/o/w = 0
bow = 0
bw./.bw = 0
wob/.wb = 0
bbw/b.. = 1
wow/.w. = -2
```

For Lean, these can initially be proved by direct finite recursion.

### 4. Closed frontier table for 3xn

This is the key missing lemma for the smaller theorem.

Statement shape:

> There is a finite family `F` of height-3 tinted strip states such that every
> P1 move from a losing family member has a P2 reply to another member of `F`,
> possibly plus components already proved to have value `0`.

We do not have this table yet.  The miner gives candidates, not a closed proof
table.

### 5. Inductive extension lemma for 3xn

Statement shape:

> If a frontier state `S_k` is losing for width `k`, then its extension
> `S_{k+2}` is losing.

The `+2` matters because the target widths are odd and many central patterns
grow symmetrically by adding two columns.

This would turn the finite table into the theorem for all odd `3xn`.

### 6. Opening reduction for 3xn

Statement:

> For every first P1 move on empty `3 x (2k+1)`, P2 has a reply that lands in
> one of the closed losing frontier families.

Small searches show many winning replies, but we have not extracted a clean
symbolic rule for all first moves.

### 7. General odd x odd cancellation theorem

This is the missing lemma for the full conjecture.

Statement shape:

> In any odd x odd board, the nonzero 2D components created by play either
> appear in color-opposite pairs or are absorbed into a larger zero-valued
> structure.

This is currently only a hope.  The bent triomino obstruction shows why the
statement must mention cancellation or larger structures; local zero reduction
alone is false.

### 8. Strategy-to-value bridge

For the exact CGT claim `value = 0`, not just "P2 wins", we need either:

- a CGT theorem that a short game is a second-player win iff it is equivalent
  to `0`, or
- a direct proof that the empty board is equal to `0` in the CGT equivalence
  relation.

This is standard CGT, but it is extra infrastructure in Lean.

## Recommended Lean Path

1. Formalize finite Col positions and outcome recursion.
2. Prove shadow-state sufficiency.
3. Prove component decomposition.
4. Prove the even-dimension copy theorem.
5. Prove a few local component values by direct computation:

   ```text
   o = *
   bw = 0
   bow = 0
   ww/w. = -2
   ```

6. Generate Lean certificates for `3x3`, `3x5`, and `3x7`.
7. Use the miner output to search for a closed `3xn` frontier table.
8. Once the table is closed, formalize the table as an inductive theorem.

## Current Bottom Line

We are missing the closure lemma, not more raw computation.

For `3xn`, the missing object is a finite list of frontier families plus a proof
that P2 can always return to the list.  For general odd x odd, the missing
object is a cancellation theorem for nonzero 2D components.

Lean can already verify definitions, even-board pairing, finite board
certificates, local component values, and eventually a finite-state table.  It
will not by itself bridge the gap from repeated component observations to a
general odd x odd theorem.
