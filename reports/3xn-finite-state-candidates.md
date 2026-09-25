# 3xn Finite-State Proof Candidates

This report solves small odd `3xn` boards in memory, scans the DFS shadow memo, and mines tinted state families that could become the finite induction table for a proof that all odd `3xn` boards are second-player wins.

Notation follows the proof miner: `o` is legal for both players, `b` is P1-only, `w` is P2-only, and `.` is dead/unavailable.

- Exact component values computed for components with at most `12` live cells.
- Tablebase files are not required; all data here comes from fresh in-memory DFS runs.

## Board Summary

| Board | Empty P1 win? | Seconds | States searched | Memo entries | Pairing cert hits |
|---|---:|---:|---:|---:|---:|
| 3x5 | False | 0.01 | 537 | 552 | 1 |
| 3x7 | False | 0.31 | 12,473 | 12,527 | 1 |
| 3x9 | False | 5.04 | 160,636 | 160,841 | 44 |

## Most Frequent Local Components

| Rank | Occurrences | Boards | Widths | Exact values | Sample |
|---:|---:|---|---|---|---|
| 1 | 77340 | 3x9 (74006), 3x7 (3326), 3x5 (8) | 1 (77340) | 1 (77340) | `b` |
| 2 | 56662 | 3x9 (53191), 3x7 (3380), 3x5 (91) | 1 (56662) | -1 (56662) | `w` |
| 3 | 26562 | 3x9 (24227), 3x7 (2294), 3x5 (41) | 2 (19167), 1 (7395) | 0 (26562) | `bw` |
| 4 | 15753 | 3x9 (15177), 3x7 (562), 3x5 (14) | 1 (8983), 2 (6770) | -1 (15753) | `w/w` |
| 5 | 12651 | 3x9 (12201), 3x7 (447), 3x5 (3) | 1 (9599), 2 (3052) | 1 (12651) | `b/b` |
| 6 | 9539 | 3x9 (8996), 3x7 (530), 3x5 (13) | 1 (5393), 3 (4146) | 0 (9539) | `b/o/w` |
| 7 | 4186 | 3x9 (3802), 3x7 (366), 3x5 (18) | 2 (4186) | -1 (4186) | `wb/.w` |
| 8 | 3684 | 3x9 (3389), 3x7 (284), 3x5 (11) | 2 (2507), 1 (1177) | -1/2 (3684) | `ow` |
| 9 | 3184 | 3x9 (2814), 3x7 (357), 3x5 (13) | 3 (2852), 2 (332) | 0 (3184) | `bw./.bw` |
| 10 | 3110 | 3x9 (2921), 3x7 (185), 3x5 (4) | 1 (3110) | 0* (3110) | `o` |
| 11 | 2830 | 3x9 (2597), 3x7 (230), 3x5 (3) | 2 (2830) | 1 (2830) | `.b/bw` |
| 12 | 2752 | 3x9 (2568), 3x7 (179), 3x5 (5) | 2 (2752) | -2 (2752) | `.w/ww` |
| 13 | 2655 | 3x9 (2432), 3x7 (219), 3x5 (4) | 2 (2655) | -1 (2655) | `wo/.w` |
| 14 | 2210 | 3x9 (1974), 3x7 (234), 3x5 (2) | 3 (1274), 2 (936) | 1 (2210) | `bbw/b..` |
| 15 | 1969 | 3x9 (1820), 3x7 (149) | 2 (1969) | 2 (1969) | `bb/b.` |

## Most Frequent 3-Row Frontier Components

| Rank | Occurrences | Boards | Widths | Exact values | Sample |
|---:|---:|---|---|---|---|
| 1 | 5393 | 3x9 (5144), 3x7 (243), 3x5 (6) | 1 (5393) | 0 (5393) | `b/o/w` |
| 2 | 4146 | 3x9 (3852), 3x7 (287), 3x5 (7) | 3 (4146) | 0 (4146) | `bow` |
| 3 | 2852 | 3x9 (2558), 3x7 (281), 3x5 (13) | 3 (2852) | 0 (2852) | `bw./.bw` |
| 4 | 1274 | 3x9 (1143), 3x7 (130), 3x5 (1) | 3 (1274) | 1 (1274) | `bbw/b..` |
| 5 | 1020 | 3x9 (937), 3x7 (81), 3x5 (2) | 3 (1020) | 0 (1020) | `wob/.wb` |
| 6 | 998 | 3x9 (932), 3x7 (64), 3x5 (2) | 3 (998) | 0 (998) | `bww` |
| 7 | 946 | 3x9 (892), 3x7 (53), 3x5 (1) | 3 (946) | -2 (946) | `wow/.w.` |
| 8 | 936 | 3x9 (831), 3x7 (104), 3x5 (1) | 2 (936) | 1 (936) | `bb/b./w.` |
| 9 | 816 | 3x9 (806), 3x7 (10) | 3 (816) | 0 (816) | `bbw` |
| 10 | 813 | 3x9 (767), 3x7 (46) | 4 (813) | -1 (813) | `wowb/.w..` |
| 11 | 716 | 3x9 (667), 3x7 (48), 3x5 (1) | 4 (716) | -1 (716) | `bww./..ww` |
| 12 | 702 | 3x9 (653), 3x7 (47), 3x5 (2) | 3 (702) | -1 (702) | `wob/.ww` |
| 13 | 686 | 3x9 (621), 3x7 (63), 3x5 (2) | 2 (686) | -1 (686) | `.b/.w/ww` |
| 14 | 630 | 3x9 (516), 3x7 (112), 3x5 (2) | 2 (630) | 0 (630) | `bb/wo/.w` |
| 15 | 535 | 3x9 (463), 3x7 (70), 3x5 (2) | 2 (535) | 0 (535) | `bw/w./b.` |

## Exact-Zero Frontier Candidates

| Rank | Occurrences | Boards | Widths | Exact values | Sample |
|---:|---:|---|---|---|---|
| 1 | 5393 | 3x9 (5144), 3x7 (243), 3x5 (6) | 1 (5393) | 0 (5393) | `b/o/w` |
| 2 | 4146 | 3x9 (3852), 3x7 (287), 3x5 (7) | 3 (4146) | 0 (4146) | `bow` |
| 3 | 2852 | 3x9 (2558), 3x7 (281), 3x5 (13) | 3 (2852) | 0 (2852) | `bw./.bw` |
| 4 | 1020 | 3x9 (937), 3x7 (81), 3x5 (2) | 3 (1020) | 0 (1020) | `wob/.wb` |
| 5 | 998 | 3x9 (932), 3x7 (64), 3x5 (2) | 3 (998) | 0 (998) | `bww` |
| 6 | 816 | 3x9 (806), 3x7 (10) | 3 (816) | 0 (816) | `bbw` |
| 7 | 630 | 3x9 (516), 3x7 (112), 3x5 (2) | 2 (630) | 0 (630) | `bb/wo/.w` |
| 8 | 535 | 3x9 (463), 3x7 (70), 3x5 (2) | 2 (535) | 0 (535) | `bw/w./b.` |
| 9 | 459 | 3x9 (404), 3x7 (51), 3x5 (4) | 4 (459) | 0 (459) | `wob./.wob` |
| 10 | 394 | 3x9 (358), 3x7 (34), 3x5 (2) | 3 (394) | 0 (394) | `bwo/..w` |
| 11 | 390 | 3x9 (282), 3x7 (108) | 3 (390) | 0 (390) | `b../wbw` |
| 12 | 379 | 3x9 (353), 3x7 (25), 3x5 (1) | 3 (379) | 0 (379) | `bwb/..w` |
| 13 | 373 | 3x9 (303), 3x7 (69), 3x5 (1) | 3 (373) | 0 (373) | `wow/o../b..` |
| 14 | 332 | 3x9 (256), 3x7 (76) | 2 (332) | 0 (332) | `.b/bw/w.` |
| 15 | 330 | 3x9 (312), 3x7 (17), 3x5 (1) | 1 (330) | 0 (330) | `b/w/w` |

## Nonzero Frontier Obstacles

| Rank | Occurrences | Boards | Widths | Exact values | Sample |
|---:|---:|---|---|---|---|
| 1 | 1274 | 3x9 (1143), 3x7 (130), 3x5 (1) | 3 (1274) | 1 (1274) | `bbw/b..` |
| 2 | 946 | 3x9 (892), 3x7 (53), 3x5 (1) | 3 (946) | -2 (946) | `wow/.w.` |
| 3 | 936 | 3x9 (831), 3x7 (104), 3x5 (1) | 2 (936) | 1 (936) | `bb/b./w.` |
| 4 | 813 | 3x9 (767), 3x7 (46) | 4 (813) | -1 (813) | `wowb/.w..` |
| 5 | 716 | 3x9 (667), 3x7 (48), 3x5 (1) | 4 (716) | -1 (716) | `bww./..ww` |
| 6 | 702 | 3x9 (653), 3x7 (47), 3x5 (2) | 3 (702) | -1 (702) | `wob/.ww` |
| 7 | 686 | 3x9 (621), 3x7 (63), 3x5 (2) | 2 (686) | -1 (686) | `.b/.w/ww` |
| 8 | 514 | 3x9 (494), 3x7 (19), 3x5 (1) | 3 (514) | -2 (514) | `.ww/ww.` |
| 9 | 486 | 3x9 (436), 3x7 (45), 3x5 (5) | 3 (486) | -1 (486) | `bww/..w` |
| 10 | 436 | 3x9 (411), 3x7 (25) | 3 (436) | -1 (436) | `wow/bw.` |
| 11 | 411 | 3x9 (375), 3x7 (33), 3x5 (3) | 2 (411) | -1/2 (411) | `ob/wo/.w` |
| 12 | 410 | 3x9 (343), 3x7 (67) | 3 (410) | -1 (410) | `wbw` |
| 13 | 402 | 3x9 (373), 3x7 (28), 3x5 (1) | 3 (402) | 1 (402) | `bwb` |
| 14 | 397 | 3x9 (389), 3x7 (7), 3x5 (1) | 2 (397) | -2 (397) | `wb/.w/ww` |
| 15 | 389 | 3x9 (362), 3x7 (26), 3x5 (1) | 2 (389) | -2 (389) | `.w/ww/w.` |

## Losing Single-Component Whole-State Candidates

| Rank | Occurrences | Boards | Widths | Exact values | Sample |
|---:|---:|---|---|---|---|
| 1 | 2 | 3x9 (2) | 9 (2) | - | `turn=P1; cols=...x6 ..b ..w ...` |
| 2 | 2 | 3x9 (2) | 9 (2) | - | `turn=P2; cols=...x6 ..w ..b ...` |
| 3 | 2 | 3x9 (2) | 9 (2) | - | `turn=P2; cols=...x5 ..bx2 ..w ...` |
| 4 | 2 | 3x9 (2) | 9 (2) | - | `turn=P1; cols=...x5 ..b ..o ..w ...` |
| 5 | 2 | 3x9 (2) | 9 (2) | - | `turn=P1; cols=...x5 ..b ..w ...x2` |
| 6 | 2 | 3x9 (2) | 9 (2) | - | `turn=P2; cols=...x5 ..w ..b ...x2` |
| 7 | 2 | 3x9 (2) | 9 (2) | - | `turn=P2; cols=...x5 ..w ..o ..b ...` |
| 8 | 2 | 3x9 (2) | 9 (2) | - | `turn=P2; cols=...x4 ..bx2 ..w ...x2` |
| 9 | 2 | 3x9 (2) | 9 (2) | - | `turn=P2; cols=...x4 ..b ..o ..w ...x2` |
| 10 | 2 | 3x9 (2) | 9 (2) | - | `turn=P2; cols=...x4 ..b ..w ...x3` |
| 11 | 2 | 3x9 (2) | 9 (2) | - | `turn=P2; cols=...x4 ..b ..w ..o ..w ...` |
| 12 | 2 | 3x9 (2) | 9 (2) | - | `turn=P2; cols=...x4 ..b ..wx2 ...x2` |
| 13 | 2 | 3x9 (2) | 9 (2) | - | `turn=P1; cols=...x4 ..o ..b ..o ...x2` |
| 14 | 2 | 3x9 (2) | 9 (2) | - | `turn=P2; cols=...x4 ..ox2 ...x3` |
| 15 | 2 | 3x9 (2) | 9 (2) | - | `turn=P1; cols=...x4 ..o ..w ..o ...x2` |

## How To Use This

A plausible `3xn` proof should promote a small subset of the exact-zero frontier candidates into lemmas, then show every P1 move from each losing whole-state family has a P2 reply landing back in the family set. Nonzero frontier obstacles are the states that need cancellation partners or their own recurrence lemmas.
