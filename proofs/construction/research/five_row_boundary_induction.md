# Five-row boundary induction: dependencies and an interface obstruction

Status: **partial mathematical advance; the five-row theorem remains open.**
This note continues the [latest handoff](col_research_handoff.md) and the
[three-row theorem](../empty_3xn_theorem.md). It proves an obstruction to closing
the current boundary family by immediate interval separators, checks the finite
contracts of the DD reduction, and isolates the remaining induction obligations.
It also improves the outer-even and center-even DD cases: no-reply separators
make `DR_even<0` and `DX_even<0` sufficient, removing the fixed DR margin and
the starred DX obligation from this alternative reduction. It does not revive
the obstructed fixed `DX -> L` projection.

## Definitions and comparison direction

Rows are numbered 0 through 4, columns 0 through `n-1`. The patterns, read down
an endpoint column, are

| Name | Pattern | Blue-forbidden row | White support |
| --- | --- | --- | --- |
| D | `obwbo` | 2 | {0,2,4} |
| U | `wbobo` | 0 | {0,2,4} |
| V | `bwbob` | 1 | {1,3} |
| X | `bowob` | 2 | {1,2,3} |
| R | `wobob` | 0 | {0,1,3} |
| J | `owobo` | 1 | {0,1,2,4} |

Each pattern has precisely one White-only cell, at its Blue-forbidden row.
`PQ_n` means P at the left end and Q at the right end, with shared permissions
elsewhere. At `n=1`, **intersect both permissions**, rather than taking a sum or
choosing one endpoint. Horizontal reflection exchanges P and Q. DD also permits
vertical reflection; reflect the *whole* virtual construction when normalizing
an opening to rows 0, 1, or 2. Empty side regions have value 0 and have no endpoint
contract: no hypothesis about `PQ_0` is used.

Every construction here uses

`A_actual ⊆ A_virtual`, `B_virtual ⊆ B_actual`,

and no edge between different virtual regions has two virtual White-legal
endpoints. Only then is `G_actual ≤ sum(virtual regions)` asserted.

For a short game, `G≤0` means Blue loses when next; `G<0` also requires White to
win when next. After a Blue opening a negative upper bound suffices. A merely
nonpositive upper bound needs a further White move with a nonpositive child.
After the specified White reply, Blue is next and a nonpositive bound suffices.

## Complete DD Blue-opening dependency table

Let `n≥3` be odd, `a=c`, and `b=n-c-1`. Normalize the opening row to `r≤2`.
For an interior column both a and b are positive. Since `n-1` is even, a and b
have the same parity as c. Every positive recursive width is strictly less than
n. The following bounds are conditional on the auxiliary targets; their
geometric comparison contracts themselves are unconditional.

| Opening and location | White action | Virtual separator | Smaller games | Next player at comparison | Required conclusion |
| --- | --- | --- | --- | --- | --- |
| r=0, c odd | No prior reply | `.wbob` = 0 | `DU_a + DU_b`; positive odd a,b | White | `<0` from two strict U bounds |
| r=0, c even, interior | Reply `(2,c)` | `...bo` = 1/2 | `DR_a + DR_b`; positive even a,b | Blue | `≤ -1/4+1/2-1/4 = 0` |
| r=0, c=0 or n−1 | Reply at opposite outer row in the same column, `(4,c)` | `..wb.` = 0 | One `DR_(n-1)` up to horizontal reflection; other side empty | Blue | `≤-1/4`; no +1/2 charge |
| r=1, c even, interior | No prior reply | `w.wbo` = −3/2 | `DV_a + DV_b`; positive even a,b | White | `≤1/2−3/2+1/2 = −1/2 <0` |
| r=1, c=0 or n−1 | No prior reply | `w.wbo` = −3/2 | One `DV_(n-1)`; other side empty | White | `≤1/2−3/2 = −1 <0` |
| r=1, c odd | No prior reply | `...ob` = 1/2 | `DJ_a + DJ_b`; positive odd a,b | White | `<−1/4+1/2−1/4 = 0` |
| r=2, c even | Reply `(0,c)` | `....o` = star | `DX_a + DX_b`; positive even a,b | Blue | `(DX_a+star)+DX_b ≤0` |
| r=2, c odd | No prior reply | `bw.wb` = 0 | `DD_a + DD_b`; positive odd a,b | White | One DD strictly negative and the other nonpositive |

There are no endpoint center openings: row 2 is Blue-forbidden at both D ends.
The U, J, and final D cases cannot have empty sides because c is odd and both
endpoint column indices are even. In the X case c is positive and even and is
not `n−1`, so `a,b≥2`; the star is never assigned to an empty side.

The inherited D restriction does not change the V separator at an endpoint.
The corner rule is genuinely different from the interior R rule; applying the
interior rule with an empty side would leave the unsupported upper bound
`1/2+DR_(n-1)≤1/4` under the corrected target.

### Finite local checks and the all-width geometric argument

The [checker](dd_reduction_check.py) defines the ten local contracts (the six
cases, the corrected corner, and the three new no-reply R/X variants),
explicitly plays the local moves, and checks both permission inclusions and
White seam disjointness. Eighteen new response-DAG
certificates in [dd_local_certificates](dd_local_certificates/) prove both
inequalities for the nine dyadic separator instances: 70 checkpoints and 80
universally checked first-move/reply edges. The isolated shared vertex `....o`
is star directly: both players have exactly one move to the empty game.
Generation uses minimax; verification uses the existing independent
[set-based DAG verifier](number_certificates.py).

The arbitrary-width extension is symbolic. A Blue opening changes its column
and removes Blue permission only at row r in either adjacent column. A same-
column White reply removes White permission only at its row in the adjacent
columns. All other columns retain their original permissions. Thus the checked
near-end mask applies to either side at every length. Its intersection with an
inherited D mask at side width one preserves the inclusions: if
`A_actual⊆A_near` and `A_actual⊆A_D`, then
`A_actual⊆A_near∩A_D`, and similarly for the White inclusion. This intersection
can only remove White seam support. Width-zero sides have no edges or cells.
There are exactly two possible seams, both incident with the separator and
both checked locally. This proves the composition for every n; a separate
assembly sweep only tests its implementation.

## New improvement: the R case needs no immediate reply

**Proved arbitrary-width comparison.** After Blue opens `(0,c)` in `DD_n`,
keep the separator `..obo` at an interior column and use R at each adjacent
side endpoint. No White reply is made before the comparison. Then

`G_after_Blue ≤ DR_a + DR_b`.

After a boundary opening instead keep `..wbo`, obtaining

`G_after_Blue ≤ −1/2 + DR_(n−1)` for `n≥3`.

Here `..obo=0` and `..wbo=−1/2` are exact finite values, proved by the new
independent response-DAG certificates. In the interior, the actual opening
leaves Blue legal on rows 2,3,4 of the separator; retaining White only at 2,4
gives `..obo`. R has Blue permission on every row except 0, matching the
neighbor effect of the Blue opening; its White support `{0,1,3}` is disjoint
from `{2,4}`. At a D endpoint the separator's row 2 was already Blue-forbidden,
so it is `..wbo`. All other cells obey the same width-independent comparison
argument given above, including side width one.

Use this construction for even c, so each positive side width is even. Under
the requested `DR_even≤−1/4` target it gives **strict** post-Blue bounds:
`≤−1/2` inside, and `≤−3/4` at an endpoint. White is next and wins from these
bounds. Thus the two original R rows in the table can be replaced as follows:

| Opening | White reply before comparison | Bound | Sufficient DR hypothesis |
| --- | --- | --- | --- |
| r=0, c even, interior | None | `DR_a+DR_b<0` | Both positive even DR games strictly negative |
| r=0, c=0 or n−1 | None | `−1/2+DR_(n−1)<0` | `DR_(n−1)≤0` already suffices |

In particular, the **weaker uniform target `DR_k<0` for positive even k is
sufficient** in the conditional DD induction. No fixed negative margin is
needed. The original table remains above to audit the handoff's six-case
construction and its explicit replies; this improvement replaces only the
outer-even choice. No arbitrary-width DR bound is proved here.

## New improvement: a no-reply X cut removes the star obligation

For a center opening `(2,c)` with even c, retain the separator `o...o`, and
use X on each side's cut endpoint. Blue is legal only on separator rows 0,4;
retaining White only there preserves the comparison. X's White support is
`{1,2,3}`, disjoint from the separator's `{0,4}`. The two shared separator
cells are disconnected, so its value is `star+star=0`. The new local DAGs
also independently certify this zero value.

Thus, with White next and no prior reply,

`G_after_Blue ≤ DX_a + DX_b < 0`

provided `DX_k<0` for positive even k. Both a and b are at least two, since
center endpoint openings are illegal. All recursive widths decrease.

The original targets `DX_k≤0` **and** `DX_k+star≤0` imply `DX_k<0`: equality
`DX_k=0` would make the second inequality `star≤0`, which is false. This
argument applies to arbitrary short games and needs no special classification
of Col values. Conversely we do not claim that every negative short game
absorbs star; the new construction simply has no star to absorb. Therefore
strict negativity alone is an alternative sufficient DX target for DD.
It remains an unproved arbitrary-width target.

## What the auxiliary targets would prove

The sufficient targets in the question are:

- `DU_k<0` for positive odd k;
- `DV_k≤1/2` and `DR_k≤−1/4` for positive even k;
- `DX_k≤0` and `DX_k+star≤0` for positive even k;
- `DJ_k<−1/4` for positive odd k.

The new constructions permit replacing the listed DR target by `DR_even<0`
and replacing the pair of X targets by `DX_even<0`. In the original reply-based
X construction, its two inequalities remain separate obligations: dropping the
starred one while retaining only nonpositivity is invalid (`0+star` is the
counterexample). The new no-reply construction instead requires strictness
and removes that star entirely.

The D intersection at width one is D itself, and `DD_1=0`, not strictly
negative. Consequently at the center opening `(2,1)` of `DD_3`, the last row of
the table gives `DD_1+DD_1=0` with **White next**. This remains a valid comparison
but does not prove a White win. A separate base certificate for `DD_3<0` resolves
that case; it is included with the [White-first work](five_row_white_first.md).
At all odd `n≥5`, the positive odd widths a and b in this case sum to `n−1≥4`,
so at least one is ≥3. That side can supply the required strictness.

At width one the U and J base positions must also use intersections. They are
`DU_1 = wbwbo` and `DJ_1 = o.wbo`. These are genuine positive-odd target cases,
not empty-side conventions. Their finite targets can be verified separately;
they do not establish the arbitrary-width statements.

**Conditional induction theorem.** Suppose the five auxiliary target families
hold on their stated domains (optionally with DR and DX replaced by the alternative strict targets). Suppose `DD_1=0`, `DD_3<0`, and for every odd `n≥5`
there is a legal White first move whose child is nonpositive, with a proof
using only smaller-width hypotheses (or an explicit descending alternative
rank). Then strong induction proves `DD_n≤0` for every positive odd n and
`DD_n<0` for every odd `n≥3`.

Proof: the table proves Blue-first loss using auxiliary results at widths <n
and smaller DD strictness. The separately supplied White-first witness proves
White-first win. Together they give strict negativity at n and make it
available for larger D cases. The rank n decreases in every invocation in the
table. A purported White-first proof using `DD_n<0` again would be circular.

This formulation is a conditional theorem, **not a closed induction**. In
particular, proving `DD_n≤0` at a width does not discharge its White-first
obligation at that same width.

## New obstruction: White-only support cannot be created by relaxation

Write `Wonly(A,B)=B\A`. In any admissible comparison,

`Wonly(A_virtual,B_virtual) ⊆ Wonly(A_actual,B_actual)`.

Indeed, a virtual White-only cell is actual White-legal because virtual White
permissions are a subset; it is actual Blue-illegal because all actual Blue
permissions must be retained virtually. Also, a White move creates no new
White-only cells: the only removed Blue permission is the occupied cell,
which loses its White permission as well. Further deletion of White
permissions cannot create White-only cells either.

Initially `DD_n`, for n≥2, has exactly two White-only cells, `(2,0)` and
`(2,n−1)`. Thus after a White first move, any virtual full-height interval of
width ≥2 with both endpoints from D,U,V,X,R,J must use these two inherited
cells for its two distinct required White-only endpoints. It must therefore
span the whole original width. A strictly narrower such interval is
impossible. This applies regardless of how a bounded-width local separator is
shaped or scored; no local numerical improvement changes the permission
invariant. See the [detailed proof and base certificates](five_row_white_first.md).

**Precisely eliminated candidate.** An immediate White-first induction step
that plays one White move, cuts into contiguous full-height recursive
rectangles, and uses only two-ended rectangles of width ≥2 with endpoints in
this six-letter alphabet, all narrower than n, cannot supply any such
recursive call. A scheme relying on at least one such call is impossible.
This does not exclude a separate all-finite-piece tiling scheme, one-ended
states, another geometry, an endpoint without a White-only requirement, or a
bounded dialogue that first allows a Blue move. In particular it does not
prove that DD is nonnegative.

The advance is a necessary **interface** condition for a new induction: an
immediate White-first interval reduction must allow a new cut endpoint with
no White-only cell, or use a different decomposition mechanism. Merely adding
more ordered pairs drawn from the current six letters cannot fix this step.

## New obstruction on the DX side

The present target pairs are `{DD,DU,DV,DR,DX,DJ}` and their geometric
reflections. In a `DX_n` interior Blue opening in row 0 or 1, consider removing
just the opening column, with any single legal White reply allowed. Suppose
the side retaining the original X end has width ≥2. No target pair embeds on
that side:

- D cannot be the old X endpoint: D needs White permission at both outer rows,
  while X has permanently removed both.
- D cannot be the new endpoint beside the opening column: D needs a White-only
  center cell. The off-center Blue opening has not removed its Blue permission.
  A White reply elsewhere leaves it Blue-legal; a White reply on it occupies it
  and removes White permission too.

Each old target pair has a D endpoint, so these two exclusions are exhaustive.
This is an all-width legality obstruction to that specific construction class,
independent of the separator's value and independent of the sign of DX. The
[detailed DX study](dx_boundary_obstruction.md) checks the finite support
possibilities. Among the named masks, a new endpoint next to a row-0 opening
must have its White-only cell at row 0 (U/R); next to row 1 it must be V/J.
Consequently this style of recursion forces new X-pairs, at least one of
`XU/XR` and at least one of `XV/XJ`, with applicable reflections. These are
necessary state choices, not established numerical bounds.

## Remaining dependencies and next experiment

The present six-pair system does not close. The following work remains before
it could imply the requested empty-board theorem:

| Dependency | Current status | Required next result |
| --- | --- | --- |
| Six DD Blue-opening contracts, corner correction, and improved R/X cuts | Local geometry proved; separator values independently checked; DR and DX strict negativity suffices in the new cuts | None for these contracts |
| `DD_1=0`, `DD_3<0` | New independent finite certificates | No inference beyond these widths |
| DU, DV, DR, DX, DJ on their full parity domains | Targets, supported by handoff finite results | Width-decreasing symbolic constructions |
| White-first `DD_n` for odd n≥5 | Separate unresolved obligation; immediate current-alphabet interval reduction obstructed; simple new T compensation fails at width 2 | Endpoints without White-only requirements plus viable bounds, delayed play, or another geometry |
| DX off-center recursion | Original six pairs obstructed for one-column splits | New X-pairs or wider/delayed constructions |
| Ordinary empty odd-width 5×n bridge | Unresolved | A turn-correct response to every ordinary opening |

A useful next finite search should distinguish White-first states from
Blue-first states, include endpoints with no required White-only cell (such
as all-Blue masks) for the former, and include new X-pairs forced by the latter.
Every transition must record both White support and numerical obligations,
not just a best scalar bound.
A local dialogue must include all legal Blue continuations, including moves
outside its local window. Its recursive leaves must decrease width, or use a
stated lexicographic rank such as `(width, remaining dialogue depth)`; the
second component must actually decrease for any equal-width transition.

The fixed `DX_n≤L_n` route remains unavailable: the handoff establishes
`L_12=0` and nonnegative, eventually unbounded-positive lower bounds thereafter.
This says nothing adverse about the sign of DX itself. The empty-three-row
theorem may be used only for regions whose virtual permissions and graph are
really an empty rectangle.

## Reproduction and provenance

From the repository root:

```sh
python3 proofs/construction/research/dd_reduction_check.py
python3 proofs/construction/research/dd_reduction_check.py --generate
```

Also run the independent companion checks:

```sh
python3 proofs/construction/research/wf_white_first_check.py
python3 proofs/construction/research/dx_verify_interface_contracts.py
python3 proofs/construction/research/provenance_check.py
```

The default run is search-free for the numerical response-DAG certificates; `--generate`
regenerates them with minimax before checking. The default geometry regression
covers 735 vertically normalized openings at odd widths 3 through 31, once for
the original reduction and once with the improved R/X cuts. Its role
is regression, not proving the quantified all-width statement.

The [verification record](five_row_verification.json) saves the four new-check
commands and outputs, plus hashes of the 30 response-DAG certificates (712
checkpoints and 2,155 universally checked move-response edges). The 21-contract
interface catalogue is also independently checked by recursive short-game
order, separately from these response DAGs. The record also includes the
replay of the recovered historical three-row bases and J5 root.

See [certificate provenance](five_row_certificate_provenance.md) for exact
available root mappings and missing mappings. Missing handoff artifacts are
repository audit gaps, not counterexamples to the corresponding mathematical
arguments. The new obstruction proofs above are local permission arguments
and do not depend on the absent later L or five-row certificate collections.
