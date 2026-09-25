# Round five: literature and theory stream

Deliverables:

- [LITERATURE.md](LITERATURE.md): what is published on Col on grids, with
  exact locations and a verified / secondhand / not-accessed label for each
  claim. The odd×odd conjecture is open in the literature; published
  solutions stop at 3×3, 3×5, 3×7, 3×9, 5×5 (Demeur 2020, via Uiterwijk
  2021).
- [COL_VALUES.md](COL_VALUES.md): a self-contained proof that every Col
  position, i.e. every shadow state `(A, B)` on any graph and every sum of
  such, is `x` or `x+*`. Consequences for `≤`, `<`, `+*`, `T_q`, outcome
  classes and the round-4 star bookkeeping. Explosive separator sets (can
  be deleted), adjacent twins, permission increments, and two refuted
  claims.
- [GENERAL_IDEAS.md](GENERAL_IDEAS.md): ranked approaches for arbitrary
  odd heights, each with a falsification test and its result. It includes
  a proof that mirroring Blue's first three moves loses on every odd×odd
  board with a side `≥ 5`, and the domino conjecture, which would settle
  every minority-cell opening.
- [PROGRESS.md](PROGRESS.md): time-stamped log.

Code (one thread each; every run capped at 30 minutes):

| File | Purpose |
| --- | --- |
| `cgt_core.py` | General canonical-form engine and Col evaluator on any graph |
| `col_values_exhaustive.py` | Every shadow state of 20 small graphs → `col_values_exhaustive.json` |
| `col_values_check.py` | Random graphs and grids → `col_values_check_seed1.json` (`python3 col_values_check.py 60 1 out.json`) |
| `col_values_extra.py` | Permission increments, explosive sets → `col_values_extra.json` |
| `col_fastval.cpp` | Theorem-based fast grid evaluator (`c++ -O2 -std=c++17 col_fastval.cpp -o col_fastval`); modes `value`, `openings`, `isolate`, `ddreserve`, `mirror`, `random` |
| `fastval_crosscheck.py` | `col_fastval` against `cgt_core.py` (1,950 states, 0 mismatches) |
| `col_probe.cpp` | Early minimax prober (mirror-strategy counts); superseded for values |
| `ideas_tests.py`, `reserve_openings.py` | Falsification tests for GENERAL_IDEAS.md |
| `runs/` | Raw outputs of the `col_fastval` experiments |

In zsh, pass board sizes held in a variable as `${=b}`; plain `$b` is not
word-split.
