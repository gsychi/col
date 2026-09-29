# Exact-bound closure for 5-row strip families: obligations and soundness

Stream: `closure/`, round five. Tool: `xclosure.cpp` (built on `xcolout5.cpp`).
Labels as in [`../HANDOFF.md`](../HANDOFF.md). Everything the engine outputs is
**EVIDENCE**; the argument below is what turns a complete, replayed rule table
into a proof.

Conventions: Blue = Left = positive, White = Right. Shadow state `(A, B)`.
Blue at `v`: `(A∖N[v], B∖{v})`; White at `v`: `(A∖{v}, B∖N[v])`. Strips have
5 rows. `G ⧏ H` means "not `H ≤ G`".

## 1. The closure lemma being proved

A **family** `F` is given by two fixed 3-column end blocks `L`, `R`. Its member
`F_w` (`w ≥ 6`) is the 5 × w strip with `L` in columns 0–2, `R` in columns
`w−3..w−1` and neutral (legal for both) columns in between.

Each family used gets a bound `q_F[p]`, a value `x` or `x + *` with `x`
dyadic, for each parity `p`. The claim is

> **(C)** For every family `F` in the final list, every parity `p` with a
> closed status, and every `w ≥ 6` with `w ≡ p (mod 2)`: `F_w ≤ q_F[p]`.

For the root `KD` (DD after White `(2,0)`) with `q[1] = 0`, (C) gives
`K_n ≤ 0` for odd `n ≥ 7` and so `DD_n ≤ −1` by the reserve move
(HANDOFF §2.3).

## 2. Facts used (all PROVED in `../literature/COL_VALUES.md`)

- F1–F4, Conway's order: `G ≤ H` iff no `G^L` has `H ≤ G^L` and no `H^R` has
  `H^R ≤ G`. The order is transitive and compatible with `+`.
- Thm 5: every Col position, and every finite sum of Col positions, numbers
  and stars, equals `y` or `y + *` for a dyadic `y`.
- Table 1 / F4: for `a = y + ε*`, `b = x + η*`:
  `a ≤ b` iff (`ε = η` and `y ≤ x`) or (`ε ≠ η` and `y < x`).
- Lemma 2 (comparison principle): cut the strip at column seams; for every
  cut edge with both endpoints White-legal, remove White's permission at one
  endpoint. Then `G ≤ Σ pieces`. Removing White permissions and cutting
  Blue–Blue edges only increase the right side.
- Monotonicity (special case of Lemma 2): fewer Blue permissions or more
  White permissions on the same graph gives a smaller or equal game.
- Lemma 4: for `v ∈ B`, `G ≤ G^{R,v} + *`; for `v ∈ B∖A` (White-only),
  `G ≤ G^{R,v} − 1`.

## 3. Deriving the obligations from the canonical form of `q`

Let `G = F_w` and `q = x + η*` in canonical form. By Conway's definition,
`G ≤ q` iff

- **(B)** no Blue option has `q ≤ G^L`, i.e. every `G^L ⧏ q`; and
- **(W)** no Right option `q^R` of `q` has `q^R ≤ G`, i.e. `G ⧏ q^R` for each.

**Sufficient conditions for (B).** Fix a Blue opening `G^L`.

1. *With a White reply.* If some White move gives `G^{LR}` and a cut gives
   `G^{LR} ≤ Σ` with `Σ ≤ q`, then `G^{LR} ≤ q`. In `G^L − q` White moves to
   `G^{LR} − q ≤ 0` and wins, so `q ≰ G^L`, i.e. `G^L ⧏ q`.
2. *With no reply.* If a cut gives `G^L ≤ Σ` and `Σ ⧏ q`, then `G^L ⧏ q`:
   otherwise `q ≤ G^L ≤ Σ`, contradicting `Σ ⧏ q`.

   `Σ < q` implies `Σ ⧏ q`, so "strictly less" is a special case. The engine
   uses the exact `⧏` test, which also accepts, for example, `Σ = x + *`
   against `q = x`. It subsumes the alternative "`G^L ≤ q^L`" (White moves in
   `−q`), since `q^L ⧏ q` always holds.

**Sufficient condition for (W).** For the Right option `q^R`: if some White
move gives `G^R` and a cut gives `G^R ≤ Σ ≤ q^R`, then in `G − q^R` White
moves to `G^R − q^R ≤ 0` and wins, so `G ⧏ q^R`. (The other way to satisfy
(W), `G ≤ q^{RL}`, is not used.) The White move may be anywhere.

**Canonical Right options** (each `q` has at most one):

| `q` | canonical form | Right option |
| --- | --- | --- |
| integer `k ≥ 0` | `{k−1 \| }` or `{ \| }` | none, so no (W) obligation (Lemma A) |
| integer `k < 0` | `{ \| k+1}` | `k + 1` |
| `m/2^j`, `m` odd, `j ≥ 1` | `{(m−1)/2^j \| (m+1)/2^j}` | `(m+1)/2^j` |
| `x + *` | `{x \| x}` | `x` |

**Comparing a sum with `q`.** Piece bounds are values `y_i + ε_i*`. Since
`≤` is compatible with `+`, `Σ pieces ≤ Σ bounds = Y + E*`, where
`Y = Σ y_i` and `E = ⊕ ε_i`. With `q = x + η*`:

- `Y + E* ≤ q` iff (`E = η` and `Y ≤ x`) or (`E ≠ η` and `Y < x`);
- `Y + E* ⧏ q` iff not `q ≤ Y + E*` iff (`E = η` and `Y < x`) or
  (`E ≠ η` and `Y ≤ x`).

In the engine: `xle` and `xlf` in `xclosure.cpp`. For a Right option (a
number) the first line with `η = 0` applies.

## 4. Two further ways to prove `F_w ≤ q`

**End-block reserve (`E`).** If `u` is White-only in an end block and White at
`u` turns `F_w` into the member `F'_w` of another family, then
`F_w ≤ F'_w − 1 ≤ q_{F'} − 1` (Lemma 4(4)). It suffices that
`q_{F'} ≤ q + 1`. Only columns 0–1 (or `w−2..w−1`) are used, so the move's
effects stay inside the block for every `w ≥ 6`.

**Reserve-cut (`R`).** For a White move `v` and a cut of `G^{R,v}` with sum `Σ`:
if `v` is White-only, `G ≤ G^{R,v} − 1 ≤ Σ − 1`, so `Σ ≤ q + 1` suffices; if `v`
is shared, `G ≤ G^{R,v} + * ≤ Σ + *`, so `Σ ≤ q + *` suffices (add `*` to both
sides; `* + * = 0`). One such rule per width proves `F_w ≤ q` with no
Blue-first obligations.

Strategy order in the engine: for `x < 0`: reserve, table, reserve-cut; for
`x ≥ 0`: table, reserve-cut.

**No-move White-first rule.** (W) also holds if a cut of `G` itself (no move)
gives `G ≤ Σ` with `Σ ⧏ q^R`: if `q^R ≤ G` then `q^R ≤ Σ`, a contradiction. The
engine tries this candidate first, with seams in the windows around columns
3 and `w − 4`.

**Two-round Blue rule (`b`).** For a Blue opening `G^L` with no one-round
rule, pick a White reply `y1` and prove `P = G^{L,y1} ≤ q` by Conway's
definition applied to `P`:
- (B′) for every Blue move `x2` legal in `P`, anywhere on the strip, a
  one-round rule: a White reply and a cut with `Σ ≤ q`, or no reply and a cut
  with `Σ ⧏ q`;
- (W′) if `q` has a Right option, a White move in `P` and a cut with
  `Σ ≤ q^R`, or no move and a cut with `Σ ⧏ q^R`.

Then `G^{LR} = P ≤ q`, so `G^L ⧏ q`. The sub-rules use seams from the windows
around both the opening and `x2` (up to 3 seams), and every piece is again
strictly shorter than `w`. Two-round rules are used **only at widths below
`W(p)`**. There they are finite facts about that single width, and the
coverage argument (§7) never stretches them. At `W(p)` only one-round rules
are accepted. Every `x2` is checked; no symmetry reduction is applied inside
`P`. JSON: type `b`, with the sub-rules in `subs`.

## 4a. Gap-representative two-round rule (`G`)

A type-`b` rule is a fact about one width. Type `G` is a two-round rule that
is checked on finitely many *reduced configurations* and is valid for a whole
class of positions whose long neutral runs have arbitrary length of a fixed
parity. That makes it usable at `W(p)` and, through §7, at every larger width.

### 4a.1 Layout and class

Fix `F`, `w`, a Blue opening `(r, c)` of `F_w` and a White reply `y1`. Put
`P = F_w^{L,(r,c); R,y1}`. A column is **neutral** if all five cells are legal
for both players. A **gap** is a maximal run of neutral columns of `P` that
contains neither column 0 nor column `w − 1`. Write

    P = B_0 N^{g_1} B_1 N^{g_2} ... N^{g_k} B_k

with blocks `B_i` (all other columns, maximal neutral runs touching an end
included in `B_0` or `B_k`). Each block between two gaps is non-empty and its
columns next to a gap are non-neutral. For positive integers
`h = (h_1..h_k)` let `P[h]` be the strip with the same blocks and gap lengths
`h`. Fix `T ≥ 1` (engine default 6, CLI `-T`). Gap `i` is **long** if
`g_i ≥ T`, otherwise **short**. The **class** of the rule is

    C = { P[h] : h_i = g_i for short i;  h_i ≥ T and h_i ≡ g_i (mod 2) for long i }.

The **representative** vector `ρ` has `ρ_i = g_i` (short) and
`ρ_i = T + ((g_i − T) mod 2)` (long). Note `ρ_i ≤ h_i` for every `P[h] ∈ C`,
with `h_i − ρ_i` even.

### 4a.2 What the engine checks

A **sub-rule** on a strip `S` is a one-round rule exactly as in §3/§4: for a
Blue move `x2` of `S`, a White reply `y2` in `S^{x2}` with a cut of sum
`Σ ≤ q`, or no reply and a cut of `S^{x2}` with `Σ ⧏ q`; for the White-first
part, a White move (or none) in `S` with `Σ ≤ q^R` (or `Σ ⧏ q^R`). Every
sub-rule has at least one seam. Pieces of length `≤ 7` use exact values,
longer pieces a family bound (member or dominated, §5), as everywhere else.

A **range** is an interval `[lo, hi]` of columns of `S` that is a run of
neutral columns of `S` (before `x2`). An **insertion point** for it in a
sub-rule is a column `j` with `lo − 1 ≤ j ≤ hi` and a piece `[a, b]` of the
sub-rule that is bounded through a family (JSON `src` `f` or `d`) with
`a + 2 ≤ j ≤ b − 3`. It stands for "insert two neutral columns between `j`
and `j + 1`".

The rule is accepted if:

- **(G1) block moves.** On `S = P[ρ]`: for every Blue-legal `x2` in a block
  column, a sub-rule with an insertion point for the range of every long gap.
- **(G2) short-gap moves.** On `S = P[ρ]`: for every short gap and every
  Blue-legal `x2` in it, a sub-rule with an insertion point for every long gap.
- **(G3) long-gap moves.** For every long gap `i`, every `l` with
  `T ≤ l ≤ 2T + 3` and `l ≡ g_i (mod 2)`, and every offset `u` with
  `0 ≤ u ≤ l − 1`, `u ≤ T + 1`, `v := l − 1 − u ≤ T + 1`: on
  `S = P[ρ with ρ_i := l]` (gap `i` occupying columns `s..s+l−1`), for every
  Blue-legal `x2` in column `s + u`, a sub-rule with an insertion point for
  every other long gap, for `[s, s+u−1]` if `u ≥ T`, and for
  `[s+u+1, s+l−1]` if `v ≥ T`.
- **(G4) White-first.** If `q` has a Right option `q^R`: on `S = P[ρ]`, a
  White-first sub-rule with an insertion point for every long gap. (The
  engine only tries White moves outside long gaps; this is a search
  restriction.)

`P[ρ]` is `S` for (G1), (G2) and (G4) because short gaps are exact. The engine
does not apply any symmetry reduction to the second move.

### 4a.3 One insertion

**Lemma 4a.1.** Let `R` be a sub-rule on `S` with an insertion point `j` in
piece `[a, b]` for a range `[lo, hi]`. Let `S⁺` be `S` with two neutral columns
inserted between `j` and `j + 1`, and `R⁺` the translated rule (columns `> j`
move right by 2; the piece `[a, b]` becomes `[a, b + 2]`). Then `R⁺` is a valid
sub-rule on `S⁺` with the same piece bounds, the same `Σ`, and the same
comparison. In `S⁺` the range becomes `[lo, hi + 2]`, a run of neutral columns
two longer than `[lo, hi]`.

*Proof.* Let `Q` be the final strip of `R` (after `x2`, `y2` if any, and the
seam drops). Because the piece is bounded through a family, its columns
`a+3 .. b−3` are neutral in `Q` (checked by `piece_bound`). From
`a + 2 ≤ j ≤ b − 3`, at least one of `j`, `j + 1` lies in `[a+3, b−3]`; call it
the *middle column*. It is neutral in `Q`.

(a) *No move is made in column `j` or `j + 1`.* Suppose a move (by either
player) is made in column `j`. Then `j` is non-neutral in `Q` (the played cell
is dead), so the middle column is `j + 1` and must be neutral in `Q`. If
`j + 1` is non-neutral in `S`, it stays non-neutral (permissions only shrink).
If it is neutral in `S`, the move at `(row, j)` removes the mover's permission
at `(row, j + 1)` (it was present just before the move, otherwise `j + 1` was
already non-neutral). Either way `j + 1` is non-neutral in `Q`, a
contradiction. A move in column `j + 1` is symmetric. Drops touch only seam
columns, which are the end columns `a`, `b` of pieces, and `a < j`, `j + 1 < b`.

(b) *The moves commute with the insertion.* A move at a column `m ∉ {j, j+1}`
changes permissions only in columns `m − 1, m, m + 1`, and these are the same
columns (after translation) in `S⁺`, where the inserted columns are adjacent
only to `j` and `j + 1`. Legality of each move depends only on its cell. So
`S⁺` after `x2⁺, y2⁺` equals (`S` after `x2, y2`) with two neutral columns
inserted at `j`, and those columns stay neutral.

(c) *The cut is the same.* No seam is at `j` (the piece `[a, b]` contains
`j` and `j + 1`). Seam columns and their contents are unchanged, so the same
drops satisfy the edge condition of Lemma 2. Hence `Q⁺` is `Q` with the
insertion.

(d) *Piece bounds are unchanged.* Pieces other than `[a, b]` are identical.
The piece `[a, b + 2]` has the same left end block (columns `a..a+2`, all
`≤ j`) and the same right end block (old columns `b−2..b`, all `≥ j + 1`), and
its middle is the old neutral middle plus two neutral columns. So it is the
member of the same family at length `n + 2` (or dominated by it, with the
same blocks), with the same parity and bound. `Σ` is unchanged.

Finally, the inserted columns are adjacent to a column of `[lo, hi]` (`j ≥ lo−1`
and `j + 1 ≤ hi + 1`) and neutral, so in `S⁺` they join that run. ∎

After the insertion, `j` is still an insertion point for `[lo, hi + 2]` in the
piece `[a, b + 2]`, and every other recorded insertion point `j'` is still one
(translated by 2 if `j' > j`). Distinct ranges are separated by at least one
non-range column (a non-empty block, or the column of `x2`), so their
insertion points are distinct. The lemma can therefore be applied any number
of times, at any of the recorded points, in any order.

### 4a.4 Coverage of every second move in every member of the class

**Lemma 4a.2.** Let `P[h] ∈ C`. For every Blue-legal `x2` of `P[h]` there is a
checked configuration `S` and move `x2'` such that `P[h]`, with `x2`, is
obtained from `S`, with `x2'`, by insertions at recorded insertion points of
the sub-rule for `(S, x2')`. The same holds for (G4) and the White-first part.

*Proof.* In every case each long gap `i′` not containing the move has length
`ρ_{i′}` in `S` and `h_{i′} ≥ ρ_{i′}` in `P[h]`, with even difference. Insert
`(h_{i′} − ρ_{i′})/2` pairs at its recorded point. Blocks and short gaps are
carried along by translation.

- `x2` in a block column: `S = P[ρ]`, `x2'` is the same block cell.
- `x2` in a short gap: `h_i = g_i`, `S = P[ρ]`, same offset in the gap.
- `x2` in long gap `i` at offset `u` (so `v = h_i − 1 − u`). Put
  `u* = u` if `u ≤ T + 1`, else `u* = T + ((u − T) mod 2)`. Define `v*`
  likewise. Put `l = u* + v* + 1`. Then `u*, v* ≤ T + 1`, so `l ≤ 2T + 3`;
  `l ≡ h_i ≡ g_i (mod 2)`; and `l ≥ T`. If neither side was reduced,
  `l = h_i ≥ T`. Otherwise the reduced side is `≥ T`, so `l ≥ T + 1`. So
  `(l, u*)` is a (G3) configuration. If `u* < u` then `u* ≥ T`, so the left
  sub-range was recorded; insert `(u − u*)/2` pairs there. By (a) the point is
  not next to the column of `x2`, so the new columns land left of `x2` and
  lengthen the left sub-run. The right side is the same with `v`. The result
  is `P[h]` with `x2` at offset `u` of gap `i`.
- (G4): `S = P[ρ]`.

Each insertion is Lemma 4a.1, so the translated sub-rule is valid on the
target. ∎

### 4a.5 The rule proves `F_w^L ⧏ q` for the whole class

**Proposition 4a.3.** If (G1)–(G4) hold, then `P[h] ≤ q` for every
`P[h] ∈ C`, assuming (C) for every family at every length `< width(P[h])`.

*Proof.* Conway's definition applied to `P[h]` (§3): for (B′), each Blue
option `P[h]^{x2}` has a transferred sub-rule by Lemma 4a.2. With a reply,
`P[h]^{x2,y2} ≤ Σ ≤ q`, so `P[h]^{x2} ⧏ q`. With none, `P[h]^{x2} ≤ Σ ⧏ q`, so
`q ≰ P[h]^{x2}`. (W′) likewise with `q^R`. So `P[h] ≤ q`. ∎

Then for the opening that produced `P[h]`, White's reply gives
`G^{LR} = P[h] ≤ q`, hence `G^L ⧏ q` (§3, item 1).

**Induction measure.** `P[h]` is not a family member. Its bound is proved
directly by Conway's definition, not by the induction hypothesis. The only
inputs are piece bounds of transferred sub-rules. Each sub-rule has at least
one seam, and after the insertions its pieces partition the columns of
`P[h]`, whose width is the width `w'` of the family member being proved. So
every piece is strictly shorter than `w'`. Pieces of length `≤ 7` receive no
insertion and use exact values. Family pieces use (C) at their stretched
length `< w'`, which is the induction hypothesis on the first coordinate of
the measure `(w, live cells)` (§5). The reduced configurations can be
narrower than `P[h]`, never wider (`ρ_i ≤ h_i`, `l ≤ h_i`). A stretched piece
may be longer than `W(p)`; (C) covers every length. There is no same-width
step.

### 4a.6 Widths: use at `W(p)` and beyond

Below `W(p)` a `G` rule is used only for the opening it was found for:
`P = P[g] ∈ C`. The insertion-point checks are still needed whenever some
gap is long, because the checked configurations are the reduced ones.

At `W(p)`, a `G` rule for an opening at distance `d_L = c`, `d_R = w − 1 − c`
is accepted only if:

- `d_L ≥ 9` ⟹ gap 1 is long and contains column 3; and
- `d_R ≥ 9` ⟹ gap `k` is long and contains column `w − 4`.

**Lemma 4a.4.** Under the first condition, for every `m ≥ 0`, `F_{w+2m}`
opened at `(r, c + 2m)` with reply `y1 + (0, 2m)` equals `P[h]` with
`h_1 = g_1 + 2m` and the other gaps unchanged. It is therefore in `C`. The
same holds on the right with no shift. Both sides can be combined.

*Proof.* `F_{w+2}` is `F_w` with two neutral columns inserted between
columns 2 and 3. Column 3 is neutral in `P` and in `F_w`. So no move of the
opening or reply is in columns 2, 3 or 4: a move in column 2 or 4 would remove
a permission of column 3, and a move in column 3 kills a cell. By the
commutation argument of Lemma 4a.1(b), inserting and then playing the
translated moves gives `P` with two neutral columns inserted between 2 and 3.
These join the run containing column 3, which is gap 1. Induct on `m`. On the
right, insert between `w − 4` and `w − 3`. ∎

By the claim of §7, every side that is shortened when an opening at
`w' > W(p)` is reduced to `W(p)` has distance `≥ 9` at `W(p)`. Lemma 4a.4
then puts the opened-and-replied position at `w'` into the class of the
`W(p)` rule, and Proposition 4a.3 proves `G^L ⧏ q` at `w'`.

The earlier engine condition ("gap 1 is long and ends left of the opening")
also implies this in practice, but it does not state that the lengthened run
is the one the stretch lands in. The engine now tests that column 3
(respectively `w − 4`) lies in the gap.

### 4a.7 JSON

Type `G`: `board` (the drawing of `P`), `gaps` (`g`), `T`, `white` (the reply
`y1`), `stretch` (the sides that satisfied the §4a.6 condition, at `W(p)`)
and `subs`. Each sub-rule additionally has `board` (the drawing of `S`
before `x2`), `gaps` (the gap vector of `S`), `sranges` (ranges `[lo, hi]` in
`S` coordinates) and `ins` (for each range, the insertion point `j` and
the index of the piece). A replay checker must:

1. recompute the layout of `board` and the set of configurations (G1)–(G4)
   from `gaps` and `T`, and match each to exactly one sub-rule;
2. check each sub-rule as a one-round rule on its `board`;
3. check each insertion point, including `lo − 1 ≤ j ≤ hi`,
   `a + 2 ≤ j ≤ b − 3`, and that the piece has `src` `f` or `d`;
4. at `W(p)`, check the §4a.6 condition.

## 5. The induction

Measure: `(w, number of live cells of F_w)`, ordered lexicographically.

- **Base.** `w = 6, 7`: `F_w` has an exact value `v_F[p]` from the solver
  (bisection with outcome classes, Cor 4.3), and `q_F[p]` is chosen with
  `v_F[p] ≤ q_F[p]` (§6).
- **Step, `w ≥ 8`.** The rule used for `F_w` bounds every piece by:
  - its exact value if the piece has length `≤ 7` (no induction); or
  - `q_G[ℓ mod 2]` if the piece has length `ℓ ≥ 8` and is the member `G_ℓ`
    of a family in the list; since `ℓ < w`, this is the induction hypothesis;
  - or `q_G[ℓ mod 2]` if the piece is dominated by `G_ℓ` (fewer Blue and more
    White permissions in the end blocks, same neutral middle): piece `≤ G_ℓ`
    by monotonicity, then the induction hypothesis (`ℓ < w`).
  Every rule has at least one seam, so every piece is strictly shorter than
  `w`. The only same-width step is the end-block reserve, where `F'_w` has
  strictly fewer live cells (the cell `u` dies).
- Every (family, parity) used anywhere must itself be closed, with the bound
  that was used. When a bound is weakened, every closed (family, parity)
  that used it is re-queued and re-checked (the `users` sets in the engine).

## 6. Bounds, drift and weakening

`v_F[0]` and `v_F[1]` are the exact values at widths 6 and 7. The engine
starts with `q = v` and, if every strategy fails, weakens `q` along the ladder
exact → smallest multiple of 1/4 that is `≥ v` → of 1/2 → integer. For
`v = x + *` "`≥ v`" means strictly above `x` when `x` is on the grid. Each
level must be strictly weaker than the previous one; levels that give the
same bound are skipped. The level each family ends with is recorded in
`runs/<tag>_families.json` (`bound`, `level`, `history`).

Any bound `q ≥ v` is sound at the base widths. Weakening can only fail to
help; it never invalidates a proof, because every user of the weakened bound
is re-checked.

## 7. Width coverage

**Checked widths.** For `p = 0`: `w = 8, 10, …, 20`; for `p = 1`:
`w = 9, 11, …, 21`. Write `W(p)` for the largest (20 or 21). Every Blue
opening at every checked width is handled, up to the symmetries of `F_w`
(§8). For (W) and reserve-cut obligations, one rule per checked width.

**Search windows** (a search restriction only; validity of a rule does not
depend on them). For an opening at column `c` with distances `d_L = c`,
`d_R = w − 1 − c`: window `RW = 4` if `min(d_L, d_R) ≤ 6`, else `2`. Replies lie
in columns `[c − RW, c + RW]`, seams `j` (between `j` and `j+1`) in
`[c − RW, c + RW − 1]`. White-first rules use the same window around White's
move column.

**Stretch lemma.** Let a rule for `F_w` have an end piece, say the left one
`[0, j]`, of length `≥ 8` that is a family member or dominated by one. Its
middle columns `3..j−3` are neutral in the piece. Drops happen only at seam
columns, so they are untouched neutral columns of the position, and they lie
in `F`'s neutral middle `3..w−4`. Insert two neutral columns after column 2.
This gives `F_{w+2}` with the rule translated by 2. The left piece becomes the
member of the same family (or is dominated by it) at length `+2`, with the
same parity and bound. All other pieces are unchanged. So the rule is valid
at `w + 2`. The right side is symmetric.

**All widths `w > W(p)`.** Take an opening `(r, c)` at such a `w`. Repeatedly
remove two neutral columns on the side farther from the opening (left if
`d_L > d_R`, else right) until the width is `W(p)`. Undoing each removal is a
stretch on that side, so it is enough that the rule at `W(p)` has a family
end piece on every side that was shortened.

*Claim:* a side shortened at least once has distance `≥ 9` at `W(p)`. Let
side `X` be shortened last at width `w_1 ≥ W(p) + 2`. It was the larger side,
so before shortening `X ≥ (w_1 − 1)/2 ≥ (W(p) + 1)/2`, and it ends at
`X − 2 ≥ (W(p) − 3)/2`. That is `≥ 8.5` for `W = 20` and `≥ 9` for `W = 21`.
A side at distance `d ≥ 9` at width `≥ 20` has an end piece of length
`≥ 8`: if the other side is `≤ 6` then `d ≥ 13`, `RW = 4` and the piece has
length `≥ d − 3 ≥ 10`; otherwise `RW = 2` and it has length `≥ d − 1 ≥ 8`.
Pieces of length `≥ 8` are family pieces by construction.

The engine enforces this directly. At `w = W(p)`, a Blue-opening rule is
accepted only if every side with distance `≥ 9` has an end piece of length
`≥ 8`. A White-first or reserve-cut rule is accepted only if at least one end
piece has length `≥ 8`. A two-round rule of type `G` is accepted at `W(p)`
only under the gap condition of §4a.6, and then covers every larger width by
Lemma 4a.4 and Proposition 4a.3. Type `b` is never used at `W(p)`. The side is recorded in the JSON as `stretch`. White-first obligations
for `w > W(p)` use the `W(p)` rule stretched on that side.

**Flag on the old engine (`closure.cpp`).** Its comment says widths 8..18
cover every opening class. Under its own windows that is not true. The class
`d_L = 6`, `d_R` even and `≥ 12` first occurs at `w = 19`. At `w = 17`
(`d_R = 10`) a rule may use a right piece of length 7, which is bounded by its
exact value and does not transfer. Likewise far classes such as
`(d_L, d_R) = (9, 10)` first occur at `w = 20`, and `(10, 10)` at `w = 21`.
`xclosure` checks 8..20 and 9..21 and uses the stretch lemma above.

## 8. Symmetry

If `F_w` equals its vertical mirror, only openings (and White moves) in rows
0–2 are checked. If it equals its left–right mirror, only columns
`≤ (w−1)/2` are checked. The rule for a mirrored opening is the mirrored
rule; the value oracle is symmetry-invariant (keys are canonical over the four
rectangle symmetries). Records carry `sym` (`v`, `h`, `vh`) to say which
reductions were applied.

## 9. What the engine trusts, and what I am unsure about

These are the points a certification pass must replay or re-prove:

1. **Exact values of pieces of length ≤ 7, and of family members at widths 6
   and 7.** They come from `xcolout5` alpha-beta searches (EVIDENCE). The
   search prunes Blue or White moves at private cells via
   `blue_dominated`/`white_dominated`. That is a solver-internal dominance
   claim I have not re-proved. Each value should be re-certified, for
   example with `colcert5`, or with a search-free checker on the recorded
   `draw` of the piece.
2. **Transposition-table keys (a bug, fixed here; affects old logs).**
   `ground_truth/colout5.cpp` keys multi-component nodes by raw board
   bitmasks, without the board width. The old `closure.cpp` shares one table
   between searches on boards of different widths, so a 5×6 and a 5×7
   position with equal bitmasks can collide. `xcolout5.cpp` adds the width
   to the key. Integer bounds in the old `bounds_cache*.txt` files could in
   principle be affected. `xclosure` uses them only as bisection starting
   brackets and falls back to the full range if a bracket is inconsistent,
   so a wrong hint costs time but cannot give a wrong value.
3. **Timeouts.** A piece whose value search exceeds the limit (`-L`, default
   900 s) is marked unknown and never used. This is sound.
4. **Drop patterns.** For a seam next to a one-column middle piece, the rows
   to drop are computed from the strip before the other seam's drops. This
   can drop a permission that was already gone, which is harmless:
   dropping White permissions only increases the right side.
5. **Dominance** is used only between a piece and a family member with the
   same neutral middle and length. Stretching preserves it (§7).
6. **Same-width steps.** Only the end-block reserve, and it strictly lowers
   the live-cell count. Rules always have at least one seam.
7. **Bisection classification** uses Cor 4.3: P means `G = t`, N means
   `G = t + *`. The old engine re-confirmed N by testing `G + * − t`; this one
   does not, relying on the PROVED corollary.
8. **Not covered by the argument:** anything about the empty board or `DD`
   beyond the reserve step `K_n ≤ 0 ⟹ DD_n ≤ −1`. That step is PROVED (Lemma
   4(4)) but needs `(2,0)` to be White-only in `DD`, which holds by the
   definition of the `obwbo` end column.

## 10. Machine-readable output

- `runs/<tag>_rules.jsonl`: one line per rule of every successful attempt,
  and one `failed` line per failed attempt. Fields:
  - `fam`, `par`, `att` (attempt id); `bound` (the `q` proved);
  - `type`: `B` (Blue opening), `b` (two-round Blue opening, sub-rules in
    `subs`), `W` (White-first; `white` null means the no-move cut),
    `R` (reserve-cut), `E` (end-block reserve);
  - `w`, `open` `[row, col]`, `white` `[row, col]` or null (reply or White
    move);
  - `seams` (cut after these columns), `drops` `[seam, rows dropped in the
    left column, rows dropped in the right column]` as 5-bit row masks;
  - `pieces` with `cols`, `src` (`x` exact value, `f` family bound, `d`
    dominated by family), `fam`, `fpar`, `val`, and `draw` (rows separated
    by `/`: `o` both, `b` Blue-only, `w` White-only, `.` neither);
  - `sum`, `target`, `cmp` (`le`: sum ≤ target; `lf`: sum ⧏ target),
    `stretch`, `sym`.
  The final proof uses, for each (family, parity), the attempt `att` recorded
  in `runs/<tag>_families.json`.
- `runs/<tag>_families.json`: per family the blocks (`w6`, `w7` drawings) and,
  per parity: measured value, bound, level, status (2 table, 3 reserve,
  4 reserve-cut, −1 failed, 1 pending), method, attempt, needs, history.
- `runs/xvalues.txt`: exact-value cache, `hex(canonical key) value`.
