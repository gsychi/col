# Col Tablebase Proof-Mining Report

This report scans shadow-key tablebases as generalized tinted positions: `o` legal for both players, `b` P1-only, `w` P2-only, and `.` absent/dead inside a component bounding box.

- Tablebase directory: `data/tablebases`
- Sample stride: `25` (1 means full scan)
- Boards scanned: `8`
- Distinct component families: `1602413`

## Board Summary

| Board | Entries | Scanned | STM win % | Components | Avg comps/position | Opening % | Midgame % | Endgame % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 3x3 | 27 | 2 | 50.0% | 1 | 0.50 | 50.0% | 0.0% | 50.0% |
| 3x5 | 150 | 6 | 83.3% | 8 | 1.33 | 83.3% | 16.7% | 0.0% |
| 3x7 | 9385 | 376 | 68.9% | 502 | 1.34 | 11.4% | 60.6% | 27.9% |
| 5x5 | 31700 | 1268 | 72.4% | 1824 | 1.44 | 5.1% | 90.5% | 4.4% |
| 3x9 | 139381 | 5576 | 65.2% | 11897 | 2.13 | 5.4% | 53.4% | 41.2% |
| 3x11 | 16689534 | 667582 | 69.0% | 2065780 | 3.09 | 0.4% | 43.0% | 56.6% |
| 5x7 | 79253910 | 3170157 | 69.8% | 9350123 | 2.95 | 0.1% | 44.7% | 55.2% |
| 3x13 | 74827013 | 2993081 | 77.8% | 8115322 | 2.71 | 0.6% | 73.4% | 26.0% |

## Most Frequent Tinted Component Families

These are component families after translation/symmetry/color-swap canonicalization. `STM win %` is the outcome of the whole tablebase position, so treat it as correlation, not a component value proof.

### 1. `1x1`

- Occurrences: `6221287`
- STM win %: `71.6%`
- Local values (<=12 cells): 1 (52%), -1 (48%)
- Avg cells: `1.0` (`o` 0.0%, `b` 52.4%, `w` 47.6%)
- Phase mix: opening 0.1%, midgame 46.9%, endgame 53.1%
- Top boards: 5x7 (3007610), 3x13 (2491395), 3x11 (718087), 3x9 (3883), 5x5 (248)

```text
b
```

### 2. `1x2`

- Occurrences: `1779900`
- STM win %: `72.4%`
- Local values (<=12 cells): 1 (50%), -1 (50%)
- Avg cells: `2.0` (`o` 0.0%, `b` 50.5%, `w` 49.5%)
- Phase mix: opening 0.0%, midgame 51.9%, endgame 48.1%
- Top boards: 5x7 (917405), 3x13 (691372), 3x11 (170216), 3x9 (842), 5x5 (52)

```text
bb
```

### 3. `1x2`

- Occurrences: `1443955`
- STM win %: `72.7%`
- Local values (<=12 cells): 0 (100%)
- Avg cells: `2.0` (`o` 0.0%, `b` 50.0%, `w` 50.0%)
- Phase mix: opening 0.1%, midgame 41.5%, endgame 58.4%
- Top boards: 5x7 (763933), 3x13 (482043), 3x11 (197021), 3x9 (870), 5x5 (61)

```text
bw
```

### 4. `1x3`

- Occurrences: `408755`
- STM win %: `74.4%`
- Local values (<=12 cells): 0 (100%)
- Avg cells: `3.0` (`o` 33.3%, `b` 33.3%, `w` 33.3%)
- Phase mix: opening 0.0%, midgame 58.6%, endgame 41.4%
- Top boards: 5x7 (223022), 3x13 (128197), 3x11 (57259), 3x9 (256), 5x5 (16)

```text
bow
```

### 5. `2x2`

- Occurrences: `381237`
- STM win %: `74.0%`
- Local values (<=12 cells): 1 (54%), -1 (46%)
- Avg cells: `3.0` (`o` 0.0%, `b` 51.2%, `w` 48.8%)
- Phase mix: opening 0.2%, midgame 46.2%, endgame 53.6%
- Top boards: 5x7 (184549), 3x13 (139406), 3x11 (56935), 3x9 (310), 5x5 (26)

```text
.b
bw
```

### 6. `1x2`

- Occurrences: `334462`
- STM win %: `78.9%`
- Local values (<=12 cells): -1/2 (55%), 1/2 (45%)
- Avg cells: `2.0` (`o` 50.0%, `b` 22.3%, `w` 27.7%)
- Phase mix: opening 0.0%, midgame 28.5%, endgame 71.5%
- Top boards: 5x7 (198062), 3x13 (74288), 3x11 (61873), 3x9 (199), 5x5 (30)

```text
bo
```

### 7. `1x3`

- Occurrences: `261740`
- STM win %: `71.2%`
- Local values (<=12 cells): 0 (100%)
- Avg cells: `3.0` (`o` 0.0%, `b` 49.2%, `w` 50.8%)
- Phase mix: opening 0.0%, midgame 36.6%, endgame 63.4%
- Top boards: 5x7 (188195), 3x13 (54398), 3x11 (19077), 3x9 (62), 5x5 (7)

```text
bbw
```

### 8. `1x1`

- Occurrences: `244730`
- STM win %: `90.3%`
- Local values (<=12 cells): * (100%)
- Avg cells: `1.0` (`o` 100.0%, `b` 0.0%, `w` 0.0%)
- Phase mix: opening 0.0%, midgame 25.5%, endgame 74.5%
- Top boards: 5x7 (158555), 3x13 (48650), 3x11 (37393), 3x9 (112), 5x5 (12)

```text
o
```

### 9. `2x2`

- Occurrences: `219682`
- STM win %: `75.7%`
- Local values (<=12 cells): 2 (60%), -2 (40%)
- Avg cells: `3.0` (`o` 0.0%, `b` 60.0%, `w` 40.0%)
- Phase mix: opening 0.0%, midgame 53.2%, endgame 46.8%
- Top boards: 3x13 (111489), 5x7 (86324), 3x11 (21727), 3x9 (134), 5x5 (7)

```text
.b
bb
```

### 10. `2x2`

- Occurrences: `163321`
- STM win %: `71.6%`
- Local values (<=12 cells): -1 (69%), 1 (31%)
- Avg cells: `3.0` (`o` 33.3%, `b` 20.7%, `w` 46.0%)
- Phase mix: opening 0.1%, midgame 42.1%, endgame 57.8%
- Top boards: 5x7 (97233), 3x13 (40820), 3x11 (25168), 3x9 (91), 5x5 (6)

```text
.b
bo
```

### 11. `2x3`

- Occurrences: `133964`
- STM win %: `74.4%`
- Local values (<=12 cells): 1 (63%), -1 (37%)
- Avg cells: `4.0` (`o` 0.0%, `b` 56.5%, `w` 43.5%)
- Phase mix: opening 0.0%, midgame 53.1%, endgame 46.9%
- Top boards: 3x13 (59938), 5x7 (57184), 3x11 (16742), 3x9 (91), 5x5 (5)

```text
..b
wbb
```

### 12. `1x3`

- Occurrences: `92859`
- STM win %: `75.3%`
- Local values (<=12 cells): 1 (55%), -1 (45%)
- Avg cells: `3.0` (`o` 0.0%, `b` 51.5%, `w` 48.5%)
- Phase mix: opening 0.0%, midgame 36.0%, endgame 64.0%
- Top boards: 5x7 (46553), 3x13 (30855), 3x11 (15414), 3x9 (33), 5x5 (2)

```text
bwb
```

### 13. `2x3`

- Occurrences: `89610`
- STM win %: `72.9%`
- Local values (<=12 cells): 0 (100%)
- Avg cells: `4.0` (`o` 0.0%, `b` 50.0%, `w` 50.0%)
- Phase mix: opening 0.4%, midgame 53.8%, endgame 45.9%
- Top boards: 5x7 (38729), 3x13 (35448), 3x11 (15316), 3x9 (101), 5x5 (13)

```text
.bw
bw.
```

### 14. `2x3`

- Occurrences: `89337`
- STM win %: `71.1%`
- Local values (<=12 cells): -2 (51%), 2 (49%)
- Avg cells: `4.0` (`o` 0.0%, `b` 49.4%, `w` 50.6%)
- Phase mix: opening 0.0%, midgame 58.5%, endgame 41.5%
- Top boards: 5x7 (48653), 3x13 (34233), 3x11 (6402), 3x9 (47), 5x5 (2)

```text
.bb
bb.
```

### 15. `2x2`

- Occurrences: `88846`
- STM win %: `69.2%`
- Local values (<=12 cells): 0 (100%)
- Avg cells: `3.0` (`o` 0.0%, `b` 48.7%, `w` 51.3%)
- Phase mix: opening 0.0%, midgame 31.4%, endgame 68.6%
- Top boards: 5x7 (62270), 3x13 (19554), 3x11 (6988), 3x9 (29), 5x5 (4)

```text
.b
wb
```

## Exact Local Zero Component Candidates

These component families were locally evaluable by the CGT engine and every sampled observation had exact value `0`. Because component signatures are canonicalized under color swap, `0` is the safest value to mine this way.

| Signature | Value observations | Occurrences | Phase mix | Sample |
|---|---:|---:|---|---|
| `1x2` | 1443955 | 1443955 | O 0% / M 42% / E 58% | `bw` |
| `1x3` | 408755 | 408755 | O 0% / M 59% / E 41% | `bow` |
| `1x3` | 261740 | 261740 | O 0% / M 37% / E 63% | `bbw` |
| `2x3` | 89610 | 89610 | O 0% / M 54% / E 46% | `.bw/bw.` |
| `2x2` | 88846 | 88846 | O 0% / M 31% / E 69% | `.b/wb` |
| `2x3` | 81124 | 81124 | O 0% / M 41% / E 58% | `..b/wbw` |
| `2x2` | 65365 | 65365 | O 0% / M 51% / E 49% | `bb/ww` |
| `2x3` | 50458 | 50458 | O 0% / M 61% / E 39% | `.bw/bow` |
| `2x2` | 47418 | 47418 | O 0% / M 45% / E 55% | `bo/wb` |
| `2x3` | 43515 | 43515 | O 0% / M 35% / E 65% | `..b/wbo` |
| `2x4` | 20034 | 20034 | O 0% / M 72% / E 27% | `.bow/bow.` |
| `2x2` | 19683 | 19683 | O 0% / M 44% / E 56% | `bo/ob` |
| `2x4` | 15727 | 15727 | O 0% / M 42% / E 58% | `..bw/bbw.` |
| `2x2` | 14441 | 14441 | O 0% / M 45% / E 55% | `bw/wb` |
| `2x2` | 13801 | 13801 | O 0% / M 19% / E 81% | `.o/ob` |
## Candidate Neutral / Defensive Components

This section uses only positions with exactly one legal component, so the win/loss observation belongs to that component instead of a sum of components. It is still win/loss, not a full CGT value.

| Signature | Single-component observations | STM loss % | All occurrences | Sample |
|---|---:|---:|---|---|
| `3x3` | 14 | 100.0% | 6403 | `..b/wbw/bw.` |
| `3x3` | 13 | 100.0% | 2728 | `..b/w.w/bwb` |
| `1x3` | 13 | 100.0% | 261740 | `bbw` |
| `2x3` | 13 | 100.0% | 43515 | `..b/wbo` |
| `2x2` | 12 | 100.0% | 88846 | `.b/wb` |
| `3x3` | 12 | 100.0% | 5780 | `..b/wbo/.wb` |
| `3x3` | 11 | 100.0% | 3696 | `..b/wbw/.wo` |
| `2x3` | 11 | 100.0% | 81124 | `..b/wbw` |
| `3x3` | 11 | 100.0% | 4214 | `..b/wbw/ow.` |
| `2x3` | 11 | 100.0% | 50458 | `.bw/bow` |
| `3x3` | 11 | 100.0% | 8705 | `..b/..b/wbw` |
| `3x3` | 11 | 100.0% | 5369 | `.b./bwb/w.w` |

## Whole-Position Correlation Check

For comparison, these components appear often in losing whole positions, but those positions can contain multiple components.

| Signature | Occurrences | STM loss % | Phase mix | Sample |
|---|---:|---:|---|---|
| `3x3` | 2416 | 41.6% | O 0% / M 31% / E 69% | `..b/wbb/.b.` |
| `2x3` | 2469 | 41.4% | O 0% / M 13% / E 87% | `.b./bbw` |
| `3x3` | 1481 | 39.8% | O 0% / M 37% / E 63% | `.b./bow/bw.` |
| `3x5` | 1001 | 39.8% | O 6% / M 91% / E 4% | `..bw./.boow/boow.` |
| `3x3` | 4724 | 38.7% | O 0% / M 46% / E 54% | `..b/wbb/.ww` |
| `3x3` | 2067 | 38.6% | O 0% / M 38% / E 62% | `..b/obo/b..` |
| `2x4` | 1114 | 37.6% | O 0% / M 16% / E 84% | `...b/wbwb` |
| `3x3` | 1073 | 37.5% | O 0% / M 19% / E 81% | `..b/bwb/..w` |

## Initial Interpretation

- Repeated small tinted components are the likely analogue of the Linear Col boundary classes (`b...o`, `b...b`, `b...w`).
- Families with heavy midgame frequency are the best candidates for explaining solver behavior and move-ordering crossovers.
- The next step is to validate top families by isolating component values, not just correlating them with whole-position outcomes.
