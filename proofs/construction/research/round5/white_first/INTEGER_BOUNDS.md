# Integer bounds remove the White-first problem (2026-09-24)

Labels as in [`../HANDOFF.md`](../HANDOFF.md).

## 1. Why strictness keeps appearing (PROVED)

For a short game `G` and a number `x`, `G ≤ x` means Left (Blue), moving
first, loses `G − x`. Blue's options there include moves in the number
component `−x`. If `−x` has a Left option, which is the case for every
`x < 0` and every non-integer `x > 0`, Blue can move there, and White must
then win `G` (plus a number) **moving first**. So proving `G ≤ −1`,
`G ≤ −1/2` or `G ≤ 1/2` needs a White-first witness. This is the source of
the DD strictness obligation.

**Lemma A (integer bounds are Blue-first).** Let `k ≥ 0` be an integer.
Then `G ≤ k` iff, for every Blue option `G^L`, at least one holds:

- (a) some White option `G^{LR}` has `G^{LR} ≤ k`;
- (b) `k ≥ 1` and `G^L ≤ k − 1`.

*Proof.* Write `k` in canonical form. For `k ≥ 1`, `−k = { | −(k−1)}` has no
Left option, so the Left options of `G − k` are exactly `G^L − k`. `G − k ≤ 0`
iff each of them has a Right option `≤ 0`. Those Right options are
`G^{LR} − k` and, for `k ≥ 1`, `G^L − (k−1)`. For `k = 0` only the first
kind exists. ∎

Every statement Lemma A requires has the form "position `≤` nonnegative
integer", which is again Blue-first.

**Negative integers come from reserve moves.** By COL_VALUES.md Lemma
4(4), if `u` is White-only in `G`, then `G ≤ G^{R,u} − 1`. Iterating,
`G ≤ −m` follows from `m` White private moves and a final bound `≤ 0`.
Every endpoint letter D, U, V, X, R, J has a White-only cell, so this is
widely available.

**Consequence.** An induction that uses only integer bounds — nonnegative
bounds via Lemma A, negative ones via reserve moves — never needs a
White-first witness. Comparisons still apply: if `G ≤ Σ T_i` and each
`T_i ≤ k_i` with `k_i` integers, then `G ≤ Σ k_i`. The rule for a table
proving `F ≤ k` is:

- with no reply after a Blue opening, the region bounds must sum to `≤ k − 1`;
- after a White reply, they must sum to `≤ k`.

The price is rounding: a region of value `−1/2` counts as `0`, and a region
of value `x + *` with `x` an integer counts as `x + 1`.

## 2. The reserve move at `(2,0)` is worth exactly 1 (EVIDENCE)

`KQ_n − DQ_n = 1` for every right letter `Q ∈ {D, U, V, X, R, J}` at every
width 3–6, and at most widths 1–2. Data: `runs/values.jsonl` and
`../ground_truth/`. So Lemma 4(4) is tight here, and **`K_n ≤ 0` is
equivalent to `DD_n ≤ −1`**. The K route is exactly "prove the true integer
value bound `DD_odd ≤ −1` by a Blue-first table".

`K_1..K_9 = 1, 2, 0, 1, 0, 1, 0, 1, 0` (EVIDENCE), so `K_n ≤ 0` at every
odd width tested.

## 3. `K_7` under integer bounds (EVIDENCE)

Tool: `int_reply_test.py`. It uses exact region values from `colval` and
`colout5`, each rounded up to an integer, at most 2 vertical seams, and
every White-drop choice at each seam. Output:
`runs/int_reply_K7.jsonl`, `runs/int_reply_K7_o13.txt`.

| Blue opening (rows 0–2 by symmetry) | Result |
| --- | --- |
| (0,1), (0,3), (0,5), (1,0), (1,2), (1,4), (1,6), (2,1), (2,3), (2,5) | Close with **no reply**; integer sum −1 |
| (0,0), (0,2), (0,4), (0,6), (1,1), (1,5), (2,2), (2,4) | Close **after one White reply**; integer sum 0 |
| **(1,3)** | **Fails.** All 9 winning replies give best integer sum +1 with ≤ 2 seams |

Pattern: minority-parity openings close with no reply, and majority ones
need a reply. This is the same parity split as on the empty 5 × 9 board.
The single obstruction is the opening beside the centre, (1,3). Its best
splits leave a width-6 piece of value 1 next to a piece of value 0 or
−1/4. The loss comes from rounding (−1/4 → 0) and from the centre piece's
+1.

## 4. What this does and does not establish

- PROVED: Lemma A and its consequence (§1).
- EVIDENCE: one level of the `K_7` table closes under integer bounds for
  18 of 19 opening classes.
- NOT established:
  - that the region families used here have the needed integer bounds at
    all widths. Each needs its own integer table, as the next level of the
    closure;
  - any all-width geometric argument;
  - any certificate.

## 5. Next steps

1. Crack `K_7` opening (1,3). Options: one more ply of expansion (Blue's
   second move, then close with integer bounds); three seams; or one
   explicitly fractional piece whose White-first witness is certified
   directly as a finite fact.
2. Rerun on `K_9` to see whether the same reply and seam shapes recur
   with a shift by 2. That is the evidence that a width-independent table
   exists.
3. Collect the region families used, as (left end, right end) pairs, with
   their integer bounds. Run the same integer test on each family, and
   iterate until the family set closes or a family fails. This is the
   closed boundary-state search of handoff §23, now in a form where every
   obligation is Blue-first.
