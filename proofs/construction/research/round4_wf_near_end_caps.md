# Near-end marked caps with the original auxiliary margins

Status: **proved parameterized local reductions, independently certified finite
upper bounds**. These extend the four-column repair in
[round3_wf_wider_caps.md](round3_wf_wider_caps.md). They close additional
infinite classes of marked-phase openings but do not close the mutual
induction, propagate an arbitrary-width DD margin, or prove the empty-board
bridge.

The three ideas tested here were: absorb the mark and an opening in a short
end cap; seek a row-complete cap table returning the original six ordinary
families; and make a seam-compatible White reply before cutting when strictness
is otherwise missing. Each gives a positive contract below.

## Common geometry and the exact hypotheses

Use the marked family from [round 2](round2_wf_delayed_phase.md):
`F_Q(n,p,t)` is `DQ_n` after an actual White move `(t,p)`. Its required
width/position scopes remain unchanged:

| Q | Width parity | Required position domain |
| --- | --- | --- |
| D, U, J | odd | `p>=2`, `p+1<=n<=2p-1` |
| R, V | even | `p>=2`, `p+1<=n<=2p` |
| X | even | `p>=2`, `p+1<=n<=2p-2` |

Here t is 2 for even p, and 1 or 3 for odd p. These are permissions and
actual moves; the mark's neighbor exclusions are retained.

Let the cap consist of the last w columns, let `L=n-w`, and suppose Blue
opens in the cap's first column, at `(r,L)`. The left strip has width L.
For normalized row r=0,1,2, select the interface by L's parity:

| L parity | r=0 | r=1 | r=2 |
| --- | --- | --- | --- |
| odd | U | J | D |
| even | R | V | X |

For r=3,4 reverse the corresponding endpoint pattern vertically. When
normalizing a whole marked D-ended or X-ended board vertically, also
replace t by `4-t`; U and J are asymmetric and their contracts below check
all five rows separately.

Keep cap Blue permissions and retire cap White permissions in its first
column wherever the selected strip interface permits White. If the original
White mark lies in that first cap column, every contract also checks that
the strip interface forbids White in row t. Thus the mark's actual restriction
on the strip is respected. Blue's opening forbids Blue in the neighboring
strip cell in row r, exactly as the selected interface requires.

Consequently, each stated cap inequality gives a safe upper comparison:
actual Blue legality is contained in virtual Blue legality; virtual White
legality is contained in actual White legality; and the two White seam
supports are disjoint. All other permissions are inherited. Endpoint
restrictions intersect wherever applicable.

The comparisons use these **conditional ordinary hypotheses only**:

```math
DU_L<0,\quad DJ_L<-\tfrac14,\quad DD_L<0\qquad(L\ge3\text{ odd}),
```

```math
DR_L\le-\tfrac14,\quad DV_L\le\tfrac12,\quad
DX_L\le0,\quad DX_L+*\le0\qquad(L>0\text{ even}).
```

The DD strictness is a separate recursive obligation, not a newly proved
ordinary bound. The paired X hypotheses imply `DX_L<0`: equality to zero
would make `DX_L+*` equal star. The claims do not assume the stronger
round-2 hypotheses `DR<=-1/2`, `DV<=0`, or `DU,DD,DJ<-1/2`.

## 1. A complete same-column X repair

Take `F_X(n,n-2,2)` with even `n>=6`. Blue opens in the marked column
`c=n-2`; row 2 is occupied, so the four possible rows are 0,1,3,4.
Absorb the last two columns. The following independently certified cap
upper bounds suffice:

| Blue row | Strip endpoint | Cap upper bound | Cap masks `(A,B)` |
| --- | --- | ---: | --- |
| 0 or 4 | R or its reflection | `1/8` | `(968,392)` for row 0 |
| 1 or 3 | V or its reflection | `-1` | `(962,393)` for row 1 |

The masks are reconstructed in the checker; the bound `1/8` is a convenient
strict margin and is not an asserted exact cap value.

White is next after Blue. The comparisons are

```math
G\le DR_{n-2}+\tfrac18\le-\tfrac18<0,
\qquad
G\le DV_{n-2}-1\le-\tfrac12<0.
```

Thus every legal Blue row in the marked column is handled by original
ordinary targets. The recursive width `n-2` is positive, even, and smaller
than n. Together with round 3, this now treats every row at columns
`c=p` and `c=p-2` on the reachable X diagonal `p=n-2`.

The missing intervening column is concrete: at `c=p-1`, the inner-row
three-column cap with interface J has exact value `1/2` in the discovery
calculation. The old sufficient bound `DJ<-1/4` does not absorb that debt.
This observation is not a lower bound for the actual whole position and is
not promoted to an independently certified obstruction here.

## 2. Row-complete D-ended caps, and endpoint-marked U/J caps

Take a required `F_D(n,p,t)` phase. Let `w` be 2, 3, or 4 and assume
`L=n-w<=p<=n-1`: the mark is anywhere inside the last w columns. Let Blue
open at `(r,L)`, in any legal row. The finite cap table is uniformly:

| Cap width w | L parity | Outer-row cap bound | Inner-row cap bound | Center-row cap bound |
| --- | --- | ---: | ---: | ---: |
| 2 or 4 | odd | `0`, interface U | `1/4`, interface J | `0`, interface D |
| 3 | even | `0`, interface R | `-1`, interface V | `0`, interface X |

Occupied Blue moves are omitted. All legal mark positions and permitted mark
rows are covered; this is not only a center-row or vertically normalized
mark claim. The finite certificates establish these common upper bounds,
not an unstated equality for every cap.

For odd L the resulting sums are strictly negative by `DU_L<0`,
`DJ_L+1/4<0`, and `DD_L<0`. For even L they are strictly negative by
`DR_L<=-1/4`, `DV_L-1<=-1/2`, and the paired X targets. White is next, so
this strictness is exactly what is needed. Every call has width L<n;
require `L>=3` when odd and `L>=2` when even. The separate small bases are
not silently assigned strict `DD_1`.

There is a useful extension with asymmetric far endpoints. For
`Q=U` or `J`, take `F_Q(n,n-1,2)` at odd n. With w=2 or 3, the same table
holds for every Blue row at `c=n-w`. The proof checks U and J without
reflecting away their orientation. For w=2 the recursive widths are odd
and use the first row of the table; for w=3 they are even and use the
second row. Again, keep only instances in the required phase domain and
with recursive widths in the stated ordinary scope.

These caps absorb positive or fuzzy local pieces into a bounded interaction
before returning an ordinary game. No marked ordered-pair state is introduced
by any of these transitions.

## 3. Three explicit White replies remove a local strictness demand

The following local coordinates describe a cap with first column 0 and
far endpoint Q. The mark and opening are actual moves before the optional
reply. After the displayed White reply, Blue is next.

| Q | Cap width | Existing White mark | Blue opening | New White reply | Strip interface | Certified resulting cap bound |
| --- | ---: | --- | --- | --- | --- | ---: |
| U | 3 | `(1,1)` | `(2,0)` | `(4,0)` | X | `0` |
| J | 3 | `(1,1)` | `(0,0)` | `(0,2)` | R | `1/4` |
| R | 2 | `(1,1)` | `(2,0)` | `(0,0)` | X | `0` |

All three return an even strip width L. Global mark and reply coordinates
are obtained by adding L to their columns. The U/J cases have odd total
width and the R case even total width, so the original mark has the
correct odd-column row-1 parity. Keep the exact phase position domains
stated above.

For U and R, the cap-zero bound and `DX_L<=0` yield a nonpositive total.
No star-compensated X inequality is needed for these particular replies.
For J, `DR_L+1/4<=0` suffices: the reply changes turn order precisely where
an equality might otherwise prevent a White-first winning comparison.
In the J cap the reply occupies an isolated shared vertex; its removal
retains the remaining interaction rather than replacing it with a guessed
strict scalar margin.

The replies on the seam are at rows 4 and 0 respectively. X forbids White
there, so their new exterior White restrictions fall only on already
retired strip permissions. The J reply is internal to the cap. All are
legal in the actual board as well as the virtual cap. These are therefore
parameterized legal reply-and-cut constructions, not merely cap outcome
observations.

## What the tests did and did not settle

`round4_wf_caps_probe.py` explored 407 admissible short-cap contracts with
width at most four, all six far endpoint letters, and the parity-correct
mark rows. Its selected scalar thresholds or local reply rule closed 328.
The unclosed entries are failures of those particular numerical templates,
not assertions that the actual marked games are positive. Some fuzzy caps
can also be handled by coupled hypotheses that this discovery criterion
does not use.

A further exploratory attempt moved the cut one column left of an
adjacent inner-row Blue move and used the all-Blue endpoint `T=bobob`.
For the width-four X cap with mark `(2,2)` and Blue `(1,1)`, its scalar
value was zero in discovery. The already certified `DT_2=0` therefore
supplies no White-next margin at that smallest cut. This did not yield a
new closed subsystem; no general DT claim is made.

The proved transitions cover fixed neighborhoods of the endpoint. For a
mark far from that endpoint, cuts to its left still produce ordered-pair
marked states, and the positive marked-XX issue remains outside the cases
absorbed above. The adjacent inner-row X opening, same-endpoint marked D
openings, and the original central DD strictness propagation also remain
separate dependencies. Thus the growing cap catalogue is a finite set of
usable induction clauses, not a closed symbolic induction.

## Certificate mapping and reproduction

Run:

```sh
python3 proofs/construction/research/round4_wf_check.py
```

The checker reconstructs every local root from endpoint permissions and
legal moves, verifies each stored DAG using the independent coordinate-set
checker in `number_certificates.verify`, and checks the comparison geometry.
The default command performs no minimax search. `--generate` is a separate
certificate discovery mode.

The [manifest](round4_wf_certificates/manifest.json) maps all 61 claims:

- `dend_*`: the row-complete D-ended cap table;
- `endmark_*`: the U/J endpoint-marked cap table, with all five Blue rows;
- `xsame_*`: the two vertically representative X same-column cap bounds;
- `reply_*`: the three post-reply cap bounds.

The package contains **21,272 checkpoints and 87,745 universally checked
response edges**. The default checker also runs 627 reachable embeddings,
all with smaller positive recursive width; these regress the symbolic
geometry proof, rather than proving its unbounded scope by sampling.
`round4_wf_verification.txt` records a fresh verification run. The broader
catalogue in `round4_wf_caps_probe.json` and the selected scalar probes in
`round4_wf_scalar_probe.json` are explicitly discovery data. Their respective
Python scripts reproduce them without treating them as arbitrary-width facts.
