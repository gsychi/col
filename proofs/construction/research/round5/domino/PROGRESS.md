# Domino stream progress

## 2026-09-25

- 01:02 Started. Built `colout5` into `/tmp/domino/`. Launched the remaining ten 5×9
  classes (`-j 1 -t 22 -T 22`).
- `-L` in `colout5` is a whole-process wall limit, and the process exits at the first
  inconclusive query. `D_5x9_B20_W10` hit 600 s with 40/42 root children done
  (INCONCLUSIVE, slower than budget). The other classes are rerun one process each with
  `-L 400` (`/tmp/domino/run_rest2.sh`).
- 5×9 results so far (all `value 1`, P-outcome at guess 1): B13_W23 118.7 s, B13_W12
  62.2 s, B13_W14 51.8 s (and 81.7 s on rerun), B20_W21 119.4 s.
- Theory, see `PROOF_ATTEMPTS.md`. Headlines:
  - PROVED: the minority consequence needs the **lower** bound `D ≥ 1`; even `D ⧐ −1`
    suffices for "minority opening ≠ 0". `D ≤ 1` is not used.
  - PROVED (any graph): `O_w + O_x ≤ −2` for adjacent cells; `D(x,w) ≥ O_x + 1`.
  - REFUTED as routes: parity-restricted games (3×n), strong domination (W), integer
    potentials beyond the anti-parity class, Lemma 4 at the anti-domino, reserve cashing,
    symmetry pairing on odd × odd boards.
  - CONJECTURE PF (parity formula) with strong EVIDENCE on every rectangle with sides ≥ 2:
    value = #free majority − #free minority when Blue is on majority, White on minority,
    and White has a stone. Implies the domino lemma and all minority openings `= −2`.
  - PROVED: PF ⟺ two one-move statements (B), (W′) by induction; (B) EVIDENCE everywhere.
  - PROVED: on 2×n boards every opening is `≤ −1` (EVIDENCE: all openings of 12 even boards
    are exactly `−1`).
- 5×9 finished: 21/22 classes `= 1` (also B22_W12, B22_W21, B22_W23, B24_W14, B24_W23).
  B20_W10 INCONCLUSIVE at 600 s, skipped (over budget). Logs in `runs/`.
- PF random samples (`colout5`, 1 thread): 5×7 40/40, 5×9 12/12, 7×7 8/8 decided plus
  4 INCONCLUSIVE at 150 s. No counterexample.
- Correction: PF ⟺ (B′) `G^{L,z} ⧏ F` + (W′). The strong (B) `≤ F − 1` holds on the odd
  boards tested but fails on 3×4 (1,211/1,450) where PF holds.
- REFUTED: integer lower bounds `V2`, `V2 − Σ(deg y − 2)` on the extended class (§13);
  fixed Blue answers to White off-parity moves (§14). EVIDENCE: after a White off-parity
  move, `G^{R,y} − F ≥ 1/4` on all of 3×5.
- Finished. No jobs running.
