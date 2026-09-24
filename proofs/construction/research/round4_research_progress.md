# Fourth continuation: endpoint recursions and a coupled corner candidate

Status: **proved new local reductions, finite marked-position results, and
precisely scoped obstructions**. Neither the auxiliary induction nor the
ordinary five-row bridge is complete. No general odd-rectangle theorem is
claimed. This continues [round three](round3_research_progress.md).

The positive advance is a larger collection of width-decreasing clauses:
marked endpoint caps now return the original ordinary families in several
row-complete cases, and three new paired boundary targets share the same
center-row recursion near an X endpoint. Separately, an actual corner reply
to a central opening survives independent checks without cutting the board.

## Ideas tested and their status

| Idea | Result | What remains |
| --- | --- | --- |
| Absorb a White mark and the next Blue move in a two-, three-, or four-column end cap | Proved row-complete D-ended cap tables and further U/J/X clauses, conditional on smaller original targets | Marks farther from the endpoint and the remaining opening columns |
| Pair each RX/VX/XX bound with its starred comparison | Proved algebra and three common center-row endpoint transitions | Other rows, deeper openings, and independent White-first witnesses |
| Optimize the entire immediate one-column cut at a difficult XX opening | Proved every such comparison at the specified XX7 opening is at least 1; a four-column cap repairs it | A systematic rule choosing sufficient wider interactions |
| Answer a central ordinary-board opening at a corner and retain all edges | Independently proved the resulting M3<0, M5=0, M7≤0 | A symbolic reduction for M at arbitrary width; other first openings |
| Leave a monotone staircase between individually nonpositive 2×2 tiles | Proved impossible for the stated construction at every odd width ≥3 | Multiple interacting paths or different tiles are outside this obstruction |
| Peel two rows while preserving a genuinely empty rectangle | Proved corner-opening obstruction at every odd width ≥3 | A decomposition retaining the cross-seam interaction |
| Replace the grid by perfect-matching, spanning-path, or symmetric convex graph hypotheses | Exactly checked counterexamples to all three proposed generalizations | A proof using the stronger structure of rectangles |

An unclosed search entry is inconclusive. A positive virtual comparison is
not a positive actual board. The statements below distinguish these from
actual finite counterexamples to specified replies or graph conjectures.

## Marked caps now cover more of the White-first DD dependency

Write `F_Q(n,p,t)` for `DQ_n` after an actual White move `(t,p)`, on the
exact domains required by the [central White-first assembly](round2_wf_delayed_phase.md).
The [new cap proof](round4_wf_near_end_caps.md) retains the mark, its neighbor
exclusions, and the physical far endpoint. Let a cap occupy the last w
columns, let `L=n−w`, and put the next Blue move in column L.

For Q=D, w=2,3,4, and every parity-correct legal mark inside that cap, all
legal Blue rows return the following ordinary smaller games:

| Cap width | Outer row | Inner row | Center row |
| --- | --- | --- | --- |
| 2 or 4; L odd | `DU_L+0` | `DJ_L+1/4` | `DD_L+0` |
| 3; L even | `DR_L+0` | `DV_L−1` | `DX_L+0` |

Use L≥3 when odd and L≥2 when even. White is next; every entry is strictly
negative under the original targets and smaller-width DD strictness.
The paired DX targets imply DX<0 but do not give a fixed negative margin.
U/J endpoint-marked caps of widths two and three satisfy the same table.
Three further explicit White replies produce nonpositive comparisons with
Blue next, including a cap of 1/4 absorbed exactly by DR≤−1/4.

On the required X diagonal `F_X(n,n−2,2)`, the new two-column construction
handles all legal Blue rows in the marked column. Its outer-row cap is at
most 1/8 and its inner-row cap is at most −1, giving respectively
`DR_(n−2)+1/8<0` and `DV_(n−2)−1<0`. Together with round three, columns
`c=p` and `c=p−2` are handled on this diagonal.

These are actual symbolic clauses, each with a smaller recursive width and
checked seam permissions. They do **not** replace the whole round-two
White-first assembly by an induction using only the original margins.
The intervening X column, distant marks, other openings, and the quantitative
dependencies of that assembly remain. Its stronger DD margin is not proved
or propagated merely by these new caps.

## A common recursion for paired RX, VX and XX bounds

Define `T_q(G)` to mean both `G≤q` and `G+*≤q`. The
[short-game algebra](round4_star_bounds.md) proves that both inequalities
are then strict, that an extra star preserves T, and that weak numerical
bounds can be added to it. These rules do not use a classification of Col
values. Strict negativity alone does not in general absorb a star.

Consider the still-unproved targets

```math
T_1(RX_k),\qquad T_2(VX_k),\qquad T_1(XX_k)
\quad(k\ge3\text{ odd}).
```

The [width-three bases](round4_pair_bases.md) are independently proved by
six direct ordinary/starred certificates. These also cover the auxiliary
star opening, so no same-width strictness is assumed at the finite bases.

For a center-row Blue opening near the X endpoint of `(P,X)_n`, P in
{R,V,X}, the [exact endpoint caps](round4_dx_progress.md) give:

| Distance from X endpoint | Minimum odd width | Upper bound after Blue |
| --- | --- | --- |
| 1 | 5 | `(P,X)_(n−2)` |
| 2 | 5 | `(P,D)_(n−3)−1` |
| 3 | 7 | `(P,X)_(n−4)+*` |

The distance-two child is DR, DV or DX up to horizontal reflection. The
original bounds suffice with a numerical gap. The other two clauses use
the smaller paired target, unchanged or with its star toggled. White is
next, so the strict conclusion is essential. All eighteen combinations
of parent family, distance and external star parity are recorded in a
[conditional ledger](round4_star_bound_ledger.json).

At the diagnostic opening `XX_7` after Blue `(2,3)`, all sixteen strongest
safe one-column supports give virtual value at least 1; the best is exactly
`XX_3+XX_3=1`. Yet retaining four columns gives the actual upper bound
`XX_3+*=1/2+*<1`. This proves both the narrow-cut obstruction and its repair.
It does not refute the actual XX target.

The auxiliary star itself is a possible Blue opening. Taking it leaves the
same-width unstarred comparison with White next. A sound proof must first
establish that unstarred strict comparison independently, then prove the
starred inequality. The rank `(width,stage)` decreases if stage 0 is the
unstarred strict assertion and stage 1 the starred assertion. Stage 0 may
not call its same-width paired target. Other rows, deep interior openings,
and the White-first witness remain explicit missing clauses.

## A surviving ordinary-board route keeps the two moves coupled

Let M_n be the actual empty 5×n position after
`Blue (2,(n−1)/2), White (0,0)`, for odd n. Blue is next. The proposal is
`M_n≤0`; it answers the central-opening class only.

The [bridge investigation](round4_bridge_ideas.md) independently proves

```math
M_3<0,\qquad M_5=0,\qquad M_7\le0.
```

On 5×5, all White replies are covered by symmetry and certificates: the
four corners are the only winning replies to central Blue. The successful
corner strategy is adaptive, covering all later Blue moves. The width-seven
certificate checks 447,623 response checkpoints and 3,306,842 edges using
actual coordinate-set moves and a strictly decreasing live-cell rank.
Its opposite-start classification remains Unknown; neither equality nor
strictness is claimed for M7.

These finite results are specific strategy facts, not a proof by
extrapolation. The next constructive question is whether coupled marks can
move through a finite state family until a smaller M or boundary game
remains. Replacing M by the previously unsuitable uniform one-ended target
would discard the interaction this test deliberately preserves.

## Two infinite obstructions and three finite counterexamples

The bridge note proves that a particular induced top-to-bottom staircase,
with arbitrary seam-safe path White permissions and independently phased
nonpositive 2×2 square tiles on its two sides, never gives a nonpositive
comparison on an odd-width five-row board. Adjacent White-legal path cells
are allowed, so this goes beyond the earlier independent-support obstruction.
An elementary supporting lemma proves that an odd path with full Blue
support and alternating White support is strictly positive from length five
onward. The proof is a move-count strategy, not extrapolated computation.

It also proves that after a lower-corner Blue opening, peeling the bottom
two rows while retaining the rest as a genuinely empty rectangle leaves a
comparison cap at least 1 after any eligible White reply, for every odd
width ≥3. For height five the empty upper 3×n component is zero; that fixed
seam cannot supply the desired nonpositive total. This explicitly respects
the scope of the empty-three-row theorem.

Finally, [three small exact-star counterexamples](round4_graph_shortcuts.md)
eliminate broader shortcuts: a six-vertex bipartite tree with a perfect
matching; a ten-vertex even bipartite graph with a Hamiltonian path; and a
3×5 grid with its four corners removed. The last shape is row/column convex,
has odd row/column lengths and both reflection axes, and both fixed paths
have value zero. Its own value is star. None is an ordinary-rectangle
counterexample, and the clipped shape is not asserted to recover a missing
historical artifact mapping.

## Remaining dependencies and next discriminating tests

The [six-case DD audit](five_row_boundary_induction.md) remains authoritative
for endpoint openings, empty sides, width-one intersections and strictness.
The following tasks still separate these local advances from the theorem:

1. Close DX and the returned paired RX/VX/XX families over every opening,
   with separate unstarred White-first witnesses. Extend the proven endpoint
   clauses toward interior moves; do not merely assume a finite-width pattern.
2. Complete the reachable marked-state system for White-first DD. A focused
   next test is a legal White reply or a wider retained interaction for the
   adjacent inner-row X opening, where the simple cap leaves an unpaid
   positive contribution. Track the exact endpoint supports of every child.
3. Try a width-decreasing transition for coupled M states, allowing a moving
   mark or more than one interacting retained region. Even a full M theorem
   would cover only central openings; the ordinary-board bridge must cover
   all openings.
4. For general odd rectangles, seek a construction using actual rectangular
   interfaces or dynamic exact modules. The graph shortcuts above cannot
   justify ignoring additional edges or replacing notched regions by rectangles.

Every recursive transition must decrease width or a stated well-founded
rank. The fixed DX≤L route remains disproved and is not used. Bounded failures
remain inconclusive. Literal all-positive odd area still needs the `1×1=*`
exception; no arbitrary-height theorem is claimed.

## Verification and provenance

Run the independent checkers, without their discovery searches:

```sh
python3 proofs/construction/research/round4_verify.py
```

All six checkers pass. They replay 99 DAGs (98 new and one explicitly reused),
with 529,093 checkpoints and 3,672,781 response edges. The verification record
lists outputs, certificate counts, reused artifacts, and hashes.
Numerical DAGs check every universal move and supplied response;
separate exact-order checks handle the algebra and small graph examples.
Geometry sweeps are regression tests; the written local support proofs and
symbolic obstructions supply their all-width scope.

All newly used roots are explicitly mapped in the component manifests.
Earlier missing `T_middle1`, compatible Z7, historical five-row/L and other
mappings remain listed in the [provenance audit](five_row_certificate_provenance.md).
These provenance gaps have not become mathematical refutations, and no
historical mapping is claimed recovered by a newly generated artifact.
