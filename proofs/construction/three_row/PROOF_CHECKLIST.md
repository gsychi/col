# Proof checklist: why finite checks plus the written induction cover every width

This file explains exactly which parts of the all-width theorem
([`../empty_3xn_theorem.md`](../empty_3xn_theorem.md)) are written mathematics,
which are finite certificates, and why the width sweep in `verify.py` is a
regression test rather than the proof.

Conventions are those of the theorem: rows 0–2, columns 0..n−1, Blue = Left
moves first, masks row-major with bit `r·w + c`. `N[v]` is the closed
neighbourhood. After Blue at `v` and (if any) White at `w`, the actual legal sets
are `A_P = full ∖ N[v] ∖ {w}` and `B_P = full ∖ {v} ∖ N[w]`. Write
`Aff = N[v] ∪ N[w]` for the cells where the position differs from the empty
board.

## 0. Status labels

| Claim | Label | Basis |
| --- | --- | --- |
| `H_n = 0` for every `n ≥ 1` | **PROVED** | written arguments §2–§6 plus the replayed certificates §5 |
| Each gadget bound in §5 | **CERTIFIED-FINITE** | response DAG replayed by `verify.py` |
| Widths 3, 7, 11 | **CERTIFIED-FINITE** | stored assemblies replayed by `verify.py` |
| Assemblies at widths 1..203 (and 1..403) | regression test | `verify.py` sweep; not used as a proof step |

## 1. Division of labour

| Ingredient | Kind | Where |
| --- | --- | --- |
| Comparison principle, including the game-order inequality used in case 1 | written | §2 |
| Half-turn mirror for even `n` | written; the machine checks only that the half-turn is a fixed-point-free automorphism | §3 |
| Colour symmetry `H_n = −H_n` | written | §3 |
| Locality lemma (reduces every width to finitely many local facts) | written | §4.1 |
| Width arithmetic and normalization inequalities, per case | written algebra; regression-checked | §4.2–4.8 |
| The finitely many local windows, seam types, and end types | finite, machine-checked | §4, `verify.py` |
| Gadget bounds (ordinary and dyadic) | certificates | §5 |
| Base widths 3, 7, 11 | stored assemblies over certificates | §5.3 |
| Coverage of all openings; strictly decreasing recursion | written, regression-checked | §6 |

## 2. The comparison principle

**Statement.** Let `P` be a position on the 3 × n board with legal sets
`(A_P, B_P)`. Partition the columns into consecutive blocks and dead columns.
Give block `i` virtual legal sets `(A_i, B_i)` on its own cells, with game
`T_i` played on the block's internal grid edges only; dead columns get
`A = B = ∅`. Let `A* = ∪A_i`, `B* = ∪B_i`. If

1. `A_P ⊆ A*` (in particular no actual Blue move lies in a dead column),
2. `B* ⊆ B_P`, and
3. every grid edge whose endpoints lie in different blocks (or a block and a
   dead column) has an endpoint outside `B*`,

then `P ≤ Σ T_i` in the game order, whoever is to move in `P`.

**Proof.** We show Left (Blue) moving first loses `P + Σ(−T_i)`. In `−T_i` a
Left move is a White placement in `T_i`, a Right move a Blue placement. Right
(White) keeps the invariant: `A_P ⊆ A*`, `B* ⊆ B_P`, where `(A_P, B_P)` and
`(A_i, B_i)` are the current legal sets.

* Blue plays `v ∈ A_P` in `P`. Then `v ∈ A*`, so `v` lies in some block `i` and
  White answers with the Blue placement at `v` in `T_i` (a Right move in
  `−T_i`). Afterwards `A_P ∖ N[v] ⊆ A* ∖ N_i[v]` because `N_i[v] ⊆ N[v]`, and
  `B* ∖ {v} ⊆ B_P ∖ {v}`.
* Blue makes a White placement at `w ∈ B_i` in some `−T_i`. Then `w ∈ B_P`, and
  White plays `w` in `P`. Afterwards `A_P ∖ {w} ⊆ A* ∖ {w}`. For
  `B* ∖ N_i[w] ⊆ B_P ∖ N[w]`: a cell `x ∈ N[w]` in block `i` lies in `N_i[w]`;
  a cell `x ∈ N[w]` in another block or dead column is joined to `w` by a
  crossing edge, and `w` was in the initial `B*`, so by hypothesis 3 `x` was
  never in `B*`.

White always has an answer; the game is finite, so Blue, who moved first, runs
out of moves. Hence `P − Σ T_i ≤ 0`. ∎

**Consequences used.** Each certificate proves a Blue-first loss of
`T_i + q_i` for an explicit dyadic `q_i` (`q_i = 0` for ordinary DAGs), i.e.
`T_i ≤ −q_i`. So `P ≤ Σ T_i ≤ −Σ q_i`.

* If White has already replied (Blue to move) and `−Σ q_i ≤ 0`, then `P ≤ 0`:
  Blue to move loses.
* In case 1 (no reply; White to move) `−Σ q_i = −1 + 1/4 = −3/4`, so
  `P ≤ −3/4 < 0`, and White wins moving first. A bound `≤ 0` would not suffice
  here; strictness is essential.

The theorem file states this principle but justifies only the Blue-to-move
outcome form. Case 1 needs the game-order form proved above (README,
discrepancy D5).

## 3. Width classes other than 4k+3 ≥ 15

**Even `n`.** The half-turn `ρ(r, c) = (2 − r, n − 1 − c)` is a graph
automorphism and an involution; a fixed cell would need `c = (n − 1)/2`,
impossible for even `n`. White answers every Blue move `v` by `ρ(v)`. Invariant
after each White move: Blue has a stone at `x` exactly when White has one at
`ρ(x)`. If Blue's `v` is legal, then `ρ(v)` is empty (else `v` would be
occupied, or `ρ(v) = v`) and no neighbour `ρ(u)` of `ρ(v)` carries a White
stone (that would put a Blue stone at the neighbour `u` of `v`). So White always
has a reply, and Blue moving first loses: `H_n ≤ 0`. Colour symmetry gives
`H_n = 0`. *Machine check:* `ρ` fixed-point-free,
involutive, adjacency-preserving for every even `n ≤ 203`; the argument itself
is written.

**`n = 4k + 1`.** The layout `E4^k F1` on the empty board (Blue to move):
`Aff = ∅`; `E4` and `F1` allow Blue everywhere, so hypothesis 1 holds; hypothesis
2 is trivial; the only seam types are `E4|E4` and `E4|F1`, both
`010 & 101 = 0`. Bound sum `0`. So `H_{4k+1} ≤ 0`, and colour symmetry (the empty
board is its own conjugate, `H = −H`) gives `H_{4k+1} = 0`. `k = 0` is `F1` alone.

**`n ∈ {3, 7, 11}`.** Stored assemblies, §5.3.

## 4. The induction step, n = 4k + 3 ≥ 15, as finitely many local facts

After normalization `r ∈ {0, 1}`, `0 ≤ c ≤ 2k + 1` (§6), with `k ≥ 3`.

### 4.1 Locality lemma

For every layout used below:

* (L1) the block widths add up to `n` and blocks are consecutive — width
  arithmetic, written for each case;
* (L2) hypotheses 1–2 at every cell of `Aff`, every cell of a block whose
  Blue mask is not full, and every dead-column cell — the **window**;
* (L3) every block outside the window is a full-Blue filler (`E4`, `E4bar`,
  `C3`, `J5`, `F1`) disjoint from `Aff`;
* (L4) hypothesis 3 at each seam, which depends only on the pair of block
  types, through the right port of the left block and the left port of the
  right block — the **seam table**;
* (L5) White's reply is legal.

together imply the comparison hypotheses. Indeed, for a cell `x ∉ Aff`,
`x ∈ A_P ∩ B_P`, so hypotheses 1–2 at `x` say only that `x`'s block allows Blue
at `x`, which is (L3) or part of (L2). The cells of `Aff` and the non-full
blocks sit at **fixed offsets from the opening column `c`** in every case below.
Their local coordinates, and their membership in `A_P` and `B_P`, depend only on
the case and on a small *variant* (whether an `E4` exists to the left, whether
`s = 7`, the local cell in case 1). So each window is one of finitely many
translated patterns. `verify.py` records every window it meets, relative to
`c`, with all actual and virtual bits, and requires the set of windows to be
exactly the analysed set below.

### 4.2 Case 1: `r + c` odd

* Layout `E4^k C3`, with the `E4` block `j = ⌊c/4⌋` replaced by the opened block
  `E4_open_(r,ℓ)`, `ℓ = c mod 4`. Width `4k + 3`.
* Bounds: `c ≤ 2k + 1 < 4k` (`k ≥ 1`), so the opening is in an `E4` block. Also
  `j ≤ ⌊(2k + 1)/4⌋ ≤ k − 2` for `k ≥ 3`, so the opened block's right neighbour
  is an `E4`, never `C3`.
* Parity: `r + ℓ ≡ r + c` is odd, and `r ∈ {0, 1}`, so `(r, ℓ)` is one of
  `(0,1), (0,3), (1,0), (1,2)`. Only these **four** opened-E4 bounds are needed.
  (The row-2 cells `(2,1), (2,3)` arise only without vertical normalization;
  their bounds are supplied and checked anyway, §5.)
* Window: the opened block (its Blue mask is not full), plus `(r, c+1)` in
  `E4_{j+1}` when `ℓ = 3`, and `(1, c−1)` in `E4_{j−1}` (`j ≥ 1`) or off the board
  (`j = 0`) when `ℓ = 0`. Five variants. The neighbour cells impose nothing:
  they are Blue-illegal and White-legal in `P`.
* Seams: `E4|E4`, `E4|E4_open`, `E4_open|E4`, `E4|C3`; all are `010 & 101`
  (an opened block's White mask is a subset of `E4`'s).
* No reply, White to move; bound sum `−1 + 0 + 1/4 = −3/4 < 0`.

### 4.3 Case 2: `(0,0)`, White `(2,2)`

* Layout `K_corner E4bar^k`, width `3 + 4k`.
* `Aff = {(0,0),(0,1),(1,0),(1,2),(2,1),(2,2),(2,3)}`. Window: `K_corner`
  (all of it) and the cell `(2,3)` = `E4bar` local `(2,0)`. That cell is
  Blue-legal and White-illegal in `P`; `E4bar` has `b` there. One variant.
* Seams: `K_corner|E4bar` (`100 & 010`), `E4bar|E4bar` (`101 & 010`).
* Blue to move; sum `0`.

### 4.4 Case 3: `r = 0`, `c = 4a + 2`, White `(2, c−2)`

* `b = k − a − 1`. From `4a + 2 ≤ 2k + 1`: `b ≥ (2k − 3)/4 > 0`, so `b ≥ 1` for
  `k ≥ 2`.
* Layout `E4^a K_outer2 E4bar^b`; width `4a + 7 + 4b = 4k + 3`. `K_outer2` starts at
  `c − 2`; its root is exactly the local position after Blue `(0,2)`, White
  `(2,0)`, with the seam exclusion at local `(1,6)`.
* `Aff ⊆` columns `c−3..c+1`. Window: `K_outer2`; plus `(2, c−3)` = `E4` local
  `(2,3)` (`b`; Blue-legal, White-illegal in `P`) if `a ≥ 1`, or off the board if
  `a = 0`. Two variants.
* Seams: `E4|E4`, `E4|K_outer2` (`010 & 100`), `K_outer2|E4bar` (`101 & 010`),
  `E4bar|E4bar`.
* Blue to move; sum `0`.

### 4.5 Case 4: `r = 0`, `c = 4a + 4`, White `(2, c+2)`

* `c ≥ 4` (`c = 0` is case 2), so `a ≥ 0`. From `4a + 4 ≤ 2k + 1`:
  `b = k − a − 1 ≥ (2k − 1)/4 > 0`, so `b ≥ 1`.
* Layout `E4^a K_outer4 E4bar^b`; width `4k + 3`. `K_outer4` starts at `c − 4`.
  It is the horizontal reflection of `K_outer2`, root `(1046471, 515951)`, ports
  `101/100`.
* `Aff ⊆` columns `c−1..c+3`. Window: `K_outer4`, plus `(2, c+3)` = `E4bar` local
  `(2,0)` (`b`). One variant (`Aff` never reaches the left neighbour).
* Seams: `E4|E4`, `E4|K_outer4` (`010 & 101`; needs `a ≥ 1`, first at `n = 19`),
  `K_outer4|E4bar` (`100 & 010`), `E4bar|E4bar`.
* Blue to move; sum `0`.

### 4.6 Case 5: `r = 1`, `c = 4a + 1`, White `(0, c−1)`

* `b = k − a − 2`. From `4a + 1 ≤ 2k + 1`: `a ≤ ⌊k/2⌋ ≤ k − 2` for `k ≥ 3`, so
  `b ≥ 0`. (At `k = 2`, `c = 5` gives `b = −1`: this is why width 11 is a base.)
* Layout `E4^a T_middle1 E4^b J5`; width `4a + 6 + 4b + 5 = 4k + 3`. `T_middle1`
  starts at `c − 1`; its root is the local position after Blue `(1,1)`, White
  `(0,0)`, with seam exclusions at local `(0,5)` and `(2,5)`.
* `Aff ⊆` columns `c−2..c+1`. Window: `T_middle1`; plus `(0, c−2)` = `E4` local
  `(0,3)` (`b`) if `a ≥ 1`, or off the board if `a = 0`. Two variants.
* Seams: `E4|E4`, `E4|T_middle1` (`010 & 001`), `T_middle1|E4` (`010 & 101`,
  `b ≥ 1`), `T_middle1|J5` (`010 & 101`, `b = 0`, only `k ∈ {3, 4}`), `E4|J5`
  (`010 & 101`).
* Blue to move; sum `0`.

### 4.7 Case 6: `r = 1`, `c = 4a + 3`, White `(0, c+1)`

* `s = n − c − 1 = 4k + 2 − c ≥ 2k + 1 ≥ 7`, `s ≡ 3 (mod 4)`; `3 ≤ c ≤ 2k + 1 < n`.
* Layout: the empty board `H_c` on columns `0..c−1`, dead column `c`, then `Z7`
  on `c+1..c+7`, then `E4bar^((s−7)/4)`. Width `c + 1 + 7 + (s − 7) = n`. `Z7` must
  be the repeatable root `(2097022, 2088828)` (right port `101`) whenever
  `s ≥ 11`. At `s = 7` the physical-edge root `(2097022, 2097020)` (right port
  `111`) may be used; `verify.py` checks both roots there.
* `Aff ⊆` columns `c−1..c+2`. Window: `H_c`'s cell `(1, c−1)` (Blue-illegal,
  White-legal in `P`; `H_c` allows both), the dead column (all three cells are
  Blue-illegal in `P`, so hypothesis 1 holds there), and `Z7`. Two variants
  (`s = 7`, `s ≥ 11`).
* Seams: `H_c|DEAD`, `DEAD|Z7`, `Z7|E4bar` (`101 & 010`), `E4bar|E4bar`.
* Blue to move; the sum is `H_c + 0 + 0`, and `H_c = 0` by the induction
  hypothesis (§6). Only `H_c ≤ 0` is used.

### 4.8 The finite list that constitutes the proof of the step

* 13 windows, 5 + 1 + 2 + 1 + 2 + 2 for cases 1–6. `verify.py` pins them in
  `EXPECTED_WINDOWS`, together with two supplementary row-2 case-1 windows
  that exercise the reflected opened-E4 bounds. All occur already at `n = 15`.
* The seam table: 25 adjacent type pairs, all compatible. All occur by
  `n = 19`. It includes `E4|E4` and `E4|F1` from the `4k+1` family.
* Ends: left-end types `E4`, `E4_open_*`, `K_corner`, `K_outer2`, `K_outer4`,
  `T_middle1`, `H_c`, `F1`; right-end types `C3`, `E4bar`, `J5`, `Z7_end`, `F1`.
  The ports `111` of `C3` and `Z7_end` face only the physical right edge; those
  of `H_c` face the edge and a dead column.
* Width arithmetic and parameter bounds: the linear identities and
  inequalities in §4.2–4.7.

## 5. Finite inputs (certificates)

All files are under `certificates/`, bound by `manifest.json`, and replayed by
`verify.py`. The ordinary checker requires, at every checkpoint (Blue to move),
exactly one legal White reply to every Blue move, with the successor present,
`|A ∪ B|` decreasing by at least 2, and every checkpoint reachable. The dyadic
checker requires every option of the mover (board moves and the canonical Left
option of the number) to be answered, the successor present, and a strict
rank descent.

### 5.1 Roles used by the induction and by `4k+1`

| Role | Width | Blue | White | Ports L/R | Bound | Certificate |
| --- | ---: | ---: | ---: | --- | --- | --- |
| `E4` | 4 | 4095 | 2023 | 101/010 | ≤ 0 | `ordinary/tile_e4d37d528005` |
| `E4bar` | 4 | 4095 | 3710 | 010/101 | ≤ 0 | `ordinary/tile_675ea04f7dff` |
| `F1` | 1 | 7 | 5 | 101/101 | ≤ 0 | `ordinary/tile_e06eb7fc2dd6` |
| `K_corner` | 3 | 244 | 94 | 011/100 | ≤ 0 | `ordinary/tile_8532d5d099db` |
| `K_outer2` | 7 | 2080241 | 2039675 | 100/101 | ≤ 0 | `ordinary/tile_09197aa9813a` |
| `K_outer4` | 7 | 1046471 | 515951 | 101/100 | ≤ 0 | H-reflection of `K_outer2` (`derived/`) |
| `T_middle1` | 6 | 253500 | 130844 | 001/010 | ≤ 0 | `ordinary/tmiddle1` |
| `J5` | 5 | 32767 | 21845 | 101/101 | ≤ 0 | `ordinary/atlas_3x5_W21845` |
| `Z7` (repeatable) | 7 | 2097022 | 2088828 | 001/101 | ≤ 0 | `ordinary/z7` |
| `Z7_end` | 7 | 2097022 | 2097020 | 001/111 | ≤ 0 | `ordinary/tile_76ba798e4bc4` |
| `C3` | 3 | 511 | 503 | 101/111 | ≤ 1/4 | `numerical/cap_minus_quarter_blue` |
| `E4_open_0_1` | 4 | 4056 | 2021 | 101/010 | ≤ −1 | `numerical/opened_bulk_plus_one_blue` |
| `E4_open_0_3` | 4 | 3955 | 2023 | 101/010 | ≤ −1 | `numerical/opened_bulk_c3_plus_one_blue` |
| `E4_open_1_0` | 4 | 3790 | 2023 | 101/010 | ≤ −1 | `numerical/opened_bulk_middle0_plus_one_blue` |
| `E4_open_1_2` | 4 | 2843 | 1959 | 101/010 | ≤ −1 | `numerical/opened_bulk_middle2_plus_one_blue` |
| `E4_open_2_1` | 4 | 2271 | 1511 | 101/010 | ≤ −1 | V-reflection of `E4_open_0_1` (`derived/`), not needed after normalization |
| `E4_open_2_3` | 4 | 895 | 2023 | 101/010 | ≤ −1 | V-reflection of `E4_open_0_3` (`derived/`), not needed after normalization |

For a numerical root `[A, B, p, q]` the mover is Blue (mask `A`) and is Left in
the number `p/q`. The certificate proves `T + p/q ≤ 0`, so the bound is
`−p/q`: `C3 − 1/4 ≤ 0` and `E4_open + 1 ≤ 0`. The `*_white` files prove the
reverse inequalities (`C3 = 1/4`, `E4_open = −1`). They are replayed but not
used.

Reflections (`K_outer4`, the two row-2 opened bounds, and the two reflected
base tiles) are rebuilt from their sources inside `verify.py`. Each reflection
is checked to be a grid automorphism, compared with the stored copy, and the
rebuilt DAG is **replayed in full**. The proof therefore does not rely on a
symmetry lemma for certificates.

### 5.2 Diagrams of the special gadgets

```text
K_corner   K_outer2   K_outer4   T_middle1  Z7        Z7_end    C3
.wo        ow.wooo    ooow.wo    ..ooob     .booooo   .booooo   ooo
wob        bowooob    booowob    ..wooo     .ooooob   .oooooo   boo
ob.        .booooo    ooooob.    owooob     ooooooo   ooooooo   ooo
```

### 5.3 Base widths 3, 7, 11

`certificates/base/existing_library_scan.json` is a byte-identical copy of
`research/existing_library_scan.json`. For each normalized opening of `3 × 3`
(4), `3 × 7` (8) and `3 × 11` (12), it stores a White reply and a tiling.
`verify.py` checks each tiling with the same comparison checker as the sweep:
coverage of every column, reply legality, both inclusions, seams, and bound
sum `≤ 0`. It also checks that the representatives reflect onto every cell.
The tilings use, besides `E4`, `E4bar`, `F1`, `K_corner` and `Z7_end`, the
ordinary tiles `4d9d5d12cc0f` (B2), `da4864d83b99`, `501c8151efe6` (and its
H-reflection), `2398ea84ec04`, `468c39840ab4`, `7de2134cc103`, `09fb65f2292a`
(and its H-reflection), `8b16696647a7` and `55c55441362e`.

The six cases cannot replace these bases. At `n = 7`, openings `(1,1)` (case 5,
`b = −1`) and `(1,3)` (case 6, `s = 3`) fail; at `n = 11`, opening `(1,5)` fails
(case 5, `b = −1`). Run `verify.py --small-width-diagnostics` to see this.

## 6. Coverage and induction bookkeeping

* **Normalization.** The reflections `(r,c) ↦ (2−r, c)` and
  `(r,c) ↦ (r, n−1−c)` are automorphisms of the empty board that do not swap
  colours, and they preserve checkerboard parity. Every cell maps to some
  `(r,c)` with `r ∈ {0,1}`, `c ≤ (n−1)/2 = 2k+1`. The reply and the whole
  comparison transport along the automorphism.
* **Exhaustive cases.** For normalized `(r,c)`: odd `r+c` is case 1. For
  `r = 0` and `c` even: `c = 0` is case 2, `c ≡ 2 (mod 4)` is case 3, and
  `c ≡ 0 (mod 4)` with `c ≥ 4` is case 4. For `r = 1` and `c` odd,
  `c ≡ 1 (mod 4)` is case 5 and `c ≡ 3 (mod 4)` is case 6. `verify.py` evaluates
  the six predicates independently and requires exactly one to hold.
* **Induction.** This is strong induction on `n ≡ 3 (mod 4)`. The bases are
  `3, 7, 11` (§5.3); the step is `n ≥ 15`. The only recursive call is `H_c` in
  case 6, with `c ≡ 3 (mod 4)` and `3 ≤ c ≤ 2k + 1 < n`. The width strictly
  decreases, and the call stays in the family, so there is no circularity.
  Each step yields `H_n ≤ 0`, and colour symmetry gives `H_n = 0`. The sweep
  mirrors this: a width is "established" only after all its openings pass,
  and case 6 may only call established widths.

## 7. What `verify.py` checks, mapped to this file

| `verify.py` step | Covers |
| --- | --- |
| SHA-256 of every file vs `SHA256SUMS` and `manifest.json` | integrity of §5 |
| `replay_ordinary`, `replay_numeric` on all 33 DAGs | §5.1, §5.3 bounds |
| rebuild and replay of the 5 reflections; automorphism check | `K_outer4`, row-2 opened bounds, reflected base tiles |
| role binding: root = declared masks, ports and diagram recomputed from masks, bound = −offset, pinned roots | §5.1 table |
| `check_opened_e4_roles` | every odd cell of E4 has a bound ≤ −1 (6/6) |
| `check_base_widths` | §5.3 |
| sweep, `plan_width_4k3` + `check_comparison` | (L1), (L2), (L4), (L5) and bound sums for every opening, n ≤ 203 |
| `local_window` + `EXPECTED_WINDOWS` | the window list of §4.8 is complete and correct |
| `check_seam_table`, end sets | seam table and ends of §4.8 |
| `check_case6_structure` | left region is exactly `H_c`, dead column, correct Z7 version, E4bar tail |
| `established` set | strictly decreasing recursion (§6) |
| `check_reflection_coverage`, `check_board_symmetries` | §6 normalization |

## 8. Why the width sweep is a regression test

By §4.1, the comparison hypotheses at any width `n = 4k + 3 ≥ 15` reduce to
width arithmetic, one of the 13 windows, filler blocks, and seam types from the
table. The windows are translation-invariant patterns determined by the case
and variant, and every one already occurs at `n = 15`. Every seam type occurs
by `n = 19`. Larger widths only insert more `E4` blocks on the left and more
`E4bar` (or `E4`) blocks on the right, which add no new window, seam type, or
end. The sweep to 203 (or 403) therefore re-executes the same finite facts on
concrete boards. It guards against transcription errors in the case formulas,
but it is not the reason the theorem holds for all widths.

## 9. Trust base

* The Python interpreter and `verify.py` itself. Its checker logic is copied
  from `original_proof/verify.py`, `atlas/verify.py` and
  `number_certificates.py`, uses only coordinate sets and standard-library
  modules, and imports nothing outside this directory.
* The written arguments §2–§4.1 and §6, which are not machine-checked: the
  comparison principle, the mirror strategy, colour symmetry, the locality
  lemma, and the induction logic.
* Not formalized in a proof assistant; not externally refereed.
