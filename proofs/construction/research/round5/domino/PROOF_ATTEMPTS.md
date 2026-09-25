# Domino lemma: proof attempts (round 5, domino stream, 2026-09-25)

Labels: **PROVED**, **EVIDENCE** (exact computation on finitely many positions, never
extrapolated), **CONJECTURE**, **REFUTED**. Conventions as in `../HANDOFF.md`: Blue = Left,
`X` = majority cells (`r+c` even), `Y` = minority cells. `D(a,b)` = Blue stone on `a`, White
stone on `b`, rest empty. `O_a` = Blue opening at `a` (White to move). All code is in this
directory and uses the Theorem-5 evaluator `../center/colcore_fast.hpp` (copy of
`../literature/col_fastval.cpp`); build with `g++ -O2 -std=c++17 X.cpp`.

## 0. Summary

| # | Approach | Status |
| --- | --- | --- |
| 1 | Which inequality the minority consequence needs | PROVED: it needs `D ≥ 1` (lower bound), not `D ≤ 1`; `D(x,w) ⧐ −1` already suffices for "minority opening ≠ 0" |
| 2 | Lemma 4 twice: `O_w + O_x ≤ −2` for adjacent cells, any graph | PROVED; gives `D(x,w) ≥ O_x + 1` |
| 3 | Parity-restricted games `Dmaj ≤ D ≤ Dmin` (both equal 1 if restrictions are harmless) | REFUTED as an all-size route (3×n: `Dmaj` → negative, `Dmin` > 1 from 3×9) |
| 4 | Parity formula (PF): value = #free X − #free Y on parity-respecting positions | CONJECTURE, strong EVIDENCE on all rectangles with sides ≥ 2; implies the domino lemma and all minority openings `= −2` |
| 5 | PF by induction: reduces to two one-move statements (B) and (W′) | PROVED reduction; (B), (W′) EVIDENCE; strong domination (W) REFUTED |
| 6 | Potential-function upper bound Φ on the anti-parity class | REFUTED past the class (off by exactly 1/2 once Blue has a majority stone) |
| 7 | Lemma 4 at the anti-domino (`G^{y,z}`) | REFUTED as a strict route (gives exactly `F − 1`, i.e. `≥ F`, never `⧐ F`) |
| 8 | Reserve cashing (fill White-only X, kill Blue-only Y) | REFUTED (count-neutral but loses ownership; 3×3 minority opening gives `≤ 0`, true `−2`) |
| 9 | Free cuts through a Blue-dead column (3×n, middle-row vertical domino) | PROVED inequalities `S_c + S_{n−1−c} − 1 ≤ D ≤ T_c + T_{n−1−c} − 1`; with EVIDENCE strip values gives only `0 ≤ D ≤ 1` |
| 10 | Even boards: openings `= −1` (PF analogue) | PROVED `≤ −1` on every 2×n and next to a symmetry axis of any even board; EVIDENCE `= −1` everywhere computed |
| 11 | Symmetry pairing for `D` on odd × odd boards | REFUTED (PROVED: no board symmetry maps `v` to an adjacent `u`) |
| 12 | Majority openings via one off-parity White reply | EVIDENCE: a reply `y ∈ X` with `S(v,y) ≤ 0` exists on 3×5, 3×7, 5×5; mirror reply not always; PF does not cover them (PROVED: they are outside the PF class, and PF fails exactly there) |
| 13 | A closed extended class for (W′): White also on `X`, bound `V2` or `V2 − Σ(deg y − 2)` | REFUTED (both lower bounds fail on 3×3) |
| 14 | Fixed Blue answer to a White off-parity move (diagonal, adjacent, distance 2) | REFUTED as a rule; EVIDENCE: `G^{R,y} − F ≥ 1/4` on all of 3×5 |
| 15 | 5×9 domino check | EVIDENCE: 21/22 classes `= 1`, one INCONCLUSIVE (budget) |

## 1. What the consequence needs (PROVED)

Let `w ∈ Y` and `x ∈ X` adjacent. After Blue opens at `w`, `x` is White-only, so Lemma 4(4)
gives `O_w ≤ O_w^{R,x} − 1`. The position `O_w^{R,x}` is Blue `w`, White `x`, whose colour swap
is `D(x,w)`; hence

```math
O_w \le -D(x,w) - 1 .
```

- `D(x,w) ≥ 1` gives `O_w ≤ −2` (Prop. 3.2 of GENERAL_IDEAS.md).
- `D(x,w) ≥ 0` gives `O_w ≤ −1`.
- `D(x,w) ⧐ −1` (Blue wins `D + 1` moving first; i.e. number part `> −1`, or `D = −1+*`)
  gives `−D − 1 ⧏ 0`, hence `O_w ⧏ 0` (if `A ≤ B` and `B ⧏ C` then `A ⧏ C`), hence
  `O_w ≠ 0`. This is the weakest form that settles minority openings.
- `D ≤ 1` is **not** used. It only yields `O_x ≤ D(x,u) − 1 ≤ 0` for majority `x`, which
  excludes `O_x = *` and says nothing about `O_x = 0`.

So the task statement's "D ≤ 1 is what the consequence needs" is incorrect: the consequence
needs the **lower** bound. After colour exchange, the lower bound `D(x,w) ≥ 1` is the
**upper** bound `D(w,x) ≤ −1` for Blue on a minority cell next to White on a majority cell.

## 2. Lemma 4 applied twice (PROVED, any finite graph)

For adjacent vertices `w, x` of any graph, starting from the empty position:

```math
O_x \le D(x,w) - 1, \qquad O_w \le -D(x,w) - 1, \qquad\text{so}\qquad O_w + O_x \le -2 .
```

*Proof.* In `O_x`, `w ∈ N(x)` is White-only; Lemma 4(4) gives the first inequality. The
second is §1. Add them. ∎

Consequences: `D(x,w) ≥ O_x + 1` (a lower bound on the domino from the majority opening),
and an opening equal to `0` forces every neighbouring opening to be `≤ −2`. With data
(`O_x ∈ {−1/2, −3/4, −1}` for majority `x`) the lower bound gives only `D ≥ 0`, `≥ 1/4`,
`≥ 0`; the missing slack is exactly Lemma 4's non-tightness at majority openings.

## 3. Parity-restricted games (REFUTED as a route)

`Dmaj` = `D` with Blue restricted to `X`; `Dmin` = `D` with White restricted to `Y`. By
monotonicity `Dmaj ≤ D ≤ Dmin`, and with both restrictions the game is a sum of integers:
Blue's `X` moves never interact with White's `Y` moves, and the value is
`#free X − #free Y = 1`. So `Dmaj = 1` would prove `D ≥ 1`, `Dmin = 1` would prove `D ≤ 1`.

EVIDENCE (`restrict.cpp`, `dmaj.cpp`), 3 × n, `v = (0,0)`, `u = (1,0)`:

| n | 3 | 5 | 7 | 9 | 11 | 13 | 15 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Dmaj` | 1 | 1/2 | 1/4 | 1/8 | 0 | −1/4 | −1/2 |
| `Dmin` | 1 | 1 | 1 | 3/2 | 3/2 | 7/4 | 2 |

The same numbers appear for `v = (1,1)`, and on the path `1 × n` (where `D` itself is `1/2`
for `n ≥ 5`). On 5 × 5 every pair has `Dmaj = 1/2`, `Dmin = 1`. **Consequence:** a proof of
`D ≥ 1` must use Blue minority moves (already on 3 × 5), and a proof of `D ≤ 1` must use
White majority moves (3 × 9). Also, any potential-function argument for a lower bound whose
class only needs Blue's `X` moves proves the bound for `Dmaj` too, so no such argument exists.

## 4. The parity formula (CONJECTURE, EVIDENCE)

**Conjecture PF.** On an `m × n` board with `m, n ≥ 2`, colour the cells `X` (`r+c` even) and
`Y`. If every Blue stone is on `X`, every White stone is on `Y`, and there is at least one
White stone, then

```math
G = \#\{\text{free } X\} - \#\{\text{free } Y\} = |X| - |Y| - |P| + |Q| .
```

On odd × odd boards `|X| − |Y| = 1`, so `G = 1 − |P| + |Q|`. On boards with an even side,
`|X| = |Y|`, the formula also holds with `X`, `Y` exchanged (a reflection swaps them), and
the White-stone condition can be replaced by "at least one stone".

Instances: `D(v,u) = 1` (the domino lemma); White minority opening `= 2`, i.e. every minority
opening `= −2` (colour swap); on even boards every opening `= −1` and every domino `= 0`.

EVIDENCE (`parity_formula.cpp`, `pf_regions.cpp`, `dominate.cpp`):

| Board | Positions checked | PF holds |
| --- | --- | --- |
| 3×3 | all (every `P ⊆ X`, `Q ⊆ Y`, `Q ≠ ∅`) | 480/480 |
| 3×5 | all | 32,512/32,512 |
| 3×7 | `|P|, |Q| ≤ 3` | 40,600/40,600 |
| 3×9 | `|P|, |Q| ≤ 2` | 9,646/9,646 |
| 5×5 | `|P|, |Q| ≤ 3` | 112,644/112,644 |
| 3×4, 4×4, 3×6, 4×5, 2×3, 2×5 | `|P|, |Q| ≤ 3` | all |
| 2×2 … 4×6 | openings | every opening `= −1` (12 even boards) |
| 5×7 | 40 random (`gen_pf.py`, seed in `runs/pf5x7.txt`), `colout5` | 40/40 |
| 5×9 | 12 random | 12/12 |
| 7×7 | 12 random, `-L 150` | 8/8 decided; 4 INCONCLUSIVE (time), none contradict |

Where it fails (so a proof must use the global rectangle):
- `Q = ∅` on odd × odd boards: `|P| = 1` always fails (majority openings), `|P| = 2` fails in
  5/28 (3×5) and 18/78 (5×5); `|P| = 3` holds on 5×5.
- The path `1 × 5`: 16/24.
- Rectangles with a hole: 3×5 minus a corner (`X` cell): 6 failures of 4,032; minus a `Y`
  cell: 1,663 failures of 3,813; 5×5 minus a corner: 2 of 89,102.

## 5. PF by induction: reduction to one-move statements

Let `C` be the PF class of a fixed board, `F(G) = #free X − #free Y`.

- **(B)** For `G ∈ C` and a Blue-legal `z ∈ Y`: `G^{L,z} ≤ F(G) − 1`.
- **(W′)** For `G ∈ C` and a White-legal `y ∈ X`: `G^{R,y} ⧐ F(G)`.
- **(W)** (strong form) `G^{R,y} ≥ F(G) + 1`.

**Lemma 5.1 (PROVED).** (B) on `C` implies `G ≤ F` on `C`. (W′) on `C` implies `G ≥ F`.

*Proof.* Induction on the number of free cells; `F` is an integer.
`G ≤ F`: a Blue parity move `x ∈ X` (free `X` cells are always Blue-legal in `C`) gives a
position of `C` with `F − 1`, so `G^{L,x} ≤ F − 1` by induction; an off-parity move is
handled by (B); so no `G^L ≥ F`. If `F < 0`, then `F = { | F+1}` and we need `G ⧏ F + 1`:
free `Y` cells exist and are all White-legal, and a White parity move gives `F + 1` by
induction. `G ≥ F` is the mirror image: White parity moves give `F + 1`, off-parity moves
are (W′); if `F > 0` a free `X` cell exists and Blue's parity move gives `F − 1`. ∎

So PF (and with it the domino lemma and all minority openings) is equivalent to (B) and
(W′), each a statement about positions with **one** off-parity stone. The minority-opening
direction needs only (W′), on the positions of `C` reachable from `D` by parity moves.

The converse holds only in weak form: PF implies (W′) and **(B′)** `G^{L,z} ⧏ F`, not (B).
So PF ⟺ (B′) + (W′); (B) is a stronger, sufficient condition.

EVIDENCE (`dominate.cpp`): (B) holds on every computed class position of odd × odd boards
(3×3 112/112, 3×5 13,104/13,104, 3×7 112,488/112,488, 3×9 65,364/65,364). On even boards
(B) is **false** although PF holds: 3×4 (`|P|, |Q| ≤ 3`) PF 1,722/1,722, (B) 1,211/1,450,
(W) 1,148/1,352. So an all-board proof of the upper half must use (B′), not (B).
(W) is **REFUTED**: 3×3 `b.b/obo/ooo` (`F = 2`), White `(2,0)` gives `5/2`; on 3×5 it fails
in 4,304 of 21,504 cases, always with value `F + 1/2` or similar, never `≤ F`.
(W′) holds wherever PF was checked (it is implied by PF).

Observed structure (`offparity.cpp`, 3×5 full): after a White off-parity move, some Blue
**majority** reply restores `≥ F` in every case where any Blue reply does (21,336/21,336;
the remaining cases are endgames where `F < 0` and Blue moves in the integer). After a Blue
off-parity move, some White **minority** reply restores `≤ F` (12,896/12,896). Adjacent
("anti-domino") replies are usually not good (1,586 and 8,496 cases).
Example, 3×5 `D((0,0),(1,0))`: White majority moves give `3/2` or `7/4` (better for White
than parity moves, `2`, but `⧐ 1`); after White `(0,4)`, Blue's only good reply is `(2,4)`.

## 6. Potential-function upper bound on the anti-parity class (REFUTED beyond the class)

The needed direction, after colour exchange, is an **upper** bound on positions with Blue on
`Y` and White on `X`: `G ≤ Φ := #(Blue-legal free Y) − #(White-legal free X)`
(`Φ = −2` at a minority opening, `−1` at the swapped domino). An integer potential proves
`G ≤ Φ` by induction if every Blue move lowers `Φ` by `≥ 1` and, when `Φ < 0`, White has a
class move raising it by `≤ 1`. White's `X` moves raise `Φ` by exactly 1. Blue's `Y` moves
lower it by 1. A first Blue `X` move from the anti-parity class lowers it by `deg ≥ 2` minus
1, fine; but the resulting mixed positions violate `G ≤ Φ` (`potential.cpp`, 3×3: e.g.
`.../.../ob.` has value `1/2`, `Φ = 0`; every failure is by exactly `1/2`). Without Blue
`X` stones `G = Φ` held in all 465 cases. No integer potential of this kind can work.

## 7. Lemma 4 at the anti-domino (REFUTED as a strict route)

For (W′) at `y`, pick a Blue-only neighbour `z ∈ Y` of `y`; Lemma 4(2) gives
`G^{R,y} ≥ G^{y,z} + 1`, so `G^{y,z} ⧐ F − 1` would suffice. EVIDENCE (`antidom` variant of
`dominate.cpp`): `G^{y,z} = F − 1` exactly in the failures (3×3 0/192 good; 3×5 2,450/21,504,
and 12,800 cases have no such `z`). It proves only `G^{R,y} ≥ F`, not the strict `⧐`.

## 8. Reserve cashing (REFUTED)

For upper bounds on the anti-parity class one may fill every White-only `X` cell with a White
stone (Lemma 4(4), `−1` each) and kill every Blue-only `Y` cell (Prop. 6.3(1), `+1` each);
both are `Φ`-neutral and end in an uncoloured region `R` (value `0` or `*`). The bound is
`G ≤ Φ + [G(R) − (|R∩Y| − |R∩X|)]`, and the bracket is positive in general: on the 3×3
minority opening `R` = two isolated corners, bracket `= 2`, bound `0` versus true `−2`.
Cashing destroys the ownership information that PF encodes.

## 9. Free cuts on 3 × n (PROVED inequalities)

Middle-row vertical domino, `v = (1,c)` (`c` odd), `u = (0,c)`. The cell `(2,c)` is
White-only. Lower bound: its edges can be deleted in the dual comparison (it is
Blue-illegal), so `D ≥ S_c + S_{n−1−c} − 1`, with `S_k` the 3×k strip whose column next to
the cut is (Blue-only, White-only, shared). Upper bound: Lemma 4(4) at `(2,c)` gives
`D ≤ T_c + T_{n−1−c} − 1`, `T_k` = end column (Blue-only, White-only, Blue-only).
EVIDENCE (`strips.cpp`): `S_k = 1/2`, `T_k = 1` for odd `k ≤ 9` (0 for even `k`). Hence
`0 ≤ D ≤ 1` for these dominoes at those widths: the cut loses exactly the needed unit.

## 10. Even boards (PROVED parts)

- **2 × n: every domino with `u` below `v` has value 0, and every opening is `≤ −1`.**
  Column `c` is full, so `D = L + R` with `L` = 2×c ladder whose last column is
  (White-only over Blue-only). The row swap is a fixed-point-free involution mapping the
  Blue-legal set onto the White-legal set, so `L = 0` (COL_VALUES Cor. 5.1); same for `R`.
  Lemma 4(4) at `u` gives `O_v ≤ D − 1 = −1`.
- **Any board with a fixed-point-free involutive symmetry `σ`:** if `σ(b)` is adjacent to
  `b`, then `D(b, σb) = 0` (antisymmetric) and `O_b ≤ −1`.
- EVIDENCE: every opening of 2×2 … 2×9, 3×4, 3×6, 4×4, 4×5, 4×6 is exactly `−1`.

## 11. Symmetry pairing on odd × odd boards (REFUTED, with proof)

A colour-reversing pairing strategy for `D` needs a board symmetry exchanging `v` and `u`.
For the half-turn, `u = ρ(v)` adjacent would need `2|v − c| = 1`; for a reflection in a
row or column of cells, the two cells of a crossing domino would be at distance `1/2`
from the axis; for diagonal reflections (square boards) `(r,c)` and `(c,r)` are never
adjacent, nor `(r,c)` and `(n−1−c, n−1−r)`. So no such symmetry exists (PROVED). This is the
parity obstruction: on even boards the same argument works near an axis (§10).

## 12. Majority openings

PF says nothing: majority openings are the class positions with `Q = ∅` where PF fails.
After White's reply the position must leave the class (a White minority reply gives at best
`D − 1 = 0`, tight, GENERAL_IDEAS §3). A White reply `y ∈ X` with `S(v,y) ≤ 0` gives
`O_v ≤ S + * ≤ *`, hence `O_v ≠ 0`. EVIDENCE (`samepar.cpp`): such replies exist for every
majority opening of 3×5, 3×7, 5×5 (4 to 11 per opening), typically corners or cells at even
distance along an edge; the half-turn mirror reply is not always one (5×5 `(1,1)`:
`S = *`). "`O_v ≤ −1/2`" cannot come from one reply plus Lemma 4(3) alone on 5×5 (the best
`S` is `0` for `(0,0)`, `(2,2)`); it also needs Blue's options.

## 13. A closed extended class for (W′) (REFUTED)

To prove (W′) by the same induction as Lemma 5.1, one needs a class containing the
positions `G^{R,y}` and a lower bound valid on it. Tried (`class2.cpp`, `class2b.cpp`):
Blue ⊆ `X`, White anywhere, at least one White stone on `Y`, with
`V2 = #free X − #(White-legal free Y)`.

- `value ≥ V2`: holds with no White `X` stone (it is PF there) and with 2 White `X` stones on
  3×3, but fails 64/704 on 3×3 (all with one White `X` stone, e.g. `oob/bb./.bb` is `5/2`,
  `V2 = 3`). On 3×5 (`|P| ≤ 8`, `|Q| ≤ 7`) it fails in 12,124 of 66,784 positions.
- `value ≤ V2`: holds on 3×5 for up to 2 White `X` stones, fails from 3 on.
- Penalised `value ≥ V2 − Σ_{White y ∈ X} (deg y − 2)`: fails 64/704 on 3×3, 5,956/66,784
  on 3×5.

So the White off-parity stone costs White a **fractional** amount that no integer
potential of this shape captures. A proof of (W′) has to argue about the position after
the move directly, not through an integer bound on a closed class.

## 14. Blue's answer to a White off-parity move (EVIDENCE; fixed rules REFUTED)

`offhist.cpp`, all 21,504 cases `G ∈ C`, `y ∈ X` White-legal, on 3×5 (`|P| ≤ 8`,
`|Q| ≤ 7`): `G^{R,y} − F` takes values in `{1/4, 1/2, 1/2+*, 3/4, 7/8, 1, 1+*, …, 3}`;
minimum `1/4` (24 cases), never `≤ 0`. On 3×3 it is `1/2` or `1`. So (W′) holds there
with a margin of at least `1/4` (EVIDENCE only; the minimum margin may shrink with size,
cf. `Dmaj = 2^{−k}` in §3).

`offdiag.cpp`, same cases: some Blue majority reply restores `≥ F` whenever any reply does
(21,336/21,336). Fixed rules: a diagonal neighbour of `y` is good in 10,496, a cell at
distance 2 in 19,344, an adjacent minority cell in 1,586. None is a strategy. After a Blue
off-parity move, an adjacent White majority reply is good in 8,496/13,104; some minority
reply is good in 12,896 (all where any reply is).

## 15. 5×9 domino check (EVIDENCE)

`colout5 -j 1 -t 22 -T 22`, one process per class (`run_rest2.sh`, logs `runs/d5x9*`):
21 of 22 classes have value `1` (P-outcome at guess 1). `D_5x9_B20_W10` (`v = (2,0)`,
`u = (1,0)`) is INCONCLUSIVE after 600 s (40/42 root children done) and was skipped, as it
is over the ~150 s budget.
