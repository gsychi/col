# closure/ progress

## 2026-09-25 exact-bound closure (xclosure)

- New engine `xclosure.cpp` (on the patched solver copy `xcolout5.cpp`).
  Bounds are exact values `x` / `x+*`. Blue-first obligations use `Σ ≤ q`
  after a reply and `Σ ⧏ q` with no reply. White-first obligations use one
  White move with `Σ ≤ q^R`. There are also end-block reserve and
  reserve-cut strategies, and a weakening ladder with re-checks of users.
  Theory and soundness: `NOTES.md`.
- Coverage: widths 8..20 / 9..21, with the stretch lemma (NOTES §7). The old
  8..18 claim missed some opening classes.
- Found and fixed a transposition-table key collision risk in
  `ground_truth/colout5.cpp` when one table is shared across board widths
  (NOTES §9.2). `closure.cpp` and its logs are affected in principle.
- Sanity test: KD (1,3) at w = 9 and 11 closes with no reply
  (`[3:1/4] + [−1/2]`, sum −1/4 ⧏ 0), matching `t3_k13b.log`.

### Runs x1 and x2 (killed)

- x1 stopped at the first failure of each (family, parity), which hid how
  widespread the failures were. x2 collected every failure. It then hit the
  400-family cap, mostly because of two-round searches and new families
  created in pass 3.
- KD even parity (q = 1, after weakening from the exact value): closes,
  280 openings.
- KD odd parity (q = 0, exact): one-round rules fail at the central
  majority-parity openings for every odd w from 13 to 21, for example (1,7),
  (2,6) and (2,8). The best no-reply sum is exactly 0 (not ⧏ 0), and the best
  after-reply sum is 1/4.
- Two-round rule for KD (2,6) at w = 13: reply (0,6), then every Blue second
  move closes (`runs/t_k13c.log`). This is allowed only below W_max
  (NOTES §4). At W_max = 21, two-round rules are not covered by the current
  stretch argument.
- F3/0 fails at w = 8 (2,4). F4/0 (bound 3/2) fails a White-first rule at
  w = 8 (target 2), which led to adding the no-move White-first candidate.

### Diagnostics with more cut shapes (stopped 02:22 UTC on request)

- Added `-alldrops` (every subset of shared White rows dropped at each seam)
  and `-rwfar N` (wider reply and seam window at far openings). Ran
  `-diag -alldrops -rwfar 4 -S 3` (unlimited new families) on KD odd, q = 0:
  - **(1,7) at w = 15 and w = 21 close with no reply**:
    `[7:1] + [F45: −5/4]`, sum −1/4 ⧏ 0 (`runs/d17b.log`, `runs/d17c.log`).
    At w = 21 the right piece has length 14, so the W_max stretch condition
    holds. F45 = `woooooo/.woooob/.ooooow/oooooob/boooooo` (w7), with values
    (w6, w7) = (−5/4, −1/2). It is a new family, and x2 never created it
    because of its new-family budget. **Not yet proved:** F45/0 must itself
    close with bound −5/4, and this rule must be re-found inside a real run.
  - **(2,6) at w = 15 still fails**: no reply gives best 0
    (`[5:1/2] + [F3: −1/2]`), and every reply gives ≥ 1/4, even with 3 seams
    and all drop patterns (`runs/d26b.log`, complete). So this opening
    genuinely needs a deeper rule. A finite two-round rule exists at w = 13
    (`runs/t_k13c.log`).
  - All the jobs above are finished or killed. No xclosure process is running.

### Unfinished code (in `xclosure.cpp`, NOT compiled or tested)

- A gap-representative two-round rule (type `G`: `find_BG`, `gap_configs`,
  `gap_sub`, `layout_of`, and a `ranges` stretch check in `search_cands`).
  After the opening and reply, P = blocks separated by runs of neutral
  columns. A gap < T (default 6) is exact. A gap ≥ T stands for all longer
  gaps of the same parity. Every second Blue move is checked on a reduced
  configuration: gap lengths ≤ T+1, and a long gap split by x2 checked for all
  lengths T..2T+3 with both parts ≤ T+1. Every long (sub)gap must have an
  insertion point in the neutral middle of a family piece of its sub-rule.
  This would make two-round rules valid at W_max and beyond, which is needed
  for (2,6)-type openings.
  Still to do:
  - wire it into `run_table` and the CLI (`-G`, `-T`, `-noG`);
  - add `gaps`, `sranges` and `board` to `rule_json`;
  - write NOTES §4a (the soundness argument above);
  - compile separately from edits and test on KD (2,6) at w = 15 and 21.

### Most promising next steps

1. Finish and test the `G` rule on KD (2,6), w = 15..21.
2. Rerun from KD with a larger `-M` (e.g. 5000) and a larger `-N`, so that
   families like F45 get created, and report the family count needed.
