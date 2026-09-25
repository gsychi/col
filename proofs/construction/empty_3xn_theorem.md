# Empty 3 × n Col boards have value zero

## Status and scope

This document records the later gadget-and-induction proof of the all-width
theorem. It supersedes earlier project notes that described the empty
`3 × (4k+3)` family as unresolved. The finite gadget certificates are the
computer-assisted part; the argument below supplies the unbounded induction.

The gadget names and bounds below are those used in the proof: `E4`, its
horizontal reflection `E4bar`, the one-column end tile `F1`, `K_corner`,
`K_outer2`, `K_outer4`, `T_middle1`, `J5`, `Z7`, and the cap `C3`; their
exact roots (width, Blue mask, White mask, White ports) and certificate
files are bound in `three_row/manifest.json` (table in
`three_row/README.md`). In particular, `C3 ≤ 1/4` and an
`E4` opened on an odd-parity cell has bound at most `-1`. The tiling
comparison principle is stated in the proof of composition below. This file
records the proof and its finite inputs; it does not replace the independent
machine-checkable certificate data for those inputs.

## Theorem

For every positive integer `n`, the empty `3 × n` Col board has value zero:

```math
H_n = 0.
```

Equivalently, the second player wins.

## Composition principle

For an actual position, construct virtual regions so that:

1. Blue has at least all the moves Blue had in the actual position;
2. White has no moves in the virtual position that are unavailable in the
   actual position; and
3. no edge crossing between virtual regions has White-legal cells at both
   endpoints.

Then the actual game is bounded above by the sum of the virtual region games:

```math
G_{actual} \leq \sum_i T_i.
```

*Proof.* It suffices that Blue, moving first, loses
`G_actual + Σ(−T_i)`. White answers each Blue move at `v` in `G_actual`
with the Blue placement at `v` in the block containing `v`, which is a
Right move in `−T_i`; this is available by condition 1. Each Blue move in
some `−T_i` is a White placement `w` in `T_i`, and White answers it by
playing `w` in `G_actual`; this is available by condition 2. An actual Blue
stone removes at least as much Blue legality as its virtual copy, so
condition 1 persists. An actual White stone at `w` removes White legality
from neighbours of `w` in other blocks. By condition 3 those cells were never
White-legal virtually, so condition 2 persists. White therefore always has
an answer, and Blue runs out of moves first. Consequently, a virtual sum at
most zero shows that Blue loses when Blue is to move in the actual position.
A virtual sum below zero shows `G_actual < 0`, so White wins even when White
is to move (Case 1). The argument is unchanged with dyadic numbers added to
the virtual sum. This is a one-sided comparison, not a claim that cutting
arbitrary board edges preserves game value.

## Even widths

If `n` is even, the half-turn rotation of the `3 × n` board has no fixed
square. After Blue's first move, White plays the rotated square; thereafter
White mirrors every Blue move by the same rotation. The paired occupancy
preserves legality and leaves the last move to White. Hence `H_n = 0`.

## Widths congruent to 1 modulo 4

For `n = 4k + 1`, tile the board as `E4^k F1`, where `F1` is the certified
one-column end gadget. The gadget bounds and compatible White boundary masks
give a virtual sum at most zero. The comparison principle therefore gives
`H_(4k+1) ≤ 0`. The empty board is color-symmetric, so `H_n = -H_n`; hence
`H_(4k+1) = 0`.

## Widths congruent to 3 modulo 4

The boards of widths 3, 7, and 11 are finite certified base cases. For
each of their 4, 8, and 12 normalized openings,
`research/existing_library_scan.json` stores a White reply and a tiling by
certified tiles, replayed by `three_row/verify.py`. Besides `E4`, `E4bar`,
`F1`, `K_corner` and the physical-edge `Z7`, those tilings use nine further
ordinary tiles. The six cases below do not cover these widths. At `n = 7`,
Case 5 at `(1,1)` would need `b = −1` and Case 6 at `(1,3)` would have
`s = 3`; at `n = 11`, Case 5 at `(1,5)` would need `b = −1`.

Proceed by
strong induction for `n = 4k + 3 ≥ 15`, assuming every smaller width in this
family has value zero. (Only the recursive case below invokes the hypothesis.)

After Blue's first move at `(r,c)`, vertical and horizontal reflection let us
assume `r ∈ {0,1}` and `0 ≤ c ≤ 2k+1`. Reflections preserve checkerboard
parity. There are six cases.

### Case 1: `r+c` is odd

Tile the board as `E4^k C3`, with the cap in columns `4k,4k+1,4k+2`. Since
`c ≤ 2k+1 < 4k`, Blue opened the `E4` block `j=⌊c/4⌋`, at local cell
`(r, c-4j)`. Because `r ∈ {0,1}` and `r+c` is odd, that cell is one of
`(0,1), (0,3), (1,0), (1,2)`. For each of them a numerical certificate
proves `E4_open + 1 ≤ 0`, where the opened block has Blue mask
`4095 ∖ N[v]` and White mask `2023 ∖ {v}`. All other `E4` blocks are at most
zero, and the cap `C3` (Blue mask `511`, White mask `503`, left port `101`)
satisfies `C3 - 1/4 ≤ 0`. By the comparison principle in its game-order
form,

```math
G \leq -1 + \frac14 = -\frac34 < 0,
```

and White, who is to move, wins.

For the remaining cases `r+c` is even. These are outer-row openings in an
even column, or middle-row openings in an odd column.

### Case 2: outer corner `(0,0)`

White replies at `(2,2)`. Use `K_corner E4bar^k`, with widths `3+4k=n`.
The White boundary masks are compatible and every piece is nonpositive, so
`G ≤ 0`.

### Case 3: outer row, `c=4a+2`

Set `b=k-a-1`; White replies at `(2,c-2)`. Tile as
`E4^a K_outer2 E4bar^b`. The exceptional gadget has width seven and local
moves `(0,2)` for Blue and `(2,0)` for White. The total width is
`4a+7+4b=4k+3`. The normalization ensures `b≥0`; compatible seams and
nonpositive gadget bounds give `G≤0`.

### Case 4: outer row, `c=4a+4`

Again set `b=k-a-1`; White replies at `(2,c+2)`. Tile as
`E4^a K_outer4 E4bar^b`, where `K_outer4` is the horizontal reflection of
`K_outer2`: Blue mask `1046471`, White mask `515951` (diagram
`ooow.wo / booowob / ooooob.`, White ports `101 / 100`). Its local moves are
`(0,4)` for Blue and `(2,6)` for White. Since `c ≥ 4` (the corner `c = 0` is
Case 2), `a ≥ 0`, and `4a+4 = c ≤ 2k+1` gives `b ≥ (2k-1)/4 > 0`, so
`b ≥ 1`. The total width is `4a+7+4b=4k+3`. The left port `101` meets
`E4`'s right port `010`, and the right port `100` meets `E4bar`'s left port
`010`. All pieces are nonpositive, so `G≤0`. (The stored root with White
mask `516079` has left port `111` and is usable only when `a = 0`.)

### Case 5: middle row, `c=4a+1`

Set `b=k-a-2`; White replies at `(0,c-1)`. Tile as
`E4^a T_middle1 E4^b J5`. The widths sum to
`4a+6+4b+5=4k+3`. From `c≤2k+1`, we have
`a≤floor(k/2)≤k-2` for `k≥3`, so `b≥0`. All pieces are nonpositive and their
seams are compatible. Therefore `G≤0`.

### Case 6: middle row, `c=4a+3` (the recursive separator case)

Blue occupies `(1,c)`. This makes all three squares in column `c` illegal to
Blue: the middle square is occupied and its two neighbors are adjacent to
Blue's stone. White replies at `(0,c+1)`, which already makes `(0,c)`
White-illegal, and voluntarily never plays `(2,c)`. That column is now a dead separator for the
comparison strategy.

Let `s=n-c-1` be the width to the right of the separator. Since both `n` and
`c` are 3 modulo 4, `s` is 3 modulo 4; the normalization gives `s≥7`.

On the left, Blue may have lost a boundary move due to the original stone.
Restore that permission in the virtual game, which only gives Blue extra
options. This left virtual region is exactly the empty board `H_c`. Here
`0<c<n`, so the strong-induction hypothesis gives `H_c=0`.

On the right, the response at `(0,c+1)` leaves a region tiled by
`Z7 E4bar^((s-7)/4)`, where `Z7` is the width-7 gadget with Blue mask
`2097022` and White mask `2088828` (diagram `.booooo / .ooooob / ooooooo`,
White ports `001 / 101`). Its root is the local position after the stones
at `(1,c)` and `(0,c+1)`, with White additionally forgoing local `(1,6)`, so
its right port `101` meets `E4bar`'s left port `010`. The older root with
White mask `2097020` has right port `111`. It is valid only when `s = 7`,
where `Z7` ends at the physical edge, and cannot be followed by `E4bar`.
Each gadget is at most zero and every seam has a White-illegal endpoint, so
the right contribution is at most zero. The dead
column prevents cross-region White interaction. The composition principle
therefore yields

```math
G \leq H_c + Z_7 + \sum E4bar \leq 0.
```

This is the only recursive case; its recursive board is strictly narrower
and belongs to the same `4k+3` family.

## Closing the induction

The cases cover every normalized first Blue move. In Cases 2–6, White's
stated reply leaves a position of value at most zero. In Case 1 the position
after Blue's move is already negative, so White has a reply of value at most
zero (a Right option), although none is named. Hence `H_(4k+3)≤0`. The empty
board is invariant under color exchange, hence `H_(4k+3)=-H_(4k+3)`. Together
these imply `H_(4k+3)=0`, completing the induction.

The even-width argument, the `4k+1` construction, and this `4k+3` induction
cover every positive width.

## Provenance and remaining formalization work

Each named gadget and numerical bound is bound to an exact certificate root
in `three_row/manifest.json`. `python3 proofs/construction/three_row/verify.py`
replays every certificate without search and checks the base widths. It
also checks the six-case tilings for every normalized opening at widths up
to 203, the local windows and seam table on which the all-width argument
rests (`three_row/PROOF_CHECKLIST.md`), and the strictly decreasing
recursion. The finite sweep is a regression test; the all-width claim rests
on the written induction and those finitely many local checks. The broader project status,
five-row research program, known obstructions, and next targets are collected
in the [research handoff](research/col_research_handoff.md).
