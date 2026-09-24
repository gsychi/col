# X-families stream: progress log

Stream question: can DX (even widths) and the paired RX/VX/XX targets be
closed for every Blue opening? Labels: PROVED, CERTIFIED-FINITE, EVIDENCE,
CONJECTURE, CONDITIONAL, REFUTED.

## Tools (discovery only; no proof force)

- `tools/xval.cpp`: exact values by component decomposition and the
  simplicity rule. It assumes the number-or-number-plus-star theorem. It
  reproduces all 27 previously certified values that were checked.
- `tools/xout.cpp`: outcome search with dyadic and star offsets, folding
  small components. It currently runs slower than `xval` at width 6.
- `tools/xboard.py`: board builder plus a pipe to `xval`.
- `tools/caps_scan.py`: scans the X-cap families defined below.
- Rust raw solver copy in `/tmp/x_families/raw_research`: about 64 s for one
  Blue-first query on `DX_6+1/4`. Exact search past width 7 is costly, so
  the plan uses small certified pieces plus symbolic reductions.

New discovery values (EVIDENCE): `XX_5=5/8`, `RX_5=1/2+*`, `VX_5=1/2`.

## Structural reduction (geometry to be written up and checked)

Cut an interior Blue opening `(r,c)` of `DX_n` at the opening column. The
left piece `(D,S)_c` uses a letter S whose White-only cell is at row r. The
right piece is an **X-cap** `K^{(r)}_m(S)`, with `m=n-c`: Blue sits at
`(r,0)`, X is at the far end, and column 0 loses White wherever S permits
White. With this cut, every left piece is an original D-family (an external
target). The whole interior DX problem therefore reduces to five
one-parameter cap families:

| Row, parity of c | Left piece | Cap family | Needed cap bound | Values found, m ascending (EVIDENCE) |
| --- | --- | --- | --- | --- |
| 2, c even | DX_c<0 | K2_m(X), m even | number part <= 0 | 0, *, 0 |
| 2, c odd | DD_c<=0 | K2_m(D), m odd | already <= DX_(m-1) | -1, -1/2 |
| 0, c odd | DU_c<0 | K0_m(U), m odd | <= 0 | -1/2, -1, -1 |
| 0, c even | DR_c<0 | K0_m(R), m even | number part <= 0 | 0, *, 0 |
| 1, c even | DV_c<=1/2 | K1_m(V), m even | < -1/2 | -2, -3/2, -3/2 |
| 1, c odd | DJ_c<-1/4 | K1_m(J), m odd | <= 1/4 | 1/2, 1/2+*, 1/2 **(fails)** |

Row 1 with odd c needs either `DJ_odd<-1/2` or a different cut. Note that
`DJ_1=-1/2+*` is a boundary case.

Next steps:
1. Find an induction on m for the cap families themselves.
2. Repair row 1 with odd c.
3. Handle the endpoint openings at c=0 and c=n-1.
4. Build certificates and a search-free checker for columns above 30 cells.
