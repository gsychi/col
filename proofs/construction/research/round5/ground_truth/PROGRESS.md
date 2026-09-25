# Ground-truth stream: progress log

Stream question: what are the exact values of the five-row boundary families
(DD, DU, DV, DR, DX, DJ, one-ended D/U/V/X/R/J, RX, VX, XX, XU, XR, XV, XJ, M)
and do the conjectured auxiliary bounds survive at larger widths?

Status labels follow section 28 of the handoff: PROVED, CERTIFIED-FINITE,
EVIDENCE, CONJECTURE, REFUTED.

## Major news (failures of conjectured targets)

None yet. (DX_8 = −1/4, not −1/8: the DX margin stopped shrinking.)

## Log

- 2026-09-23 13:30 — Started. Read handoff, round-4 notes, five-row induction
  and White-first notes. Writing DEFINITIONS.md and an exact value solver.
- 14:00 — DEFINITIONS.md done; masks cross-checked against every recorded
  value (no mismatch). Widths 1–5 valued exactly by colval (EVIDENCE).
- 14:25 — Width 6 complete for all families; width 7 complete for all but
  DR_7 (EVIDENCE, colout bisection with P-outcome at the reported value).
  Width 7: DD −1, DU −1, DV 1, DX 1/2, DJ −1/2, RX 1/2, VX 1/2, XX 1/2,
  XU 1/2, XJ 1/2, M_7 −1, D −1/2, U −1/2, V 1, X 1/2, R 0, J 0, DT 1.
  All width-7 targets hold: DU_7<0, DJ_7=−1/2<−1/4, DD_7<0, T_1(RX_7),
  T_2(VX_7), T_1(XX_7), M_7≤0.
- 14:25 — Rust raw solver: DX_8 vs 0 timed out at 1800 s for both movers
  (INCONCLUSIVE). Switched sweeps to colout3 (threshold TT + separate
  valuation of split components): DJ_7 in 61 s vs 96 s for colout2.
  Width-8 sweep (DX, DR, DV, DD, DU) started, log runs/sweep_w8.log.
- 14:26 — First width-8 attempt and the DR_7 job were killed by an external
  SIGTERM (rc −15; the "Error" rows in values.jsonl are not results).
  Relaunched detached (nohup) together with DR_7.

### Continuation (second agent, from 15:53)

- 15:55 — No job was running (the nohup relaunch had died with its shell;
  runs/sweep_w8.log empty). Added `launch.py`: double-fork + setsid launcher
  with a wall-clock cap; every long job now goes through it.
- 16:00 — `colout5.cpp`: colout plus TT best-move, history heuristic, root
  symmetry dedupe, idle-thread helping on unfinished root children, progress
  lines, `-L` wall limit (timeout ⇒ INCONCLUSIVE), persistent component-value
  file (`-V`/`-W`). Validated: all 110 recorded values of widths 1–6 match
  (`validate.py`); multithreaded run matches widths 1–5.
- 16:20 — Tried a Lemma-4 "single opponent move refutation" at expected-loss
  nodes (sound, COL_VALUES Lemma 4). As a full recursive search it blows up
  (DJ_7: 1.2 G nodes vs 16 M); disabled (`-R 0` default).
- 16:24 — **DX_8 = −1/4** (EVIDENCE; colout, 4 threads, 1535 s; trail
  −1/8:R −1:L −1/2:L −1/4:P). So DX_8 ≠ −1/8: the halving trend
  −1, −1/2, −1/4 stops at width 8. Target DX_8 < 0 HOLDS, margin 1/4.
  Observation: the test at the correct threshold is cheap once the table is
  warm; the wrong-threshold tests dominate (−1/8 test: 10.5 G nodes).
- 16:27 — Launched DJ_9 (guess −3/8, 4 threads, cap 3 h; runs/dj9.*) and
  DR_8, DV_8 (1 thread, cap 1 h; runs/w8a.*).
- 16:33–17:30 — **DR_8 = −1/2, DV_8 = 0, DD_9 = −1, DU_9 = −1** (EVIDENCE,
  colout5, P-outcome at the value). All four targets HOLD.
- Solver studies: table size barely matters (64× entries → 1.5× fewer nodes);
  move ordering is near-optimal (first move wins at 96–98% of won nodes);
  cut-move bounds (Lemma 4) are useless (+4 per cut); the Cor 4.4 "pass rule"
  is exact but saves only ~20% nodes. "Win with margin" tests cost ~20× a
  P-test half (DJ_7: 193 M vs 10 M nodes).
- Certificates: `colcert5.cpp` (generator) + `checkcert.cpp` (independent,
  search-free checker; folded DAG + locally verified value table) +
  `certify.py`. Verified DD_3, DX_4, DJ_5, DJ_1 pairs; corruption tests rejected.
- ~17:57 — DJ_9 (Blue-first at −3/8) killed externally after 5045 s:
  INCONCLUSIVE (1/44 root children, 43 G nodes). Relaunched as the decisive
  target test at −1/4, Blue-first and White-first in parallel (runs/dj9b.*,
  runs/dj9w.*, 2 threads each, cap 3 h).
