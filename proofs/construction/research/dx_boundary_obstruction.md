# One-column interface contracts: DD improvements and a DX closure obstruction

Status: proved structural results, with a finite independently checked
separator catalogue. Neither result establishes the auxiliary families or the
empty five-row theorem. Endpoint letters have the permissions specified in the
[handoff](col_research_handoff.md), not stones. In particular, width-one
endpoint restrictions intersect.

## A stronger outer-even DD reduction

**Proposition.** Let `n` be odd and Blue open `DD_n` at `(0,c)`, with `c`
even. Put `a=c` and `b=n-c-1`. If both sides are nonempty, then immediately
after Blue's move, with White next,

```math
G \le DR_a + DR_b.
```

If the opening is at an endpoint and `n>1`, then

```math
G \le -\frac12 + DR_{n-1}.
```

If `n=1`, the post-opening game has value `-1/2`. Bottom-row openings follow
by vertical reflection.

**Proof.** Do not make a White reply. For an interior opening, retain the
opening column as the separator `..obo`, and put `R=wobob` at the adjacent
end of each side. The separator's Blue support is `{2,3,4}` and its White
support is `{2,4}`. Each new `R` endpoint lacks Blue only in row 0, exactly
where adjacency to the Blue opening has already removed Blue's permission.
Its White support `{0,1,3}` is disjoint from `{2,4}`. Thus actual Blue
legality is contained in virtual Blue legality, virtual White legality is
contained in actual White legality, and both seams are safe. The far `D`
endpoints stay unchanged. The right side is a horizontal reflection of
`DR_b`.

The separator is the three-vertex path `obo`. Its two possible endpoint
Blue openings leave `*`, and its middle Blue opening leaves `-2`. Either
White endpoint opening leaves `bo=1/2`. Thus

```math
\texttt{..obo}=\{*,-2\mid1/2\}=0.
```

At an endpoint, the pre-existing `D` restriction additionally excludes Blue
from row 2, changing the separator to `..wbo`, of value `-1/2`. The same
White-support check applies to its sole seam. Both values are independently
verified by the attached checker. The endpoint case with `n=1` has no side
region. This proves the proposition. Every recursive call has smaller
width. ∎

Consequently, the fixed quantitative DR hypothesis in the earlier six-case
DD reduction can be replaced by the strictly weaker sufficient target

```math
DR_k<0\qquad(k>0\text{ even}).
```

Two negative interior contributions give a negative post-Blue bound; the
endpoint separator supplies an additional `-1/2`. Under the user's proposed
stronger target `DR_k <= -1/4`, these bounds are respectively `<= -1/2`
and `<= -3/4`. This is a **conditional** DD improvement: it does not prove
the DR hypothesis. It also does not supply the separate White-first DD
obligation. White is next in this construction, and strict negativity is
explicitly retained.

## A stronger center-even DD reduction

**Proposition.** For a legal Blue opening `(2,c)` of `DD_n` with odd `n`
and even `c`, put `a=c` and `b=n-c-1`. Without a White reply,

```math
G \le DX_a+DX_b.
```

Here `a` and `b` are both positive even integers strictly smaller than `n`:
the center cell of either `D` endpoint is Blue-forbidden, so `c` cannot be
an endpoint.

**Proof.** The separator `o...o` retains actual Blue support `{0,4}` and
restricts White to the same support. Its two live vertices are isolated
shared cells, so its exact value is `*+*=0`. Each adjacent `X=bowob`
endpoint lacks Blue only in row 2, where adjacency to the opening already
removed Blue's permission. Its White support `{1,2,3}` is disjoint from
the separator support `{0,4}`. All three comparison conditions hold. ∎

Thus the following sufficient auxiliary target

```math
DX_k<0\qquad(k>0\text{ even})
```

handles these DD openings: both contributions are negative while White is
next. The user's original pair of sufficient targets already implies
strict negativity, without a classification theorem for Col values:

```math
DX_k\le0\quad\hbox{and}\quad DX_k+*\le0
\quad\Longrightarrow\quad DX_k<0.
```

Indeed, equality `DX_k=0` would make the second inequality assert `*<=0`,
which is false. Conversely, this no-reply construction requires no
star-absorption claim; strict negativity alone suffices. It avoids playing
a White move in one separator star and leaving the other star to be
absorbed by a side game. This is again a conditional simplification of the
DD induction, not a proof of the arbitrary-width DX target.

## A precise obstruction to closure using only the six original pairs

Let

```text
F0 = {DD, DU, DV, DR, DX, DJ},
```

including horizontal and vertical reflections. Consider the following
candidate induction rule: after a Blue opening in a `DX_n` strip, optionally
make one White reply anywhere, isolate only the opening column as a
separator, and represent each nonempty retained side by **one** member of
`F0`, using the permission comparison directly. The separator's game and
permissions may be chosen arbitrarily. The sides cannot be re-tiled,
reshaped, or replaced using some additional game identity within this rule.

**Theorem (failure of this rule).** If Blue opens at `(r,c)` with
`r in {0,1,3,4}`, `1 <= c <= n-3`, then the retained right side, which has
width at least two and retains the original `X` endpoint, cannot be any
member of `F0`. This holds after no White reply or any legal single White
reply anywhere on the board. Thus this particular rule cannot close a
mutual induction for the six original pair families. There are such
openings for arbitrarily large even `n`, so finitely many base cases do not
remove the obstruction.

**Proof.** Every member of `F0` has a `D` endpoint. Consider either possible
placement of that endpoint on the retained side.

* At the original `X` end, actual White is forbidden in rows 0 and 4.
  `D` requires White at both rows. Subsequent moves cannot restore White
  permissions, so this placement violates virtual White ⊆ actual White.
* At the cut end `(column c+1)`, the row-2 cell is initially shared, and
  the off-center Blue opening is not adjacent to it. It remains
  Blue-legal unless White's one reply occupies exactly this cell. In that
  event it is also White-illegal. In either event it cannot meet `D`'s
  simultaneous requirements that Blue be forbidden and White be legal
  there: the former is needed by actual Blue ⊆ virtual Blue, and the
  latter by virtual White ⊆ actual White.

The two endpoint columns are distinct even when the retained width is two.
Vertical reflection fixes `D` and `X`, and the same row-2 argument handles
rows 3 and 4. This eliminates both orientations of every candidate. ∎

The width-at-least-two condition is essential to the stated proof. For a
width-one side, the two endpoint masks intersect and the separate endpoint
argument does not apply. The theorem does **not** assert impossibility for
wider separators, added endpoint states, several pieces per side, local
move sequences with further Blue moves, or exact graph simplifications. It
also says nothing adverse about the true sign of `DX_n`.

## What an expansion using the named endpoint alphabet must add

This paragraph is a necessary interface condition, not a claimed sufficient
or uniquely minimal expansion. Allow all unordered pairs from the named
alphabet and its vertical reflections, under the same one-column rule.
At the original `X` end, the only admissible named endpoint is `X` itself:
each named endpoint forbids Blue at exactly one row, forcing that row to be
2, and the remaining possibility `D` fails its White support.

At the cut end, each named endpoint's unique Blue-forbidden cell is
White-legal. White's reply cannot create such a cell by occupying it.
Therefore its row must be the row whose Blue permission was removed by
adjacency to the opening. This forces:

| Blue opening row | Possible cut-facing named endpoints | Necessary new X-pair disjunction |
| --- | --- | --- |
| 0 | U or R | at least one of XU, XR |
| 1 | V or J | at least one of XV, XJ |
| 2 | D or X | DX or XX |

Rows 4 and 3 give the vertically reflected versions. A reply can make some
of these possibilities inadmissible; it cannot add other named
possibilities. The table forces at least one new pair in each of the first
two rows if this induction rule is retained. It does not force all four
pairs, nor prove that those additions are enough. The relevant width
parities also need separate bounds: for even parent width, the two side
widths have opposite parity.

Relative endpoint orientation also matters after expansion. For example,
`UU` and `U reverse(U)` are different permission templates; reflecting the
whole board does not identify these two. A list of unordered pairs of six
unoriented names must not silently discard such states.

## Finite support and value catalogue

For a neutral opening column and fixed named endpoints on both cuts, the
catalogue uses the actual remaining Blue support and the **largest** White
support compatible with both side endpoints. For these fixed interfaces,
extra Blue permissions or fewer White permissions can only increase the
comparison game. These maximal-support choices therefore dominate the
other scalar upper bounds for that same interface. A White reply in the
opening column is allowed exactly when its row is White-forbidden in both
adjacent endpoint patterns.

The complete no-reply catalogue is:

| Opening row | Near endpoints | Separator | Exact value |
| --- | --- | --- | --- |
| 0 | U,U | `.wbob` | 0 |
| 0 | U,R | `..bbb` | 2 |
| 0 | R,R | `..obo` | 0 |
| 1 | V,V | `w.wbo` | -3/2 |
| 1 | V,J | `...bb` | 1 |
| 1 | J,J | `...ob` | 1/2 |
| 2 | D,D | `bw.wb` | 0 |
| 2 | D,X | `b...b` | 2 |
| 2 | X,X | `o...o` | 0 |

The full JSON also contains all 12 admissible same-column White-reply
contracts, their left/right/separator White supports, and exact values.
Mixed endpoints have expensive separator values despite individually
useful boundary states. These are interface costs of this construction;
they are not signs or lower bounds for the actual board.

Artifacts:

* [dx_interface_contracts.json](dx_interface_contracts.json): the 21 local contracts.
* [dx_interface_contracts.py](dx_interface_contracts.py): discovery/regeneration using alternating outcomes with dyadic/star summands.
* [dx_verify_interface_contracts.py](dx_verify_interface_contracts.py): independent, search-free contract checker using recursive short-game order.

Run:

```sh
python3 proofs/construction/research/dx_verify_interface_contracts.py
```

Recorded output:

```text
Verified 21 complete one-column contracts and '..wbo' = -1/2.
Verified 57216 rejected original-family side embeddings (finite regression only).
```

The first line checks every legal same-column reply in the stated catalogue
and every exact local value. The second line is merely regression coverage
of the geometric obstruction, including width-two retained sides and
White replies anywhere. The arbitrary-width theorem is proved by the
two-cell permission argument above, not by those finite examples.
