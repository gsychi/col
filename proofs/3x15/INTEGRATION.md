# Integrating the new proof into the Col project

## Immediate exact result

The empty 3 × 15 board is now covered by a complete, independent strategy
certificate. The production DFS need not finish its original huge DAG to
establish this finite result.

The former bottleneck is also certified directly:

```text
Blue = {0,14}; White = {44}; White to move
winning White response = 12
```

The response is **not** 30. Its justification is the A4 + E4 + E4 + B2
one-sided tiling, not a heuristic or an assumed periodicity theorem.

## Do not import the wrong claim

A tile in this package is certified **Blue-to-move losing**. It is not
necessarily a zero-valued game, and no exact numerical CGT value is supplied.
Do not insert every tile into a zero-component database or conclude that
its outcome can be substituted into an arbitrary game sum.

The permitted composition is precise: all tiles are Blue-first losing,
White always responds in the tile Blue just selected, and all possible White
cross-tile interactions have been excluded. The checker enforces the latter
condition explicitly.

## A genuinely new pruning test

Implement an optional **one-sided tiling certificate evaluator** before an
expensive unresolved strip search:

1. Orient the actors so the state to certify is Blue-to-move losing.
2. Consider small vertical blocks and the verified tile library.
3. Accept a tile at an embedding only if:
   - actual Blue legality within the block is contained in the tile's Blue
     legality;
   - the tile's White legality is contained in actual White legality.
4. Join adjacent blocks only when their White-legality endpoint masks are
   disjoint, so no White interaction crosses the join.
5. Permit a completely Blue-illegal column to be retired for White too;
   it becomes a dead gap.
6. Return a certified loss only when a partition covers every actual Blue
   move. A failed certificate search is **inconclusive**, not a win.

A failed local matching condition does not justify deleting an edge.
An absent library tile does not justify inventing its outcome.

## Eight-state boundary dynamic program

For three-row strips, a completed prefix only needs to communicate its three
White-legality bits at its right boundary. Let `p` be that 3-bit mask. A tile
whose left White-boundary mask is `l` can be appended if:

```text
p & l == 0
```

The next state is the tile's right White-boundary mask. Thus the certificate
search uses only eight boundary states per column, plus the finite tile
library. This is **not** an unproved compression of arbitrary Col positions:
it is exact dynamic programming for the explicitly restricted, certified
one-sided-tiling strategy class.

`tiling_search.py` implements this procedure in Python. It does not consult
the manifest's 16 opening-response choices. Using only the verified tile
library, it independently finds:

```bash
python3 tiling_search.py --demon
# CERTIFIED DEMON WIN: White 12; widths [4, 4, 4, 2]

python3 tiling_search.py --root
# SUCCESS: 16/16 representative openings certified ...
```

For an OR node with White to move, try each legal White response and call the
Blue-loss tiling evaluator on its child. One certified child supplies an
exact winning response. In particular, this certifies the formerly blocked
state at White 12 without exploring its large child game tree.

## Testing expectations

First run the existing Python certificate verifier, then implement a second
verifier in Rust using the engine's exact legality updates. Require agreement
on all local strategy edges and all opening-case embeddings.

Next add:

- exact replay of all 45 opening choices through the certified strategy;
- rejection tests for corrupt replies and invalid cross-block joins;
- certificate-backed regression tests for the demon response at 12;
- a regression retaining the previously found fact that the response at 30
  is not certified as winning;
- counters for tiling queries, matching tiles, successful covers, and actual
  subtree cutoffs.

Use a theorem/certificate tag in stored outcomes. Publish only a fully checked
certificate result. Keep its move/partition witness so the solver can emit an
explanation rather than only an outcome bit.

## Scope

The 3 × 15 finite result is complete. The written proof also establishes all
empty 3 × (4k+1) strips and the specific three-stone blocked-state family for
widths 4k+3 >= 7. It does not establish every empty 3 × (4k+3) strip, nor all
odd-by-odd rectangles.
