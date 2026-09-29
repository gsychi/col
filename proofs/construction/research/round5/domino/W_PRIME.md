# (W′) on 3 × n

Status: **partial.** (W′) is verified exhaustively on 3×3, 3×5, 3×7 and 3×9 (every
PF-class position and every White majority move, 134,103,040 cases on 3×9). For all odd `n`
it is **reduced by proved cut lemmas** to five strip lemmas (S1, T, K, P, E), with two exceptions:
the positions in which one side of the move's column is completely empty and has width ≡ 1 mod 4
(middle-row move) or width ≡ 2 mod 4 (edge move). In those cases each cut tried loses exactly the
value that (W′) needs, and a new *empty-tail lemma* is required (§5). The upper half of PF
(`G ≤ F`) is certified by dual cuts on every position up to 3×9 with no exceptions (§7).

Every number below is reproduced by `run_wp.sh`, which writes `runs/wp_*.txt`.

Notation follows `PROOF_ATTEMPTS.md`. On 3×n with `n` odd, the majority cells are
`X = {(r,c) : r+c even}` and the minority cells are `Y`. Even columns read `X Y X`, odd columns
`Y X Y`. The class `C` consists of positions with Blue stones on `X` only, White stones on `Y`
only and at least one White stone. `F = #free X − #free Y`. `G ⧐ H` means "not `G ≤ H`"
(greater than or confused with). (W′) says: for `G ∈ C` and a White-legal free `y ∈ X`,
`G^{R,y} ⧐ F`. By Lemma 5.1, (W′) on `C` gives `G ≥ F` on `C`. For a strip piece `S` with
its own count `F_S` (all its free cells, including dead ones), write `e(S) = S − F_S`.

## 1. Summary

| Item | Status |
| --- | --- |
| (W′) on 3×3, 3×5, 3×7, 3×9 | VERIFIED exhaustively (`runs/wp_rule.txt`) |
| Blue answer rule R* (§2) works on every case to 3×9 | VERIFIED, 0 failures |
| Minimum margin of `G^{R,y} − F` | `1/4` on 3×5, 3×7 and 3×9 (24, 48 and 48 cases) |
| Cut lemmas M, EB, EO, EW with their accounting identities (§3) | PROVED |
| Empty T-strip `∈ {0, *}`; empty nwn strip `≥ 0` (§4) | PROVED |
| Reduction of (W′) on 3×n to S1, T, K, P, E, except the empty-side cases F1, F2 (§5) | PROVED (conditional) |
| Strip lemmas T, K, P, E, and S1 on narrower strips (§4) | EVIDENCE to width 8–9 |
| Cases F1, F2 | open. Cuts provably insufficient (they give exactly `F` or `F + *`) |
| Upper half `G ≤ F`, strong (B), 3×3 to 3×9, all contents | VERIFIED; dual certificates 100% |

## 2. The answer rule R* (verified)

Let `y = (r,c)` be White's move and `s = ±1` a direction. A side of column `c` is *W* if it
holds a White stone, *b* if it holds only Blue stones, *e* if it is empty, *0* if it has no
columns.

- **Middle move**, `y = (1,c)`, `c` odd.
  - Both sides W: no answer is needed, since `G^{R,y} ≥ F + 1` (branch M-WW).
  - Otherwise let `s` point to a White-free side. Blue answers `(0,c+s)`, or `(2,c+s)` if
    that is taken (M-empty, M-Bonly). If both are Blue stones, no answer is needed (M-Bonly-cut).
- **Edge move**, `y = (r,c)`, `r ∈ {0,2}`, `c` even; `y' = (2−r,c)`.
  - If a side is empty and has width ≥ 2, Blue answers `(r, c∓2)` inside it (E-empty).
  - Else, if a White stone sits at `(2−r, c+s)` (next to `y'`), Blue answers `(r, c+2s)`
    (E-opp-W, or E-oppB-W when `y'` is Blue).
  - Else, if `y'` is a Blue stone: no answer is needed (E-oppB).
  - Else Blue answers `y'` (E-opp).

An *answer* case is certified when `G^{y,b} ≥ F`, which implies `G^{R,y} ⧐ F`. A *free* case is
certified when `G^{R,y} ≥ F + 1`. On 3×9, per branch (`runs/wp_rule.txt`):

| Branch | Cases (3×9) | Kind | Failures |
| --- | ---: | --- | ---: |
| M-WW | 7,225,344 | free | 0 |
| M-Bonly | 5,013,568 | answer | 0 |
| M-Bonly-cut | 2,379,776 | free | 0 |
| M-empty | 2,125,760 | answer | 0 |
| E-empty | 1,060,544 | answer | 0 |
| E-opp | 38,883,520 | answer | 0 |
| E-opp-W | 19,265,504 | answer | 0 |
| E-oppB | 38,883,520 | free | 0 |
| E-oppB-W | 19,265,504 | answer | 0 |

Earlier versions of the rule failed. There were 48 failures on 3×5/3×7 (E-oppB with a White
stone next to `y'`) and 40 on 3×9 (M-Wb, answering on the wrong side). Those failures are why
the E-oppB-W branch exists and why `s` points to the White-free side.

## 3. Cut lemmas (proved)

Tools: the comparison principle (Lemma 2) and its dual. A lower bound may remove Blue
permissions, add White permissions, and delete edges having a Blue-illegal endpoint. Other
tools are Lemma 1.1 (dead cells vanish, sums split) and Lemma 4(2): at a Blue-only cell `v`,
`G ≥ G^{L,v} + 1`.

**Trace names** (boundary modification on a piece's end column next to the cut):
- *nwn*: the end column is `X Y X`, and its middle `Y` is White-illegal.
- *T*: the end column is `Y X Y`; its `Y` next to White's stone is White-illegal and its
  other `Y` is Blue-illegal. That second `Y` may hold a White stone; such content is called W*.
- *P*: the far piece of branch EW. Its end column `X Y X` has a Blue stone at the corner on
  White's row and a White-illegal `X` at the other corner.

**M (middle move).** Let `y = (1,c)`. The cells `(0,c)` and `(2,c)` are free `Y` cells (a White
stone there would make `y` illegal) and are now White-illegal. Remove their Blue permission.
Column `c` is then dead, and its neighbours `(1,c±1)` are White-illegal, so

```math
G^{R,y} \ge L^{nwn} + R^{nwn}, \qquad F_L + F_R = F + 1,
```

with `L` and `R` odd-width strips in the standard colouring. Hence
`G^{R,y} − F ≥ 1 + e(L^{nwn}) + e(R^{nwn})`. Since `L^{nwn} ≥ L` (a White permission was
removed), PF-lower on a W side gives `e ≥ 0`.

**EB (edge move, `y'` already Blue).** The cell `(1,c)` is dead and column `c` is spent, so the
split is **exact**: `G^{R,y} = L~ + R~`, two even-width T-traced strips, and `F = F_L + F_R`.

**EO (edge move, Blue answers `y'`).** The same exact split gives `G^{y,y'} = L~ + R~`, with
`F = F_L + F_R + 1`. So `G^{y,y'} − F = e(L~) + e(R~) − 1`.

**EW (edge move, White stone at `(2−r,c+s)`, Blue answers `b = (r,c+2s)`).** After `y` and
`b`, the cell `(r,c+s)` is dead and `y'` is Blue-only. If `y'` is free, apply Lemma 4(2) at
`y'`. Then `(1,c)` is dead, and `(1,c+s)` is a Blue-only cell whose remaining edge goes to the
Blue-illegal cell `(1,c+2s)`; delete that edge. The result is

```math
G^{y,b} \ge L^{\sim} + 1 + P + [y' \text{ free}], \qquad
F = F_L + F_P + 1 + [y'\text{ free}] + [b\text{ free}],
```

so `G^{y,b} − F ≥ e(L~) + e(P)` when `b` was free.

Branches M-Bonly-cut and E-oppB-W use the same cuts with one term of the accounting shifted by 1
in Blue's favour.

## 4. Strip lemmas

Proved:

- **T0.** An empty T-strip of even width is `0` or `*`, and `F = 0`. *Proof:* the row
  reflection `r ↦ 2−r` maps the position to its colour swap. It exchanges the White-illegal and
  Blue-illegal trace cells and fixes the empty interior. By Cor 5.1 the value lies in `{0, *}`.
- **N0.** An empty odd nwn strip has value `≥ 0`, i.e. `e ≥ −1`. *Proof:* restoring the White
  permission lowers the value to the empty board `H_k = 0` (`empty_3xn_theorem.md`).

Evidence (`runs/wp_lemmas.txt`):

- **T.** An even T-strip with a White stone has `e ≥ 1/2`, and `e = 1` when the trace cell is
  not a White stone. A Blue-only T-strip has `e ≥ 1/4`.
  - Seen: W → `1`; W* → `1` or `1/2`; b → `≥ 1/4`; empty → `*` (widths 2, 6), `0` (widths 4, 8).
- **K.** A Blue-only odd nwn strip has `e ⧐ −1`.
  - Seen: minimum `−3/4` (3×3, 3×7) or `−1/2` (3×5, 3×9); `*` occurs at widths 1, 5, 9.
  - The earlier form `e ≥ −1/2` is **false** (`−3/4` occurs), but only `e ⧐ −1` is used.
  - Empty nwn strips have `e = −1` (widths 1, 5, 9) and `e = −3/4` (widths 3, 7).
- **P.** Every P-strip (W or b content) has `e ≥ 0`. Seen: exactly `0`, widths 1–9.
- **E.** The empty strips at the residues not covered by T0 and N0:
  - the empty nwn strip of width ≡ 3 mod 4 has `e ⧐ −1` (seen: `−3/4` at widths 3, 7);
  - the empty T-strip of width ≡ 0 mod 4 is `0` (seen at widths 4, 8).
- **S1.** PF-lower on narrower odd strips. This is the induction hypothesis itself; `L^{nwn} ≥ L`
  converts it to `e(L^{nwn}) ≥ 0`. Plain even strips satisfy PF for every content at widths
  2, 4, 6.

## 5. Conditional reduction and the exact failing cases

**Theorem (conditional).** Assume S1 below width `n`, together with T, K, P and E. Then (W′) holds
at every 3×n position of `C` except in the two families F1 and F2 below.

*Proof, by branch.* (If `X ⧐ 0` and `Y ≥ 0` then `X + Y ⧐ 0`.)

- **M, both sides W.** `G^{R,y} − F ≥ 1 + 0 + 0`.
- **M, a b side.** The other side is W (a White stone exists off column `c`), so
  `G^{R,y} − F ≥ 1 + e_W + e_b ⧐ 0` by S1 and K.
- **M, an empty side of width ≡ 3 mod 4.** `G^{R,y} − F ≥ 1 + e_W + e_e ⧐ 0` by S1 and E.
  (N0 alone gives only `≥ 0`.)
- **EB.** Some side is W, so `e(L~) + e(R~) ≥ 1/2 + (≥ 0 or ∈ {0,*}) > 0` by T and T0.
- **EO.** No trace cell holds a White stone (that is branch EW), so a W side gives `e = 1`. The
  other side gives `≥ 0` by T, or `0` by E if it is empty of width ≡ 0 mod 4. Hence
  `G^{y,y'} ≥ F`.
- **EW.** `e(L~) ≥ 0` by T (or by E if it is empty of width ≡ 0 mod 4), and `e(P) ≥ 0` by P.

Every branch closes except these two:

- **F1 (M, empty side of width `w ≡ 1 mod 4`).** The empty nwn strip is exactly `F − 1`
  (`e = −1`), so the cut gives `G^{R,y} − F ≥ e_W`. This fails whenever `e_W = 0`: 65,032
  cases on each side on 3×9, all with `Z − F = 0`. The true margin is `1/2`. Example
  (rows separated by `/`, `+` = free X, `-` = free Y):

  ```
  +-+-BWBWB / -Y-BWBWBW / +-+-BWBWB    F = −1,  cut gives F,  G^{R,y} − F = 1/2
  ```

- **F2 (EO or EW, empty side of width `w ≡ 2 mod 4`).** The empty T-strip is `*`, so the cut
  gives `F + *`, which is not `≥ F`. On 3×9: 195,616 EO and 131,104 EW cases per side. The true
  margin is `1 + *`. Example:

  ```
  +-Y-BWBWB / -+-BWBWBW / +-+WBWBWB    F = 0,  EO cut gives F + *,  G^{R,y} − F = 1 + *
  ```

Blue-only sides never fail. Across all branches the certificates cover 133,319,536 of
134,103,040 cases on 3×9; the other 783,504 are exactly F1 ∪ F2 (`runs/wp_cert.txt`).

**Why cuts cannot fix F1/F2.** Each cut at column `c` dissolves the column's 3 cells into
traces. When one side is empty, that side's exact value (`F − 1` or `*`) leaves no slack.
Tested alternatives lose more:
- Including Blue's answer in the cut (a Blue corner stone plus a dead middle cell, or a
  Blue-illegal bottom cell) gives empty pieces with `e = *` or `e = −1`.
- Extracting `(2,c)` with Lemma 4(2) gives W pieces with `e = −3/4`.

Rule R* does handle both families (branches M-empty and E-empty, 0 failures to 3×9). The proof
of that answer is what is missing.

**Key missing lemma (empty-tail lemma).** Let `y` be on column `c`, with one side of
column `c` empty and of width `w`, and the other side W. Then:
- for a middle move with `w ≡ 1 mod 4`, `G^{R,y} ⧐ F`;
- for an edge move with `w ≡ 2 mod 4`, `G^{R,y, b} ≥ F` for Blue's answer `b = (r, c∓2)`.

This is a statement about an unbounded empty region next to a boundary defect, of the same kind
as `H_n = 0`. The natural proof tiles the empty side with the colour-swapped `E4` gadgets of
`empty_3xn_theorem.md` (lower-bound form, Blue ports), plus one certified end gadget spanning
column `c` and a few columns on each side. Then only the gadget next to `y` needs a finite
certificate, and the W side re-enters through S1. Finding that gadget is the next step.

## 6. Margin

The minimum of `G^{R,y} − F` is exactly `1/4` on 3×5 (24 cases), 3×7 (48) and 3×9 (48)
(`runs/wp_margin.txt`), and it is never `0` or confused with `0`. So a uniform `≥ 1/4` is
consistent with the data and would give (W′) with slack. The cut proof does not see this
margin in F1/F2, which is why those cases need a sharper tool.

## 7. Upper half (dual certificates)

`wp_certB.cpp` applies the colour-dual cuts to each Blue move `z ∈ Y`, over **all** contents
(including no White stone), with these branches:
- M: remove White permission at `(0,c)` and `(2,c)`;
- EB: `z'` is White;
- EW: White answers `(r,c+2s)`, then Lemma 4(4) at `z'`;
- EO: White answers `z'`.

Results (`runs/wp_certB.txt`):
- On 3×3 to 3×9 every case is certified. On 3×9 that is 96,468,992 Blue moves over all
  134,217,728 positions.
- `G ≤ F` and the strong (B) have no failures.
- Upper-trace strips (`runs/wp_upper.txt`): odd `bnW` strips have `e = −1`, with some Blue-only
  cases at `−3/2`, and empty ones at `−1`. This holds for all content to width 7, and for
  White-free content at width 9.

So PF-upper on odd boards reduces to the odd `bnW` lemma (`e ≤ −1`) plus PF-upper on plain
even strips. Even strips (PF holds at widths 2, 4, 6 for all content) need their own induction.
That induction produces empty T-type pieces worth `*`, which is the same obstruction as F2.
PF on 3×n therefore needs the empty-tail lemma on both halves. Once it is proved, the lemmas
T, K, P and bnW are one-parameter strip families that are natural targets for the same
gadget-tiling method.

## 8. What generalises

- **Any m × n.** These carry over unchanged:
  - the accounting identities (F is additive over cut pieces, corrected by the cut column's
    free cells and the answers played);
  - Lemma 4 cell extraction;
  - T0-type antisymmetry for empty strips whose traces are exchanged by the row reflection
    (this works for every height).
- **Height 3 is special** in two places:
  - A White stone on the middle cell makes both other cells of its column White-illegal, and
    removing their Blue permission kills the column at a cost of exactly one point (M).
  - An edge stone plus one Blue stone on the opposite cell kills the column exactly (EB/EO).
- **5 × n.** One stone never kills a column. A White stone at `(2,c)` leaves `(0,c)` and `(4,c)`
  live, and an edge stone plus an opposite Blue answer leaves `(2,c)` free. A column cut
  therefore needs either two answers in the column or permission removal on 2–3 cells, costing
  up to one point each against a gain of one.

  The rule-based data (§14 of `PROOF_ATTEMPTS.md`) shows the answers exist, but a cut proof
  needs either multi-column separators (a White stone plus a Blue answer on adjacent columns,
  as in Case 6 of the empty-board proof) or a potential that pays for the cut. The first
  finite target is a 5×n answer rule verified on 5×5 and 5×7 PF positions, together with a
  census of which two-column separators certify.
- **m × n in general.** The reduction pattern "rule, then cut into strip families, then
  per-family lemmas" survives, but the families become two-parameter (height × boundary
  pattern). The empty-tail lemma becomes the analogue of `H_{m×n} = 0` with a boundary defect,
  which is itself open beyond the widths computed in `COL_VALUES.md`.

## 9. Replay

`sh run_wp.sh` takes about 20 minutes on one core. It builds `wp_rule`, `wp_cert`, `wp_certB`,
`wp_bnd` and `offhist` into `/tmp/wp` with `-O3 -march=native`, and writes:
- `runs/wp_rule.txt`: §2.
- `runs/wp_cert.txt`: §§3, 5.
- `runs/wp_lemmas.txt`: §4.
- `runs/wp_margin.txt`: §6.
- `runs/wp_certB.txt` and `runs/wp_upper.txt`: §7.

Helper studies used while designing R* are `wp_offsets.cpp`, `wp_opp.cpp` and `wp_qempty.cpp`.
