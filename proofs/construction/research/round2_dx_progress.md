# Expanded DX interfaces: exact cancellation families and remaining transitions

Status: **partial progress, not a closed auxiliary induction**. This continues
[the first DX study](dx_boundary_obstruction.md) and the
[conditional DD induction](five_row_boundary_induction.md). It proves an
all-even cancellation family, records parameterized DX reductions, and certifies
selected finite values needed to avoid misleading sign assumptions in an
expanded alphabet. No conclusion about arbitrary empty odd-by-odd boards is
claimed.

## An exact unbounded helper family

For any permission pattern `P`, let `conjugate(P)` exchange `b` and `w`
and fix `o` and `.`. For positive even `n`,

```math
(P,\overline P)_n=0,
```

where the bar here denotes **color conjugation**, not vertical reflection.

Proof: horizontal reflection is a fixed-point-free graph automorphism. It
maps the initial Blue permission set onto the initial White permission set.
After each first-player move, the second player plays its reflection. The
paired occupied cells carry opposite colors. If that reply had an adjacent
same-color stone, reflecting this earlier stone would give a same-color
neighbor of the first player's just-played cell, contradicting legality.
The reply is unoccupied because completed pairs are always occupied together,
and it has the required initial permission by the stated equality of masks.
Thus the second player can always reply, regardless of their color. This is
an exact pairing proof for every even width; no seam is cut.

In particular `J=owobo` has color conjugate `obowo=reverse(J)`. Therefore

```math
(J,\operatorname{reverse}(J))_{2m}=0.
```

Also

```math
JJ_{2m}=0.
```

For the latter use the half-turn instead of horizontal reflection: it is
fixed-point-free at even width and maps each `J` endpoint's Blue permissions
onto the opposite endpoint's White permissions. These are two distinct
relative endpoint orientations; both have now been proved zero. This helper
requires no recursive hypothesis and may be used at any width.

## Complete no-reply DX cut table

Let `DX_n` have D on the left and X on the right, with positive even n.
Both D and X are vertically symmetric, so normalize a Blue opening to
`r in {0,1,2}`. For an interior opening put `a=c`, `b=n-c-1`. Each positive
side is strictly narrower than n, and a,b have **opposite parity**.

Each row below is an unconditional geometric comparison, immediately after
Blue's opening with **White next**. The separator values are exact. The
near-side endpoint is the same on both sides, so the right term is written
up to horizontal reflection.

| Opening row | Chosen new endpoint | Separator | Post-Blue upper bound |
| --- | --- | --- | --- |
| 0 | U | `.wbob` = 0 | `DU_a + UX_b` |
| 0 | R | `..obo` = 0 | `DR_a + RX_b` |
| 1 | V | `w.wbo` = -3/2 | `DV_a - 3/2 + VX_b` |
| 1 | J | `...ob` = 1/2 | `DJ_a + 1/2 + JX_b` |
| 2 | D | `bw.wb` = 0 | `DD_a + DX_b` |
| 2 | X | `o...o` = 0 | `DX_a + XX_b` |

The proof is the width-independent local support argument already checked
in [the complete one-column catalogue](dx_interface_contracts.json): Blue
loses precisely row r in each adjacent side column; the chosen endpoint's
sole Blue-forbidden row is r; its White support is disjoint from the
separator White support. The far D and X restrictions are retained.
At a width-one side, intersect near and far masks. This preserves both
inclusions and can only remove White seam support. **To win with White
next, the resulting sum must be negative, or a separate White move must be
proved.**

Endpoint openings require different separator values:

| Opening end | Row | New side endpoint | Separator | Post-Blue bound |
| --- | --- | --- | --- | --- |
| D | 0 | U | `...bb` = 1 | `1 + UX_(n-1)` |
| D | 0 | R | `..wbo` = -1/2 | `-1/2 + RX_(n-1)` |
| D | 1 | V | `w.wbo` = -3/2 | `-3/2 + VX_(n-1)` |
| D | 1 | J | `...bb` = 1 | `1 + JX_(n-1)` |
| X | 0 | U | `.w.ob` = -1/2 | `DU_(n-1) - 1/2` |
| X | 0 | R | `..wbb` = 0 | `DR_(n-1)` |
| X | 1 | V | `..wbb` = 0 | `DV_(n-1)` |
| X | 1 | J | `...ob` = 1/2 | `DJ_(n-1) + 1/2` |

There is no legal row-2 Blue opening at either endpoint. The six distinct
endpoint separator values are independently checked in
[round2_dx_check.py](round2_dx_check.py). The geometric formulas follow by
intersecting the neutral-column post-opening permissions with the inherited
endpoint pattern, then restricting White to the complement of the chosen
side endpoint's support.

## Constructive portions of a possible enlarged induction

The tables prove the following **conditional** portions of DX's Blue-first
step. They are not arbitrary-width assertions about the new helper states.

* Center openings with odd c already close using the original framework:
  `DD_a<=0` at positive odd a and `DX_b<0` at positive even b give a negative
  sum. The case a=1 is safe because `DD_1=0` is added to a strict DX bound.
* Outer openings at the X endpoint close directly from `DU_(n-1)<0`, with
  an additional `-1/2` separator margin.
* Outer interior openings with odd c would close upon adding
  `UX_even<=0`, since `DU_odd<0` supplies strictness.
* Row-1 interior openings with even c and row-1 openings at the D endpoint
  would close upon adding `VX_odd<=1/2`; together with `DV_even<=1/2`, the
  interior bound is at most `-1/2`.

The unresolved classes include outer and center interior openings with
even c, outer openings at the D end, and the row-1 odd-column/X-end cases.
The latter show why a stronger DJ target such as `DJ_odd<-1/2` would be
useful, subject to its width-one exception and control of `JX_even`.
The current `DJ_odd<-1/4` target does not automatically close these rows.
Every recursive side in these proposals has smaller width; an induction
must also prove each newly introduced family's own opening and strictness
obligations. The exact J cancellation families above need no such induction.

## A concrete invariant for a possible adaptive mirror controller

Let `tau` be a fixed-point-free involutive graph automorphism, and define

```math
\Delta(A,B)=\tau(A)\setminus B.
```

**Mirror invariant lemma.** If `Delta` is empty and Blue is next, White wins
by replying at `tau(v)` after every Blue move v. More generally, whenever
Blue plays a move v for which `tau(v)` is White-legal, that mirrored reply
is legal and changes the defect set exactly to

```math
\Delta' = \Delta\setminus \bigl(N[\tau(v)]\cup\{v\}\bigr).
```

Proof: after the pair of moves,

```math
A'=A\setminus N[v]\setminus\{\tau(v)\},\qquad
B'=B\setminus\{v\}\setminus N[\tau(v)].
```

Apply tau to the first equality and subtract the second set. The same
set `N[tau(v)] union {v}` has been removed on both sides, yielding the
displayed formula. Fixed-point-freeness ensures Blue's new stone has not
occupied the proposed White reply. No additional assumption about symmetric
occupancy is required; legality sets already encode it. ∎

For horizontal reflection of `DX_even`, the initial defect set consists of
exactly four endpoint cells: rows 1,3 at D and rows 0,4 at X. A normal mirrored
reply cannot create new defects. Thus only Blue moves whose reflected cell
belongs to this finite defect set require special treatment. This gives a
concrete state variable for adaptive research, beyond recording scalar game
bounds alone.

A special reply u can introduce new defects only in `N[u] union {v}`:

```math
\Delta_{\rm after\ B(v),W(u)}
\subseteq \Delta_{\rm before}\cup N[u]\cup\{v\}.
```

This follows because those are the only cells newly removed from White's
permission set; Blue's permission removals cannot introduce a defect.
Consequently an inward reply can expand the defect support by one column,
which a bounded controller must explicitly handle. A proposed controller
cannot silently assume its cap remains fixed.

This is a proved invariant, **not a completed controller**. A usable finite
protocol still needs to cover every defect move, retain legal replies after
all possible ordinary mirrored bulk moves, and ensure that special
transitions either decrease a finite local rank or close an end layer and
decrease width. Once defects are empty the mirror lemma finishes the game.
The White-first obligation for strict negativity remains separate. Previous
paired-end controller searches in the handoff should be compared against
these exact invariants before repeating their palettes.

## Certified finite interface costs

The following exact values have new independently checked response-DAG
certificates, with both game-order inequalities checked separately:

| Family | Exact finite values |
| --- | --- |
| UX | `UX_2=-1/4`, `UX_3=1` |
| VX | `VX_1=1/2`, `VX_2=2`, `VX_3=0` |
| XX | `XX_1=1`, `XX_2=1`, `XX_3=1/2` |
| RX | `RX_3=1/2` |
| DD | `DD_2=1` |
| DV | `DV_1=2`, `DV_3=1` |
| DX | `DX_1=1`, `DX_2=-1` |
| Checkerboard caps | `(D,wbwbw)_2=0`, `(bwbwb,X)_2=2` |

Additionally `RX_1=1/2+*` is checked by direct recursive short-game order.
Thus opposite-parity costs cannot be replaced by blanket nonpositive bounds
on all expanded pair families. For example, the apparently promising
`DR_even + RX_odd` route encounters an exact zero/star margin at small
widths, not an automatic strict negative bound.

A precise finite warning is supplied by `DX_4` opened at `(2,2)`. Its
side widths are 2 and 1. Using any of the named D/X center interfaces and
no reply gives respectively:

| Near endpoints | Exact virtual sum |
| --- | --- |
| D,D | `DD_2 + DX_1 = 2` |
| X,X | `DX_2 + XX_1 = 0` |
| D,X | `DD_2 + 2 + XX_1 = 4` |
| X,D | `DX_2 + 2 + DX_1 = 2` |

The D,D same-column White replies have separator 1 and virtual sum 3;
the X,X replies have separator star and virtual sum star. Therefore none
of these particular named-interface cuts certifies this root, even when
all endpoint pairs are added. This is **only a finite construction-class
counterexample**: a base case can bypass it, a different reply or interface
can help, and the actual DX game is not shown positive.

## Reproduction and discovery status

```sh
python3 proofs/construction/research/round2_dx_check.py
```

Recorded result:

```text
Verified 32 bound DAGs: 3664 checkpoints, 12679 checked response edges.
Verified six local caps and XR_1 = 1/2+star by independent short-game order.
Verified J conjugacy identity; all-even pairing maps proved symbolically in round2_dx_progress.md.
Verified 52 assembly branches of the all-even mirror trap (finite regression of symbolic proof).
```

The bound certificates are in [round2_dx_certificates](round2_dx_certificates/).
`--generate` regenerates them using minimax, then checks them using the
independent coordinate-set response-DAG verifier. Default mode performs no
minimax search for these bounds. Root masks and claimed values are bound
explicitly in the checker; width-one roots intersect both endpoint masks.

[round2_dx_discovery.py](round2_dx_discovery.py) and its width-1/2/3 JSON
outputs explore all 55 unordered pairs of the ten **oriented** named masks.
[round2_dx_local_search.py](round2_dx_local_search.py) explores all 16
White supports for a new row-0 endpoint, at selected small widths.
Those larger tables remain **experimental** except for the explicitly
certified subset above. [round2_dx_screen.cpp](round2_dx_screen.cpp) is a
bounded outcome screen; budget exhaustion means Unknown. No finite table
is used to establish an infinite bound.

The follow-up [mirror study](round2_dx_mirror.md) proves an infinite
obstruction to reactive horizontal/half-turn mirroring, using the two exact
checkerboard caps and the conjugate-end zero theorem. It also defines a
finite adversarial-port interface problem whose successful solution would
give a uniform DX upper bound, and independently verifies the minimum of
two proactive exceptions for a particular width-four horizontal controller.
