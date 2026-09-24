# Round five: parallel work streams toward odd × odd Col

Started 2026-09-23. **Start with [`HANDOFF.md`](HANDOFF.md)**. It records
every result, the open problems in priority order, the tools, and the
operational lessons.

Target: every empty `m × n` board with `m, n` odd and `> 1` has value zero.
The all-width `3 × n` theorem is proved and fully machine-checked; height
five is the active frontier.

| Directory | Stream | Outcome |
| --- | --- | --- |
| [`../../three_row/`](../../three_row/) | 3 × n audit package | Done: one command checks the whole 3 × n proof |
| [`literature/`](literature/) | Literature and theory | Done: Col values are `x` or `x+*` on any graph, with consequences; ranked general ideas |
| [`ground_truth/`](ground_truth/) | Five-row exact values | Families through widths 7–9; every target holds; `DJ_9` inconclusive |
| [`bridge/`](bridge/) and [`../../../5x9/`](../../../5x9/) | 5 × 9 certificate | 9 of 15 representative openings certified (27 of 45 openings) |
| [`aux_families/`](aux_families/) | DU, DV, DR, DJ induction | Stopped early; tools only |
| [`x_families/`](x_families/) | DX and paired RX, VX, XX | Stopped early; tools only |
| [`white_first/`](white_first/) | White-first DD strictness | Stopped before starting |

Claims in every stream are labelled PROVED, CERTIFIED-FINITE, EVIDENCE,
CONJECTURE, or REFUTED, following section 28 of the
[research handoff](../col_research_handoff.md).
