# Reusing a checkpoint certifies 3x19

The weighted experiment found a useful internal state in the economical bulk certificate. Extracting its reachable response DAG produces one ordinary 3x4 tile with Blue mask 1843, White mask 1825, 17 checkpoints, and 35 response edges. Its certified upper bound is zero.

**Attribution:** The same state was already present in the original library, in two reflected forms. The gain comes from exposing internal checkpoints as reusable tile roots. Positive-tile compensation and new exhaustive search are unnecessary for this 3x19 proof.

For the formerly missing Blue opening at row 1, column 7, White replies at cell 8 (row 0, column 8), zero-based. The remaining board has a compatible partition of widths 7 + 4 + 4 + 4. Every tile gives a Blue-first loss.

| Board | Certificate result | Covered opening assemblies | Uncovered cells | Replay games |
|---|---|---:|---|---:|
| 3x19 | loss | 57 | [] | 342 |
| 3x23 | unknown | 68 | [34] | 0 |
| 3x27 | unknown | 79 | [38, 42] | 0 |
| 3x31 | unknown | 90 | [42, 46, 50] | 0 |
| 3x101 | loss | Direct tiling | [] | 1818 |

`loss` means the initial player loses: empty 3x19 is a second-player win. Both the Rust checker (using engine legality transitions) and the independent Python set-based checker validate every local edge and every opening assembly. Replay covers every initial cell, three continuations per cell, and both color orientations. Sampled replay supplements the complete certificate checks.

The added safe tile closes all 57 openings on 3x19. Larger 4k+3 boards still have gaps: 3x23 at (1,11), 3x27 at (1,11)/(1,15), and 3x31 at (1,11)/(1,15)/(1,19). These are finite results, not an all-width proof.

Production defaults remain unchanged. The augmented 26-tile library and standalone executable strategy artifacts are preserved here. Unlike general weighted bounds, this extracted grid-only strategy works with the existing replay player.

Reproduce after running the weighted benchmark:

```sh
python3 scripts/checkpoint_tiling_probe.py
./col-cert --m 3 --n 19 --proof-library reports/weighted-tiling/checkpoint-library --proof-out /tmp/3x19.json
./col-cert verify /tmp/3x19.json
./col-cert verify-python /tmp/3x19.json
./col-cert replay /tmp/3x19.json --moves 26
```

Provenance, local checkpoint counts, full verifier output, timing, and replay counts: [checkpoint-probe.json](checkpoint-probe.json). Full board proof: [3x19.json](3x19.json).
