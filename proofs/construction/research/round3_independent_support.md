# Limits of independent White supports on empty rectangles

Status: **proved symbolic necessary conditions and a complete obstruction to
one specific zero-block construction**. These statements concern upper
comparison games obtained by restricting White. A positive such game says
nothing about positivity of the actual empty rectangle.

## An exact formula when both legal sets are independent

Let J and I be independent vertex sets in any finite graph. Give Blue exactly
J and White exactly I. No move can forbid another cell of the same player's
legal set. Edges between cells legal to different players do not restrict
opposite-color moves in Col. The only interaction is occupying a shared cell.
Consequently the exact game is

```math
G(J,I)=|J|-|I|+\bigl(|J\cap I|\bmod2\bigr)*.
```

The private Blue and White cells contribute opposite integers; the shared
cells are isolated stars, cancelling in pairs. This argument concerns the
permission sets, not a claim that the underlying graph has no edges.

Now give Blue every vertex of a graph V and White an independent set I.
For any independent J, restricting Blue to J gives the lower comparison

```math
G(V,I)\ge |J|-|I|+\bigl(|J\cap I|\bmod2\bigr)*.
```

In particular, if `|I|<α(V)`, taking J maximum proves `G(V,I)>0`: a positive
integer with or without star is strictly positive. If `|I|` is odd, taking
J=I gives `G(V,I)≥*`, which rules out `G(V,I)≤0` but does not establish a
strict sign.

Thus a necessary condition for such a nonpositive contract is:

1. I is a maximum independent set;
2. its cardinality is even; and
3. every maximum independent set J has even intersection with I.

The third condition follows from the same formula at equal cardinalities.
These are necessary conditions only. No sufficiency assertion is made.

## Odd rectangles have only one candidate independent support

An odd `m×n` grid has a Hamiltonian path obtained by snaking through successive
rows. This path has `mn` odd vertices. The unique independent set of size
`(mn+1)/2` on that path consists of alternate vertices including both ends:
any extra gap or skipped first vertex would leave too little room for that
many mutually nonadjacent vertices.

Every grid-independent set is independent on the path. Its alternate vertices
are precisely the larger grid checkerboard class, which is itself independent.
Therefore the grid has independence number `(mn+1)/2` and a **unique** maximum
independent set M, the majority checkerboard class.

It follows that any upper comparison of an empty odd rectangle which keeps
Blue legal everywhere and restricts White to an independent set can be
nonpositive only if White's set is exactly M. Every other independent support
gives a strictly positive virtual game. Moreover, when `mn≡1 (mod 4)`, M has
odd cardinality, so even that last candidate is not nonpositive.

This strengthens the earlier obstruction for the two pure checkerboard
choices: it excludes **all other independent White masks**, including mixed
patterns and smaller subsets. For `mn≡3 (mod 4)`, the majority support still
requires an actual value proof. The known `3×5` majority-support root is a
zero example; it must not be extrapolated to other widths.

This theorem does not restrict upper comparisons with adjacent White-legal
cells, post-opening positions where Blue already has fewer legal cells,
or adaptive White permissions. Those are precisely ways to leave its scope.

## The even shared-block partition cannot tile an odd two-dimensional rectangle

Consider the sufficient composition theorem from
[round2_height_twin_modules.md](round2_height_twin_modules.md). Its hypotheses
partition the vertices into blocks `I_j∪H_j`, where:

- the union I of the `I_j` is independent;
- every `I_j` is nonempty and even;
- every cell of `H_j` is adjacent to every cell of `I_j`; and
- `α(H_j)≤|I_j|`.

Each block is zero when Blue is legal everywhere and White exactly on `I_j`;
the global independent White support makes all seams safe. This would give
`G(V,I)≤0`.

**Theorem.** On a positive odd-by-odd rectangle, such a partition exists only
for `1×3` and `3×1`. In particular, it cannot by itself prove any odd rectangle
with both dimensions at least three.

**Proof.** The preceding necessary condition forces I to be the majority
checkerboard M. Its complement H is the other checkerboard and is independent.
Thus `α(H_j)=|H_j|≤|I_j|` for every block. Since `|I|−|H|=1`, all blocks have
equal side sizes except exactly one whose I side is larger by one.

Any two distinct grid vertices have at most two common neighbors. Hence if
`|I_j|≥4`, the complete adjacency condition forces `|H_j|≤1`; that block's
size difference would be at least three, impossible. Therefore `|I_j|=2`
for every block. All but one have `|H_j|=2`, forming unit four-cycles. The
remaining block has `|H_j|=1`, forming a straight or bent three-cell path.

The partition must therefore consist of unit `2×2` squares and exactly one
three-cell path. Each square occupies an even number of cells in each row
and each column. Since every row and column of the odd rectangle has odd
length, the three-cell path must occupy an odd number of cells in every row
and every column. Thus both dimensions are at most three.

Among the four positive odd dimension pairs with that property, `1×1` has
too few cells, and `3×3` cannot have area `3+4s`. The two remaining possibilities
are `1×3` and `3×1`, where the whole board is one qualifying path. ∎

This obstruction does not invalidate exact module deletion in a partially
played position, or a larger zero contract such as the certified `3×5` game.
It explains why the module identity is useful as a dynamic reduction but its
small zero blocks cannot directly tile the target empty rectangles.

## Verification

Run `python3 proofs/construction/research/round3_independent_support_check.py`.
The checker uses recursive Conway order to check the exact independent-set
formula and the lower comparison on every graph through four vertices. It
also checks maximum-support uniqueness on small odd grids and the geometric
parity obstruction across a finite dimension range. The general results
follow from the symbolic arguments above, not from those regressions.
