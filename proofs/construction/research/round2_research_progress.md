# Second continuation: general graph reductions and the five-row frontier

Status: **proved reductions and obstructions, with conditional induction
interfaces**. Neither the five-row theorem nor the general odd-rectangle
theorem is proved here. This continues the
[first boundary-induction audit](five_row_boundary_induction.md) and the
[research handoff](col_research_handoff.md).

The intended broad target needs a scope exception: the literal assertion
that every positive odd-area empty rectangle is zero includes `1×1=*`.
The research below concerns nontrivial odd rectangles; statements about
arbitrary heights specify their hypotheses. One-dimensional boards are a
separate family. The accepted empty `3×n` theorem and the previously identified
certificate-mapping gaps remain as recorded in the first audit.

## A positive reduction that applies beyond height five

The [shared-twin module theorem](round2_height_twin_modules.md) is an exact
identity for arbitrary finite Col permission graphs. If I is an even,
nonempty independent set of shared cells with identical live neighborhood H,
and

```math
\max\{\alpha(H\cap A),\alpha(H\cap B)\}\le |I|,
```

then `G=G−(I∪H)`, retaining all outside permissions and interactions. Here
A and B are the Blue and White legal sets. The proof gives both game-order
inequalities, so the identity can be used inside sums with other games.
The simpler graph condition `α(H)≤|I|` is sufficient.

On a rectangular grid, any two nonadjacent shared cells with identical live
neighborhoods satisfy the condition: their common neighborhood has at most
two vertices. Thus this extends the handoff's shared-leaf deletion to a
four-cycle and other grid configurations. It strictly decreases live area.
Independent Conway-order checks cover 648 finite instances with arbitrary
outside permissions; the all-graph proof is symbolic.

There is a concrete [corner application](round2_height_applications.md).
On a five-row strip, two specified White replies, with an intervening Blue
move, create shared twins and delete an upper-right `3×3` corner exactly.
The remaining bottom cap has value star. Reducing that cap's White support
without changing its value gives the useful transition

```math
G_{\text{after White's second reply}}
  \le B_z(PX_{n-3})+*.
```

Blue is next, so this branch asks for a nonpositive bound on the entire sum.
Its width drops by three. For a DD input, the existing paired DX targets
discharge this branch conditional on the number-or-number-plus-star property
for the relevant Col options, explicitly discussed in the application note.
For an ordinary empty input, P is neutral and the output is a **one-ended X**
game. Those are different obligations. All other intervening Blue moves
still require responses; the local dialogue is not yet a complete strategy.

The interface improvement is substantive. A cap with the same scalar star
value but larger White support forces a new endpoint `Y=bowbb`; the natural
uniform leaf bound for that alternative is false already at `DY_2=1/2`.
Thus scalar values alone cannot select useful recursive interfaces.

## DX: a proved infinite obstruction and a finite controller target

The [DX study](round2_dx_progress.md) supplies a full transfer table for
interior and endpoint openings, including empty sides, and checks small
expanded-family values. It also proves that a strip with color-conjugate
endpoint masks has value zero at every even width, by horizontal pairing.
In particular `JJ_even=0` by half-turn pairing and
`J reverse(J)_even=0` by horizontal pairing.

The strongest new obstruction is an actual-play theorem, not an upper-bound
failure. For every even `n≥6`, five Blue moves in columns 2 and `n−3` defeat
any policy that answers those moves by horizontal or half-turn reflection,
even choosing between them adaptively. The remaining exact game is

```math
(D,C)_2+(C,\overline C)_{n-6}+(\overline C,X)_2=0+0+2,
```

where `C=wbwbw` and `Cbar=bwbwb`. The width-six middle is empty. Blue is next
and wins this continuation. Both finite cap identities are independently
certified. See the [mirror theorem](round2_dx_mirror.md) for the complete legal
sequence and its scope.

This eliminates “mirror whenever legal, repair only when blocked,” as well
as controllers forcing such replies outside the outermost two columns at
each end. It does **not** determine the sign of DX. White can choose a
proactive different reply before the trap is complete.

At width four, independent controller DAGs prove that the specified horizontal
policy needs exactly two proactive exceptions. A new finite adversarial-port
controller problem, with an explicit descending rank, would prove
`DX_n≤0` for all sufficiently large even widths if solved positively.
Width-three horizontal caps remain Unknown at the recorded three-million-
state limit. The abstract search has no independent certificate yet, and
strict negativity still needs a separate White-first witness even after a
successful nonpositive controller.

The old fixed comparison `DX≤L` remains unusable: the established large-width
L obstruction is unchanged. No small-width dyadic extrapolation is used here.

## White-first DD: a complete conditional assembly, not closure

The [delayed-phase note](round2_wf_delayed_phase.md) accounts for every Blue
reply after White opens at the global center column of DD. White uses row 2
when that column index is even and row 1 when it is odd. The argument has
explicit contracts for endpoint columns, adjacent columns, interior cuts,
and Blue in the same column as the initial White stone.

New two-column D-end caps have values `−1`, `−1+*`, and `−1`; these repair
the previous width-one strictness and star difficulties at the edge.
Every recursive call has strictly smaller width. The proof explicitly
distinguishes a strict negative bound with White next from a nonpositive
bound with Blue next.

The cost is an additional marked-strip family `F_Q(k,p,t)`: DQ after an actual
White move `(t,p)`. This keeps the initial stone's interior exclusions rather
than pretending the residual strip is an empty rectangle. The required
domain is parity-sensitive and is narrower for X; consult the table in the
phase note. The phase position parameter has not been reduced to a finite
closed boundary-state system.

The conditional assembly needs strengthened ordinary bounds:

```math
DR_{even}\le-\tfrac12,\qquad DV_{even}\le0,
\qquad DX_{even}\le0,\quad DX_{even}+*\le0;
```

```math
DU_k,DD_k,DJ_k<-\tfrac12\quad(k\ge3\text{ odd}),
```

as well as the specified phase bounds `F_D,F_U,F_J,F_R,F_X≤0` and `F_V≤1`.
These are **unproved arbitrary-width hypotheses**. The resulting White-first
DD win does not itself propagate the stronger inequality `DD<-1/2` used
among the hypotheses. Thus smaller recursive widths alone do not make this
a closed induction.

A simpler corner-marked phase is independently disproved:
`E_X^0(4)=1/2`. The refined central domain avoids this example. Optimized
finite discovery also exposed an unnecessary X-domain extension; the phase
note narrows X to the parameters that actually arise from legal DD openings.
Those raw search observations are kept separate from certified cap values.

## What the empty-board bridge and arbitrary heights still need

The [bridge support theorem](round2_bridge_support.md) proves a sharp geometric
restriction. After exactly one Blue opening, any number of White moves and
admissible upper comparisons cannot produce a full-height, two-ended shared-
interior rectangle of width at least three if each end requires a White-only
cell. This includes all pairs from the original six letters. White-only
support can only come from neighbors of the one Blue stone; width three
would put that occupied stone in a supposedly shared interior column.

Consequently, solving DD and the original two-ended auxiliaries would still
leave an empty-board bridge. A bounded local step must retain one-ended
states, interior exclusions, another Blue move, or another geometry. The
corner dialogue above demonstrates how an additional Blue move can help,
but does not cover every continuation.

For variable height, the [reflection obstruction](round2_height_reflection_obstruction.md)
also rules out a specific broad candidate: two conjugate full wings around
a one-column axis with safe White seams. After at most t moves by each
player, its virtual game is positive whenever the height exceeds `10t`.
This excludes a bounded-round version of that particular construction
uniformly over height. It says nothing about positivity of the actual board
or about other geometries.

## Current dependency map

| Obligation | What is established | What remains |
| --- | --- | --- |
| DD after Blue opens | Six-case reduction, corrected endpoints and empty sides, independent small bases | Uniform auxiliary inequalities supplying the required strictness |
| DX at even width | Expanded transfer table, conjugate-end zeros, exact mirror-policy obstructions | A complete proactive controller or another recursive construction; separate White-first win |
| DD with White first | Complete conditional central-phase assembly and checked local caps | Phase closure and the strengthened ordinary bounds |
| Ordinary empty `5×odd` | Precise support restriction and a delayed corner reduction branch | Every intervening Blue move and the one-ended-X obligations |
| General nontrivial odd rectangles | Exact module deletion for arbitrary graphs; scoped height obstruction | A covering construction that controls all moves at arbitrary height |

The next focused target is to complete either the proactive DX controller
or the corner dialogue's missing Blue branches. Both retain interactions
that the disproved fixed-separator and reactive-mirror approaches discard.
Any resulting induction must output the same assertions it assumes and
decrease width or an explicit live-state rank on every call.

## Verification, discovery, and provenance

Run all seven new independent checkers from the repository root:

```sh
python3 proofs/construction/research/round2_verify.py
```

The generated `round2_verification.json` records exact commands, outputs and
hashes of checked artifacts. All seven checks pass: 85 numerical DAGs contain
24,947 checkpoints and 108,194 response edges; five separate mirror-policy
DAGs contain 12,756 states and 38,505 transitions. Numerical DAG checking does not run the discovery
search. Controller checking separately verifies every quantified reply and
the terminal mirror invariants. Small geometry regressions support the
implementations; the parameterized theorems above use their written symbolic
proofs.

The [first provenance audit](five_row_certificate_provenance.md) remains the
mapping for inherited artifacts. Missing later `T_middle1`, seam-compatible
`Z7`, historical inventory mappings, and five-row/L manifests have not been
recovered by this round. Those are provenance gaps, not counterexamples to
the supplied mathematical arguments. Newly used exact roots are mapped by
the new checker case tables and the White-first certificate manifest.

`round2_prepare_raw_solver.py` makes an isolated copy of the existing Rust
solver with a state budget and a raw-permission entry point; it does not
edit production sources. Its JSON probes are **finite discovery**, not
independent certificates. A disjoint `ob` path encodes `+1/2`, and a disjoint
shared cell encodes star in the offset probe. Reference DX2/DD3 outcomes
match independently certified roots. The probes support several small
strengthened bounds, including the finite observation `DR6=−1/2`, but do
not establish any arbitrary-width claim. Unknown budget results remain
Unknown. The wider bulk-tile probe likewise supplied no conclusion.
