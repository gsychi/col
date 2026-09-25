# A star-stable XX subsystem and a repaired pair-bound obstruction

Status: **proved local induction clauses and a proved obstruction to an
exhaustive one-column comparison class**. No arbitrary-width XX bound or DX
induction is claimed. These results extend the
[anchored DX caps](round3_dx_progress.md), whose column-2 reductions suggest
the sufficient targets `RX_odd<1`, `VX_odd<2`, and `XX_odd<1` for odd widths
at least three.

## Three distinct routes and the chosen bounded test

1. **Endpoint absorption.** Keep a short cap attached to a physical endpoint,
   rather than separating its finite interactions into independent pieces.
   A cap can return an ordinary smaller boundary game, possibly with a star.
   The three exact cap identities below provide new positive clauses.
2. **Coupled pair bounds.** Analyze the sum of the two side games with its
   separator before assigning unrelated scalar bounds. At a diagnostic XX
   opening, an exhaustive support test shows that even the best such
   immediate one-column sum loses the required strictness. This identifies
   a structural obstruction to that local transition, beyond failure of a
   particular six-letter alphabet.
3. **Proactive replies with a moving marked interface.** Allow a nonmirror
   White response to a bulk Blue move before the mirror traps are completed.
   Such replies may create a marked state or move the cut. The admissible
   state must retain the mark and its neighbor exclusions, and a transition
   must either shorten the residual board or decrease a finite local rank.
   This remains an untested proposal here; the disproved fixed-cap policies
   that force mirroring outside their caps are not being rerun.

A bounded raw-solver screen tested the first proposed scalar targets at
widths three and five. All twelve starting-player tests completed and
reported White wins in `RX-1`, `VX-2`, and `XX-1`. The maximum was 80,437
states. These are **experimental observations only** in
[round4_dx_targets.json](round4_dx_targets.json); they are not used to prove
an infinite assertion. The constructive work below instead proves symbolic
width reductions with independently checked finite constants.

## An exhaustive obstruction in the new XX target

Start with `XX_7` and let Blue play `(2,3)`. White is next. To support
`XX_7<1`, the relevant continuation is this position minus 1: an upper
comparison must give a game strictly below 1, or supply a legal White
reply whose child is at most 1.

Consider the following precisely specified no-reply comparison class:
partition into columns 0–2, column 3, and columns 4–6, retain the grid
edges inside each region, and change permissions only in the allowed
upper-comparison direction. The separator's minimum Blue support is
`{0,4}`. Its White support S can be any subset of `{0,1,3,4}`. For fixed S,
the strongest safe side retains all its actual White cells except rows S
at the seam; its new endpoint is

```text
Q(S)[2] = w;
Q(S)[r] = b if r is in S, and o otherwise, for r != 2.
```

The corresponding strongest virtual game is

```math
H(S)=(X,Q(S))_3+C(S)+(Q(S),X)_3,
```

where `C(S)` has Blue support `{0,4}` and White support S. Both side games
are equal by horizontal reflection. The following finite bounds are
independently checked. Side entries are certified lower bounds; no
unproved exact value is needed except in the best row, where both
directions are checked.

| S | Q(S) | Exact separator C(S) | Side lower bound | H(S) lower bound |
| --- | --- | ---: | ---: | ---: |
| empty | `oowoo` | 2 | 1/2 | 3 |
| 0 | `bowoo` | 1+* | 1/2 | 2+* |
| 1 | `obwoo` | 1 | 1 | 3 |
| 0,1 | `bbwoo` | 1/2 | 1 | 5/2 |
| 3 | `oowbo` | 1 | 1 | 3 |
| 0,3 | `bowbo` | * | 1 | 2+* |
| 1,3 | D | 0 | 1 | 2 |
| 0,1,3 | `bbwbo` | -1/2 | 3/2 | 5/2 |
| 4 | `oowob` | 1+* | 1/2 | 2+* |
| 0,4 | X | 0 | 1/2 | **1, exact** |
| 1,4 | `obwob` | * | 1 | 2+* |
| 0,1,4 | `bbwob` | -1/2+* | 1 | 3/2+* |
| 3,4 | `oowbb` | 1/2 | 1 | 5/2 |
| 0,3,4 | `bowbb` | -1/2+* | 1 | 3/2+* |
| 1,3,4 | `obwbb` | -1/2 | 3/2 | 5/2 |
| 0,1,3,4 | `bbwbb` | -1 | 3/2 | 2 |

Every listed lower bound is at least 1; every row except S={0,4} is
strictly greater than 1. The minimum is exactly

```math
XX_3+0+XX_3=\tfrac12+0+\tfrac12=1.
```

This is exhaustive in the stated class. Increasing a region's Blue
permissions or further removing White permissions only increases its game.
Once the actual retained separator White support is S, both side White
supports must avoid S at the seam. The table uses their largest allowable
supports and smallest allowable Blue supports. Asymmetric or weakened
choices therefore cannot improve on that row.

Thus **no immediate one-column permissions-only comparison in this class
can prove the needed White-next win**. This is a finite, independently
certified obstruction to a candidate induction step. It neither proves
that the actual continuation is at least 1 nor refutes `XX_7<1`.

## Positive repair: keep a star instead of losing the interaction

Let `K_w(S)` be a five-row cap of width w, with X at its outer endpoint,
neutral permissions elsewhere, and Blue played in center row at its inner
endpoint. Keep its actual Blue permissions; delete White permissions at
the inner cap edge wherever the adjoining endpoint S permits White.
The exact finite identities are

```math
K_2(X)=0,\qquad K_3(D)=-1,\qquad K_4(X)=*.
```

**Endpoint-cap lemma.** In `(X,P)_n` with `n>w`, after Blue plays `(2,w-1)`,
for any far endpoint P,

```math
G\le K_w(S)+(S,P)_{n-w}.
```

The reflected formula holds for the corresponding opening near an X right
endpoint. Specializing to P=X, the displayed identities give:

| Opening column, or its reflection | Domain | Post-Blue upper bound |
| --- | --- | --- |
| 1 | odd n>=5 | `XX_(n-2)` |
| 2 | odd n>=5 | `-1+DX_(n-3)` |
| 3 | odd n>=7 | `*+XX_(n-4)` |

**Proof of geometry.** Blue's opening excludes Blue at row 2 of the adjacent
strip endpoint. Both D and X retain every other Blue row, so the strip's
actual Blue permissions are preserved. No White move preceded the cut;
the strip's White support can safely be restricted to D or X. The cap keeps
its actual Blue set and only removes White permissions. By construction,
the White supports across the seam are disjoint. The far P endpoint is
retained, including endpoint intersection if the side has width one. Thus
actual Blue legality is contained in virtual Blue legality and virtual
White legality is contained in actual White legality. Every recursive
width is `n-w<n`. The stated domains keep the odd XX calls at least three
and the even DX call at least two. ∎

For the obstructed first instance, n=7 and w=4, this gives the strictly
stronger conclusion

```math
G_{XX_7\text{ after }B(2,3)}\le *+XX_3=*+\tfrac12<1.
```

After subtracting 1, White is next in a strictly negative game and wins.
The one-column obstruction was therefore a loss of useful interaction,
not an obstruction in the actual marked position.

## Finite auxiliary form, rank, and missing obligations

A convenient star-stable target is

```math
T_1(XX_k):\quad XX_k\le1\quad\hbox{and}\quad XX_k+*\le1
\qquad(k\ge3\text{ odd}).
```

These paired inequalities imply that both games are strictly below 1:
equality in either one would contradict the other, since star is not
nonpositive. This does not assume that the games are numbers or numbers
plus star.

The three cap clauses handle the corresponding **Blue board openings**
for both members of this paired target:

- At distance one from the endpoint, carry the external star unchanged
  and apply `T_1` at width `n-2`.
- At distance two, `DX_(n-3)<=0` suffices: both `-1+DX` and `-1+DX+*`
  are strictly below 1.
- At distance three, the cap star toggles the external-star flag, and
  `*+*=0`. Apply `T_1` at width `n-4`.

These are no-reply comparisons, so the post-opening target must be strict;
a nonpositive bound after subtracting 1 would not suffice by itself.

The same three caps also propagate analogous center-row clauses for
`T_1(RX_odd)` and `T_2(VX_odd)`, where `T_q(G)` means `G<=q` and `G+*<=q`.
For the opening at distance one or three from the X endpoint, the smaller
state is respectively the same family unchanged or with an added star.
At distance two, the returned games are `DR_even-1` and `DV_even-1`.
The original bounds `DR<=-1/4` and `DV<=1/2` put those games, with or
without an external star, strictly below the respective thresholds 1 and 2.
Thus the proposed three new scalar families share the same finite set of
center-row transitions near their X endpoint. Their full paired bounds
remain hypotheses.

The auxiliary star also gives Blue an extra possible opening in the starred
game. Consuming it leaves the same-width unstarred game with White next.
That move needs an **independently proved strict unstarred assertion**. One
valid staging is to prove `XX_n<1` first, then prove its starred bound; use
rank `(n,stage)` with unstarred stage before starred stage. The argument
must not assume `T_1(XX_n)` itself to obtain this same-width witness.

There remain unhandled deep interior center openings, outer and inner row
openings, and the White-first witness for the unstarred assertion at each
width. White-first in the starred game can consume its star and use an
established unstarred nonpositive comparison after subtracting 1. Thus
the cap table is a finite set of genuine recursive clauses, but is not a
closed `T_1` induction. RX and VX likewise have not acquired full recursive
proofs from this test.

## Independent artifacts

Run the default search-free check:

```sh
python3 proofs/construction/research/round4_dx_check.py
```

The checker binds roots to literal X and D patterns, reconstructs all
permissions with coordinate sets, and verifies supplied response DAGs with
the separate checker in `number_certificates.py`. Every universal move,
legal response, successor, and finite rank decrease is checked.

The [manifest](round4_dx_certificates/manifest.json) maps all artifacts:

- Sixteen `s*_side_lower` DAGs give the exhaustive table's lower bounds.
- `s17_side_upper` gives the matching upper bound for the exact best row.
- Six `cap*_upper/lower` DAGs give the three exact cap identities.

For the star identity the checker embeds `K_4(X)` and one isolated shared
vertex, separated by a dead column, in a 5×6 board. Both directions of
value zero prove `K_4(X)+*=0`, hence `K_4(X)=*`. The separator path identities
and `*+*=0` are separately checked by recursive short-game order, not by the
discovery evaluator. There are no missing artifact mappings for claims
proved in this note.

```text
Verified 23 bound DAGs: 9467 checkpoints, 33687 response edges.
Checked 16 exhaustive support bounds, three exact cap identities, 117 embeddings (regression).
```

The embedding sweep checks implementation; the written local support proof
provides the all-width conclusion. `round4_dx_pair_algebra.py` and its JSON
catalogue are discovery artifacts, not the default verification mechanism.
