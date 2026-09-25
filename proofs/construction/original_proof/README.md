# A certificate proof for 3 × 15 Col

**Result: the empty 3 × 15 Col board is a second-player win.**

This package proves that finite statement independently of the production
`gsychi/col` solver, its transposition tables, its unfinished searches, and its
persistent bag corpus. It also includes a small certificate for the specific
blocked three-stone position and finite lemmas supporting two parameterized
families described in `PROOF.md`.

This is a computer-assisted, independently checkable proof, not a claim that
the conjecture for every odd-by-odd rectangle has been proved. It is not a
Lean/Coq formalization.

## Check the proof

Python 3.10 or newer, standard library only:

```bash
python3 verify.py
```

The supplied run verified:

- all **16 symmetry-distinct first moves**, covering all **45 cells**;
- **22 local certificates** used by the complete board proof;
- **25 local certificates** including the additional family lemmas;
- **22,423 Blue-turn checkpoints** and **91,789 Blue-move/White-response edges**
  across the entire package;
- tiles of at most **21 cells** (3 × 7).

The recorded checker run took approximately 0.45 seconds in this environment.
That timing is machine-specific, not a claimed production-solver benchmark.

The verifier does not solve any game. It checks every listed local response,
every possible Blue move at every certified checkpoint, strict descent,
opening coverage, and the legality of combining the tiles.

## The idea

**Deliberately restrict White's choices so that all interactions between
blocks constrain Blue only.** Deleting those remaining cross-block
interactions gives Blue more freedom. Nevertheless, the resulting independent
tiles are all certified Blue-first losses. White can answer Blue within the
same tile, forever maintaining a losing checkpoint for Blue.

This is a one-sided relaxation certificate, not an assertion that cutting an
arbitrary edge preserves game value. `PROOF.md` states and proves the exact
conditions.

## The formerly blocked position

With zero-based, row-major cells on a 3 × 15 board:

```text
Blue: {0, 14}
White: {44}
White to move
```

**White plays 12, not 30.** White then avoids the boundary cells specified in
`PROOF.md`. The position is bounded above by four independently certified
Blue-first-losing tiles, of widths 4 + 4 + 4 + 2. The three distinct tile types
require only 215 checkpoints and 633 response edges in total.

The complete empty-board proof does not rely on the assertion that the other
15 openings were previously solved. All 16 are checked here.

## Run the strategy

```bash
python3 strategy.py --blue-moves 0 14
python3 strategy.py --blue-moves 22
```

Supply Blue's actual moves only. The program inserts the certified White
replies and rejects illegal input. It uses the checked response tables, not
DFS. Verify the package before relying on it.

## Regenerate, rather than trust the supplied search output

A C++17 compiler is required only for regeneration:

```bash
python3 regenerate.py --output /tmp/col-proof-regenerated
python3 /tmp/col-proof-regenerated/verify.py
```

`generate.cpp` is a plain actor-relative minimax with exact-key memoization.
It uses no geometric canonicalization, no CGT value evaluator, no component
reduction, no reserve bound, and no production-solver code. The independently
written Python verifier uses coordinate sets and does not trust the generator.

Regeneration reproduces the local strategy graphs from their root masks. The
manifest supplies the proposed opening responses and partitions; the verifier
checks those proposals independently.

## Rediscover the partition without an opening lookup

```bash
python3 tiling_search.py --demon
python3 tiling_search.py --root
```

This uses the verified tile library and an eight-state boundary dynamic
program. It independently finds White 12 for the blocked position and a
certified response to all 16 representative root openings, without searching
their game trees or reading the manifest's opening-response choices.

## Extra tests

```bash
python3 test_proof.py
```

Seven tests pass, including rejection of corrupt replies, missing or
overlapping blocks, forbidden White cross-block interactions, and 450 legal
random-play integrations spanning every possible first Blue move. The random
games are integration tests, **not** the mathematical proof: exhaustive
certificate checking is the proof.

## Contents

- `PROOF.md`: theorem, composition lemma, 16 opening cases, blocked-state proof,
  and two parameterized consequences.
- `manifest.json`: opening responses, tile placements, root masks, checksums.
- `certificates/*.json.gz`: complete local response DAGs.
- `verify.py`: independent search-free checker.
- `strategy.py`: executable White strategy for the empty 3 × 15 board.
- `tiling_search.py`: certificate-discovery DP using only the local tile library.
- `generate.cpp`, `regenerate.py`: independent certificate reproduction.
- `test_proof.py`: corruption and gameplay integration tests.
- `verification_output.json`, `tests_output.txt`, `regeneration_output.txt`:
  observed results.
- `INTEGRATION.md`: how to use these certificates in the project safely.

No modifications to the user's GitHub repository were made by this package.
