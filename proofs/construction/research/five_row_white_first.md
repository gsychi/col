# White-first DD: a support obstruction and checked base obligations

Status: the support lemma and its no-go consequence below are proved for
arbitrary graphs/widths in their stated scope. The small roots listed at the
end have independent finite response-DAG certificates. No arbitrary-width
`DD`, `DX`, or empty five-row theorem is asserted.

This note follows the latest
[research handoff](col_research_handoff.md), with the endpoint patterns
`D=obwbo`, `U=wbobo`, `V=bwbob`, `X=bowob`, `R=wobob`, and `J=owobo`.
These are permissions. End restrictions intersect at width one.

## A resource preserved by White moves and upper comparisons

For legality sets `(A,B)`, write

```math
W(A,B)=B\setminus A
```

for the set of White-only cells. If White plays at `v`, then

```math
A'=A\setminus\{v\},\qquad B'=B\setminus N[v],
\qquad W(A',B')=W(A,B)\setminus N[v].
```

The last equality follows directly from `v in N[v]`. Thus a White move
cannot create a White-only cell. Retiring more White permissions also cannot
create one.

For any valid upper comparison, `A_actual subseteq A_virtual` and
`B_virtual subseteq B_actual` imply

```math
W(A_{virtual},B_{virtual})\subseteq W(A_{actual},B_{actual}).
```

Indeed a virtual White-only cell is White-legal actually; if it were
Blue-legal actually, it would have to be Blue-legal virtually too. This
necessary condition holds before any numerical bound or seam condition is
considered. It complements rather than replaces the requirement that no
cross-region edge have two virtual White-legal endpoints.

## Proved obstruction to immediate closure in the six-letter alphabet

Consider the following precisely limited candidate protocol:

1. Begin at `DD_n`, with White to move.
2. White makes an opening, without an intervening Blue move.
3. Apply the one-sided comparison, separating off local gadgets and making
   recursive calls only to contiguous, full-height `PQ_k` rectangles with
   `P,Q in {D,U,V,X,R,J}` and `2 <= k < n`.

There can be **no such recursive call**. The same conclusion holds if the
local separator has more than one column, or if additional White permissions
are retired before the cut.

Proof: for `n >= 2`, the only White-only cells of `DD_n` are `(2,0)` and
`(2,n-1)`. By the resource lemma, all later virtual White-only cells must lie
at those two locations. Each of the six endpoint letters requires a
White-only cell: row 2 for D/X, row 0 for U/R, and row 1 for V/J. A `PQ_k`
rectangle with `k >= 2` therefore requires White-only cells in two distinct
columns, its two endpoints. They must be columns 0 and `n-1`, forcing
`k=n`, contrary to strict width decrease. If White occupies either original
White-only cell, at most one survives, making the obstruction stronger.

This is an obstruction to the specified comparison protocol, not to
`DD_n<0`. It also does not exclude width-one calls, whose endpoint
restrictions intersect and need not retain the separate White-only
requirements of both letters. Width-one calls and bounded gadgets can cover
only a bounded amount of an arbitrarily long board if the protocol has a
uniformly bounded number and total width of such pieces.

In particular, simply widening a bounded separator around White's first
move cannot close a width-decreasing induction using only the current
six-letter, two-ended family. At least one of the following changes is
necessary within this framework:

- include endpoints with no required White-only cell, in particular neutral
  or all-Blue endpoints using only `o` and `b`;
- wait for a Blue move, which can create White-only neighbors, and certify
  the intervening strategy and every Blue choice;
- use other recursive geometry or a proof mechanism outside this interval
  comparison protocol.

This is a symbolic obstruction. It is not a conclusion from a failed
bounded search. The algebraic invariant is independent of width, and the
geometric argument checks the required strict width decrease directly.

## Two endpoint caps show why the new support is not enough by itself

Define the new endpoint `T=bobob` (Blue legal in all five rows, White legal
only in rows 1 and 3). Let `DT_k` have D and T ends.

For every `n >= 2`, the following are valid one-sided comparisons after a
legal first White move in `DD_n`:

| White first move | Kept endpoint column | Exact cap value | Remaining rectangle | Valid upper bound |
| --- | --- | ---: | --- | --- |
| `(0,0)` | `.bwbo` | `1/2` | `TD_(n-1)` | `1/2 + DT_(n-1)` |
| `(2,0)` | `ob.bo` | `1` | `TD_(n-1)` | `1 + DT_(n-1)` |

The remaining rectangle is horizontally reflected to use the name DT.
For the corner move, White's stone forbids row 0 in the next column, while
the cap's White support `{2,4}` forces retirement of those two rows there.
For the center move, White's stone forbids row 2 in the next column, while
the cap's White support `{0,4}` forces retirement of those rows there.
Both leave White support `{1,3}`, namely T. Omitting the own-color neighbor
restriction at row 2 would incorrectly give `booob` in the center case.
Blue permissions are preserved, and the White seam supports are disjoint.
At `n=2`, D and T intersect in the one-column remainder.

After the White move, Blue is next. Consequently `DT_(n-1) <= -1/2`
would suffice for the corner construction, while the center construction
would require `DT_(n-1) <= -1`. These are new sufficient obligations,
not established families.

The independently certified base is `DT_2=0`. Therefore neither uniform
claim over **all positive even widths** can hold. In `DD_3` the two specific
virtual games have values `1/2` and `1`, so neither gives the needed
nonpositive comparison. The actual White moves still win: the certificate
below proves this for the center endpoint move. Positive virtual bounds
say nothing about positivity of the actual positions.

## Strictness and the width-one exception

The finite certificates establish

```math
DD_1=0,\qquad DD_3<0.
```

For `DD_3`, a Blue-first loss certificate gives `DD_3 <= 0`. A separate
certificate shows that White at `(2,0)` leaves a Blue-first losing child.
Thus White wins when moving first as well, proving strict negativity.
This explicit turn check is necessary; the first certificate alone would
not prove `<0`.

The center/odd-column case of the existing DD reduction gives
`DD_a+DD_b` immediately after Blue's move, with White next. At width three
it gives `DD_1+DD_1=0`, which cannot prove the required White-first win.
The direct `DD_3<0` certificate repairs precisely that exceptional base.
For odd `n >= 5`, the two positive odd side widths cannot both equal one;
if strict negativity has been established at every smaller odd width at
least three, their sum is strictly negative. This explains why the
inductive strictness target is `DD_n<0` for odd `n>=3`, with `DD_1=0`
separate. White-first obligations at larger widths remain open.

## Exact certificate mapping and reproduction

Run the checker without search:

```sh
python3 proofs/construction/research/wf_white_first_check.py
```

The optional `--generate` flag rediscovers the DAGs; it is not used by the
checker. The checker reconstructs each root from permission strings,
checks the White opening by coordinate-set neighborhoods, and calls the
existing independent checker in
[number_certificates.py](number_certificates.py). That checker universally
checks every first-player move, the supplied legal reply, the successor,
dyadic options, reachability, and a strictly decreasing finite rank.

All files below are in [wf_certificates](wf_certificates/); the
[manifest](wf_certificates/manifest.json) records exact masks and counts.

| Claim | Certificate file(s) |
| --- | --- |
| `DD_1=0` | `dd1_blue.json.gz`, `dd1_white.json.gz` |
| `DD_3<=0` | `dd3_blue.json.gz` |
| White `(2,0)` in `DD_3` leaves `<=0` | `dd3_white_center_endpoint_child.json.gz` |
| `DU_1<=-1/8` | `du1_plus_eighth_blue.json.gz` |
| `DJ_1<=-3/8<-1/4` | `dj1_plus_three_eighths_blue.json.gz` |
| `DT_2=0` | `dt2_blue.json.gz`, `dt2_white.json.gz` |
| cap `ob.bo=1` | `white_center_cap_minus_value_blue.json.gz`, `white_center_cap_minus_value_white.json.gz` |
| cap `.bwbo=1/2` | `white_corner_cap_minus_value_blue.json.gz`, `white_corner_cap_minus_value_white.json.gz` |

There are 12 certificates, 642 checkpoints, and 2,075 universally checked
move-response edges. The default checker also exhaustively checks the
support identity on the 2,560 legal White moves among five-cell path
permission states; this is regression coverage for the general set proof,
not evidence substituted for that proof.

These newly generated files supply the mappings for the claims above.
They do not provide the missing mappings for arbitrary five-row claims in
the handoff, and no missing historical mapping is treated as a mathematical
counterexample.
