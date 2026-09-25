# Lean proof: every empty 3 × n Col board is a second-player win

A complete Lean 4 formalisation of the all-width theorem, using only Lean's
core library (no Mathlib). The final statement uses the literal stone rules:

```lean
theorem Col.three_by_n_stones (n : Nat) :
    StoneLoses (board n) (fun _ => False) (fun _ => False)
```

With no stones on the empty `3 × n` board, the player to move loses,
whichever colour moves first.

## Build

```sh
cd proofs/lean
lake build        # about 20 s; needs the toolchain in lean-toolchain
```

Print the axioms of the final theorem:

```sh
printf 'import ColProof\n#print axioms Col.three_by_n_stones\n' > /tmp/Ax.lean
lake env lean /tmp/Ax.lean
```

## Trusted base

The Lean kernel checks every argument. The 14 certificate checks (28
`native_decide` calls: each certificate is accepted, and its root is in it)
are evaluated by compiled code, so the Lean compiler is also trusted. The only
other axioms are `propext`, `Classical.choice` and `Quot.sound`. There is no
`sorry`.

The certificates were found by exhaustive search (`gen/`), which is not
trusted: soundness rests on the checker in `Cert.lean`.

## Files

| File | Content |
| --- | --- |
| `ColProof/Game.lean` | Legality-set model, `Loses`, comparison principle, relabelling, sums |
| `ColProof/Cert.lean` | Bit encoding of `3 × w` positions, search-free checker, soundness |
| `ColProof/Data.lean` | Generated certificate data for 14 gadgets |
| `ColProof/Blocks.lean` | Seams, repeated bricks, and the window step |
| `ColProof/Main.lean` | Mirror strategy, reflections, `E4^k F1`, six cases, induction |
| `ColProof/Stones.lean` | The theorem for the stone rules of Col |
| `gen/` | Certificate generator (`python3 gen/emit_lean.py` rewrites `Data.lean`) |

## Relation to the written proof

The formal proof follows `../construction/empty_3xn_theorem.md`, but it
handles every inductive case as `E4^a · W · Ebar^b` (Case 6:
`H_c · W · Ebar^b`). The window `W` is the actual local position after Blue's
opening and White's reply, with White giving up only the seam cells that the
neighbouring ports require (see `gen/windows.py`). This removes the dyadic
bounds (`C3 ≤ 1/4`, opened `E4 ≤ -1`). Case 1 gets an explicit White reply,
and Case 5 uses a seven-column window. The step already holds at `n = 11`, so
the base cases are only the whole `3 × 3` and `3 × 7` boards.
