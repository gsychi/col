# Atlas integration review and four small L-remainder counterproofs

Date: September 5, 2026.

## Scope

This packet reviews the five proposed integration priorities against the supplied
`col_tile_atlas_2026-09-05.zip`. It does not modify the GitHub repository, rerun
3x23, prove 5x9 or 7x7, or claim a production speedup.

The original classification verifier and derived-index verifier were rerun.
They validate the 21 full-Blue classifications and the references of 152,473
partial checkpoints. Exactly 772 records have `white & ~blue == 0`.

## Exact-zero upgrade theorem

On any fixed finite Col graph, let A be the positive/first-role legal set,
B the negative/second-role legal set. Suppose a verified certificate establishes
G(A,B) <= 0 and B is a subset of A. Remove vertices unavailable to both roles.
The remaining vertex set is A. Put H=G(A,A). Monotonicity implies

    H <= G(A,B) <= 0.

Color exchange gives H=-H. Thus H<=0 and H>=0, so H=0 and G(A,B)=0.
This does not assume that every empty graph is zero. It derives zero in this
specific case from the certificate.

The same test may be applied to an actual matched state, not only an original
atlas checkpoint, once a genuine nonpositive bound for that actual state has
been proved. Inclusion matching alone is insufficient. Both the bound and
B subset A are required.

`zero_upgrades.jsonl.gz` exports all 772 source records with exact-zero tags,
source certificate/node references, and source-file SHA256 digests. It is a
proof-derived supplement, not a replacement for the source certificates.
Roles remain relative to the source checkpoint, not hardcoded physical colors.

## Directional integration rules

- G<=0: Blue loses when Blue is to move.
- G>=0: White loses when White is to move.
- G=0: the current player loses.
- Unknown or budget exhaustion proves neither direction.

To certify a White-to-move loss using the same first-actor-loss evaluator,
swap the actual masks and protect Blue's cross-tile interactions. Negating
only a cached result bit is not a valid color swap.

A refuted local tile only rejects that tile/cover/strategy attempt. It is not
an actual whole-board refutation unless the original actual state is covered
by a sound counterproof. In particular, a Blue win in a relaxation that gave
Blue additional moves is not a proof that Blue wins the physical position.

For full-Blue classified shapes, a minimal safe support S with S subset W
proves local exact zero. A maximal unsafe support U with W subset U proves
local positivity. A complete validated classification permits a fast scan of
only minimal supports; on a miss, select an unsafe witness lazily when needed.
With damaged Blue legality, safe-upper-bound matching may remain valid, but
unsafe conclusions do not transfer automatically.

## Proposed bare L construction: exact negative result

Place an (h-1)x(w-1) even-by-even bulk in the upper-left corner of an odd h x w
board, for (h,w)=(5,9) or (7,7). Its complement is an induced 13-vertex path:
down the right column, then left along the bottom row. There are no extra
edges between nonconsecutive path vertices.

Allow bulk White on one global checkerboard class. Give White every remaining
L vertex that does not border a permitted bulk White vertex. Blue retains
all L vertices. This is the maximally White-friendly independent remainder
for this particular bulk support and cut.

The induced path permissions are:

| Target | Bulk checkerboard parity | L path, from top-right to bottom-left |
|---|---|---|
| 5x9 | even | obobobobobobo |
| 5x9 | odd  | bobooobobobob |
| 7x7 | even | obobobobobobo |
| 7x7 | odd  | bobobooobobob |

Here o is shared permission and b is Blue-only permission, not a stone.

All four isolated L games are Blue-winning with either starting player.
The packet supplies complete White-first-losing DAGs both for each original
L and for a child after a certified winning Blue opening. It has 512 total
checkpoints and 1,469 response edges (including the repeated phase-even path).

Therefore none of these four bare zero-bulk plus independently-safe-L covers
works. Removing more White permissions from the L cannot repair it.

This does NOT imply that the connected boards are Blue-winning. It does NOT
rule out opening-dependent damaged remainders, signed compensation, changed
bulk supports, changed cuts, or adaptive interface play.

## Reproduction

No third-party Python dependencies are required.

    python3 verify_l_shapes.py

The checker independently reconstructs the actual geometry, maximum compatible
White permissions, roots, every legal first-actor move, every responder move,
closure, descent, and reachability. It performs no minimax and includes corrupted
interface and missing-response rejection tests.

To regenerate the four finite proof DAGs:

    python3 build_checks.py
    python3 verify_l_shapes.py

To reproduce the zero-record extraction, first extract the original atlas and
verify it, then point to its directory:

    cd /path/to/col_tile_atlas
    python3 verify.py
    python3 verify_index.py
    python3 /path/to/this/packet/export_zero_upgrades.py /path/to/col_tile_atlas

## Proposed integration order

1. Typed, role-explicit importer and two-direction checks in the same patch.
2. Complete-classification lookup, with lazy counterproof witness selection.
3. 772 exact-zero imports plus the general subset-zero promotion theorem.
4. Reproduce recorded 3x23 cases, separating proofs, refutations, rejected
   constructions, and budget-limited unknowns.
5. Parameterized macros expanding into checked primitive witnesses.
6. For taller boards, test opening-dependent/signed L constructions, rather
   than retrying the four bare cases excluded here.

Record wall time and memory as well as outcome conversion counts. A fixed
node-budget run cannot alone establish a reduction of the completed search DAG.
