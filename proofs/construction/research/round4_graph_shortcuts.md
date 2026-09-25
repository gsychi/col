# Testing broader graph and shape shortcuts

Status: **three exactly checked counterexamples to proposed generalizations**.
These are tests of alternative proof ideas, not counterexamples to empty
ordinary rectangles. None is used as a premise of the wider-cap reductions.

## Perfect matching is not enough

A tempting route is to replace the grid by a bipartite graph admitting a
perfect matching, then seek an adaptive pairing theorem for that class.
The following six-vertex tree rules this out:

```text
Edges: 0–3, 0–4, 0–5, 1–4, 2–3.
Bipartition: {0,1,2} | {3,4,5}.
Perfect matching: 0–5, 1–4, 2–3.
```

Its empty Col value is exactly star. Thus perfect-matching existence alone
does not supply a second-player strategy. A useful pairing proof must carry
more information about adjacency and the effect of replies on future moves.

## Even bipartite graphs with a Hamiltonian path need not have value zero

The stronger hypothesis of a spanning path also fails. Take ten vertices,
all path edges `i–(i+1)` for `0≤i<9`, and the three additional edges

```text
0–5, 3–8, 1–8.
```

The graph is connected, bipartite by vertex parity, and has the explicit
Hamiltonian path `0,1,...,9`. Its empty Col value is again exactly star.
Consequently even order, bipartiteness and a spanning path together do not
justify a zero-value transfer from an ordinary empty path to a grid with
additional edges. Extra same-color interactions cannot be ignored.

## Convexity and two reflection axes do not replace rectangularity

Remove the four corners from a `3×5` grid, leaving this induced graph:

```text
 . o o o .
 o o o o o
 . o o o .
```

Here o is shared and a dot is absent. The graph has odd area 11, is connected,
is convex in every row and column, has odd row and column lengths, and is
invariant under both axial reflections. Its horizontal and vertical fixed
paths are ordinary empty paths of lengths five and three, each exactly zero.
Nevertheless the entire shape has exact value star.

This supplies a concrete artifact for the kind of symmetry failure already
warned about in the handoff, and additionally tests the row/column-convex
shape proposal. It is not claimed to identify the handoff's historical
counterexample: no exact earlier artifact mapping was available. In
particular, a clipped or notched recursive shape cannot be replaced by its
bounding empty rectangle, even when it preserves these symmetries.

## Independent checks

`round4_graph_shortcuts_check.py` constructs every legal option of each
specified finite game and checks both Conway-order directions of equality
with `{0|0}`. It also checks both fixed paths against zero and verifies the
claimed combinatorial properties. This does not infer “value star” merely
from a first-player-winning outcome or from the general Col classification.

These tests eliminate broad shortcuts quickly. They leave the main constructive
program unchanged: retain the grid's interfaces, carry actual permissions,
and prove the recursive bounds for the precise shapes returned.
