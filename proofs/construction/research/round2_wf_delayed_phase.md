# Delayed White-first DD: new caps and a conditional central-phase assembly

Status: the cap comparisons and the conditional assembly theorem below are
proved, using independently checked finite cap values. The required
arbitrary-width phase inequalities and strengthened ordinary-family bounds
are **not proved**. The corner-preplay bound `E_X(even)<=0` is explicitly
refuted at width four. Nothing here proves the full five-row theorem.

All cells are permissions, with the endpoint definitions in the
[handoff](col_research_handoff.md). End conditions intersect at width one.
The White-only support obstruction from
[five_row_white_first.md](five_row_white_first.md) remains in force; the
new states retain the actual first White move instead of inventing missing
Blue exclusions at a freshly cut boundary.

## New two-column caps retain the D-end interaction

Suppose Blue has just played next to an original D endpoint. Absorb that
endpoint column and the opened column into one width-two cap. Restrict White
in the opened column to the complement of the indicated interface support.
With the opening in the left column and D in the right column, the caps are:

| Opening row | Endpoint induced on the remaining left strip | Exact cap value | Row-major cap masks `(A,B)` |
| --- | --- | ---: | --- |
| 0 | U | `-1` | `(984,614)` |
| 1 | J | `-1+*` | `(962,610)` |
| 2 | D | `-1` | `(907,614)` |

Vertical reflection supplies rows 3 and 4. Horizontal reflection gives
caps at the left D endpoint. In particular, these replace the weaker
one-column expressions `0+DU_1`, `1/2+DJ_1`, and `0+DD_1` by caps that are
strictly negative in every row. The row-1 cap contains an isolated shared
cell; deleting it leaves a certified game of value `-1`, proving the exact
`-1+*` claim without a generic inference from outcome class N.

These caps are valid for arbitrary remaining width. The Blue opening
removes Blue legality at the adjacent remaining boundary cell in its own
row. This is exactly the White-only row of U, J, or D. All actual Blue
permissions remain virtual, all virtual White permissions were actual, and
the cap's White boundary support is disjoint from the new endpoint's White
support. The recursive width decreases by two.

Consequently, if a remaining phase game has upper bound zero, every
penultimate-column opening is answered already: the post-Blue sum is
strictly negative, so White wins moving next. This repairs both the J
star obstruction and the DD width-one strictness obstruction at that edge.

## Corner preplay: a complete transfer table, and its precise failure

Let `E_Q^t(k)` be `DQ_k` after White plays `(t,0)`, for `t=0` or `4`.
This includes the White exclusion at `(t,1)`. It is an actual post-move
position whenever the first move is legal, not merely an altered end-column
mask. The two values of `t` are necessary: a corner preplay breaks vertical
symmetry.

For a Blue move in column `c>=2`, normalize its row vertically to
`r<=2`; when reflecting, also replace `t` by `4-t`. Write `a=c` and
`b=n-c-1`. For interior columns, the existing six-case geometry transports
exactly as follows:

| Normalized Blue opening | Next White action | Upper comparison | Turn at comparison |
| --- | --- | --- | --- |
| `r=0`, c odd | none | `E_U^t(a)+DU_b` | White |
| `r=0`, c even | `(2,c)` | `E_R^t(a)+1/2+DR_b` | Blue |
| `r=1`, c even | none | `E_V^t(a)-3/2+DV_b` | White |
| `r=1`, c odd | none | `E_J^t(a)+1/2+DJ_b` | White |
| `r=2`, c even | `(0,c)` | `E_X^t(a)+*+DX_b` | Blue |
| `r=2`, c odd | none | `E_D^t(a)+DD_b` | White |

At the right endpoint `c=n-1`, the outer-row response is instead the
corrected opposite-corner response: it gives `E_R^t(n-1)` with Blue next.
An inner-row endpoint opening gives `E_V^t(n-1)-3/2` with White next.
The center endpoint is Blue-illegal. At `c=n-2`, the new two-column caps
above improve the table to `E_U^t(n-2)-1`,
`E_J^t(n-2)-1+*`, or `E_D^t(n-2)-1`, all with White next.

The two columns near the preplayed corner also have explicit contracts.
The following table assumes the original White move was `(0,0)`, without
vertical normalization:

| Blue location | Kept cap width | Remaining ordinary state | Exact cap value |
| --- | ---: | --- | ---: |
| `(1,0)` | 1 | `DV_(n-1)` | `-1/2` |
| `(3,0)` | 1 | reflected `DV_(n-1)` | `-1` |
| `(4,0)` | 1 | reflected `DR_(n-1)` | `0` |
| `(0,1)` | 2 | `DU_(n-2)` | `0` |
| `(1,1)` | 2 | `DJ_(n-2)` | `-1` |
| `(2,1)` | 2 | `DD_(n-2)` | `0` |
| `(3,1)` | 2 | reflected `DJ_(n-2)` | `*` |
| `(4,1)` | 2 | reflected `DU_(n-2)` | `0` |

Blue cannot play `(0,0)` or `(2,0)`. Every comparison in this table is
immediately after Blue, hence needs strict negativity. The ordinary
handoff targets settle every listed case for odd `n>=5`, except `(1,0)`
asks for `DV_(n-1)<1/2`. The center entry uses strict `DD_(n-2)<0`, and
the star entry is negative because `DJ_(n-2)<-1/4` and `*<1/4`.
These are genuine arbitrary-width local reductions, not a bounded search.

However, the attractive uniform phase hypothesis `E_X^0(k)<=0` at even
widths is false:

```math
E_X^0(4)=\frac12.
```

Both numerical directions are independently certified. Thus this particular
corner phase cannot be assigned the proposed nonpositive X bound uniformly.
This does not refute another response policy, a width-dependent compensation,
or `DX_k<=0` itself. It identifies exactly why the simplest corner-phase
closure fails.

A local White move in the V separator cannot recover a missing strictness
margin either. The separator `w.wbo=-3/2` has White moves in rows 0, 2, and 4,
whose exact children are `-1/2`, `-1/2`, and `-1`. Their side interfaces remain
safe, but even the best local reply raises the cap value by `1/2`.

## A parity-aware central phase avoids that particular counterexample

Define `F_Q(k,p,t)` to be `DQ_k` after White plays `(t,p)`. Use the domain

```math
p+1\le k\le2p,\qquad
 t=2\text{ if }p\text{ is even},\qquad
 t\in\{1,3\}\text{ if }p\text{ is odd}.
```

The exact required scopes are:

| Phase family | Width parity | Required range |
| --- | --- | --- |
| D, U, J | odd | `p+1 <= k <= 2p-1` |
| R, V | even | `p+1 <= k <= 2p` |
| X | even | `p+1 <= k <= 2p-2` |

Always `p>=2`; the stated rule for t applies in every row. The X family
excludes `k=2p`, because it would correspond to a center-row Blue opening
at the original D endpoint, where Blue is illegal. The first required X
bases are `(k,p,t)=(4,3,1)` and `(4,3,3)`, not `(4,2,2)`.

At `p=k-1`, the permitted
patterns still make White's move legal: p even gives odd k and row 2 is
White-legal in D/U/J; p odd gives even k and rows 1 and 3 are White-legal
in R/V/X. Thus F is always a genuine post-White position in the stated
scope. It is a finite collection of symbolic marked-strip families, with
an additional position parameter; no finite interface closure is claimed.

The parity restriction matters. For example, White at `(2,3)` in `DD_5`
is not a winning first move, whereas White at `(1,3)` and `(3,3)` wins.
These are finite discovery observations, not a general checkerboard theorem.
Similarly the Q-half condition alone would wrongly include endpoint phases
with inappropriate parity. The corner-phase counterexample does not apply
to the restricted F domain. An optimized raw solver also reports a
Blue-first win for `F_X(6,3,1)` and `F_X(6,3,3)`, but those are exactly
excluded `k=2p` states. This is experimental evidence against the
overspecified phase conjecture, not a certified counterexample to the
reachable phase target or to DD.

## Conditional White-first assembly theorem

For odd `n=2m+1>=5`, suppose the following bounds are available at all widths
strictly below n that occur in the proof.

Ordinary states:

```math
DR_{even}\le-\tfrac12,\qquad DV_{even}\le0,
\qquad DX_{even}\le0,\quad DX_{even}+*\le0;
```

```math
DU_k<-\tfrac12,\qquad DD_k<-\tfrac12,\qquad DJ_k<-\tfrac12
\quad\text{for odd }k\ge3.
```

Phase states throughout their family-specific domains above:

```math
F_D,F_U,F_J\le0\quad(k\text{ odd}),
\qquad F_R,F_X\le0,
\qquad F_V\le1\quad(k\text{ even}).
```

These are **sufficient hypotheses**, not established arbitrary-width facts.
In particular, the ordinary bounds strengthen the user's original targets,
and strict DD negativity alone does not imply `DD<-1/2`.

Then White wins moving first in `DD_n`.

Proof: White first plays `(2,m)` if m is even, or `(1,m)` if m is odd.
Horizontal reflection permits the next Blue move to be in column `c<=m`.
For `c<m`, vertically normalize Blue's row to `r<=2`, reflecting the
preplayed White row t too. Thus t remains 2 when m is even and ranges over
1 and 3 when m is odd.

For `2<=c<=m-1`, set

```math
a=c,\qquad k=2m-c,\qquad p=m.
```

Cut at Blue's column. The left region is ordinary `DQ_a`; horizontally
reflect the right region to get `F_Q(k,p,t)`. Since
`p+1<=k<=2p-2` for these interior columns, this is an allowed phase call
of width `k<n`, including the narrower X scope.
The six comparisons are:

| Blue opening | White action | Upper comparison | Sufficient resulting bound |
| --- | --- | --- | --- |
| outer, c odd | none | `DU_a+F_U` | `<0`, White next |
| outer, c even | center of c | `DR_a+1/2+F_R` | `<=0`, Blue next |
| inner, c even | none | `DV_a-3/2+F_V` | `<=-1/2`, White next |
| inner, c odd | none | `DJ_a+1/2+F_J` | `<0`, White next |
| center, c even | top of c | `DX_a+*+F_X` | `<=0`, Blue next |
| center, c odd | none | `DD_a+F_D` | `<0`, White next |

There is no hidden interaction when `c=m-1`. If m is even, c is odd and
all U/J/D separators already forbid White in row 2, the row affected by
the adjacent initial White stone. If m is odd, c is even and R/V/X
separators already forbid White in rows 1 and 3. Their prescribed replies
in rows 2 or 0 are legal, since the initial White row is 1 or 3. Thus the
same comparison is valid at the adjacent column, including the boundary
phase `p=k-1`.

At `c=0`, the outer-row corrected opposite-corner reply leaves `F_R<=0`
with Blue next. An inner-row opening gives `-3/2+F_V<=-1/2` with White
next. The center is illegal. At `c=1`, absorb the leftmost two columns
using the new D-end caps: the bounds are `-1+F_U`, `-1+*+F_J`, or
`-1+F_D`, all strictly negative. The phase width is `n-2`, hence smaller.
For `m=2`, the initial White stone is adjacent to this cap, but its row 2
was already retired by every relevant cap contract; this boundary case
is therefore valid as well.

It remains only to handle Blue in column `c=m`, the same column as the
initial White stone. No extra White reply is needed. Both side widths are
m and the following complete cap table applies:

| Initial White row | Blue row | Side state on both sides | Separator | Exact cap value | Sufficient bound |
| --- | --- | --- | --- | ---: | --- |
| 2 (m even) | 0 or 4 | R or its vertical reflection | `...bo` or reflection | `1/2` | `2DR_m+1/2<=-1/2` |
| 2 (m even) | 1 or 3 | V or reflection | `w..bo` or reflection | `-1/2` | `2DV_m-1/2<=-1/2` |
| 1 (m odd) | 0 | U | `..bob` | `1` | `2DU_m+1<0` |
| 1 (m odd) | 2 | D | `b..wb` | `1` | `2DD_m+1<0` |
| 1 (m odd) | 3 | reflected J | `b....` | `1` | `2DJ_m+1<0` |
| 1 (m odd) | 4 | reflected U | `b.bw.` | `1` | `2DU_m+1<0` |

The preoccupied row is Blue-illegal. The table covers all other rows.
Every side's White support excludes the initial White row, and its
White-only row is the Blue opening row. The separator support is disjoint
from both side supports. Thus all comparisons have the correct direction
and safe seams. When m is odd and n>=5, necessarily `m>=3`, so no strengthened
odd target is applied at width one. Every recursive side has width `m<n`.
This completes the conditional White-first assembly.

This is a usable induction interface: all locations and turn obligations
are accounted for, and every call decreases width. It does **not** prove
the F-family inequalities, their mutual recursive closure, or the stronger
ordinary targets. Those are the remaining mathematical dependencies.

## Finite evidence and exact artifact mappings

Run the independent verifier without search:

```sh
python3 proofs/construction/research/round2_wf_check.py
```

The [`round2_wf_certificates/manifest.json`](round2_wf_certificates/manifest.json)
lists every exact root. The checker reconstructs roots from permission
strings and legal moves, checks all response DAGs through the independent
`number_certificates.verify`, checks isolated-star decompositions, and
regresses cap embedding geometry on several widths. The unbounded scope is
provided by the symbolic arguments above, not by the regression widths.
The final package has 53 certificates, 21,283 checkpoints, and 95,515
universally checked response edges. The search-free run also checks 45 cap
embeddings and 140 phase-transfer assemblies; its output is saved in
[`round2_wf_verification.txt`](round2_wf_verification.txt).

Certificate naming maps:

- `left_column0_row*_upper/lower`: the three one-column corner-phase caps.
- `left_column1_row*_upper/lower`: the five two-column corner-phase caps;
  row 3 certifies the zero core after its isolated shared cell is removed.
- `right_penultimate_row*_upper/lower`: the new D-end two-column caps;
  row 1 certifies the `-1` core after its isolated shared cell is removed.
- `central_white*_blue*_upper/lower`: the six same-column cap types.
- `v_reply*_upper/lower`: the three exact White options in `w.wbo`.
- `corner_phase_x4_upper/lower`: `E_X^0(4)=1/2`, the failed uniform target.
- `phase_*_upper`: the sufficient F bounds at `(k,p)=(3,2),(4,2),(4,3)`.

The F certificates establish only those finite bases. For discovery beyond
those bases, [`round2_wf_phase_search.cpp`](round2_wf_phase_search.cpp) searches
finite permission states with a visit limit and a dyadic quarter offset.
Its CSV result is 0 for a Blue-first loss, 1 for a win, and 2 for Unknown
at the visit limit. It is not a certificate checker. Compile and run, for
example:

```sh
c++ -O3 -std=c++17 proofs/construction/research/round2_wf_phase_search.cpp -o /tmp/round2_wf_phase_search
/tmp/round2_wf_phase_search 6 3 10000000
/tmp/round2_wf_phase_search 6 4 10000000
```

An optional final argument `all` reproduces the wider row/quarter-offset
scan in `round2_wf_phase_w5_p3.csv`. At width six the plain C++ search found the V bounds,
while the R and X queries reached its stated 10-million-visit limit.
Subsequently the optimized raw production solver, after validation on
known certified roots, resolved the three tested R roots as Blue-first
losses, the reachable X root `(6,4,2)` as a Blue-first loss, and the two
unreachable X roots `(6,3,1/3)` as Blue-first wins. These later results are
recorded in `round2_wf_raw_phase_probe.json`; they remain discovery results,
not independent certificates. Run `round2_wf_raw_phase_probe.py` after the
root task's `round2_prepare_raw_solver.py` to reproduce them. Neither
Unknown nor a positive relaxed cap proves that the actual DD game is
positive.
