# Literature and theory stream: progress log

Stream directory: `proofs/construction/research/round5/literature/`.
Scratch: `/tmp/literature/`.

Deliverables:

1. `LITERATURE.md` — known results on Col on grids, with exact citations.
2. `COL_VALUES.md` — number-or-number-plus-star theorem in the shadow-state
   setting, with proof, computational check, and consequences.
3. `GENERAL_IDEAS.md` — arbitrary-odd-height approaches with falsification
   tests.

## Log

- 2026-09-23 13:30 — Read handoff (all sections), odd-odd roadmap, round-4
  star bounds, round-4 DX progress, round-4 graph shortcuts, round-2
  reflection obstruction and twin modules, 3×n theorem write-up.
- 13:35 — Downloaded and read Uiterwijk, ACG 2021 Part 1 (preprint PDF from
  icga.org, 10 pp.) and Part 2. Key: Demeur thesis citation [4]; odd×odd
  Col listed as "?"; Conway credited with number-or-number-plus-star.
- 13:40 — Found partial scan of ONAG 2nd ed. (Rutgers, Zeilberger EM13
  course files onag1–3.pdf). OCR + page images of pp. 91–95 read directly:
  p. 93 states the Conway–Guy theorem and the inequality
  `G^L + * <= G <= G^R + *`, deduced from the two monotonicity rules;
  p. 94 explosive-node principle and adjacent-twin tinting rule; p. 95
  small values. The handoff §18 leaf-deletion identity is a p. 94 figure.
- 13:55 — Winning Ways vol. 1 (2nd ed.) pp. 47–51 read via an OCR text
  extract (scribd upload, found by web search): "A Theorem about Col",
  proof outline, rule list, "Nick Inglis has shown ... arbitrarily large
  denominators". Also read: Austin 1976 Calgary MSc thesis (Thm 2.3 with
  Lemmas 2.1–2.2), Fenner et al. ISAAC 2015 (Col PSPACE-complete on
  uncoloured graphs; such graphs only take values 0 and *), Burke–Hearn
  (planar), Burke–Tennenhouse 2025 (triangular grids), Huntemann 2018 thesis
  and 2023 slides (boiling point of Col is 0). Demeur's thesis not found
  online.
- 14:20 — Wrote `cgt_core.py` (general canonical forms, Col on any graph,
  independent sum-outcome certifier), `col_values_check.py` (random),
  `col_values_exhaustive.py` (every shadow state of 20 small graphs).
  Exhaustive: 640,148 states, 0 failures of T1 (x or x+*), T2 (option
  inequalities), T3, T5. X1 (Blue can always win via a shared cell) REFUTED:
  2×3 `bob/.w.` = 1.
- 14:21 — `col_probe.cpp` (plain minimax with transposition table) too slow
  for 3×7 values; stopped. Wrote `col_fastval.cpp`: computes values bottom-up
  using Theorem 5 (every value is `x` or `x+*`), with component splitting and
  a translation-normalised memo. It aborts if a theorem conclusion ever
  fails. Cross-checked on 1,950 random grid states (2×3 to 4×4) against the
  general canonical-form code: 0 mismatches (`fastval_crosscheck.py`).
- 14:23 — Mirror-with-centre-repair: PROVED obstruction (three Blue moves
  with White mirroring isolate a live centre; value `*`, Blue to move).
  Confirmed numerically on 3×5, 3×7, 5×3, 5×5, 3×9, 5×7.
- 14:24 — Proposition 6.1 strengthened to `G = G − S` for explosive
  separator sets of any size; Proposition 6.2 proof written in full.
- 14:25 — Empty-board values: 3×3, 3×5, 3×7, 3×9, 5×5 all 0, with every
  opening value listed. Openings at cells with `r+c` odd are exactly `−2`
  on every board tested; other openings are `−1/2`, `−3/4` or `−1`.
- 14:40 — `LITERATURE.md` written. Web search found no post-2021 result on
  odd×odd Col; a search summary falsely claimed published 5×7/7×7 results.
- (A crash seen earlier in `col_fastval isolate` was a shell quoting bug:
  zsh does not word-split `$b`, so the board size arrived as one argument.)
- 14:55 — 5×7 openings: killed at the 30-minute cap, no output
  (INCONCLUSIVE; peak 1.08 GB).
- 15:20 — Falsification tests: static 2-row band costs `(n−1)/2`; the static
  middle column is never explosive (3×2–5×5). DD reserve bound tight for
  `n ≤ 6` (DD_7 hit the 25-minute cap).
- 15:23 — Domino pattern: Blue at `v`, White at an adjacent `u` has value
  `+1` if `v` is a majority cell and `−1` otherwise, on 3×3, 3×5, 3×7, 3×9,
  5×5. This implies minority openings are `≤ −2`; for majority openings the
  same bound is exactly `0`.
- 15:27 — `col_values_extra.py` exhaustive: Prop 6.3 bounds 0 failures;
  explosive sets 500/500 (including `G = G − S`); "increment ≤ 1+*" REFUTED
  (1×5 `www..`; max increment `3/2`). COL_VALUES.md updated.
- 15:30 — `GENERAL_IDEAS.md`, `README.md` written; JSON and run outputs
  saved in this directory.
