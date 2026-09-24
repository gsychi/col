# Independently certified width-three paired bases

Status: **proved finite bases only**. This supplies the initial odd-width
instances of the paired targets used in
[round4_dx_progress.md](round4_dx_progress.md) and
[round4_star_bounds.md](round4_star_bounds.md):

```math
T_1(RX_3),\qquad T_2(VX_3),\qquad T_1(XX_3),
```

where `T_q(G)` means both `G<=q` and `G+*<=q`. Each of the six inequalities
has its own independently verified response DAG. Thus the starred
inequalities are established directly, without a number-plus-star
classification assumption or an inference from a raw outcome.

The checker constructs three-column boards with literal endpoint masks
`R=wobob`, `V=bwbob`, and `X=bowob`. For a starred root, it embeds this board
in columns 0–2 of a 5×5 ambient grid, leaves column 3 dead, and places a
single shared vertex at `(0,4)`. All other cells in column 4 are dead.
This extra component is exactly star and has no edge to the boundary board.

Every root is `G+epsilon*−q`, with Blue next. The independent checker
verifies that every legal Blue move has a legal White response reaching
another listed losing checkpoint. It checks moves in the canonical number
as well as board moves, successor coverage, reachability and decreasing
finite rank. In the starred root, Blue's option to consume the star is
explicitly included, so its same-width White-first obligation is certified
within the finite DAG rather than assumed.

The paired inequalities imply that both corresponding games are strictly
below q, by the generic algebra in the star-bound note. They do not prove
the same assertions at any larger width or fill the remaining recursive
opening classes.

## Artifact mapping

All files are in
[round4_pair_base_certificates](round4_pair_base_certificates/manifest.json).
The manifest records dimensions, row-major masks, offset and checked counts.
In the table below `(A,B;q)` means the encoded game `G(A,B)+q`.

| Artifact | Ambient width | Root `(A,B;q)` | Checkpoints | Response edges |
| --- | ---: | --- | ---: | ---: |
| `rx3_ordinary_upper.json.gz` | 3 | `(32510,12219;-1)` | 342 | 1174 |
| `rx3_starred_upper.json.gz` | 5 | `(7572726,2332915;-1)` | 631 | 2239 |
| `vx3_ordinary_upper.json.gz` | 3 | `(32503,12218;-2)` | 317 | 1186 |
| `vx3_starred_upper.json.gz` | 5 | `(7572695,2332914;-2)` | 589 | 2262 |
| `xx3_ordinary_upper.json.gz` | 3 | `(32447,12282;-1)` | 214 | 790 |
| `xx3_starred_upper.json.gz` | 5 | `(7571703,2333938;-1)` | 456 | 1710 |

There are no missing mappings in this package. It does not require the
earlier exact-value artifacts for RX3, VX3 or XX3.

Run the search-free default check:

```sh
python3 proofs/construction/research/round4_pair_bases_check.py
```

```text
Verified 6 paired-base DAGs: 2549 checkpoints, 9361 response edges.
Proved T1(RX3), T2(VX3), T1(XX3), including each starred inequality directly.
```

The optional `--generate` flag performs certificate discovery separately;
the default checker only reconstructs and validates the supplied evidence.
