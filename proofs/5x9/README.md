# Empty 5 × 9 Col: partial certificate package

**Status: incomplete.** 9 of the 15 representative openings are
CERTIFIED-FINITE, covering 27 of the 45 openings under the four board
reflections. The empty 5 × 9 board is not yet proved to be a second-player
win. The full round-five status is in
[`../construction/research/round5/HANDOFF.md`](../construction/research/round5/HANDOFF.md)
§3.

## Check the certified openings

Each file in `certificates/partial/` proves that the position after Blue's
opening and White's reply is a Blue-first loss. The verifier uses the
standard library only and runs no search.

```sh
cd proofs/5x9
(cd certificates/partial && shasum -a 256 -c SHA256SUMS)
for f in certificates/partial/o*.json.gz; do python3 verify.py --file "$f" --root pos; done
```

| File | Opening | White reply |
| --- | --- | --- |
| `o1` | (0,1) | (0,0) |
| `o3` | (0,3) | (0,0) |
| `o9` | (1,0) | (0,2) |
| `o11` | (1,2) | (0,0) |
| `o13` | (1,4) | (0,0) |
| `o19` | (2,1) | (0,0) |
| `o21` | (2,3) | (0,0) |
| `o12` | (1,3) | (2,4) |
| `o22` | (2,4), the centre | (0,4) |

## Remaining

The majority-parity openings (0,0), (0,2), (0,4), (1,1), (2,0) and (2,2) are
not yet certified. Once all 15 exist:

```sh
python3 assemble.py certificates/partial/o*.json.gz <new files>
python3 verify.py
python3 negative_controls.py
```

`assemble.py` adds the empty-board root that answers all 45 openings by
reflecting the representatives. The search tools are in
`../construction/research/round5/bridge/src/` (`hyboard.cpp`, the hybrid
expansion-plus-comparison prover).
