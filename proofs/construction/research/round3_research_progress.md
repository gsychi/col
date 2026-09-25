# Third continuation: wider caps recover useful induction bounds

Status: **proved new local reductions, complete conditional continuations,
and precisely scoped obstructions**. There is still no closed mutually
recursive auxiliary induction and no full five-row or general odd-rectangle
theorem. This continues
[round2_research_progress.md](round2_research_progress.md).

The most useful advance in this round is positive: retaining a bounded wider
region can recover a strictly negative comparison where every one-column
permission cut loses the required margin. The new constructions return to
smaller named boundary games with explicit turn and width obligations.

## A four-column repair in a required White-first phase

The central White-first DD assembly from round two requires marked states
`F_X(k,p,t)`, meaning DX after an actual White move `(t,p)`. For every even
`k≥6`, the parameters `p=k−2,t=2` belong to its required domain.

After Blue opens in column `k−4`, retain the last four columns, including
the preplayed White stone and the X endpoint. Independently certified caps
give the following [all-width local reduction](round3_wf_wider_caps.md):

| Blue row | Upper bound after Blue | Recursive width | Required ordinary target |
| --- | --- | --- | --- |
| 0 or 4 | `DR_(k−4)` | positive even `k−4<k` | `DR≤−1/4` |
| 1 or 3 | `DV_(k−4)−1` | same | `DV≤1/2` |
| 2 | `DX_(k−4)` | same | `DX≤0` and `DX+*≤0`, hence `DX<0` |

White is next, and all three bounds are strictly negative under the user's
original sufficient targets. No strengthened DD margin or arbitrary-width
phase bound is used in this step. It settles every row in this opening
column of this infinite subfamily, conditional only on the smaller ordinary
auxiliaries.

The smallest case demonstrates exactly what the wider cap repairs. In
`F_X(6,4,2)`, after Blue `(2,2)`, **every** immediate cut into the two left
columns, the opening column, and the three right columns gives a nonnegative
virtual game. All 16 possible separator White supports and their strongest
allowed side permissions are covered by independently certified lower
bounds. The best such virtual game is exactly zero, insufficient with White
next. In contrast, the four-column construction gives an upper bound
`DX_2=−1` for the actual position.

Thus this is both a complete obstruction to that particular narrow cut and
a constructive repair. The other columns and other required marked families
still need reductions. Directly cutting marked strips can create ordered
endpoint pairs such as marked XX; the six D-anchored phases alone do not
close under that operation.

## Better three-column reductions for DX

For Blue openings in column 2 of `(D,Q)_n`, retaining the first three columns
together gives exact cap values

```text
(row, new endpoint, cap):
(0,U,0), (0,R,−1), (1,V,−2), (1,J,1/2), (2,D,0), (2,X,−1).
```

The comparison is `cap + (S,Q)_(n−3)`, with White next and strictly smaller
recursive width. It includes width-one endpoint intersections. The
[anchored-cap proof](round3_dx_progress.md) checks both permission inclusions
and every White seam.

In particular, the sufficient new targets

```math
RX_k<1,\qquad VX_k<2,\qquad XX_k<1\quad(k\ge3\text{ odd})
```

would handle all rows in column 2 of even-width DX for `n≥6`. These are
**unproved targets for that opening class**, not a full DX induction. They
still leave other columns and the separate White-first DX requirement.

The alternative explicit White replies produce an R cap of value `−1/2`
and put Blue next; those would require `RX≤1/2`, a stronger numerical target.
The no-reply cap therefore has a useful advantage despite needing strictness.
Raw observations about RX5 are kept experimental and do not establish an
arbitrary-width bound.

## The corner continuation now covers all subsequent Blue moves conditionally

Previously, the corner dialogue proved one prescribed sequence and left its
other continuations open. The [complete cap construction](round3_corner_dialogue.md)
now handles them by an adaptive component strategy.

Start at `(P,Q)_n`, where `Q` is D or neutral O, and put `k=n−3`. After
Blue `(2,k)` and White `(0,k)`, a safe X interface gives

```math
G\le PX_k+C_Q,\qquad C_O=0,\quad C_D=-1+*.
```

Blue is next. Therefore `PX_k≤0` alone suffices, with no star-compensated
option hypothesis and no appeal to the Col number-or-number-plus-star
classification. Every local cap Blue move has a checked reply; if Blue
moves in the strip, use its conditional second-player strategy. The
recursive width is `n−3<n`.

For P=D this is a complete conditional continuation using `DX_even≤0`.
For P=O it requires the different one-ended game `OX_even≤0`, which remains
unavailable as a uniform bridge target. Indeed the initial ordinary-board
reply itself fails at width five: after `B(2,2), W(0,2)`, Blue `(0,0)` leaves
White losing. This is an independently certified **actual** continuation,
not a conclusion from a positive upper bound. It refutes the claim that
this reply works at every odd width beginning at five, but permits other replies or a
construction with a separately handled base range.

An interaction-preserving notched helper does not automatically fix the
turn issue: `N_2=0`, while its relevant Blue option is star. A nonpositive
parent is insufficient to justify that fixed subsequent White reply.

## What has been eliminated, with exact scope

Three further structural results narrow the next search:

1. **Three-column end caps still cannot force exterior mirroring in DX.**
   For every even `n≥8`, a shifted five-move checkerboard sequence forces
   exact remaining value 2 if White answers by horizontal or half-turn
   reflection, even choosing adaptively. The exact end caps are each 1;
   the conjugate middle cancels. This extends the previous two-column
   obstruction. It does not determine the value of DX itself.
2. **Three central columns cannot contain every repair.** For height 3 or 5
   and every odd width at least five, a verified counterstrategy defeats
   the policy that mirrors all exterior openings and answers cap openings
   only inside the cap while preserving the exterior mirror implication.
   The [central-cap theorem](round3_central_controller.md) allows every such
   safe local reply, not merely a selected reply list. A five-column
   central controller remains Unknown at its recorded budget.
3. **Static independent White supports have very limited scope.** For a
   full-Blue odd rectangle, any independent White support other than the
   majority checkerboard gives a strictly positive virtual game. Even the
   majority support cannot be nonpositive when the area is 1 modulo 4.
   Moreover, the particular even shared-block composition theorem from
   round two can tile an odd rectangle only in the `1×3` and `3×1` cases.
   The [proof](round3_independent_support.md) applies at arbitrary dimensions.
   Exact module deletion remains useful after actual play, and larger
   zero contracts with retained interactions are not excluded.

None of these obstructions is a counterexample to a target empty rectangle.
The ordinary 5×5 and DD7 counterexamples in the component notes instead
refute specific White replies; their actual remaining positions and turn
orders are independently checked.

## Remaining induction requirements

| Part of the proof | Improvement this round | Still required |
| --- | --- | --- |
| DX Blue-first | Better anchored three-column bounds | All opening columns; a closed set of bounds on returned families |
| DX strict negativity | Reactive mirror policies more sharply excluded | A separate White-first win, or another proof of the required strict comparison |
| White-first DD | One required marked-X opening class now reduces through four-column caps using the original targets | The rest of the marked-state system and its quantitative ordinary hypotheses |
| Delayed corner branch | Every continuation is covered if the smaller PX game is nonpositive | An ordinary-board replacement for the unavailable one-ended target and other initial openings |
| Arbitrary odd height | Static support/partition obstructions proved in general | A construction retaining the necessary interactions while covering every move |

The next constructive target is a finite collection of three- and four-column
contracts covering the remaining marked-state openings. Its assertions must
include the ordered endpoint pairs actually returned, with their exact
position domains and turn requirements. Another option is a moving repair
region permitting proactive replies to exterior moves; merely enlarging the
now-disproved three-column reactive controller's search budget cannot help.

Every proposed call must decrease width or an explicit live-state rank.
The existing DD six-case table, boundary cases and strictness audit remain in
[five_row_boundary_induction.md](five_row_boundary_induction.md). No finite
checks here establish an infinite inequality by extrapolation.

## Checks and artifact status

Run all five new independent checkers without discovery:

```sh
python3 proofs/construction/research/round3_verify.py
```

The numerical package has 88 stored DAGs, 15,519 checkpoints and 59,323 response
edges. Two additional central-policy counterstrategy DAGs contain 274 nodes
and 491 edges. Exact short-game comparisons check the corner caps and
independent-support formulas separately. Geometry sweeps regress the
implementations; the written symbolic constructions establish their scope.

`round3_verification.json` records commands, outputs and hashes. Newly used
roots are mapped in the component notes and manifests. The inherited missing
`T_middle1`, compatible Z7, historical five-row/L and other inventory mappings
listed in [the provenance audit](five_row_certificate_provenance.md) have not
been recovered. Those artifact gaps remain distinct from mathematical
obstructions. The fixed `DX≤L` route remains disproved and is not used here.

All raw probes and bounded controller searches are explicitly experimental.
Unknown stays Unknown. The literal all-positive-odd-area target still needs
the `1×1=*` exception; neither the five-row nor general theorem is claimed.
