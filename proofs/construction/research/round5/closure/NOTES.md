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
piece has length `≥ 8`. The side is recorded in the JSON as `stretch`. White-first obligations
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
