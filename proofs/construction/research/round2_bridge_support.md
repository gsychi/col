# What an empty-board bridge must preserve

Status: proved interface obstruction and a precise requirement for future
constructions, not a counterexample to an empty rectangle. This continues
[the boundary induction](five_row_boundary_induction.md). It uses the existing
one-sided comparison, including both permission inclusions and White seam
safety.

## A sharp two-column limit after one Blue opening

**Theorem.** Start with an ordinary empty rectangle. Make exactly one Blue
move, followed by any legal sequence of White moves and any admissible upper
comparisons, but no further Blue move. A virtual contiguous full-height
rectangle with all interior columns fully shared and with a White-only cell
required at each of its two endpoints cannot have width three or more.

The statement concerns permission embeddings. It is independent of the
numerical values assigned to the proposed recursive games. In particular it
applies to every two-ended game from the D/U/V/X/R/J alphabet, including
arbitrarily many new pairs and their vertical reflections.

**Proof.** Let the Blue stone be at `(r,c)`. Immediately afterwards, the only
White-only cells are its orthogonal neighbors. They lie in columns
`c-1,c,c+1`. A White move cannot create a White-only cell, and an admissible
upper comparison cannot introduce one: `B_virtual\A_virtual` is a subset of
`B_actual\A_actual`. Thus these are the only possible endpoint witnesses.

Two endpoint columns separated by at least three columns of distance are
impossible, proving the assertion for width at least four. For width three,
the only possible endpoint columns are `c-1` and `c+1`. The fully shared
interior column would then contain the occupied Blue cell `(r,c)`, which is
permanently White-illegal. Making it virtually White-legal violates
`B_virtual ⊆ B_actual`. This also excludes width three. The argument persists
under further White moves and comparisons because permissions only decrease
in the needed direction. ∎

The bound is sharp as a permission statement. On an empty `5×3` board after
Blue `(0,1)`, the first two columns can be relaxed to `UV_2`:
`U=wbobo` on column 0 and `V=bwbob` on column 1. Both inclusions hold. If all
White permissions outside those two columns are retired, the seam is safe.
This example supplies no favorable scalar bound; it only shows that width two
cannot be excluded by the theorem.

## Consequence for the five-row program

Even a complete proof of all the present two-ended families would not, by
itself, supply an immediate empty-board bridge using large regions from only
those families. After a Blue opening and one White reply, every such region
would still have width at most two.

For an induction step with a uniformly bounded amount of finite local material,
the unbounded remainder must therefore use something else:

- a region with a neutral or otherwise different endpoint;
- a state that keeps additional interior White exclusions;
- a strategy that permits another Blue move before invoking a two-ended state;
- another geometry or an exact identity such as a valid module deletion.

This is why the one-ended states, delayed states, or coupled sums of regions
are substantive dependencies, even if DD is eventually solved. It does not
exclude tilings using an unbounded number of finite pieces, and it does not
prove that any required one-ended game is positive.

The theorem also explains a potential productive use of a delayed strategy:
two separated Blue stones can create distinct endpoint witnesses for a long
interval between them, provided its interior White permissions remain intact.
All Blue choices, including distant ones, would have to be covered; merely
assuming the second Blue move stays in a local window is invalid.

## A three-column symmetric-core comparison also has a positive cost

There is a useful independent obstruction when retaining untouched symmetric
wings and isolating a central strip of width three. Suppose all White
permissions in that strip's two outer columns are retired to protect the
seams, and Blue opened in its middle column at row r. Let its height be odd
`h≥3`. Even before White replies, the resulting specific strip game is
strictly positive.

Let

`a = ceil(r/2) + ceil((h-r-1)/2)`.

Each outer column is Blue-only and its row-r cell was made Blue-illegal by
the opening. Blue therefore has an independent set of `a` available cells
in each outer column, giving `2a` guaranteed private moves. White has moves
only in the middle column with row r removed, a disjoint union of paths
whose maximum independent-set size is `a`. Thus White can make at most a
moves while Blue can always make `2a`, with no cross-color interference
between these selected sets. Since `a≥1`, Blue wins with either starting
player. More strongly, restricting Blue to these private independent sets
proves a numerical lower bound of `a>0` on this virtual strip.

For completeness, a one-player placement game on a graph has integer value
its independence number (with negative sign for White): a longest legal
sequence is a maximum independent set, and the recursive integer value is
one plus the largest successor length. The selected Blue vertices and the
White-only middle graph have no same-color cross interactions.

Consequently that specific relaxed three-column core cannot supply a
nonpositive compensation term. This is a statement about the larger virtual
game, not the actual opened rectangle. It does not exclude three-column
constructions with different wing interfaces, a different White reply made
before choosing the comparison, or a different partition.

## Checks and wider-tile discovery

[round2_bridge_support_check.py](round2_bridge_support_check.py) independently
checks the permission statements on small concrete boards and the private
capacity arithmetic. The quantified theorems above rest on the set/graph
arguments, not on these finite regressions.

A separate discovery probe sought full-Blue `5×6` and `5×8` bulk tiles with
complementary White end masks and unrestricted White interior columns. The
source [round2_bridge_screen.cpp](round2_bridge_screen.cpp) uses a finite
minimax visit budget. All 18 recorded probes exhausted their 200,000-visit
budgets. The alternating `21/10` interface also exhausted 5,000,000 visits
at both widths. These results are **Unknown**, with no claimed obstruction or
proof of positivity. They are recorded in
[round2_bridge_screen_results.json](round2_bridge_screen_results.json).
