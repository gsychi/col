# Four-column caps repair a reachable marked-X induction case

Status: **proved local comparisons and a width-decreasing conditional
reduction**, with independent finite certificates. The arbitrary-width
ordinary auxiliary bounds remain hypotheses. This is a genuine additional
part of the [central-phase assembly](round2_wf_delayed_phase.md), not a
closed F-family induction or a proof of the five-row theorem.

## A positive reduction using the original auxiliary targets

As in the preceding round, `F_X(k,p,t)` is `DX_k` after an actual White
move `(t,p)`. Consider the reachable diagonal

```math
k\ge6\text{ even},\qquad p=k-2,\qquad t=2.
```

It is in the exact required X domain: `p+1<=k<=2p-2`. Suppose Blue now
plays in column `c=k-4`. Absorb the last four columns into one cap, keeping
the original X endpoint and the earlier White stone inside the cap.
The local White stone is at `(2,2)` and the local Blue opening is at
`(r,0)`. Restrict White in local column 0 to the complement of the indicated
left interface's White support. There is **no additional White reply**
before making the comparison.

The finite cap values are:

| Normalized Blue row | New endpoint of the left strip | Exact four-column cap value | Row-major cap masks `(A,B)` |
| --- | --- | ---: | --- |
| 0 | R = `wobob` | `0` | `(1045484,500134)` |
| 1 | V = `bwbob` | `-1` | `(1045198,500135)` |
| 2 | X = `bowob` | `0` | `(1040623,499879)` |

Vertical reflection covers rows 3 and 4, because D, X, and the preplayed
row-2 stone are vertically symmetric. A reflected R or V on the left has
the same value as its unreflected version next to D.

**Theorem.** After these Blue openings,

```math
G\le
\begin{cases}
DR_{k-4},&r=0,4,\\
DV_{k-4}-1,&r=1,3,\\
DX_{k-4},&r=2.
\end{cases}
```

The proof is parameterized by k. The actual Blue opening excludes Blue
from row r in the preceding column, exactly the Blue exclusion required
by the new endpoint. All its other Blue permissions are retained. Its
White support is disjoint from the cap's chosen support. The preplayed
White stone is two columns inside the cap, so it has no neighbor in the
left strip. All remaining permissions in both pieces are inherited from
the actual position. Thus actual Blue legality is contained in virtual
Blue legality, virtual White legality is contained in actual White
legality, and no cross-region edge has two virtual White-legal endpoints.
The left recursive width is the positive even number `k-4<k`.

These comparisons close every row in the specified column using only the
**original** sufficient targets from the user:

- `DR_(k-4)<=-1/4` gives a strictly negative result.
- `DV_(k-4)<=1/2` gives a result at most `-1/2`.
- The paired targets `DX_(k-4)<=0` and `DX_(k-4)+*<=0` imply
  `DX_(k-4)<0`: equality to zero would make the latter game star, which is
  not nonpositive.

White is next immediately after the Blue opening, so strictness is
essential and is supplied in all three cases. No strengthened DR/DV/DD
bound, no arbitrary-width F hypothesis, and no restricted three-row theorem
is used in this reduction.

For the first instance `F_X(6,4,2)`, the center-row opening therefore has

```math
G_{\text{after Blue }(2,2)}\le DX_2=-1.
```

This is a proved branch of the marked-state induction. Other columns of
this phase family, and the other required F families, still need their
own reductions.

## Why this is a substantive improvement over a single-column cut

The same reachable instance gives a complete, independently checked
obstruction to a precisely stated smaller candidate class.

Start at `DX_6`, play White at `(2,4)`, then Blue at `(2,2)`. Consider all
immediate upper comparisons that partition the board into columns 0–1,
column 2, and columns 3–5, retain the internal grid edges of each region,
and change permissions only in the allowed comparison direction. No extra
move is made before cutting.

The separator has minimum allowed Blue set `{0,4}` and can keep any White
subset `S` of `{0,1,3,4}`. For a fixed S, the strongest permissible side
permissions keep every actual White cell except rows in S at the seam.
The newly induced endpoint has Blue excluded in row 2 and White excluded
in S. Call it `Q(S)`. The minimal relaxed game for this support is

```math
(D,Q(S))_2\; +\; C(S)\; +\;
\bigl[(Q(S),X)_3\text{ after White at }(2,1)\bigr].
```

This is exhaustive: increasing Blue permissions, removing further White
permissions, or retiring additional White-only cells produces a game at
least as large as this one. The right-side mark includes its actual
neighbor exclusions; it is not replaced by an empty rectangle.

The following are certified **lower bounds** on the three components and
their sum. Rows in S use zero-based indices.

| S | Q(S) | Separator lower bound | Left lower bound | Marked right lower bound | Sum lower bound |
| --- | --- | ---: | ---: | ---: | ---: |
| empty | `oowoo` | 2 | -1 | 1 | 2 |
| 0 | `bowoo` | 3/4 | -1 | 1 | 3/4 |
| 1 | `obwoo` | 1 | 0 | 3/2 | 5/2 |
| 0,1 | `bbwoo` | 1/2 | 1/2 | 3/2 | 5/2 |
| 3 | `oowbo` | 1 | 0 | 3/2 | 5/2 |
| 0,3 | `bowbo` | -1/4 | 0 | 3/2 | 5/4 |
| 1,3 | D | 0 | 1 | 2 | 3 |
| 0,1,3 | `bbwbo` | -1/2 | 3/2 | 2 | 3 |
| 4 | `oowob` | 3/4 | -1 | 1 | 3/4 |
| 0,4 | X | 0 | -1 | 1 | **0** |
| 1,4 | `obwob` | -1/4 | 0 | 3/2 | 5/4 |
| 0,1,4 | `bbwob` | -3/4 | 1/2 | 3/2 | 5/4 |
| 3,4 | `oowbb` | 1/2 | 1/2 | 3/2 | 5/2 |
| 0,3,4 | `bowbb` | -3/4 | 1/2 | 3/2 | 5/4 |
| 1,3,4 | `obwbb` | -1/2 | 3/2 | 2 | 3 |
| 0,1,3,4 | `bbwbb` | -1 | 2 | 2 | 3 |

The best support, S={0,4}, is certified in both directions:

```math
DX_2+0+F_{XX}(3,1,2)=-1+0+1=0.
```

Here `F_XX` is explicitly the marked two-X-ended game, not the D-anchored
phase family. White is next, and every virtual game in this candidate
class is nonnegative. Therefore no member of this exhaustive class can
supply a White-first winning comparison at this opening. This is not a
conclusion from a failed bounded search.

It is also **not** a counterexample to `F_X(6,4,2)<=0`: the four-column
construction above proves that the actual post-Blue position is at most
`-1`. The loss of useful interaction in the one-column comparison is the
entire obstruction. The wider cap repairs it while returning to the
original ordinary boundary families.

## A local central reply that really fails

The strengthened DD hypothesis in the previous conditional assembly
arises in the odd-m branch where White opens in center row 1 and Blue
replies in center row 2. An attempted way to avoid that quantitative
hypothesis is to reply immediately in center row 4 and hope to obtain a
dead-column reduction after Blue takes the remaining top cell.

This exact local policy fails already on `DD_7`. In center column 3, the
sequence is

```text
White (1,3), Blue (2,3), White (4,3), Blue (0,3).
```

All four moves are legal. The whole center column is then dead: four cells
are occupied and row 3 is forbidden to Blue by row 2 and to White by row 4.
The remaining graph is exactly the disjoint sum

```math
DK_3+KD_3,\qquad K=\texttt{wbwob}.
```

The independently certified identity is `DK_3=0`; horizontal reflection
also gives `KD_3=0`. Thus the actual remaining game is zero, with White
next, so White loses. This refutes the specified reply, not the initial
central White strategy. An optimized finite solver finds White's row-3
reply and several off-column replies successful in the same DD7 branch;
those latter observations are experimental and are not used in the proof.

The geometric difficulty is concrete. After White row 1 and Blue row 2,
the top central cell is Blue-only and permanently White-illegal. White
cannot occupy it to erase the remaining Blue opportunity. An improvement
that avoids a positive scalar cap must retain its Blue interactions until
Blue plays that cell or a neighbor, or use a different local protocol.

## What a recursive phase proof still has to track

There is a width-decreasing geometric transition beyond the anchored F
notation. Let `F_(P,Q)(n,p,t)` be `(P,Q)_n` after White at `(t,p)`, and let
Blue open in column c at distance at least two from p. For any safe
no-reply separator contract with side endpoint S and cap value s,

```math
c<p:\quad
G\le(P,S)_c+s+
F_{(S,Q)}(n-c-1,p-c-1,t),
```

```math
c>p:\quad
G\le F_{(P,S)}(c,p,t)+s+(S,Q)_{n-c-1}.
```

Every positive recursive width is smaller than n. Adjacent moves require
checking the original White stone's exclusion at the separator; the
compatibility condition for these complementary-support contracts is
that S retains White permission in row t. Same-column moves consume the
mark inside a finite local cap, as in the previous central table.

However, a cut to the left of the mark replaces D on the marked side by S.
Thus the six D-anchored phase families do not close by themselves. A
literal one-column closure would need ordered endpoint pairs, their
vertical reflections, and correctly transformed position domains. The
concrete obstruction above is already the transition to marked XX, whose
value here is +1. A new boundary letter alone does not remove that lost
margin. The four-column cap avoids this particular positive marked
subproblem by preserving its interaction with the separator.

This leaves a clear positive target: find a bounded collection of such
end caps and delayed contracts covering the remaining marked-state
openings, and make every returned assertion one of the hypotheses actually
proved by the mutual induction. The current caps cover one infinite
parameterized opening class, not all of F_X.

## Certificate mapping and reproduction

Run the search-free checker:

```sh
python3 proofs/construction/research/round3_wf_check.py
```

The checker reconstructs every root from endpoint patterns and legal
moves, verifies every legal universally quantified move and supplied
response through `number_certificates.verify`, and checks geometry with
coordinate-derived masks. `--generate` rediscovers the response DAGs but
is not used by the default checker.

Artifacts are listed in
[`round3_wf_certificates/manifest.json`](round3_wf_certificates/manifest.json):

- `s*_separator_lower`, `s*_left_lower`, `s*_right_lower` prove all 48
  component lower bounds in the exhaustive separator table.
- The three `s17_*_upper` files establish the exact best virtual value zero.
- `cap4_r_*`, `cap4_v_*`, `cap4_x_*` establish both directions of the new
  four-column cap values.
- `dk3_upper` and `dk3_lower` establish the actual local-reply counterexample.

The package contains 59 DAG certificates, 5,408 checkpoints, and 18,742
universally checked response edges. It checks all 16 separator contracts
and the exact DD7 continuation. Thirty-nine embedding checks at even
widths 6 through 30 regress the four-column construction; the written
comparison proof, not that finite sweep, supplies the arbitrary-width
scope and strictly decreasing rank.

Additional raw-solver files are discovery only:
`round3_wf_phase_x8_probe.json`, `round3_wf_strong_odd7_probe.json`,
`round3_wf_fx6_replies.json`, and `round3_wf_cap5_probe.json`.
The targeted width-eight X-phase and width-seven strengthened ordinary
queries all reached their stated five-million-state limits. Unknown means
Unknown. The unsuccessful scalar alternatives and these search budgets
supply no claim about the sign of the original families.
