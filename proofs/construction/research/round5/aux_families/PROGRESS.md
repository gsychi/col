# aux_families stream: progress log

Stream: close the non-X auxiliary families of the DD program
(`DU_k<0` odd k, `DV_k<=1/2` even k, `DR_k<0` or `<=-1/4` even k,
`DJ_k<-1/4` odd k) by width-decreasing case tables.

Directory: `proofs/construction/research/round5/aux_families/`.
Scratch: `/tmp/aux_families/`.

Labels follow handoff section 28: PROVED, CERTIFIED-FINITE, EVIDENCE,
CONJECTURE, CONDITIONAL (on named targets), REFUTED.

## Log

- 13:25 Read handoff §1–35, five_row_boundary_induction.md, round3/round4
  progress, star-bound algebra, near-end caps, round4 DX progress,
  white-first note.  Other round-5 streams had not yet written files.
- 13:35 Wrote `tools/colval.cpp`: DISCOVERY evaluator of exact values
  `x+e*` for 5-row permission strips (component decomposition, symmetry
  memo; assumes the classical number-or-number-plus-star theorem, so its
  output is never used as proof).  Cross-checked against the existing
  independent outcome tester: `DD_2=1`, `DD_3=-1`, `D_5=-1/2`, `3x3=0`.
- 13:50 Full value search is fast to width 5 (~25 s per strip) and too slow
  at width 6 (>17 min for DU_6, killed).  Larger widths of the six named
  families are left to ground_truth/.
- 14:20 EVIDENCE (discovery evaluator, not certified): all 144 ordered pairs
  over letters `O D U V X R J u v r j T` (lower case = vertical reflection)
  at widths 1–5, saved in `pair_values_w1_5.json`.  Target families:
  DU odd = -1/2, -1, -1; DV even = 0, 0; DR even = -1/2, -1/2;
  DJ odd = -1/2+*, -3/4, -5/8.  No target is contradicted at widths ≤ 5.
  Child families produced by the six DD separators applied to a U end:
  UU odd -1/4,-1/2,-1/2; JU odd -1,-1/2,-1/2; jU odd -1/2+*,-1/2,-3/8;
  uU odd -1,-1,-1; RU even -1,-1/2; VU even 0,0; XU even -1/4,-1/4;
  vU even 0,0; rU even -1/4,-1/4.  Strongly positive pairs to avoid:
  VV/Vv (2 at even widths), XV (3/2..2), VR (3/2).
- 14:25 `tools/geometry.py`: admissible-comparison builder (left piece, cap
  with seam-retired White, right piece); reproduces all six DD separators.
  Observations to exploit next:
  * Keeping the D-end column attached to the opening column beats a
    one-column cut: after Blue (2,1) in (D,Q)_n the cap
    `[obwbo | bw.wb]` evaluates to -1 (hand computation), versus
    `DD_1 + 0 = 0` from the separator cut.  This repairs the a=1 centre case
    that otherwise needs strictness.
  * Zero-width cuts: after Blue (1,c) the opening column dominates a D end,
    giving `(P,V)_c + (D,Q)_{n-c}`; after Blue (2,c) it dominates a V end,
    giving `(P,V)_{c+1} + (D,Q)_{n-1-c}`.  Rows 0/4 cannot produce a D end on
    the far side (only U/R at c+1 or V/J at c), so U/R/V/J-anchored pair
    families are unavoidable for outer-row openings far from both ends.
  * First-level DU table with target DU_odd <= -1/4 closes numerically
    (using external DD_{>=3}<0, DX<0) provided UU_odd<0, JU_odd<=-1/2 and
    jU_odd<=-1/2 for widths >=3, uU_odd<0, RU_even<=-1/2, VU_even<3/4,
    XU_even<=-1/4, vU_even<3/4, rU_even<1/4.  All are consistent with the
    width<=5 data.  These U-anchored families need their own tables next.
- NEXT: automated closure search over (row, column-parity, end-offset)
  classes with caps up to 3 columns and fixpoint bound iteration.
