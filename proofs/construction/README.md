# Col construction research — September 5, 2026

Read `RESEARCH.md` for the mathematical statements, proofs, finite experiments,
limitations, and ranked broader construction directions.

The latest continuation is
[endpoint recursions and a coupled corner candidate](research/round4_research_progress.md):
new marked-cap clauses, paired boundary bases and recursions, certified corner
replies at widths 3, 5 and 7, and precisely scoped construction obstructions.
It follows [the wider-cap reductions](research/round3_research_progress.md),
[the general graph reductions](research/round2_research_progress.md),
[the first boundary-induction audit](research/five_row_boundary_induction.md),
and its [provenance audit](research/five_row_certificate_provenance.md).
Neither the five-row induction nor the general odd-rectangle proof is complete.

From the repository root, replay the latest six independent checkers with
`python3 proofs/construction/research/round4_verify.py`.

## Check the results

Requires Python 3.10+ and the standard library only:

```bash
python3 original_proof/verify.py
python3 research/number_certificates.py
python3 research/test_new_certificates.py
python3 research/minority_openings.py
```

The new checker validates 19 local strategy certificates containing 2,165
checkpoints and 6,489 first-player-move/second-player-response edges. This includes
both comparisons needed for each exact dyadic identity and the checked refutation
of the naive five-row bulk tile.

The unbounded minority-opening theorem follows from the written repeated-block
construction plus these checked finite lemmas. The 3,876 assembly checks through
width 101 are supplementary implementation tests, not the source of the infinite
claim.

## Regenerate the new certificates

```bash
python3 research/number_certificates.py --generate
python3 research/number_certificates.py
```

Generation uses exhaustive minimax. Verification does not.

## Explore construction coverage

These use the included original certificate package and the included finite
screen results:

```bash
python3 research/scan_existing.py
python3 research/static_2d.py
python3 research/adaptive_2d.py
```

Coverage failure is not a losing-game result. The 7x9 adaptive screen reaches its
node cap for some openings; this is marked explicitly in the output.

## Rebuild the C++ screening tools

```bash
c++ -O3 -std=c++17 research/screen.cpp -o research/screen
c++ -O3 -std=c++17 research/allmasks.cpp -o research/allmasks

# All pairs of left/right White boundary masks; Blue legal everywhere.
research/screen 3 4 5000000

# All White masks on a fixed small rectangle; Blue legal everywhere.
research/allmasks 3 4 1000000

# One specified root; result 0=actor loses, 1=actor wins, 2=budget exhausted.
research/allmasks 5 4 5000000 1048575 518119
```

The CSV files record visits, result and budget exhaustion, not guessed outcomes.
A follow-up resolved the single initially unfinished height-5, width-4 boundary
screen with masks 1048575 and 1011711 as Blue-first winning in 1,811,148 visits.

No general odd-rectangle theorem is claimed. These results are not externally
peer reviewed and are not Lean/Coq formalizations.
