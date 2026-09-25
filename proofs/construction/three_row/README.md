# Verification package for the all-width theorem: every empty 3 × n Col board is 0

**Status: PROVED**, given the written arguments in
[`PROOF_CHECKLIST.md`](PROOF_CHECKLIST.md) and
[`../empty_3xn_theorem.md`](../empty_3xn_theorem.md), plus the certificates
replayed here. No gadget role is unbound. I found **no mathematical gap** in the
six-case induction. I found documentation and binding discrepancies, listed
below with replacement text. Two of them concerned certificates the proof
needed; both are closed by today's `T_middle1` and repeatable-`Z7` files.

## One command

```sh
python3 proofs/construction/three_row/verify.py
```

It uses the standard library only, runs no game search, imports nothing
outside this directory, and takes about 10 s. Options: `--max-width N` (default
203; 403 also passes in about 45 s), `--small-width-diagnostics`, `--quiet`.
Output from the last run: [`verification_output.txt`](verification_output.txt).

Negative controls (about 20 s; scratch copies go to `/tmp/three_row/` and are
deleted afterwards):

```sh
python3 proofs/construction/three_row/negative_controls.py
```

Hashes alone: `cd proofs/construction/three_row/certificates && shasum -a 256 -c SHA256SUMS`.

## What `verify.py` checks

1. SHA-256 of all 34 files under `certificates/`, against `SHA256SUMS` and
   `manifest.json`.
2. A search-free replay of 33 response DAGs:
   * 21 ordinary DAGs: 18 files plus 3 reflections, 20,575 checkpoints, 82,899
     edges.
   * 12 dyadic DAGs: 10 files plus 2 reflections, 1,064 checkpoints, 3,130
     edges.

   The checker logic is copied from `original_proof/verify.py`,
   `atlas/verify.py` and `number_certificates.py`.
3. Reflections are rebuilt from their sources, compared with the stored
   copies, and replayed in full; each reflection map is checked to be a grid
   automorphism. The reflections are `K_outer4 = H(K_outer2)`, the row-2
   opened-E4 bounds, and two reflected base tiles.
4. Role binding. Each of the 17 roles is tied to its exact root, and its White
   ports and diagram are recomputed from the masks. Its bound is taken from
   the certificate, as `−q` for a dyadic offset `q`. The roots are also pinned
   inside `verify.py`, independently of the manifest.
5. The stored base assemblies for widths 3, 7, 11: 4, 8 and 12 normalized
   openings, with reflection coverage.
6. A sweep over widths 1..203:
   * even widths: the half-turn is a fixed-point-free automorphism;
   * `4k+1`: the tiling `E4^k F1`;
   * `4k+3 ≥ 15`: all 5,280 normalized openings, through the six cases
     transcribed from the theorem.

   For each assembly it checks disjoint coverage, reply legality,
   `A_actual ⊆ A*`, `B* ⊆ B_actual`, that no seam has White-legal cells on both
   sides, and the bound sum: `< 0` with White to move in case 1, `≤ 0` after
   White's reply in cases 2–6.

   It also checks:
   * reflection coverage of every cell;
   * the case-6 structure: the left region is exactly empty `3 × c` with
     `c ≡ 3 (mod 4)` and `3 ≤ c < n`, then a dead column, then `Z7`, with the
     repeatable version whenever `E4bar` follows, then `E4bar` blocks;
   * that case 6 only calls strictly smaller widths already established.
7. The width-independent facts on which the all-width argument rests.
   Every local window around an opening and its reply must be one of the 13
   analysed windows, plus 2 supplementary row-2 windows. The seam table has 25
   adjacent block-type pairs, and the end-block types are also checked. All
   windows occur at `n = 15` and all seam types by `n = 19`. The larger widths
   are therefore a regression test (`PROOF_CHECKLIST.md` §4, §8).

## Files

| Path | Content |
| --- | --- |
| `verify.py` | the single verifier |
| `manifest.json` | certificates (file, root, counts, SHA-256, source path) and roles (width, masks, ports, diagram, bound, where used) |
| `certificates/ordinary/` | 18 ordinary DAGs, byte-identical copies (15 from `original_proof`, `tmiddle1` and `z7` from `incoming/`, `J5` from `atlas/…/3x5/W21845`) |
| `certificates/numerical/` | 10 dyadic DAGs from `research/new_certificates/` (5 used, 5 reverse-direction) |
| `certificates/derived/` | 5 reflections, rebuilt and compared by `verify.py` |
| `certificates/base/existing_library_scan.json` | byte-identical copy of the base-width witnesses |
| `PROOF_CHECKLIST.md` | why finite checks plus the written induction cover all widths |
| `negative_controls.py`, `negative_controls_output.txt` | 15 corruptions, all rejected |
| `build_package.py` | packaging only: rebuilds the reflections, `SHA256SUMS` and `manifest.json` |
| `incoming/` | the files delivered today (left untouched) |

## Role binding

| Role | Root (width; Blue, White) | White ports L/R | Bound | Certificate |
| --- | --- | --- | --- | --- |
| `E4` | 4; 4095, 2023 | 101/010 | ≤ 0 | `tile_e4d37d528005` |
| `E4bar` | 4; 4095, 3710 | 010/101 | ≤ 0 | `tile_675ea04f7dff` |
| `F1` | 1; 7, 5 | 101/101 | ≤ 0 | `tile_e06eb7fc2dd6` |
| `K_corner` | 3; 244, 94 | 011/100 | ≤ 0 | `tile_8532d5d099db` |
| `K_outer2` | 7; 2080241, 2039675 | 100/101 | ≤ 0 | `tile_09197aa9813a` |
| `K_outer4` | 7; 1046471, 515951 | 101/100 | ≤ 0 | H-reflection of `K_outer2`, replayed in full |
| `T_middle1` | 6; 253500, 130844 | 001/010 | ≤ 0 | `incoming/tmiddle1` |
| `J5` | 5; 32767, 21845 | 101/101 | ≤ 0 | atlas `3x5/W21845` |
| `Z7` (repeatable) | 7; 2097022, 2088828 | 001/101 | ≤ 0 | `incoming/z7` |
| `Z7` (physical right edge) | 7; 2097022, 2097020 | 001/111 | ≤ 0 | `tile_76ba798e4bc4` (= `incoming/z7old`) |
| `C3` | 3; 511, 503 | 101/111 | ≤ 1/4 | `cap_minus_quarter_blue` |
| `E4` opened at (0,1), (0,3), (1,0), (1,2) | 4; (4056,2021), (3955,2023), (3790,2023), (2843,1959) | ⊆ 101/010 | ≤ −1 | `opened_bulk{,_c3,_middle0,_middle2}_plus_one_blue` |
| `E4` opened at (2,1), (2,3) | 4; (2271,1511), (895,2023) | ⊆ 101/010 | ≤ −1 | V-reflections of the (0,1) and (0,3) files |

The base widths also use nine further ordinary tile files, eleven DAGs when
the two reflections are counted: B2 `4d9d5d12cc0f`, `da4864d83b99`,
`501c8151efe6` (and its H-reflection), `2398ea84ec04`, `468c39840ab4`,
`7de2134cc103`, `09fb65f2292a` (and its H-reflection), `8b16696647a7` and
`55c55441362e`.

## Findings

* **Odd cells of E4.** All six odd-parity cells have a replayed bound ≤ −1.
  Under the theorem's normalization (`r ∈ {0,1}`), case 1 only ever meets
  `(0,1), (0,3), (1,0), (1,2)`. The row-2 cells arise only if the board is not
  reflected vertically. Their bounds are the V-reflections of the `(0,1)` and
  `(0,3)` certificates, rebuilt and replayed, and are exercised by 1,320
  un-normalized row-2 case-1 assemblies. No odd cell is missing.
* **Z7 at the physical edge.** The repeatable `Z7` also works at `s = 7`
  (checked), so case 6 does not need the physical-edge root. That root is
  still used by the stored 3 × 7 and 3 × 11 base assemblies.
* **The bases are needed.** Applied at `n = 7`, the six cases fail at `(1,1)`
  (case 5, `b = −1`) and `(1,3)` (case 6, `s = 3`). At `n = 11` they fail at
  `(1,5)` (case 5, `b = −1`). The step starting at `n = 15` is exactly right.
* **Duplicate file.** `incoming/z7old.json.gz` is node-for-node identical to
  `original_proof/…/tile_76ba798e4bc4.json.gz`.
* **Counts versus the handoff.** Handoff §28 cites 26 ordinary plus 5
  numerical certificates, with 44,664 checkpoints and 191,527 edges. That
  inventory remains unrecovered; do not cite it for this package. This
  package uses 21 ordinary DAGs (20,575 checkpoints, 82,899 edges) and 5
  needed numerical DAGs (C3 and four opened-E4 bounds; 470 checkpoints,
  1,440 edges). The remaining 7 numerical DAGs are supplementary.

## Discrepancies between `empty_3xn_theorem.md` and what the certificates support

I did not edit the theorem file. Each item gives exact replacement text.

**D1 — Case 6 needs a specific `Z7` root.** This was a certificate gap until
today. The only previously stored `Z7` (`tile_76ba798e4bc4`, White mask
2097020) has right port `111`. It fails when followed by `E4bar`, which
happens for every `s ≥ 11`; negative control `old_z7_in_repeated_position`
confirms this. Replace "On the right, the response at `(0,c+1)` leaves a
region tiled by `Z7 E4bar^((s-7)/4)`. Each gadget has upper bound zero and
their White seam masks are compatible, so the right contribution is at most
zero." with:

> On the right, the response at `(0,c+1)` leaves a region tiled by
> `Z7 E4bar^((s-7)/4)`, where `Z7` is the width-7 gadget with Blue mask
> `2097022` and White mask `2088828` (diagram `.booooo / .ooooob / ooooooo`,
> White ports `001 / 101`). Its root is the local position after the stones
> at `(1,c)` and `(0,c+1)`, with White additionally forgoing local `(1,6)`, so
> its right port `101` meets `E4bar`'s left port `010`. The older root with
> White mask `2097020` has right port `111`. It is valid only when `s = 7`,
> where `Z7` ends at the physical edge, and cannot be followed by `E4bar`.
> Each gadget is at most zero and every seam has a White-illegal endpoint, so
> the right contribution is at most zero.

**D2 — Case 4 needs a specific `K_outer4` root and an argument for its
parameters.** The stored near-match `tile_8b16696647a7` (White mask 516079)
has left port `111`. It fails after `E4`, i.e. whenever `a ≥ 1`, first at
`n = 19`; negative control `left_port_111_after_e4` confirms this. The theorem
also never shows `a ≥ 0` or `b ≥ 0` in this case. Replace the text of Case 4
after its heading with:

> Again set `b=k-a-1`; White replies at `(2,c+2)`. Tile as
> `E4^a K_outer4 E4bar^b`, where `K_outer4` is the horizontal reflection of
> `K_outer2`: Blue mask `1046471`, White mask `515951` (diagram
> `ooow.wo / booowob / ooooob.`, White ports `101 / 100`). Its local moves are
> `(0,4)` for Blue and `(2,6)` for White. Since `c ≥ 4` (the corner `c = 0` is
> Case 2), `a ≥ 0`, and `4a+4 = c ≤ 2k+1` gives `b ≥ (2k-1)/4 > 0`, so
> `b ≥ 1`. The total width is `4a+7+4b=4k+3`. The left port `101` meets
> `E4`'s right port `010`, and the right port `100` meets `E4bar`'s left port
> `010`. All pieces are nonpositive, so `G≤0`. (The stored root with White
> mask `516079` has left port `111` and is usable only when `a = 0`.)

**D3 — Case 1 should name its four certificates and their sign convention.**
Replace the paragraph beginning "Tile the board as `E4^k C3`" with:

> Tile the board as `E4^k C3`, with the cap in columns `4k,4k+1,4k+2`. Since
> `c ≤ 2k+1 < 4k`, Blue opened the `E4` block `j=⌊c/4⌋`, at local cell
> `(r, c-4j)`. Because `r ∈ {0,1}` and `r+c` is odd, that cell is one of
> `(0,1), (0,3), (1,0), (1,2)`. For each of them a numerical certificate
> proves `E4_open + 1 ≤ 0`, where the opened block has Blue mask
> `4095 ∖ N[v]` and White mask `2023 ∖ {v}`. All other `E4` blocks are at most
> zero, and the cap `C3` (Blue mask `511`, White mask `503`, left port `101`)
> satisfies `C3 - 1/4 ≤ 0`. By the comparison principle in its game-order
> form, `G ≤ -1 + 1/4 = -3/4 < 0`, and White, who is to move, wins.

**D4 — The composition principle's justification covers only the
Blue-to-move outcome.** Case 1 has White to move and a positive term
(`C3 ≤ 1/4`). It needs the game-order inequality `G_actual ≤ Σ T_i`, which the
text states but does not prove. The inequality is true; the proof is in
`PROOF_CHECKLIST.md` §2. Replace the paragraph beginning "The first condition
gives Blue extra freedom" with:

> *Proof.* It suffices that Blue, moving first, loses
> `G_actual + Σ(−T_i)`. White answers each Blue move at `v` in `G_actual`
> with the Blue placement at `v` in the block containing `v`, which is a
> Right move in `−T_i`; this is available by condition 1. Each Blue move in
> some `−T_i` is a White placement `w` in `T_i`, and White answers it by
> playing `w` in `G_actual`; this is available by condition 2. An actual Blue stone removes at least as
> much Blue legality as its virtual copy, so condition 1 persists. An actual
> White stone at `w` removes White legality from neighbours of `w` in other
> blocks. By condition 3 those cells were never White-legal virtually, so
> condition 2 persists. White therefore always has an answer, and Blue runs
> out of moves first. Consequently, a virtual sum at most zero shows that Blue
> loses when Blue is to move in the actual position. A virtual sum below zero
> shows `G_actual < 0`, so White wins even when White is to move (Case 1). The
> argument is unchanged with dyadic numbers added to the virtual sum. This is
> a one-sided comparison, not a claim that cutting arbitrary board edges
> preserves game value.

**D5 — The base widths are not tied to data.** Replace "The boards of widths
3, 7, and 11 are finite certified base cases." with:

> The boards of widths 3, 7, and 11 are finite certified base cases. For
> each of their 4, 8, and 12 normalized openings,
> `research/existing_library_scan.json` stores a White reply and a tiling by
> certified tiles, replayed by `three_row/verify.py`. Besides `E4`, `E4bar`,
> `F1`, `K_corner` and the physical-edge `Z7`, those tilings use nine further
> ordinary tiles. The six cases below do not cover these widths. At `n = 7`,
> Case 5 at `(1,1)` would need `b = −1` and Case 6 at `(1,3)` would have
> `s = 3`; at `n = 11`, Case 5 at `(1,5)` would need `b = −1`.

**D6 — The gadget inventory omits `F1` and gives no roots.** Replace the
first sentence of the opening gadget paragraph with:

> The gadget names and bounds below are those used in the proof: `E4`, its
> horizontal reflection `E4bar`, the one-column end tile `F1`, `K_corner`,
> `K_outer2`, `K_outer4`, `T_middle1`, `J5`, `Z7`, and the cap `C3`; their
> exact roots (width, Blue mask, White mask, White ports) and certificate
> files are bound in `three_row/manifest.json` (table in
> `three_row/README.md`).

**D7 — The closing paragraph implies an explicit reply in every case.**
Replace its first two sentences with:

> The cases cover every normalized first Blue move. In Cases 2–6, White's
> stated reply leaves a position of value at most zero. In Case 1 the position
> after Blue's move is already negative, so White has a reply of value at most
> zero (a Right option), although none is named. Hence `H_(4k+3)≤0`.

**D8 — Wording in Case 6 (harmless).** Replace "White replies at `(0,c+1)`
and voluntarily never plays either remaining square in column `c`." with:

> White replies at `(0,c+1)`, which already makes `(0,c)` White-illegal, and
> voluntarily never plays `(2,c)`.

**D9 — The provenance section is now out of date.** Replace the section
"Provenance and remaining formalization work" (keep the final sentence about
the handoff) with:

> Each named gadget and numerical bound is bound to an exact certificate root
> in `three_row/manifest.json`. `python3 proofs/construction/three_row/verify.py`
> replays every certificate without search and checks the base widths. It
> also checks the six-case tilings for every normalized opening at widths up
> to 203, the local windows and seam table on which the all-width argument
> rests (`three_row/PROOF_CHECKLIST.md`), and the strictly decreasing
> recursion. The finite sweep is a regression test; the all-width claim rests
> on the written induction and those finitely many local checks.

I found nothing else. Cases 2, 3 and 5 are correct as written: their replies,
tilings, width sums and parameter bounds all match the certificates. The
bounds hold exactly where the cases are applied: `b ≥ 1` in cases 3 and 4,
`b ≥ 0` in case 5 for `k ≥ 3`, and `s ≥ 7` in case 6.

## Negative controls (15/15 rejected for the expected reason)

* The old `Z7` followed by `E4bar`.
* Wrong White replies in case 3 and case 6.
* A flipped declared port (`T_middle1` left `001 → 101`).
* A flipped mask bit (`T_middle1` White mask bit (0,5)).
* The left-port-111 `K_outer4` after `E4`, with its pins adjusted so that only
  the seam check can catch it.
* A corrupted reply inside a DAG.
* A byte flip in `z7.json.gz`.
* A tampered stored reflection, with hashes refreshed.
* A missing opened-E4 (1,2) bound.
* The opened-E4 role bound to the reverse-direction certificate.
* `C3` weakened to `≤ 1`, so case 1 is no longer strictly negative.
* Case 5 applied at `k = 2`.
* The 3 × 11 base removed.
* One stored 3 × 7 base answer dropped.

See [`negative_controls_output.txt`](negative_controls_output.txt).

## Limits

* This package does not machine-check the written arguments (the comparison
  principle, the mirror strategy, colour symmetry, the locality lemma, and the
  induction). The Lean formalisation in [`../../lean/`](../../lean/README.md)
  does, together with its own certificates.
* Nothing here is externally refereed.
* Nothing here bears on height 5 or on any height ≥ 7.
