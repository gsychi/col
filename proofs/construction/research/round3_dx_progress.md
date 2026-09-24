# Anchored three-column reductions and a shifted mirror trap

Status: **proved finite cap identities and all-width local reductions; proved
obstruction to a specified fixed-cap mirror policy**. There is still no
closed induction for DX. The new RX, VX and XX inequalities below are
sufficient targets for particular openings, not established arbitrary-width
facts.

## An anchored cap can improve the separated bound

Rows and columns are zero-based. Write `(P,Q)_n` for the five-row permission
board with left endpoint P and right endpoint Q; at width one both masks
are intersected. All patterns are permissions, not stones.

Consider any `(D,Q)_n`, `n>=4`, immediately after Blue plays `(r,2)`, with
White next. Keep its first three columns as one cap. At the seam, give the
remaining width `n-3` the left endpoint S. Keep the cap's actual Blue
permissions, and retain only those actual White permissions in column 2
whose rows are not White-legal in S. Denote this cap `K(r,S)`.

The following identities are exact. They are independently certified, not
inferred from finite-width numerical patterns.

| Opening row r | New endpoint S | Exact cap K(r,S) |
| --- | --- | --- |
| 0 | U | 0 |
| 0 | R | -1 |
| 1 | V | -2 |
| 1 | J | 1/2 |
| 2 | D | 0 |
| 2 | X | -1 |

**Anchored-cap lemma.** For every listed row and endpoint, every far endpoint
Q and every `n>=4`,

```math
(D,Q)_n^{B(r,2)}\ \leq\ K(r,S)+(S,Q)_{n-3}.
```

**Proof.** Away from column 3, the right-hand region has its original
permissions. At column 3, Blue's opening has removed Blue legality only in
row r, and has removed no White legality. Each listed S permits all of these
actual Blue moves. Restricting its White moves to S is therefore safe. The
cap keeps every actual Blue permission and deletes only White permissions.
For each seam row the cap has no White permission whenever the right region
has one. Thus no deleted seam edge has two virtual White-legal endpoints.
Consequently actual Blue legality is contained in virtual Blue legality,
virtual White legality is contained in actual White legality, and the
standard one-sided separator comparison applies. When the right region has
width one, intersecting S and Q can only further remove its White seam
support; its Blue permissions still contain the actual intersection. The
cap constants are the certified finite identities in the table. The sole
recursive board has width `n-3<n`. ∎

The cap deliberately retains interactions between the D endpoint and the
opening column. If one uses only the original sufficient auxiliary targets
in the existing one-column reduction, the separated row-0 cap expression
`DR_2+0` is bounded by `-1/4`, whereas this cap is exactly `-1`. Similarly,
the separated row-1 expression `DV_2-3/2` is bounded by `-1`, whereas this
cap is exactly `-2`. These comparisons describe the improved sufficient
bound; they do not assume that either arbitrary-width target is proved.

For `DX_n` at even `n>=6`, the following three targets would suffice for
**all five openings in column 2**:

```math
RX_k<1,\qquad VX_k<2,\qquad XX_k<1
\qquad(k\geq3\text{ odd}).
```

Use S=R for row 0, S=V for row 1 and S=X for row 2. Rows 4 and 3 follow by
vertical reflection, since D and X themselves are vertically symmetric.
Each resulting upper bound is strictly negative, which is needed because
White is next. A merely nonpositive bound is insufficient at this turn.
These inequalities have not been proved for arbitrary odd k. They do not
cover other opening columns, and do not give the separate White-first
witness needed for strict negativity of DX. Small widths, including n=4,
remain separate base obligations for this formulation.

There are also three independently certified explicit White replies to the
row-0 opening: `(0,0)`, `(2,2)` or `(4,2)`. With endpoint R each gives an
anchored cap of exact value `-1/2`. For any of these replies,

```math
(D,Q)_n^{B(0,2),W(u)}\leq-\tfrac12+(R,Q)_{n-3}.
```

Here Blue is next. Accordingly the weaker strictness requirement
`(R,Q)_{n-3}<=1/2` would suffice for these replied positions. It is a
conditional alternative, not a proved bound on RX. In particular finite
raw-solver discovery suggests `RX_5=1/2+*`; that observation has no supplied
independent certificate and is not used by any theorem here.

## Widening a reactive mirror controller to three columns still fails

Let `C=wbwbw` and `Cbar=bwbwb`. Four finite cap identities are independently
certified:

| Cap | Value |
| --- | --- |
| `(D,C)_3` | -1 |
| `(Cbar,X)_3` | 0 |
| `(D,Cbar)_3` | 1 |
| `(C,X)_3` | 1 |

The favorable first pair does not justify a wider mirror controller: Blue
can choose the other checkerboard phase.

**Three-column mirror-trap theorem.** For every even `n>=8`, a White policy
on `DX_n` that answers each of the following five moves with either its
horizontal reflection or its half-turn image reaches exact value 2 with
Blue next:

| Round | Blue move |
| --- | --- |
| 1 | `(0,n-4)` |
| 2 | `(1,3)` |
| 3 | `(2,n-4)` |
| 4 | `(3,3)` |
| 5 | `(4,n-4)` |

The policy may choose the two reflections adaptively whenever both are
legal.

**Proof.** Columns 3 and `n-4` are distinct neutral columns. Blue uses odd
rows in column 3 and even rows in column `n-4`. Both reflections send a cell
to the opposite column, preserving row parity. Thus every White reply uses
the opposite checkerboard color class. The Blue moves are distinct and
never adjacent to a prior Blue stone. The same is true of any distinct
White replies. This includes n=8, where the two columns are adjacent.

The reflected row pairs `{0,4}` and `{1,3}` each have two available cells
over their two rounds; row 2 is used once. Therefore some reflected reply
is available on every round, irrespective of earlier legal choices. After
five rounds both columns are occupied with the same colors for every
adaptive choice. They disconnect the remaining board exactly as

```math
(D,\overline C)_3
 +(\overline C,C)_{n-8}
 +(C,X)_3.
```

At n=8 the middle region is empty, hence zero. At larger even widths its
two endpoint masks are color conjugates, and the horizontal pairing
theorem gives exact value zero. The independently certified end values are
1 and 1. The actual continuation is therefore `1+0+1=2`; this last identity
is an exact decomposition, not an upper comparison. Blue is next and wins.
∎

In particular, any controller that insists on a horizontal or half-turn
reply whenever Blue plays outside the outermost three columns at each end
fails for every even `n>=8`. Allowing arbitrary special White replies only
in response to a cap opening does not help: Blue's five moves are all
outside those caps. Any successful controller must permit a proactive
nonmirror reply during this sequence, or change its handling of exterior
moves. The theorem does not establish that DX is positive, and does not
rule out controllers with wider caps, moving interfaces, or nonmirror
responses to exterior openings.

## Interface refinement and bounded discovery status

[round3_dx_port_controller.py](round3_dx_port_controller.py) refines the
paired-port discovery model in the preceding
[mirror note](round2_dx_mirror.md). It tracks which exterior Blue port
orientations are blocked by actual Blue stones on the inward cap edge.
This information cannot be recovered from the two legality masks alone.
An inward cap White reply is allowed whenever its reflected exterior Blue
cell is already illegal: because its pair is occupied, because a reflected
cap Blue stone blocks it, or because an adjacent exterior Blue stone blocks
it. The neighboring exterior White cell need not already be illegal.

This stronger permission is sound: that special reply can delete exterior
White legality only opposite an already absent exterior Blue permission,
so it creates no exterior defect `tau(A)\B`. The distinction between
**Blue-blocked** and White-blocked is essential. The live-cell and unused
port-pair rank of the preceding cap lemma still decreases on every
effective abstract event; otherwise an actual mirrored middle move
decreases the secondary live-middle-cell rank.

The refined horizontal three-column search was **Unknown** at its
1,000,000-state budget. No independent abstract-controller DAG was produced.
Its negative or Unknown search outputs have no mathematical force. The
actual legal mirror-trap theorem above independently rules out this
particular forced-exterior-mirror model, even with the stronger cap-reply
rule. Increasing its search budget is therefore unnecessary.

## Certificates and checks

[round3_dx_check.py](round3_dx_check.py) reconstructs every numerical root
from literal endpoint patterns and coordinate-set moves, binds it to the
supplied DAG, and invokes the independent checker in
[number_certificates.py](number_certificates.py). Verification covers every
first-player move, a legal response, successor reachability and descent in
live-cell count plus the canonical dyadic birthday. The default check does
not call minimax; `--generate` regenerates the certificates as a separate
discovery step.

All 26 bound artifacts and their exact root mappings are present in
[round3_dx_certificates/manifest.json](round3_dx_certificates/manifest.json).
Pairs of upper/lower certificates establish each stated equality. There
are no missing mappings for the numerical claims proved in this note.

```sh
python3 proofs/construction/research/round3_dx_check.py
```

```text
Verified 26 exact-bound DAGs: 4605 checkpoints, 15767 response edges.
Checked 972 cap assemblies, including width-one endpoint intersections (regression only).
Checked 52 branches of the width-three mirror trap (regression only).
```

The finite assembly checks are regressions of the symbolic arguments above;
they are not evidence substituted for an all-width proof. The scripts
`round3_dx_anchored_caps.py`, `round3_dx_proactive_caps.py` and
`round3_dx_raw_probe.py` are discovery tools. Their JSON observations are
kept separate from the independently checked certificate manifest.
