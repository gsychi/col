# Certificate provenance for the five-row research continuation

Audit date: 2026-09-22. This audit uses
[`col_research_handoff.md`](col_research_handoff.md) as the latest mathematical
context and [`empty_3xn_theorem.md`](../empty_3xn_theorem.md) as the recorded
three-row proof. It distinguishes a missing correspondence to repository data
from a failed mathematical statement. In particular, it neither reopens the
disproved small-width formula for `L` nor treats a positive comparison game as a
positive actual game.

This document audits the pre-existing packages. New certificates produced by
the present five-row continuation have their own manifests and checkers; they
are not retroactive evidence that the handoff's larger historical certificate
collection was already present.

## Checks replayed

The following commands succeeded from the repository root, without invoking
certificate generation or minimax:

```sh
python3 proofs/construction/original_proof/verify.py
python3 proofs/construction/research/number_certificates.py
python3 proofs/construction/research/test_new_certificates.py
python3 proofs/construction/research/provenance_check.py
```

The first checks 25 ordinary response DAGs, with 22,423 checkpoints and 91,789
universally checked Blue-move/White-response edges. It also checks all 45
openings of the empty `3×15` board, represented by 16 cases, and the recorded
separate demon position. It checks hashes, root geometry, move coverage, reply
legality, successor closure, rank descent, reachability, permission inclusion,
and seam compatibility.

The second checks 19 numerical/outcome certificates, with 2,165 checkpoints and
6,489 response edges. Eighteen are pairs of comparisons proving nine exact
dyadic identities. The nineteenth refutes the naive alternating `5×4`
extrusion by a specific Blue opening. The third rejects four deliberately
damaged certificates: an illegal reply, a missing first-player branch, a
non-dyadic number, and a missing successor checkpoint.

The fourth is the new, search-free [provenance replay](provenance_check.py)
for the recovered width-3/7/11 base assemblies and the usable atlas `J5`
described below. It binds the numerical `J5` root explicitly and rechecks
every stored base assembly against verified ordinary DAG roots.

The historical handoff instead describes a later collection of **26 ordinary
and five numerical certificates**, with **44,664 checkpoints and 191,527
edges**. The two available collections above are not that inventory, and
their counts must not be substituted for it. The named-file/manifest mapping
for that later inventory remains missing.

## Three-row roots that can be identified

All masks below use row-major bits, with bit zero at the upper-left cell. For
ordinary certificates the first mask is Blue permission and the second White
permission. Port strings list White legality top to bottom. `H` below means
horizontal reflection of a certified root and its strategy, not color exchange.

The ordinary files in this table are relative to
[`original_proof`](../original_proof/manifest.json).

| Role in the proof | Width; root `(A,B)` | Checked source or derivation | White ports, left/right |
| --- | --- | --- | --- |
| `E4≤0` | 4; `(4095,2023)` | `certificates/tile_e4d37d528005.json.gz` | `101 / 010` |
| `E4bar≤0` | 4; `(4095,3710)` | `certificates/tile_675ea04f7dff.json.gz`; also `H(E4)` | `010 / 101` |
| `F1≤0` | 1; `(7,5)` | `certificates/tile_e06eb7fc2dd6.json.gz` | `101 / 101` |
| `K_corner≤0` | 3; `(244,94)` | `certificates/tile_8532d5d099db.json.gz` | `011 / 100` |
| `K_outer2≤0` | 7; `(2080241,2039675)` | `certificates/tile_09197aa9813a.json.gz` | `100 / 101` |
| A usable `K_outer4≤0` | 7; `(1046471,515951)` | `H(tile_09197aa9813a)` | `101 / 100` |

The `K_corner` root is the local position after Blue `(0,0)`, White `(2,2)`.
The `K_outer2` root fits Blue `(0,2)`, White `(2,0)` and the required seams.
Its reflection fits Blue `(0,4)`, White `(2,6)` and the required seams. Thus the
table supplies explicit safe realizations of both outer-row roles; it does
not rely on a historical alias file being present.

There is an important near-match: `tile_8b16696647a7.json.gz` has the same
`K_outer4` Blue mask but White mask `516079`, with **left port `111`**. It is
useful at a physical left boundary, as in some stored finite assemblies, but
cannot simply follow `E4`. The reflected root in the table has White mask
`515951` and the compatible left port. Numerical nonpositivity alone would
not justify swapping those roots.

The numerical files below are relative to
[`new_certificates`](new_certificate_summary.json). Each listed pair proves
both directions, by checking the game plus a number and its conjugate.

| Claim | Root position `(A,B)` | Certificate filename stems |
| --- | --- | --- |
| `C3=1/4` | `(511,503)` on `3×3` | `cap_minus_quarter_blue`, `cap_minus_quarter_white` |
| `E4=0` | `(4095,2023)` on `3×4` | `original_bulk_blue`, `original_bulk_white` |
| Blue `(0,1)` in `E4` leaves `-1` | `(4056,2021)` | `opened_bulk_plus_one_blue`, `opened_bulk_plus_one_white` |
| Blue `(0,3)` in `E4` leaves `-1` | `(3955,2023)` | `opened_bulk_c3_plus_one_blue`, `opened_bulk_c3_plus_one_white` |
| Blue `(1,0)` in `E4` leaves `-1` | `(3790,2023)` | `opened_bulk_middle0_plus_one_blue`, `opened_bulk_middle0_plus_one_white` |
| Blue `(1,2)` in `E4` leaves `-1` | `(2843,1959)` | `opened_bulk_middle2_plus_one_blue`, `opened_bulk_middle2_plus_one_white` |

Every stem has extension `.json.gz`. Vertical reflection supplies the other
two odd-parity outer-row openings. The numerical checker explicitly pins these
roots and offsets, so the claimed signs do not depend on filenames alone.

### A usable five-column `J5`

The later theorem does not give `J5`'s masks. A verified root supplying exactly
its stated role is the atlas tile
[`3x5-W21845`](../../atlas/certificates/3x5/W21845.json.gz), with
`A=32767`, `B=21845` and diagram

```text
obobo
bobob
obobo
```

Its left and right White ports are `101`. The provenance replay calls
`proofs/atlas/verify.py::verify_strategy` on this exact root and succeeds with
490 checkpoints and 1,829 edges. This proves the needed upper bound `≤0`.
It fits either `E4` on its left or a preceding tile with right port `010`.
This is an auditable realization of the role, not an assertion that the
unmapped historical alias necessarily denoted this same pattern.

### The three finite empty-board bases

[`existing_library_scan.json`](existing_library_scan.json) contains concrete
reply-and-assembly witnesses for widths 3, 7, and 11. The provenance replay
checks these witnesses without calling `scan_existing.py` or its search:

| Empty board | Stored representatives | Openings covered after reflection |
| --- | ---: | ---: |
| `3×3` | 4 | 9 |
| `3×7` | 8 | 21 |
| `3×11` | 12 | 33 |

For each witness, the audit loaded the already verified ordinary certificate,
applied any `:H1V0`-style reflection suffix to its masks, checked the initial
reply, embedded every block, and checked `A_actual⊆A_virtual`,
`B_virtual⊆B_actual`, disjoint block ownership, and every crossing edge.
Every check passed. The representative sets reflect onto all board cells.
These are recoverable finite base certificates, not missing mathematical
base cases. Their stored generation timings and the unrelated larger-width
search failures have no role in the verification.

## Three-row correspondences still missing

> **Update (2026-09-23): all three items below are closed.** `T_middle1`
> (253500, 130844) and the repeatable `Z7` (2097022, 2088828) were generated
> and replayed as Blue-first losses, and
> `python3 proofs/construction/three_row/verify.py` binds every gadget role,
> replays every certificate, and checks the six-case assembly. The text
> below records the gaps as they stood on 2026-09-22.

1. **`T_middle1`, width six.** No root/manifest alias for the later theorem's
   Blue `(1,1)`, White `(0,0)` gadget was found. Its unrelaxed Blue mask is
   `253500`; after the reply and the required White seam exclusions, the
   maximal allowable White mask is `130844`. The relevant left/right White
   port requirements are subsets of `101 / 010`. No dominating checkpoint
   with these dimensions and constraints was found in the existing atlas
   partial-tile index. This is a statement about that stored index, not about
   existence of the gadget.

2. **`Z7` with a repeatable right seam.** The existing
   `tile_76ba798e4bc4.json.gz` has root `(2097022,2097020)` and matches the
   local post-response geometry, but its right White port is `111`. It
   therefore cannot be followed by `E4bar`, whose left port is `010`.
   Permanently removing the middle-right White permission gives the candidate
   mask `2088828`; its nonpositivity is a separate obligation. No matching
   certificate or dominating atlas checkpoint was found for this required
   seam contract. The old root remains valid when its right edge is a
   physical boundary. Failure of this *identification* says nothing about
   the existence or value of the later `Z7` gadget.

3. **The later six-case assembly checker and full certificate inventory.**
   The parameterized argument is recorded in the theorem file. The older
   manifest checks a fixed `3×15` assembly, not the full later symbolic
   induction. Recovering its missing finite roots and an explicit manifest
   remains an audit task. The argument and its supplied mathematical context
   should not be replaced by the obsolete claims of unresolved widths in
   earlier `RESEARCH.md` files.

## Five-row and projected-core correspondences

The available pre-existing `5×4` atlas numerical files concern the
alternating extrusion and its openings. Their geometry is different from
`DD`, `DU`, `DV`, `DR`, `DX`, and `DJ`; they are not certificates for the
handoff's two-ended boundary claims. The CSV boundary screens are discovery
results and do not supply the requested numerical strategy DAGs.

The following historical claims lack an identified exact certificate root,
manifest, and corresponding verifier run in the pre-existing package:

| Handoff claim group | Missing provenance |
| --- | --- |
| `D1=0`, `D2=0`, `D3=-1/2`, `D4=0`, `D5<0` | The D-family certificate inventory and named roots |
| `DD7=-1` | Both comparison roots and their certificate files |
| `DX2=-1`, `DX4=-1/2`, `DX6=-1/4` | Both comparison roots at each width |
| `DR2=DR4=DR6=-1/2` | Both comparison roots at each width |
| `DU_k≤-1/8`, `k=1,3,5,7` | Upper-bound comparison roots |
| `DV_k≤1/2`, `k=2,4,6` | Upper-bound comparison roots |
| `DJ1=-1/2+*`, `DJ3=-3/4`, `DJ5=-5/8` | Numerical/star comparison roots and checker support |
| One-ended `X`, `R`, and `J` values | Exact/outcome witnesses with the claimed endpoint geometry |
| All 80 one-column separator contracts | The full catalog and mapping from opening row and White subset to its root |
| `L2,…,L10` and `L12=0` | The projected-core numerical certificate roots |
| `L_n≥0` for even `n≥12` and the growing lower bound | The lower-bound construction witnesses, finite base certificates, and their parametric assembly verification |

Some width-one entries are small enough to verify afresh, and the current
continuation does so where required. Such a new check must be labeled with
its own root and scope; it does not recover a missing historical file.

The arbitrary-width comparisons `DR≤H`, `DV≤P`, `DX≤L`, and
`DD≤C+1/2` likewise need explicit projected-region definitions and assembly
witnesses before a repository checker can reproduce them. The handoff fully
specifies `L` but does not give corresponding complete masks for `H`, `P`,
and `C`. These projected cores must not be confused with ordinary empty
three-row rectangles.

The audit does **not** demote the handoff's established `L` obstruction to a
failed search. The continuation retains that obstruction as supplied research
context: the fixed `DX≤L` route cannot establish the required uniform sign.
Missing repository provenance is a separate issue. Neither that obstruction
nor a positive upper bound for a relaxed game determines the sign of `DX`
or of the actual `DD` position.

## What would close the provenance gaps

For each missing finite claim, record dimensions, permission masks, number or
star offset, starting player, certificate path, and verifier invocation. For
each symbolic composition, record the legal opening/reply, region embeddings,
White supports at every seam, and decreasing recursive rank. In particular,
the eventual five-row induction must maintain separate obligations after a
Blue opening (White next) and after a White reply (Blue next). A valid
nonpositive finite comparison proves the latter obligation; strictness or an
explicit White move is still needed for the former.
