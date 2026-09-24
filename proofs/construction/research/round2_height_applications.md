# A corner dialogue that uses exact twin-square deletion

Status: **proved conditional local transition with strictly smaller width**.
This applies the [shared-twin deletion theorem](round2_height_twin_modules.md)
to actual play on a five-row rectangle. It is one branch of a possible local
strategy, not an answer to every intervening Blue move.

## The prescribed branch

Let the board have height five and width `n≥4`, put `k=n−3`, and use zero-based
coordinates. The left endpoint may have any of the handoff's patterns P, or
be unrestricted (`O=ooooo`). The right endpoint may be D or O. All intervening
columns are unrestricted.

Suppose Blue's first move is a legal cell `z=(r,c)` with `c<k`. White starts
the corner dialogue at

```text
W1 = (0,k).
```

If Blue's next move is the legal cell

```text
B2 = (2,k),
```

White responds at

```text
W2 = (2,k+2).
```

The White moves are legal: W1 is a new interior-column cell, and W2 is
distinct from all occupied cells and is not adjacent to W1; the D endpoint
allows White at row two. The hypothesis that B2 is legal excludes
`z=(2,k−1)`, since that first Blue stone would prohibit it. No assertion is
made when Blue chooses some other second move.

The same final local position also arises in the opposite temporal order of
the two Blue moves: Blue first opens at `(2,k)`, White plays `(0,k)`, Blue
next plays a legal z in `c<k`, and White plays `(2,k+2)`. Thus the identity
also gives a response to every such outside continuation after that specific
near-end center opening. Remaining Blue continuations are still obligations.

## Exact removal of the upper-right corner

After W2, the local top-right `3×3` block has the following permissions:

```text
 . b o
 . o b
 . . .
```

The leftmost three cells of the display are occupied or doubly forbidden;
in particular `(1,k)` is adjacent to W1 and B2. The bottom middle cell
`(2,k+1)` is adjacent to B2 and W2. Any effect of z on this block can only
remove already absent Blue permissions in its leftmost column.

The shared cells

```math
I=\{(0,k+2),(1,k+1)\}
```

are false twins in the actual live graph, with common neighborhood

```math
H=\{(0,k+1),(1,k+2)\}.
```

The vertices of H are Blue-only and nonadjacent, so `α(H)=2=|I|`. Neither
shared cell has another live neighbor. Exact twin-module deletion therefore
removes `I∪H` without changing the value, regardless of the outside edges
incident to H. The other five vertices of this `3×3` block are already dead.
Thus this branch exactly removes the whole upper-right `3×3` corner from
the live position.

The surviving outside permissions are retained; deleting this corner does
not undo the restrictions caused by the stones played there.

## A smaller boundary game and an explicit star

The surviving bottom-right `2×3` cap has permissions bounded above by

```text
wob
ooo
```

Blue is forbidden at its upper-left cell by B2, and White at its upper-right
cell by W2. If z lies just to its left, restoring an additional Blue
permission is allowed. No White permission has to be restored.

The useful interface improvement is to retire the cap's upper-left White
permission as well, giving

```text
.ob
ooo
```

**Both cap patterns have exact value `*`**, independently checked by both
recursive game-order comparisons with `{0|0}`. Neither is zero. The second
pattern retains the same value with smaller White support: its left support
is just the bottom row, corresponding to full-strip row 4. Only row 4 of
the left remainder must therefore become White-forbidden to cut this seam.

The local stones already prohibited Blue at row 2 of that endpoint and
White at row 0. The resulting endpoint is exactly the existing
`X=bowob`. Thus, if `B_z(PX_k)` means the permission game `PX_k` after the
legal Blue move z, the stronger useful comparison is

```math
G_{after\ W2}\le B_z(PX_{n-3})+*.
```

At `k=1`, P and X are intersected before applying z. The excluded first
move `(2,k−1)` is exactly the extra Blue prohibition introduced by X, so z
is a legal move in the indicated virtual smaller game. The initial right
endpoint D or O has no surviving additional effect: every D restriction
in the cropped columns is already imposed by the displayed moves.

Both comparison inclusions hold in the required direction. Crossing edges
from the left remainder into the cap occur in row 3 or 4. The cap is
White-forbidden at row 3, and the X endpoint is White-forbidden at row 4.
This proves the bound independently
of n. The recursive strip width drops from n to `n−3`; the other summand is
the fixed six-cell cap. The exact deletion itself also decreases live area.

**Turn obligation:** Blue is next after W2. Therefore a separately proved
inequality `B_z(PX_{n−3})+*≤0` would complete this branch. A nonpositive bound
for `B_z(PX_{n−3})` alone is insufficient. The transition does not prove
such a bound, and it does not discharge the alternative Blue second moves.

For an ordinary odd-width rectangle with `n≥7`, horizontal reflection can
place the first Blue move in `c≤(n−1)/2≤n−4=k−1`, so this corner dialogue
can be started after every normalized opening. Its completeness obstruction
is the missing set of responses to the other Blue moves, including moves
far from this corner; geometric applicability is not a winning strategy.

### Conditional connection to the existing DX targets

The following additional implication uses a structural assumption, rather
than following from game-order inequalities alone: each relevant Blue option
H is a number or a number plus star. The handoff records this classical
property for genuine Col games in its section 19F. Its application to these
permission games is an explicit premise of this corollary; the geometric
crop, local cap identities, and comparison above do not rely on it.

The permission games do lie within the general-graph Col scope of that
premise. Delete permanently dead vertices. For every White-only vertex,
attach an already occupied Blue pendant neighbor; for every Blue-only
vertex, attach an already occupied White pendant neighbor. Each pendant
affects only its own original vertex and supplies exactly the required
own-color prohibition. The occupied pendants have no remaining moves.
Their stones are mutually nonadjacent. If reachability from an alternating
empty-board history is required, balance the numbers of the two colors by
adding already occupied isolated vertices of the minority color; they
affect no remaining move. All these prescribed stone placements can then
be played in alternating order. The resulting residual Col game is exactly
the original permission game. This verifies the class membership of DQ
games and their Blue options; it is not a proof or independent certificate
of the general number-or-number-plus-star theorem itself.

Let G be the smaller `DX_k`, and assume both required targets `G≤0` and
`G+*≤0`. For every Blue option H of G, the first comparison implies
`H` is not `≥0`. The second implies `H+*` is not `≥0`, since it is a Blue
option of `G+*`. If H is `q` or `q+*`, these two exclusions force `q<0`:
positive q makes H positive, while at q=0 the possibilities H=0 and H=*
are excluded by the first and second comparisons respectively. It follows
that `H+*<0`.

Thus, under that Col-specific structural premise and the existing paired DX
targets, the improved crop comparison discharges this entire prescribed DD
branch without a new numerical boundary family. For odd n, `k=n−3` is
positive and even, exactly the DX target domain. The construction's other
Blue continuations and the proof of the arbitrary-width DX targets remain
unresolved.

This reasoning must not be extended to arbitrary auxiliary short games. For
an ordinary empty starting board, P is neutral, and the smaller game is the
one-ended X family, not DX. The DD hypotheses do not settle that separate
empty-board bridge.

### Why the cap's support matters

Keeping the first cap's more generous White support would instead require
retiring both rows 3 and 4 at the smaller strip's endpoint. This gives the
more restrictive new letter `Y=bowbb` and the valid but weaker comparison
`G_after W2≤B_z(PY_(n−3))+*`. The corresponding natural uniform leaf target
is already false at a small width. Independent exact game-order checks give

```math
DY_2=\frac12.
```

Its row-major permission masks are `(A,B)=(975,313)`. Blue at `(0,0)` leaves
the child with masks `(968,312)`, whose value H satisfies `H≥0`. Consequently
`H+*` cannot be nonpositive: otherwise `*≤H+*≤0`, a contradiction.

Thus `B_z(DY_k)+*≤0` for **all** positive even k and all legal z is not a
viable auxiliary family. The corner transition supplies an exact geometric
reduction, but this particular cap separation can lose the numerical sign.
It needs a different treatment of the surviving cap interaction, additional
compensation, or carefully limited exceptional branches. The positive
comparison says nothing about positivity of the actual post-reply position.

## Why the extra Blue move matters for exact deletion

There is no pair of shared false twins in an actual empty `m×n` rectangle,
`m,n≥3`, immediately after just one Blue move and one White move.

For completeness, let u and v be hypothetical shared twins. Neither may
neighbor either stone. Every neighbor in `N(u)△N(v)` must therefore be a
nonoccupied dead vertex adjacent to both stones. Two distinct grid vertices
have at most two common neighbors, so `|N(u)△N(v)|≤2`.

Vertices farther apart than distance two have disjoint neighborhoods of
total size at least four, so they cannot be such twins. At distance two:

- For straight separation, u and v have one common neighbor. The bound of
  two forces both vertices to be corners, at opposite ends of a side of
  length three. Their two unmatched neighbors have just one common
  neighbor, so they cannot both be adjacent to two distinct stones.
- For diagonal separation, u and v have two common neighbors. The degree
  bound leaves either a corner and its inward diagonal vertex, or two edge
  vertices surrounding one corner. In the first case the two unmatched
  neighbors have only two common neighbors, one being the shared vertex
  itself, which cannot be a stone. In the second case the two unmatched
  neighbors are distance four apart and have no common neighbor.

Adjacent vertices are not independent false twins and have no common open
neighbor in this triangle-free graph. These cases exhaust the possibilities.
This obstruction concerns actual shared twins after two moves; it does not
rule out making a valid comparison first, other exact identities, or later
adaptive reductions. The three-move corner dialogue above demonstrates the
new possibility once a second Blue move has occurred.

## Reproduction

```sh
python3 proofs/construction/research/round2_height_applications_check.py
```

The checker reconstructs legal moves from permissions, checks the shared
twins and exact common live neighborhood, checks the cap's exact star value,
and checks both permission inclusions and every White seam for the smaller
assembly. It also regresses the two-move no-twin statement on finite small
rectangles. The symbolic proofs above, not those finite ranges, establish
the parameterized claims.
