# Mirror strategy and the centre: what a general lemma would need (2026-09-24)

Target: a general odd × odd lemma based on the half-turn `ρ`, the only board
symmetry whose fixed set is a single cell, the centre `c`. Labels as in
[`../HANDOFF.md`](../HANDOFF.md).

## 1. Reduction to the centre component (PROVED)

Call a position **antisymmetric** if `ρ(A) = B`, which is the case after
White has mirrored every Blue move.

**Lemma 1.** An antisymmetric position `P` equals the value of the
connected live component containing `c`, which is `0` or `*`. If `c` is
dead, `P = 0`.

*Proof.* The live-component structure is `ρ`-invariant. A component `K`
not containing `c` either maps to a different component `ρ(K)`, and then
`K + ρ(K) = K + (−K) = 0` because `ρ` together with colour exchange maps `K`
onto `−K`; or it maps to itself with no fixed cell, and is then `0` by the
mirror lemma (bridge notes, 16:35). The component `C` of `c` is itself
antisymmetric, so `C ≅ −C` and `C ∈ {0, *}`. ∎

**Corollary.** Every Blue opening `v` adjacent to `c` is answered by the
mirror reply `ρ(v)`. The centre then has a Blue and a White neighbour, so it
is dead, and the position is `0`. This holds on **every** odd × odd board.

Checked numerically on 3×3, 3×5, 5×3, 3×7 and 5×5: all 23,885
antisymmetric positions have value `0` or `*`, and value equals the centre
component's value in every case. Tool: `antisym.cpp`.

## 2. Three natural general lemmas, all REFUTED

| Candidate | Result | Tool |
| --- | --- | --- |
| "An antisymmetric position is `*` iff `c` is live and isolated" | REFUTED. `*` with a non-isolated centre: 44 positions on 3×7, 296 on 5×5 | `antisym.cpp` |
| "The value is determined by the states of `c` and its four neighbours" | REFUTED. 11 of the neighbour patterns on 3×7, and 12 on 5×5, occur with both values. Distant stones matter; e.g. 3×7 `BwooowB/.ooooo./WbooobW` is `*` | `nbpattern.cpp` |
| "The mirror reply to any first move `v ≠ c` gives `0`" | REFUTED on 5×5: Blue `(1,1)` with White `(3,3)` is `*`, and likewise `(1,3)`/`(3,1)`. It holds for every opening on 3×5, 3×7 and 3×9 | `onepair.cpp` |

**Consequence.** The centre component's value is a *global* quantity. No
White strategy of the form "mirror, plus a controller that looks only near
the centre" can be proved correct by a local argument. A general odd × odd
proof via symmetry needs a different invariant, not a finite centre gadget.
Proposition 2.1 of GENERAL_IDEAS.md was the first sign of this.

## 3. Files

- `colcore_fast.hpp`: evaluator core copied from `../literature/col_fastval.cpp`.
- `antisym.cpp`: enumerates antisymmetric positions and checks Lemma 1.
- `nbpattern.cpp`: tallies value by the local pattern around the centre.
- `onepair.cpp`: value after one opening and its mirror reply.

Build any of them with `g++ -O2 -std=c++17 X.cpp -o X`; run with `./X H W`.
