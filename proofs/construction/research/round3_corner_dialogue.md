# Completing the corner continuation table, and an actual obstruction

Status: **proved conditional transition covering every intervening Blue move;
proved finite counterexample to the proposed ordinary-board reply policy**.
This continues [the exact twin-square corner branch](round2_height_applications.md).
It does not complete a boundary-state induction or the ordinary-board bridge.

Coordinates are zero-based. Write `O=ooooo`; endpoint letters denote permissions,
and intersect endpoints at width one.

## A complete conditional continuation

Let `n≥4`, `k=n−3`, let the left endpoint be P, and let the right endpoint Q be
O or D. Start with the two actual moves

```text
Blue (2,k), White (0,k).
```

Both moves are legal. The left `5×k` rectangle has actual Blue prohibited at
its right-end row 2 and White prohibited at its right-end row 0. Retire its
right-end White permission at row 4. The resulting endpoint is exactly
`X=bowob`, so this virtual component is `PX_k`.

Keep the remaining three columns as a single cap. Retire White at row 3 of
the cap's first column; its other first-column permissions are already
absent except for the shared cell at row 4. Thus the cap's left White support
is `{4}`, while X's right White support is `{1,2,3}`. Every cut edge has at
most one virtual White-legal endpoint. Blue permissions are unchanged or
restored, and White permissions are only retired. This proves the safe
comparison after White's reply:

```math
G_{after\ W1}\le PX_k+C_Q.
```

The cap masks in row-major `5×3` coordinates and exact values are:

| Q | Blue mask | White mask | Exact value |
|---|---:|---:|---|
| O | 32054 | 32180 | `0` |
| D | 31798 | 30100 | `−1+*` |

Their permissions, with rows separated by slashes, are respectively
`.bo/.oo/.wo/.oo/ooo` and `.bo/.ob/.ww/.ob/ooo`.

These equalities are verified by independently constructing all legal options
and checking Conway order in both directions. They do not use the general
number-or-number-plus-star premise from the handoff.

Consequently **`PX_k≤0` alone is sufficient for this reply to win against
every subsequent Blue continuation**. Blue is next after W1. For Q=O the
comparison is nonpositive, and for Q=D it is strictly negative. The only
recursive rectangle has width `k=n−3<n`; the cap has fixed size.
For the D-ended cap this particular opening even admits the weaker numerical
hypothesis `PX_k≤1/2`, since then the sum is at most `−1/2+*<0`. This does not
weaken the separate DX requirements in other DD opening cases.

There is also an explicit local response table. In cap coordinates, answer
every local Blue move with White `(2,2)`, except:

| Local Blue move | White reply |
|---|---|
| `(2,2)` | `(4,0)`; this Blue move exists only for Q=O |
| `(4,2)` | `(3,1)` |

Every resulting cap is nonpositive. This covers all ten Blue options of
`C_O` and all nine Blue options of `C_D`. The only reply on the seam is
`(4,0)`, whose additional exterior White restriction lands on the already
retired row 4 permission of the strip. A local Blue move may further prohibit
actual strip Blue moves; restoring those virtual permissions is safe.

If Blue instead moves in the left strip, use the second-player strategy of
`PX_k≤0` to reply in that component. The untouched cap remains nonpositive.
This is an existential conditional strategy, not an algorithm for the still
unproved arbitrary-width target. The fixed White reply `(2,k+2)` from the
earlier twin-square branch is unnecessary for this argument. In particular,
the complete conditional continuation does **not** need the stronger
star-compensated option hypotheses required by that fixed reply.

For P=D this is a finite cap construction conditional on `DX_k≤0`. For P=O
the dependency is the different, one-ended game `OX_k`; replacing it by DX
would illegally remove actual Blue permissions at the other endpoint.

## An actual failure on the ordinary `5×5` board

The preceding conditional strategy does not supply an ordinary-board bridge.
More strongly, its proposed initial White response already fails in an
actual small board, before making any comparison:

```text
Empty 5×5: Blue (2,2), White (0,2), Blue (0,0).
```

After the first two moves the actual masks are `(33408891,33550193)`.
After Blue `(0,0)`, they are `(33408856,33550192)`. White is next and loses.
The search-free response DAG
[`ordinary5_center_bad_reply.json.gz`](round3_corner_certificates/ordinary5_center_bad_reply.json.gz)
has White-first root `[33550192,33408856,0,1]`, 4,682 checkpoints, and 21,950
edges. The checker rebuilds these masks from the empty board and the moves,
then validates complete legal reply coverage and rank descent.

This eliminates the precisely stated candidate “answer Blue `(2,n−3)` by
White `(0,n−3)` for every ordinary odd width `n≥5`.” It is a losing response,
not a counterexample to the empty-board theorem. It also does not rule out
using that response only above a separately proved base range.

## Keeping the cap interaction still requires the correct turn condition

One might avoid the X cut by defining a notched helper `N_k`: on an ordinary
`5×(k+3)` board, make Blue `(2,k)` and White `(0,k),(2,k+2)`, then apply exact
twin-square deletion to the upper-right corner. This is a permission game;
the two White moves describe its restrictions, rather than a claimed
alternating history. Keep every surviving exterior restriction and edge.
An intervening remote Blue move commutes with these moves whenever legal.

For `k=2` the exact live root is `(33391715,33000545)` and **`N_2=0`**.
Independent second-player DAGs in both color orders certify this equality:

| Certificate | First-player root | Checkpoints | Edges |
|---|---|---:|---:|
| `notch2_zero_0.json.gz` | `(33391715,33000545)` | 430 | 1535 |
| `notch2_zero_1.json.gz` | `(33000545,33391715)` | 394 | 1329 |

Nevertheless the Blue `(0,0)` option of `N_2` has exact value `*`, with masks
`(33391680,33000544)`. This is also the actual four-move continuation

```text
B (2,2), W (0,2), B (0,0), W (2,4),
```

after exact twin deletion. Blue is next and wins. Both directions of the
equality to `{0|0}` are independently checked from all legal options.
Therefore a uniform strict target `N_even<0` fails at its first positive
even width, and merely proving `N_even≤0` would not justify the fixed remote
reply. The missing requirement is an appropriate bound on its Blue options,
or a different adaptive reply. The same smallest case has `OX_2=*` and its
Blue `(0,0)` option equal to zero, so adding the residual cap star really does
leave star; it is not an artifact of a loose numerical bound.

## Reproduction and remaining dependencies

Run:

```sh
python3 proofs/construction/research/round3_corner_check.py
```

This replays all three stored DAGs without generation or strategy search,
checks the cap equalities and all 19 specified local responses, checks the
exact star option, and tests 126 endpoint/width embeddings. The latter are
regressions supplementing the symbolic interface argument above.

[`round3_corner_probe.cpp`](round3_corner_probe.cpp) is a separate bounded
discovery program. Its masks, offsets, and star states use an explicit
structured cache key. Its incomplete runs establish no inequalities. In
particular, an `N_4` probe exhausted ten million visits in each starting
color and was inconclusive; no arbitrary-width claim follows from it.

The remaining recursive requirement for the complete D-ended construction
is `DX_even≤0` (and other DD cases still retain their own strictness and
White-first obligations). For the ordinary board, a one-ended boundary
theorem or a construction preserving more favorable interaction is still
needed. The handoff's historical `OX_6>0` statement remains a separate
artifact-mapping gap; none of the counterexamples proved here depends on it.
