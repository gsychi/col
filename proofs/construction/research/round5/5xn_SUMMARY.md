# 5 × n: what we know (2026-09-29)

Goal: every empty 5 × n Col board with n odd is `0` (second-player win).
Labels: **PROVED**, **CERTIFIED** (finite, replayed certificate), **EVIDENCE**
(solver output), **CONJECTURE**, **REFUTED**. Details: [`HANDOFF.md`](HANDOFF.md),
[`closure/NOTES.md`](closure/NOTES.md), [`closure/PROGRESS.md`](closure/PROGRESS.md),
[`domino/PROOF_ATTEMPTS.md`](domino/PROOF_ATTEMPTS.md).

## TL;DR

- 5 × n is **open**, but it now reduces to **one remaining obstacle**: a Blue
  opening at the centre of the strip after the reserve move. Everything else
  in the main family closes.
- The route: prove `K_n ≤ 0` for odd n, where K is the DD boundary strip
  after White's private move `(2,0)`. `K_n ≤ 0` gives `DD_n ≤ −1` (PROVED
  reduction). This is the White-first step that blocked round four.
- The engine proves the **even-width** half (`K ≤ 1`, 280 opening classes)
  and closes every **odd-width** opening except the central ones, such as
  `(2,6)`. Those miss by **exactly 1/4**.
- `(2,6)` at width 13 **does close with a two-round rule**: White replies
  `(0,6)`, and all 28 Blue continuations cut to sums ≤ 0. What is missing is a
  version of the width-extension argument that covers two-round rules. It is
  designed but not yet built.
- 5 × 9 is **9 of 15** representative openings certified (27 of 45 openings),
  but that board alone does not prove 5 × n.

## Key insights

1. **Every value is a number or number+\*** (PROVED). The conjecture is
   equivalent to "no Blue opening equals exactly 0". Bounds are comparisons
   of dyadic numbers, so rule checking is exact arithmetic.
2. **The reserve move converts a strict bound into a non-strict one**
   (PROVED). White's private cell `(2,0)` is worth exactly 1 (EVIDENCE:
   `KQ_n = DQ_n + 1`). So `DD_n < 0` becomes `K_n ≤ 0`, which the
   comparison principle produces directly.
3. **Integer bounds need no White-first facts** (Lemma A, PROVED). But
   rounding to integers loses the proof: `1/4` rounds to 1 and `−1/2` to 0.
   **Exact dyadic bounds are necessary.** With them, the old blocker `(1,3)`
   closes with one rule at every width (`1/4 + (−1/2) = −1/4`).
4. **Checkerboard parity decides difficulty** (EVIDENCE). Minority openings
   (r+c odd) are `−2` and close immediately. Majority openings are `−1/2` to
   `−1` and need replies. The hardest ones are central, where the end
   blocks give no help.
5. **Local one-round arguments hit a wall at the centre** (EVIDENCE, widths
   13–21). The best cut after a centre opening sums to exactly 0, or to 1/4
   after a reply. Not ⧏ 0 means the one-round rule fails. More seams and every
   drop pattern don't fix `(2,6)`. White needs a second reply.
6. **The width-coverage argument had a hole, now fixed.** "Widths 8..18 cover
   all opening classes" was false: some classes first appear at widths 19–21.
   The correct check is widths 8..20 and 9..21, plus a **stretch lemma**. If
   a long end piece is a family member, inserting two neutral columns
   gives a valid rule at w+2. So finitely many widths prove all widths.
7. **The solver had a transposition-table bug**: keys ignored the board width
   when one table was shared across widths. It is fixed in `xcolout5.cpp`. Old
   integer-bound logs are suspect in principle. The new values do not use
   them.
8. **No repeating 5-row tile exists** (EVIDENCE): no neutral 5 × k block with
   k ≤ 5 is ≤ 0. So 5 × n can't copy the 3 × n tiling. It needs families
   with fixed end blocks plus induction on width, which is what the closure
   does.
9. **Pure mirroring is refuted** on odd × odd boards with a side ≥ 5 (PROVED).
   The mirror reply does work for openings next to the centre (PROVED).

## Status of the closure (induction over boundary families)

| Piece | Status |
| --- | --- |
| Reserve reduction `K_n ≤ 0 ⟹ DD_n ≤ −1` | PROVED |
| KD even widths, bound 1 | closes (EVIDENCE, solver values not yet certified) |
| KD odd widths, one-round openings | close except central majority openings |
| `(1,7)` at w = 15, 21 | closes with no reply: `[7:1] + [F45: −5/4] = −1/4`; needs family F45 to close at −5/4 |
| `(2,6)` at w = 13 | closes with a two-round rule (reply `(0,6)`) |
| `(2,6)` at w ≥ 15 | open: needs the two-round rule plus an all-widths extension |
| Other families spawned (F3/0, F4/0, …) | some fail at w = 8–10; not yet re-run with exact rules and larger caps |

## What remains, in order

1. **Two-round rules at every width.** A gap-representative rule (`G`):
   neutral runs longer than T stand for all longer runs of the same parity.
   It is written in `closure/xclosure.cpp` but not compiled, wired in, or
   proved. Then test it on `(2,6)` for w = 15..21.
2. **Full rerun with larger family caps** (`-M 5000`), so families like F45
   are created. Report whether the list closes.
3. **Speed.** The last runs stopped at the 400-family cap, and the next
   run is about 10× larger. Measured options:
   - cache values per independent component (258k cached pieces contain only
     133k distinct components);
   - guess-then-confirm values (2 searches instead of about 6);
   - prune drop patterns by monotonicity;
   - persist the transposition table.
4. **Certify the finite inputs.** Replay the exact values of pieces ≤ 7
   columns with an independent checker, and re-prove the solver's
   dominance pruning.
5. **Bridge to the empty board.** Map each empty 5 × n opening to boundary
   families (DD, DJ, DX, …) with one reply. The DJ margin is shrinking
   (`−3/4, −5/8, −1/2` at odd widths) and may break at `DJ_11`.

## Side results useful for 5 × n

- **Domino lemma** (for every odd × odd board, every minority opening ≤ −2).
  It reduces to one one-move statement, (W′) (PROVED equivalence). (W′) holds
  on every position checked (EVIDENCE). On 5 × 9, 21 of 22 domino classes
  equal 1, and the last timed out. This would dispose of all minority
  openings at once, but not the central majority openings that block 5 × n.
