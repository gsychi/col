# Approaches for arbitrary odd heights, with falsification tests

Stream: literature and theory (round five). 2026-09-23.

Labels: **PROVED**, **CITED**, **EVIDENCE** (finite computation, never
extrapolated), **CONJECTURE**, **REFUTED**. Values use the conventions of
[COL_VALUES.md](COL_VALUES.md): every position is `x` or `x+*`; Blue is
Left; "opening" means Blue's first move on an empty board, and the opening
value is the value of the resulting position with **White to move**. A
cell `(r,c)` is *majority* if `r+c` is even (corners are majority; there
are `(mn+1)/2` of them) and *minority* otherwise.

## 0. Ranking

Plausibility is my estimate that the idea is true or workable as stated;
leverage is how much of the odd×odd conjecture it would settle.

| Rank | Idea | Plausibility | Leverage | Status after testing |
| --- | --- | --- | --- | --- |
| 1 | §3 Domino lemma: settles every minority opening on every odd×odd board | high | medium (about half the openings) | CONJECTURE; the implication is PROVED; EVIDENCE on 5 boards |
| 2 | §4 Private-reserve reduction for boundary families (DD) | high | medium (turns strict White-first targets into non-strict ones) | EVIDENCE: tight for `n ≤ 6` |
| 3 | §1 Reformulation: "no opening equals 0" and the stronger "every majority opening is `≤ −1/2`" | high | high if provable | PROVED equivalence; EVIDENCE for the strengthening |
| 4 | §2 Mirror strategy with a centre controller | low–medium | very high | pure mirror REFUTED (proof); windows of 5 columns are still open |
| 5 | §6 Height lifts by static band peeling | — | — | REFUTED as a bounding method |
| 6 | §7 Explosive separators / fixed cross | — | — | static middle column REFUTED on small sizes; cross and dynamic separators untested |
| 7 | §8 Linear potential functions | — | — | REFUTED (proof) |
| 8 | §9 Literature techniques (tinted-chain induction, complexity) | — | guardrails | — |

## 1. The number reformulation (PROVED; COL_VALUES.md Cor. 5.2)

Every empty board `E` is `0` or `*`, every opening is `< 0`, `= 0` or `= *`,
and `E = 0` iff **no opening equals `0` exactly**. Openings never have a
positive number part. So a proof only needs, for each opening `K`, some
bound `K ≤ V` where `V` is a sum of Col positions, numbers and stars with
number part `< 0`, or number part `0` plus a star (Cor. 4.5).

**Strengthening (CONJECTURE, EVIDENCE §5).** Every opening on an odd×odd
board with both sides `≥ 3` is `≤ −1/2`. On every board computed, openings
take only the values `−1/2`, `−3/4`, `−1`, `−2`. A proof with slack `1/2`
may be easier to make inductive than one with slack "strictly below 0",
because slack adds under sums.

*Falsification test:* compute all openings on the next boards (5×7, 3×11).
5×7 did not finish within the 30-minute cap on one thread (INCONCLUSIVE).
The ground-truth and bridge streams have 5×7 data; they should check it.

## 2. Mirror strategy with a centre defect

The half-turn `ρ` pairs every cell except the centre `c`. White's natural
plan: answer `v` with `ρ(v)`, and repair when Blue takes `c`. Uiterwijk
§3.2 notes that the centre breaks this; Part 2 shows that in impartial Col
the first player wins odd×odd by taking the centre and mirroring in the
same colour (LITERATURE.md §2.1).

**Proposition 2.1 (PROVED).** Let `m, n` be odd, `m, n ≥ 3`, `n ≥ 5`
(transpose if only `m ≥ 5`). Write cells relative to `c`. If Blue plays
`(−1,−1)`, `(1,−1)`, `(0,2)` and White answers each by its half-turn image
`(1,1)`, `(−1,1)`, `(0,−2)`, the resulting position has value `*` with Blue
to move, so Blue wins.

*Proof.* All six moves are legal: the three Blue cells are pairwise
nonadjacent, the three White cells likewise, and all lie on the board. The
four neighbours of `c` are dead: `(−1,0)` touches Blue `(−1,−1)` and White
`(−1,1)`; `(1,0)` touches Blue `(1,−1)` and White `(1,1)`; `(0,−1)` touches
Blue `(−1,−1)` and White `(0,−2)`; `(0,1)` touches White `(1,1)` and Blue
`(0,2)`. No neighbour of `c` holds a stone, so `c` is live for both players
and isolated in the live graph: it contributes `*` (Lemma 1.1(2),(3)). The
stone pattern is `ρ`-antisymmetric, so `ρ` maps Blue permissions onto White
permissions, and `ρ` is fixed-point-free on the other live cells, so they
contribute `0` (Cor. 5.1). The total is `*` and Blue is to move. ∎

So any White strategy that mirrors Blue's first three moves loses on every
odd×odd board with a side `≥ 5`; mirroring "until the centre is taken" is
refuted for all such sizes, not only the ones computed. On 3×3 the line
does not fit, and an exhaustive check found no position where Blue's centre
move beats mirroring. With the mirror-then-repair strategy, the number of
mirrored positions where Blue's centre move wins is 2 on 3×5 and 36 on 3×7
(EVIDENCE, `col_probe.cpp`). The line itself was evaluated with
`col_fastval isolate` on 3×5, 5×3, 3×7, 5×5, 3×9 and 5×7: value `*` each
time, as the proposition predicts ([runs/isolate.txt](runs/isolate.txt)).

*What survives.* White must deviate from mirroring near the centre within
Blue's first few moves. Round 3 ([round3_central_controller.md](../../round3_central_controller.md))
already refuted mirroring outside a central window of 3 columns, for
heights 3 and 5 and all odd widths `≥ 5`. Proposition 2.1 is compatible
with a controller on a window of 5 columns, which is Unknown.
*Falsification test (not run here; it needs a controller search):* for
5×7, search for a White strategy that plays half-turn images outside the
central 5 columns and anything inside. One Blue line winning against every
such strategy refutes the 5-column window for that board.

## 3. Parity of openings and a domino lemma

**Observation (EVIDENCE, §5).** On 3×3, 3×5, 3×7, 3×9 and 5×5, every
minority opening has value exactly `−2`, and every majority opening has
value in `{−1/2, −3/4, −1}`. The repository already proves that minority
openings are `≤ −1` on every 3×n strip
([RESEARCH.md](../../RESEARCH.md) §4); majority openings are the hard case
there too.

Let `D(v, u)` be the position with a Blue stone at `v` and a White stone at
an adjacent cell `u` (all else empty). By colour swap,
`D(v, u) = −D(u, v)`.

**Conjecture 3.1 (domino lemma).** On every odd×odd board with both sides
`≥ 3`, `D(v, u) = 1` when `v` is majority (so `D(v, u) = −1` when `v` is
minority).

*EVIDENCE.* True for every adjacent pair on 3×3, 3×5, 3×7, 3×9 and 5×5
(all pairs up to reflection; [reserve_openings.py](reserve_openings.py),
output in [runs/reserve_openings.txt](runs/reserve_openings.txt)).

**Proposition 3.2 (PROVED).** Conjecture 3.1 for a board implies that every
minority opening on it is `≤ −2`, hence `< 0`.

*Proof.* After Blue opens at a minority cell `v`, every neighbour `u` is
White-only. Lemma 4(4) of COL_VALUES.md gives
`E^{L,v} ≤ (E^{L,v})^{R,u} − 1 = D(v, u) − 1 = −2`. ∎

**The same reduction fails for majority openings (REFUTED as a route).**
For a majority opening `v` and any neighbour `u`, Lemma 4(4) gives
`E^{L,v} ≤ D(v,u) − 1 = 0` on every board computed: exactly `0`, never
strict, while the true values are `−1/2` to `−1`. One White private move is
not enough; a proof for majority openings needs a second argument.

*Next tests.* (a) `D(v,u)` on 5×7 and 3×11 (each is one position; cheaper
than solving the board). (b) Whether `D(v,u) = 1` has a strategy proof:
Blue is exactly one move ahead, i.e. `D(v,u) − 1 = 0` is a second-player
win when a lone White-only cell is added.

## 4. Private-reserve reduction for boundary families

Lemma 4(4): at a White-only cell `u`, `G ≤ G^{R,u} − 1`. So
`G^{R,u} ≤ q + 1` implies `G ≤ q`, and `G^{R,u} < q + 1` implies `G < q`.
A strict target on `G` becomes a target with slack on a position that has
one more stone.

**Test on DD** (5×n strip, both end columns `obwbo`, as in round 4; cell
`(2,0)` is White-only). `K_n` = DD_n after White plays `(2,0)`.

| n | DD_n | K_n | bound K_n − 1 |
| --- | --- | --- | --- |
| 1 | 0 | 1 | 0 |
| 2 | 1 | 2 | 1 |
| 3 | −1 | 0 | −1 |
| 4 | 0 | 1 | 0 |
| 5 | −1 | 0 | −1 |
| 6 | 0 | 1 | 0 |

EVIDENCE (`col_fastval ddreserve`, [runs/ddreserve.txt](runs/ddreserve.txt);
`n = 7` hit the 25-minute cap). The bound
is **tight** for every `n ≤ 6`. The DD values agree with the ground-truth
and aux-families streams (DD_2 = 1, DD_3 = DD_5 = −1, DD_6 = 0).

*Consequence for the white_first stream.* To prove `DD_odd < 0` it suffices
to prove the **non-strict** `K_odd ≤ 0` (then `DD_odd ≤ −1`). `K_3 = K_5 = 0`
exactly, so there is no slack in `K ≤ 0`, but non-strict upper bounds are
what the comparison principle produces directly (no White-first case
analysis). *Falsification test:* `K_7 ≤ 0`, one position of 35 cells;
ground truth has DD_7 = −1, and `K_7 > 0` would not contradict that, it
would only kill this route.

## 5. Empty-board data (EVIDENCE)

All with `col_fastval` (theorem-based evaluator, cross-checked against the
general canonical-form code; COL_VALUES.md §7). Empty boards 3×3, 3×5,
3×7, 3×9, 5×5 all have value `0`, agreeing with Demeur (CITED-SECONDHAND).
Raw output: [runs/openings.txt](runs/openings.txt).
Openings, one cell per symmetry class, `(row, column)` from a corner:

| Board | Majority openings | Minority openings |
| --- | --- | --- |
| 3×3 | (0,0) −1/2; (1,1) −1 | (0,1), (1,0): −2 |
| 3×5 | (0,0), (0,2), (1,1): −1/2 | (0,1), (1,0), (1,2): −2 |
| 3×7 | (0,0), (0,2), (1,3): −1/2; (1,1) −1 | (0,1), (0,3), (1,0), (1,2): −2 |
| 3×9 | (0,0), (0,2), (0,4), (1,1), (1,3): −1/2 | (0,1), (0,3), (1,0), (1,2), (1,4): −2 |
| 5×5 | (0,0), (0,2), (2,0), (2,2): −1/2; (1,1) −3/4 | (0,1), (1,0), (1,2), (2,1): −2 |

5×7: INCONCLUSIVE (the empty-board evaluation did not finish in 30 min
within about 1.2 GB).

## 6. Height lifts by band peeling (REFUTED as a bounding method)

Idea: cut `m × n` into an `(m−2) × n` block and a `2 × n` band, and bound the
board by the sum. The comparison principle only allows deleting the cut
edges after removing White's permission on one side of the cut, which
makes that side Blue-favourable. For an opening in the upper block:
`K ≤ K_{upper} + P_n`, where `P_n` is the `2 × n` band with its top row
Blue-only.

*Test (EVIDENCE, [ideas_tests.py](ideas_tests.py),
[runs/ideas_tests.txt](runs/ideas_tests.txt)):* `P_1 = 1/2`, and `P_n = (n−1)/2` for
`n = 3, 5, 7, 9, 11`. For `m = 5` the block is `3 × n`, whose openings are
`≥ −2` (§5), so the bound is useless for every `n ≥ 5`, and for every
majority opening already at `n = 3`. Removing White's permission on the
block's bottom row instead changes the block, not the band; that variant
was not tested. Only *dynamic* height lifts, where the cut is chosen during
play, remain; none was tested.

## 7. Explosive separators and a fixed cross

Proposition 6.1 of COL_VALUES.md (PROVED): if one side `C` of a separator
`S` has the same value with `S` tinted Blue-only as with `S` tinted
White-only, then `S` can be deleted: `G = G − S`. With `S` the middle
column of an `h × (2k+1)` board, `C` is `h × (k+1)` and the two tintings are
negatives of each other, so `S` is explosive iff `C^b ∈ {0, *}`. Then the
board would be twice the `h × k` board, hence `0`.

*Test (EVIDENCE):* `C^b` for `h × (k+1)` with its last column Blue-only:
3×2: 1, 3×3: 3/2, 3×4: 3/2, 3×5: 2, 5×2: 2, 5×3: 5/2, 5×4: 2, 5×5: 5/2.
Never `0` or `*`: **the static middle column is not explosive** on these
sizes. The fixed cross (middle row plus middle column, four quadrant sides)
was not tested; the analogous test is whether a quadrant-plus-cross side
has equal values under the two tintings of the cross. Separators created
by play (the isolated centre in §2 is one) remain possible; no systematic
test was run.

## 8. Potential functions

**Linear tint potentials are REFUTED (PROVED).** Suppose
`x(G) ≤ β(|A∖B| − |B∖A|)` for all grid positions. A lone Blue-only cell
(`x = 1`) forces `β ≥ 1`, and a lone White-only cell (`x = −1`) forces
`β ≤ 1`, so `β = 1`. The 3×3 corner opening leaves two White-only cells
and no Blue-only cell, so the potential is `−2`, but `x = −1/2 > −2`. The
lower-bound version fails by colour symmetry. Nonlinear potentials (for
example independence numbers of the Blue-only and White-only parts) were
not explored; any such potential must reproduce the parity split of §5,
which is a strong filter.

## 9. Literature techniques and guardrails

- **Tinted-chain induction** (Uiterwijk Thm 2, Linear Col) is the only
  published all-length proof. The repository's 3×n theorem is its
  two-dimensional analogue; the round-4 boundary-family program (DD, DX, …)
  is the natural continuation, and §4 applies to it directly.
- **Deletion rules** (ONAG pp. 94–95; Winning Ways rules 1–8) need cut
  vertices, which full grids lack (§7).
- **Complexity** (Fenner et al. 2015; Burke–Hearn; Burke–Tennenhouse on
  triangular grids): Col is PSPACE-complete on planar and triangular-grid
  inputs with adversarial pre-colouring. A proof must use the structure of
  empty square boards (symmetry, parity, periodic boundaries); a uniform
  rule deciding arbitrary grid shadow states is not to be expected.

## 10. Exactly what was falsified here

1. Mirroring Blue's first three moves: loses on every odd×odd board with a
   side `≥ 5` (Proposition 2.1, PROVED).
2. The single-reserve bound for majority openings: gives exactly `≤ 0` on
   3×3, 3×5, 3×7, 3×9, 5×5 (EVIDENCE), so it cannot prove strictness there.
3. Static 2-row band peeling of `5 × n`: band price `(n−1)/2` for
   `n = 3…11` (EVIDENCE) exceeds every `3 × n` opening deficit once `n ≥ 5`.
4. The static middle column as an explosive separator: not explosive for
   3×2–3×5 and 5×2–5×5 (EVIDENCE).
5. Linear tint potentials (PROVED).
6. From COL_VALUES.md: "a winning Blue move exists at a shared cell"
   (REFUTED, 2×3) and "a White-only cell made shared adds at most `1+*`"
   (REFUTED, 1×5 and 2×3).

Nothing here proves the odd×odd conjecture for any new size.
