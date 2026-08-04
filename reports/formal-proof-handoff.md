# Formal Proof Handoff

Status: **NOT PROVED**

This gate intentionally distinguishes finite computational evidence from an all-width theorem. It exits successfully only after every finite certificate replays, the frontier family closes, width 13 is covered, and a symbolic two-column extension certificate exists.

| Obligation | Passed | Evidence |
|---|---:|---|
| Transition replay | True | `invalid=0` |
| Frontier response closure | True | `open=0` |
| Held-out width prediction | False | `held_out={'width': 9, 'frontiers': 471, 'seen_at_smaller_width': 394, 'novel_count': 77}` |
| Local CGT recurrences | True | `errors=0` |
| Opening reduction through width 13 | True | `widths=[3, 5, 7, 9, 11, 13]` |
| Evidence reaches width 13 | False | `widths={'5': 204, '7': 3279, '9': 40783}` |
| Symbolic two-column extension | False | `no generated certificate currently quantifies over arbitrary neutral middle length` |

## Formalization order

1. Define legal-mask shadow states and prove stone histories with the same masks have identical options.
2. Prove termination by strict decrease of the union of legal masks.
3. Prove disconnected live components form a disjunctive sum.
4. Import and check the finite local CGT option recurrences.
5. Import and replay the frontier response table.
6. Prove the symbolic `n → n+2` extension and conclude all odd `3×n` by induction.

The generated JSON files are explicit audit artifacts. They are not treated as axioms: an eventual Lean development should parse or regenerate them and use finite decision procedures for steps 4 and 5.
