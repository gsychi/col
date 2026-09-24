# Bridge stream: progress log

Stream question: does every opening on an empty 5 × n board reduce to the
boundary families, and can 5 × 9 be certified?

Status labels: PROVED, CERTIFIED-FINITE, EVIDENCE, CONJECTURE, CONDITIONAL,
REFUTED (handoff §28).

## Log

- 2026-09-23 13:30 — Started. Read handoff §1–35, 3x15 package, round-2/3/4
  bridge notes (M_n, staircase, peeling, graph shortcuts, central controller).
- 13:45 — Wrote `src/colcgt.hpp` (exact number/number+star value engine with
  component splitting, symmetry + colour-swap canonical memo, growable table)
  and `src/colval.cpp`. Sanity: H_{3x3,3x5,3x7}=0, D_1=0, D_3=-1/2, 5x5=0.
- 13:55 — Wrote `src/decomp.cpp`: dynamic program over vertical column cuts
  with minimal White seam retirements and exact block values (EVIDENCE tool).
  - 5x5, blocks ≤ 4 wide: every opening with r+c odd has a reply + cut
    decomposition; every r+c even opening has none in this class.
  - 5x7, blocks ≤ 4 wide: every opening except (2,0) has at least one
    reply + decomposition (EVIDENCE until certified).
- 14:10 — Wrote `src/certgen.cpp` (DAG for T − q + s*) and `check_dag.py`
  (independent search-free checker, number + star options, rank descent).
  Test: D_3 ≤ −1/2 certificate (709 checkpoints) replays.
- 14:25 — Bulk-tile scan (EVIDENCE, exact engine values): no neutral 5×k tile,
  k = 1..5, that is all-shared except White retired at rows S_L of its first
  column and S_R of its last, has value ≤ 0 when S_L ∪ S_R = all five rows.
  So no single self-repeating neutral 5-row block exists at these widths,
  unlike E4 in 3 rows. This does not exclude alternating two-tile chains or
  tiles with interior retirements.
- 14:27 — 5x7 opening (2,0) with vertical blocks up to width 6: stopped at
  the 30-minute cap with no output. INCONCLUSIVE. The first 5x9 width-4 sweep
  never started (it was launched as a background job from a sandboxed shell
  and died). Next: add branch-and-bound pruning to `decomp`, and build an
  adaptive prover that expands a few actual Blue/White plies before
  decomposing, then rerun 5x9.

## Session 2 (5×9 certificate push), 2026-09-23 from 15:53

- 16:00 — Background jobs: launching with `nohup … &` from the tool shell dies
  when the call returns, even outside the sandbox. Working recipe:
  `/tmp/5x9/detach.py LOG cmd…` (Python `Popen(start_new_session=True)`).
- 16:10 — New certificate format `col-hybrid-v1` (one node = claim
  G(A,B)+q+s* ≤ 0 on its own box; justifications: arithmetic, expansion,
  comparison with retirements; children referenced through box isometries).
  Tools: `src/hybrid.hpp` (node store, canonical frames, local prover using
  exact values: components → comparison with exact child bounds, single
  component → expansion), `src/hylocal.cpp`, `src/hyboard.cpp` (whole-board
  adaptive prover: exact closure / vertical-cut DP closure / depth-limited
  expansion). Verifier: `proofs/5x9/verify.py` (stdlib, search-free).
  Test: full certificate for empty 5×5 ≤ 0 has 6,667 nodes, verifies in 0.4 s.
- 16:15 — decomp 5×9, blocks ≤ 4 wide, one White reply (EVIDENCE, seconds per
  opening): every opening with r+c odd has 21–26 closing replies; every
  opening with r+c even has none (same parity split as 5×5).
- 16:20 — CERTIFIED-FINITE (verify.py --file): odd openings (0,1), (0,3),
  (1,0), (1,2), (1,4), (2,1), (2,3), each after one White reply, 1.2k–2.0k
  nodes each (/tmp/5x9/odd/).
- 16:30 — Even openings, depth 1 (one more Blue/White round), blocks ≤ 4:
  all fail fast (e.g. (0,0): Blue's second move (0,2) has no reply with a
  closing ≤4-wide cut; best sum +1). Blocks ≤ 5, depth 0: (0,0) best sum
  +1/4 (replies (2,0), (2,2)). Blocks ≤ 6 (cap 28 live cells), (0,0)+(2,0):
  no closure (174 s). Diagnosis: even openings have little slack (5×5 even
  openings are −1/2 or −3/4, odd ones −2); every seam costs ≈ 1/2.
- 16:35 — Mirror lemma noted (PROVED, elementary): if σ is an involutive
  isometry of the box, A ⊆ σ(B) and no σ-fixed cell is White-legal, White
  wins moving second by answering v with σ(v). On 5×9 (180° rotation) the
  only fixed cell is the centre, so it cannot close a live-centre position.
