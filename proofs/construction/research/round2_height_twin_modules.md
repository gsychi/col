# Exact deletion of a shared twin module

Status: **proved symbolic reduction**, with finite independent game-order
regressions. This extends the handoff's two-shared-leaves/one-center deletion
identity. It supplies a positive exact reduction for an adaptive interface
program; it does not assert that every rectangle can be reduced this way.

## A zero local contract with independent White support

Let `I` consist of `p>0` independent vertices, shared by both players. Let `H`
be a disjoint graph on which only Blue has permission. Every vertex of `I`
is adjacent to every vertex of `H`. There are no other vertices in this local
game. Write `α(H)` for the independence number of the graph on H.

**Local lemma.** If p is even and `α(H)≤p`, this permission game has value zero.

Proof when Blue starts:

- If Blue first plays in I, all of H becomes Blue-illegal. White responds
  at another vertex of I. The remaining `p−2` shared, isolated vertices have
  value zero; White can continue pairing them.
- If Blue first plays in H, all of I becomes Blue-illegal. White responds
  in I after every Blue move. Every subsequent Blue move lies in H, and all
  Blue stones there form an independent set, so Blue can make at most
  `α(H)≤p` such moves altogether. White's p independent legal vertices give
  a legal reply to each. Thus Blue loses.

When White starts, White must play in I. Blue responds in a different vertex
of I, making all of H Blue-illegal and leaving `p−2` isolated shared vertices
with White next. Blue pairs the remaining moves and wins. Both starting
players lose, proving zero. The proof is independent of the number of edges
within H; only its independence bound matters.

The conditions are sharp for this contract class. If p is odd, Blue can win
when starting by playing only in I, where neither player blocks another
remaining vertex. If `α(H)>p`, Blue can play an independent set in H and
outlast all p White moves. Neither case can supply a nonpositive local game.

## Exact module deletion with arbitrary outside interactions

Let `G` be any finite Col permission position. Suppose I is an even, nonempty
set of shared, pairwise nonadjacent vertices, all with exactly the same
neighborhood H. Thus the vertices of I are **false twins**: their only
neighbors are precisely all vertices of H. Assume

```math
\alpha(G[H])\le |I|.
```

Permissions on H may be arbitrary. Edges from H to the outside graph may also
be arbitrary. Then

```math
\boxed{G=G-(I\cup H).}
```

Here deletion means removing the indicated vertices and their incident
edges, retaining the outside permissions exactly.

For the upper inequality, restore every Blue permission in H, retire every
White permission in H, and separate `I∪H` from the outside. The resulting
local contract is zero by the local lemma. No vertex of I has an outside
neighbor, and every crossing edge exits through H, which is now
White-unavailable. Thus the composition comparison applies with precisely
the required direction:

```math
A_{actual}\subseteq A_{virtual},\qquad
B_{virtual}\subseteq B_{actual},\qquad
G\le 0+G-(I\cup H).
```

Apply the same argument after exchanging the colors. The vertices of I are
still shared, the local contract is again zero, and the resulting inequality
is `−G≤−(G−(I∪H))`. This supplies the reverse inequality and proves equality.
No assumption about the sign or numerical nature of the outside game enters
the argument. The result remains valid with any additional disjunctive game.

Every use strictly decreases the number of vertices: at least the two shared
vertices are removed. A recursive protocol using this identity can therefore
use vertex count, or `(width, live-vertex count)`, as a well-founded rank.

### Sharpening with the actual permissions

The conservative graph condition above can be weakened to

```math
\max\{\alpha(G[H\cap A]),\alpha(G[H\cap B])\}\le |I|.
```

For the upper inequality, keep Blue's existing permissions on H, retire
White there, and cut the same seams. The local lemma uses only the
Blue-legal subgraph `G[H∩A]`; the other vertices of H are now dead. For the
reverse inequality, exchange colors and use `G[H∩B]`. Thus both local
contracts are zero under the displayed condition, without restoring either
player's permissions on H. This proves the same exact deletion identity
even when `α(G[H])>|I|`.

For example, take two shared twins whose common neighborhood consists of
three pairwise nonadjacent vertices. Deletion is valid if each player is
legal on at most two of those three vertices, although the unrestricted
neighborhood has independence number three. The checker includes all
permission assignments meeting this sharpened condition.

### Particular cases

| Shared set I | Common neighborhood H | Exact reduction |
| --- | --- | --- |
| Two shared leaves | One vertex, with arbitrary outside neighbors | The handoff's three-vertex deletion |
| Two shared opposite corners of a four-cycle, with no other live neighbors | The other two corners, which may connect arbitrarily outside | Delete the whole four-cycle |
| Two shared false twins | Any H with `α(H)≤2` | Delete both twins and all of H |
| `2q` shared false twins | Any H with `α(H)≤2q` | Delete the entire module |

In an ordinary rectangular-grid graph, two distinct nonadjacent vertices
have at most two common neighbors. Consequently, **any two shared,
nonadjacent false twins in a live induced-grid position can be deleted
together with their common live neighborhood**. This covers an isolated
shared pair, the straight or bent three-cell configuration, and the
four-cycle configuration. It requires equality of their live neighborhoods,
not merely two shared neighbors among other live edges.

For an odd number p of shared twins, if `α(H)≤p−1`, delete an even subset
of `p−1` twins and all of H. The remaining twin becomes an isolated shared
vertex. Hence the corresponding exact identity is

```math
G=G-(I\cup H)+*.
```

This star must remain in any subsequent numerical obligation.

## Composition as a sufficient theorem

There is also a useful upper-bound version without requiring exact twins in
the original graph. Let an independent White support I be partitioned into
nonempty even sets `I_j`. Assign every remaining vertex to a set `H_j`, so
that the sets `I_j∪H_j` partition the graph. Suppose every vertex of `H_j`
is adjacent to every vertex of `I_j`, and `α(H_j)≤|I_j|`.

Give Blue permission everywhere and White permission exactly on I. Each
local block is zero by the lemma. The entire I is independent, so no
cross-block edge has two White-legal endpoints. The one-sided composition
gives a nonpositive whole game. Blue wins when White starts by pairing the
even number of vertices in I, so the whole permission game is in fact zero.

This is a sufficient theorem for an ordinary empty graph as well: retiring
White outside I gives a zero upper bound, and color symmetry then gives
zero for the empty graph. A rectangle proof would still need an explicit
partition satisfying all these conditions. The theorem alone is not that
partition and does not bypass the handoff's failed bounded mosaic searches.

## A scope obstruction for checkerboard-only White contracts

For any independent White support I, if `|I|` is odd, Blue wins when starting
by playing only in I. White also has to play in I, neither player's moves
there block another vertex of I, and the odd final move belongs to Blue.
Consequently the restricted game is **not ≤0**. This is a turn-specific
claim, not an assertion that the game is strictly positive; one isolated
shared cell is the counterexample to the latter inference.

On an odd `m×n` rectangle with `mn≡1 (mod 4)`, the majority checkerboard class
has `(mn+1)/2` vertices, an odd number. Therefore a construction that keeps
Blue legal everywhere and restricts White to that class fails throughout
this dimension family, including `5×5`. Restricting White to the minority
class cannot help: Blue can use the larger independent opposite class and
outlast White regardless of who starts. These statements concern the
restricted comparison, not the ordinary empty rectangle.

## Reproduction and next use

```sh
python3 proofs/construction/research/round2_height_twin_check.py
```

The checker constructs finite short games directly and compares them with
Conway's recursive order definition. It does not call a minimax solver or
assume that matching outcomes imply matching values. It checks arbitrary
permissions on H and outside vertices in several graph shapes, including
outside edges through H and a nontrivial H with independence number two.
The arbitrary-graph identity is proved by the two comparison inequalities,
not inferred from these examples.

The next useful experiment is a bounded local dialogue that creates shared
false twins in a partially played five-row strip, then invokes this exact
deletion and enters smaller boundary games. Every possible intervening Blue
move, including a move outside the local window, remains an obligation.
No claim is made here that one immediate reply already creates such twins
in an ordinary empty rectangle.
