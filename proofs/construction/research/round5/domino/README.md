# Domino lemma (all odd × odd boards)

**Conjecture.** On an empty odd × odd board with both sides ≥ 3, place a
Blue stone on a majority cell `v` (`r + c` even) and a White stone on an
orthogonal neighbour `u`. The resulting position has value exactly `1`.

**Why it matters (PROVED consequence).** It implies that every minority
opening is `≤ −2`, hence `< 0`, on every odd × odd board
(GENERAL_IDEAS.md Prop. 3.2). The proof: after Blue opens at a minority cell,
each neighbour is White-only, and Lemma 4(4) of COL_VALUES.md gives
`opening ≤ D − 1`, where `D` is the domino position with colours exchanged,
`= −1`. That settles about half of all openings at every size.

## Evidence (EVIDENCE: `colout5` outcome search at the guessed value 1)

Every adjacent pair up to reflection, all equal to `1`:

| Board | Classes | Result |
| --- | --- | --- |
| 3×3, 3×5, 3×7, 3×9, 5×5 | all | 1 (earlier, `literature/runs/reserve_openings.txt`) |
| 5×5 | 12 | all 1 |
| 3×11 | 16 | all 1 |
| 5×7 | 17 | all 1 |
| 3×13 | 19 | all 1 |
| 5×9 | 22 | running; first 8 all 1 |
| 7×7 | 24 | queued |

Reproduce with:

```sh
python3 gen_domino.py H W > q.txt
colout5 -j 4 -t 24 -T 24 < q.txt
```

`colout5` is built from `../ground_truth/colout5.cpp`.

## Status

CONJECTURE with strong evidence. No proof yet. Note that `D − 1 = 0`
says Blue is exactly one move ahead. Lemma 4(4) is tight in every
minority opening computed: the opening equals `D(u, v) − 1`.
