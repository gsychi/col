# Round five handoff: state of the odd × odd Col proof (2026-09-23)

Read this first. It records everything round five established, what is
still open, the tools that exist, and the operational lessons from running
parallel agents. Older context is in
[`../col_research_handoff.md`](../col_research_handoff.md) (conventions, the
3 × n proof, the five-row program through round four, obstructions) and
[`../round4_research_progress.md`](../round4_research_progress.md).

Target conjecture: every empty `m × n` Col board with `m, n` odd and `> 1`
has value `0` (second-player win). Labels: **PROVED** (written argument, all
finite inputs replayed by an independent search-free checker),
**CERTIFIED-FINITE** (specific sizes, certificate replayed), **EVIDENCE**
(solver output, not certified), **CONJECTURE**, **REFUTED**.

## 1. Status in one paragraph

Heights 1 and 3 are solved, and every board with an even side is solved. The
all-width 3 × n theorem is now fully machine-checked. Height 5 is open. The
five-row boundary-family program has every conjectured bound holding
wherever it has been computed, through width 7 to 9 depending on the
family, but three structural gaps remain: White-first strictness, the J
family's shrinking margin, and a bridge from empty boards. The 5 × 9 board
is 9/15 certified. Heights ≥ 7 have no approach. The literature (Uiterwijk
2021) lists odd × odd Col as open, and a web search found nothing later.

## 2. PROVED

### 2.1 Every empty 3 × n board is 0

- Statement and proof: [`../../empty_3xn_theorem.md`](../../empty_3xn_theorem.md).
  It was corrected on 2026-09-23 with the audit's nine text fixes, including
  a full proof of the comparison principle in its game-order form.
- Check it all with `python3 proofs/construction/three_row/verify.py`
  (stdlib, no search, about 10 s). Corruption tests:
  `python3 proofs/construction/three_row/negative_controls.py` (15/15
  rejected).
- Package: [`../../three_row/`](../../three_row/). It contains `manifest.json`
  (17 roles → exact roots and certificates), `PROOF_CHECKLIST.md` (why finite
  local checks plus the written induction cover all widths: 13 local windows
  all occur at n = 15, 25 seam types by n = 19) and `README.md`.
- The two missing gadgets were generated and verified in round five:
  - `T_middle1`: 3 × 6, Blue `253500`, White `130844`.
  - Repeatable `Z7`: 3 × 7, Blue `2097022`, White `2088828`, right port `101`.
    The old `Z7` (White `2097020`) is valid only at a physical right edge.

### 2.2 Col value structure (any graph, any shadow state)

The source is [`literature/COL_VALUES.md`](literature/COL_VALUES.md), with a
self-contained proof and an exhaustive check on 640,148 small states.

- **Every Col position is `x` or `x+*`** for a dyadic `x`. This covers every
  shadow state `(A, B)` including cells legal for neither player, every
  virtual region, all sums of these, and sums plus dyadic numbers and stars.
  It does not cover arbitrary auxiliary games such as `↓`. Cited: ONAG p. 93;
  Winning Ways vol. 1 pp. 47–48; Austin 1976 Thm 2.3.
- For `G = x + ε*`: `G < q ⟺ x < q`. Round four's paired target
  `T_q(G)` ("`G ≤ q` and `G + * ≤ q`") is **equivalent to `x < q`**. Star
  bookkeeping largely disappears.
- **Lemma 4 (option inequalities).** For `v ∈ A`, `G^{L,v} + * ≤ G`, and if
  `v ∉ B`, `G^{L,v} + 1 ≤ G`. For `v ∈ B`, `G ≤ G^{R,v} + *`, and if
  `v ∉ A`, `G ≤ G^{R,v} − 1`. So a move on a player's private cell costs
  that player at least 1.
- **Colour symmetry.** Every empty board is `0` or `*`. It is `*` iff some
  Blue opening equals `0` exactly. So the conjecture is equivalent to
  **"no opening has value exactly 0"**, and openings never have a positive
  number part.
- **Comparison principle** on arbitrary graphs (Lemma 2), plus explosive
  separator sets (`G = G − S`) and adjacent twins (ONAG p. 94).
- **Refuted:**
  - "If Blue wins moving first and has a shared cell, some shared-cell move
    wins" (2 × 3 `bob/.w.`).
  - "Making a White-only cell shared adds at most `1+*`" (1 × 5 `www..`; the
    maximum increment is `3/2`).

### 2.3 Other proved results from the theory stream

These are in [`literature/GENERAL_IDEAS.md`](literature/GENERAL_IDEAS.md).

- **Mirror strategy refuted on every odd × odd board with a side ≥ 5**
  (Prop. 2.1). Blue plays `(−1,−1)`, `(1,−1)`, `(0,2)` relative to the
  centre, White mirrors by half-turn, and the centre becomes an isolated
  live cell worth `*` with Blue to move. A central controller on a
  5-column window is untested; round three refuted windows of 3 columns.
- **Domino implication** (Prop. 3.2). If `D(v,u) = 1` for Blue at a
  majority cell `v` and White at an adjacent `u`, with the rest empty, then
  every minority opening is `≤ −2`.
- **Private-reserve reduction.** At a White-only cell `u`,
  `G ≤ G^{R,u} − 1`. Applied to `DD` (White-only cell `(2,0)`): if
  `K_n = DD_n` after White `(2,0)`, then `K_n ≤ 0` implies `DD_n ≤ −1`.
  This turns the **strict** White-first obligation into a **non-strict**
  bound, which the comparison principle produces directly. Evidence: tight
  for n ≤ 6 (`K_3 = K_5 = 0`); `K_7` is untested.
- **Linear tint potentials cannot work** (proof). **Static band peeling
  fails** as a height-lift bounding method.

## 3. CERTIFIED-FINITE: 5 × 9, 9 of 15 representative openings

Certificates are in [`../../../5x9/certificates/partial/`](../../../5x9/certificates/partial/),
with `SHA256SUMS`. Each proves the position after Blue's opening and White's
reply is a Blue-first loss. Check one with:

```sh
python3 proofs/5x9/verify.py --file proofs/5x9/certificates/partial/o22.json.gz --root pos
```

| Opening | White reply | Parity | Certificate nodes |
| --- | --- | --- | --- |
| (0,1) | (0,0) | minority | 1,967 |
| (0,3) | (0,0) | minority | 1,660 |
| (1,0) | (0,2) | minority | 1,654 |
| (1,2) | (0,0) | minority | 1,860 |
| (1,4) | (0,0) | minority | 1,203 |
| (2,1) | (0,0) | minority | 1,652 |
| (2,3) | (0,0) | minority | 1,858 |
| (1,3) | (2,4) | majority | 27,844 |
| (2,4) centre | (0,4) | majority | 4,386 |

Under the four reflections these cover **27 of the 45 openings**: all 22
minority cells, the 4 cells of the `(1,3)` class, and the centre.

**Remaining:** (0,0), (0,2), (0,4), (1,1), (2,0), (2,2), all majority.
- With blocks ≤ 5 and one expansion round, (0,4), (2,0) and (2,2) failed
  the first pass. In each, one specific second Blue move had no closing
  White answer at that depth; for (0,0), the best reply had score 1/4.
- (0,0), (0,2) and (1,1) were stopped mid-run. Each had a White reply with
  closure score 1.0 at its depth, meaning every Blue continuation was
  handled, but the certificate was not yet emitted.

Later attempts, all killed or failed:
- Short runs on (2,2) and (0,4) with other parameters failed within
  seconds (`/tmp/5x9/e3`, `e4`).
- The final batch ran `hyboard` (built as `/tmp/bridge/b59prove` from the
  current `bridge/src/hyboard.cpp`) with expansion depth 2, blocks ≤ 5 and a
  90-minute cap on (0,0), (0,2), (1,1), (2,0) and (2,2). It was stopped after
  about 5 minutes with no result.
- `bridge/PROGRESS.md` stops at 16:35, so these later runs are recorded
  only here.

**Reply scan, 2026-09-24 (EVIDENCE).** The prover `bridge/src/hy2.cpp` in
`scan` mode, run by the job pool `bridge/tools/pool.py`, fixes an opening
and a White reply, then tries to close every second Blue move. Results are
in `bridge/runs/scan_2026-09-24/SUMMARY.txt`. Best reply found per opening:

| Opening | Best White reply | Second Blue moves left open | Their best closure sums |
| --- | --- | --- | --- |
| (0,0) | (2,2) | 4 of 41 | (2,6) 0, (3,3) 0, (4,2) 0, (4,4) 1/2 |
| (0,4) | (2,4) | 5 of 40 | (2,2) 0, (2,6) 0, (4,2) 0, (4,6) 0, (4,4) 1/4 |
| (2,2) | (2,4) | 8 of 39 | five at 0, three at 1/4 |
| (2,0) | (0,0) | 13 of 40 | mostly 0 |

A sum of exactly 0 is one ply short: after that Blue move White must reply,
so the closure needs a strictly negative sum or another expansion round.
The open cases therefore look like one more level of expansion on a few
continuations, not a new idea. (0,2) and (1,1) were not scanned. The pool
was stopped by the user mid-run on 2026-09-24.

Still to do: finish these six, run `proofs/5x9/assemble.py` on all 15, then
`verify.py` (package mode) and `negative_controls.py`, and write
`PROOF.md`.

The certificate format is `col-hybrid-v1`: a DAG of whole-board Blue-to-move
checkpoints. Each is either **expanded** (every Blue move has a listed White
reply) or **closed** by a comparison partition into regions, each backed by
a local certificate or a numerical comparison. Tools: `bridge/src/hyboard.cpp`
(hybrid prover), `hybrid.hpp`, `hylocal.cpp`, `decomp.cpp` (column-cut
decomposition DP), `certgen.cpp`, `bridge/check_dag.py`.

## 4. EVIDENCE: exact values

### 4.1 Five-row boundary families

Computed with the `ground_truth` solvers. Widths 1–5 use `colval`; wider
widths use `colout*` bisection with a P-outcome at the value. Definitions and
masks are in [`ground_truth/DEFINITIONS.md`](ground_truth/DEFINITIONS.md),
cross-checked against every previously recorded value. Raw data is in
`ground_truth/values.json` and `ground_truth/runs/values.jsonl`; rows with
status `Error` there come from killed jobs and are not results.

| Family | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DD | 0 | 1 | −1 | 0 | −1 | 0 | −1 | | −1 |
| DU | −1/2 | 1/2 | −1 | 0 | −1 | 0 | −1 | | −1 |
| DV | 2 | 0 | 1 | 0 | 1 | 0 | 1 | 0 | |
| DR | 1 | −1/2 | 1/2 | −1/2 | 1/2 | −1/2 | | −1/2 | |
| DX | 1 | −1 | 1 | −1/2 | 1/2 | −1/4 | 1/2 | −1/4 | |
| DJ | −1/2+* | 1/2 | −3/4 | 1/2 | −5/8 | 0 | −1/2 | | ? |
| DT | 2 | 0 | 1 | 0 | 1 | 0 | 1 | | |
| D | 0 | 0 | −1/2 | 0 | −1/2 | 0 | −1/2 | | |
| U | −1/4 | 0 | −1/2 | 0 | −1/4 | 0 | −1/2 | | |
| V | 1 | 0 | 1 | 0 | 1 | 0 | 1 | | |
| X | 1 | * | 1/2 | 0 | 1/2 | 1/4 | 1/2 | | |
| R | 0 | * | 0 | 0 | 0 | 1/4 | 0 | | |
| J | * | 0 | 0 | 0 | * | 0 | 0 | | |
| XX | 1 | 1 | 1/2 | 1 | 5/8 | 1 | 1/2 | | |
| RX | 1/2+* | 1 | 1/2 | 1 | 1/2+* | 1 | 1/2 | | |
| VX | 1/2 | 2 | 0 | 3/2 | 1/2 | 3/2 | 1/2 | | |
| XU | 1 | −1/4 | 1 | −1/4 | 1/2 | −1/4 | 1/2 | | |
| XJ | 1 | * | 1/2 | 0 | 1/2 | 1/4 | 1/2 | | |
| M | | | −1 | | 0 | | −1 | | |

`M_n` is the empty 5 × n board after Blue `(2,(n−1)/2)` and White `(0,0)`,
with Blue to move. `DJ_9`: a 4-thread run testing `−3/8` finished 1 of 44
root children in 70 minutes before it was stopped (INCONCLUSIVE).

**Target verdicts.** Every target holds at every computed width. Each is a
condition on the number part `x`:

| Target | Widths computed | Margins |
| --- | --- | --- |
| `DU_k < 0`, odd k | 1–9 | −1/2 then −1 |
| `DV_k ≤ 1/2`, even k | 2–8 | always 0 |
| `DR_k ≤ −1/4`, even k | 2–8 | −1/2 |
| `DX_k < 0`, even k | 2–8 | −1, −1/2, −1/4, −1/4 |
| `DJ_k < −1/4`, odd k | 1–7 | margins 1/4, 1/2, 3/8, 1/4 |
| `DD_n < 0`, odd n ≥ 3 | 3–9 | −1 |
| `XX_k < 1`, `RX_k < 1`, `VX_k < 2`, odd k ≥ 3 | 3–7 | ≥ 3/8 |
| `M_n ≤ 0` | 3, 5, 7 | −1, 0, −1 |

### 4.2 Empty-board openings

Computed with `literature/col_fastval`. Minority means `r+c` odd from a
corner.

| Board | Majority openings | Minority openings |
| --- | --- | --- |
| 3×3 | (0,0) −1/2; (1,1) −1 | all −2 |
| 3×5 | (0,0), (0,2), (1,1): −1/2 | all −2 |
| 3×7 | (0,0), (0,2), (1,3): −1/2; (1,1) −1 | all −2 |
| 3×9 | (0,0), (0,2), (0,4), (1,1), (1,3): −1/2 | all −2 |
| 5×5 | (0,0), (0,2), (2,0), (2,2): −1/2; (1,1) −3/4 | all −2 |

The domino values `D(v,u) = ±1` hold for every adjacent pair on those five
boards. The empty 5 × 7 board did not finish in 30 minutes on one thread.

## 5. Observations that should shape the next attempt

1. **Checkerboard parity decides difficulty.** Minority openings are exactly
   `−2` everywhere computed, and close immediately. On 5 × 5, 5 × 7 and
   5 × 9, a single reply plus a split into blocks ≤ 4 wide works. Majority
   openings are only `−1/2` to `−1`. They never close without extra plies of
   play-out, and each comparison seam costs about 1/2. The 3-row proof has
   the same shape: its case 1 is the minority case.
2. **No repeating 5-row block exists.** No neutral 5 × k tile (k = 1–5)
   retired only at its end columns is `≤ 0`. A 5 × n proof cannot copy the
   `E4` tiling. It needs alternating blocks, interior retirements, or
   adaptive interfaces (handoff §23).
3. **The DX margin stopped halving.** `DX_8 = −1/4 = DX_6`, so the fear that
   X margins → 0 is not supported by current data.
4. **DJ is the most endangered target.** At odd widths it goes
   `−3/4, −5/8, −1/2`, rising by 1/8 per step. Continuing would give
   `DJ_11 = −1/4`, which breaks `DJ_k < −1/4` and the J case of the six-case
   `DD` reduction (`DJ_a + 1/2 + DJ_b`). This is a CONJECTURE either way.
5. **`M_7 = −1`** makes the coupled-corner route for central openings more
   viable than round four's `M_7 ≤ 0` suggested.
6. **The mirror strategy fails only at the centre.** Combined with "no
   opening equals 0", a proof organised around centre control is natural.
   Pure mirroring is refuted (§2.3).

## 6. What is still needed, in priority order

1. **Finish 5 × 9** (finite, near). Six majority openings remain (§3). This
   needs more search, not a new idea: deeper expansion, blocks up to 6,
   longer caps. Then assemble and package. Record the reply and
   decomposition patterns per opening class; they are the data for the
   symbolic bridge.
2. **White-first strictness for DD.** This is the main 5 × n blocker. The
   private-reserve route (§2.3) **survived its first test** on 2026-09-24
   (EVIDENCE, `white_first/`):
   - `K_1..K_9 = 1, 2, 0, 1, 0, 1, 0, 1, 0`, so `K_n ≤ 0` holds with
     equality at n = 3, 5, 7, 9, giving `DD_n ≤ −1` there.
   - Letter `K` is the `DD` end column after White `(2,0)`. Masks are in
     `white_first/wf_families.py`, self-tested against DD-after-(2,0) for
     n ≤ 12.
   - A survey of Blue openings in `K_7` (`white_first/runs/decomp_K7_*.txt`)
     finds many one-cut, no-reply splits with bounds −1, −1/2 or 0.
   - Values of the K-ended families it creates (`KU`, `KV*`, `KX*`, `KR*`,
     `R*D`, `X*D`, and others) are in `white_first/runs/values.jsonl`.

   Next steps: certify `K_3`, `K_5`, `K_7 ≤ 0`, then build the width-
   decreasing Blue-opening table for `K_n` with a dependency ledger. The
   stream was stopped before either was done.

   **Integer-bound discipline (2026-09-24,
   [`white_first/INTEGER_BOUNDS.md`](white_first/INTEGER_BOUNDS.md)).**
   - PROVED: a bound `G ≤ k` with `k` a nonnegative integer needs only
     Blue-first facts (Lemma A). Negative integer bounds follow from White
     private moves (Lemma 4(4)). Fractional or negative bounds are what
     force White-first witnesses, so an induction using only integer bounds
     has no White-first obligations at all.
   - EVIDENCE: the reserve move is worth exactly 1 (`KQ_n = DQ_n + 1`,
     widths 3–6), so `K_n ≤ 0 ⟺ DD_n ≤ −1`.
   - EVIDENCE: under integer rounding, 18 of 19 `K_7` opening classes close.
     Minority openings need no reply (sum −1); majority openings close after
     one reply (sum 0). The one failure is (1,3), beside the centre.
   - Next: crack (1,3), repeat on `K_9`, then iterate over the region
     families used until the set closes.
3. **The DJ question.** Settle `DJ_9` and, if possible, `DJ_11`; this needs
   a much faster solver. Or redesign the J case with width-dependent targets
   before investing in proving `DJ_k < −1/4`.
4. **X families at every opening.** These are now plain strict inequalities
   on number parts (§2.2). The round-four endpoint clauses and the forced
   new X-pairs (XU/XR, XV/XJ) remain the starting point.
5. **The 5 × n bridge.** Turn the 5 × 9 per-opening patterns into width-
   independent rules mapping openings to boundary families, using `M_n` for
   central openings.
6. **Domino lemma** (`D(v,u) = 1` for majority `v`). It would settle every
   minority opening on every odd × odd board. Test 5 × 7 and 3 × 11 first;
   each is a single position.
7. **General height.** There is no mechanism yet. Candidates: a central
   controller on a 5-column window, and dynamic or cross separators. See
   `GENERAL_IDEAS.md` §2 and §7.

## 7. Tools

| Tool | Location | What it does |
| --- | --- | --- |
| 3 × n verifier | `proofs/construction/three_row/verify.py` | Full 3 × n proof check |
| Plain certificate generator | `proofs/3x15/generate.cpp` | Blue-first-loss DAG, h·w < 32 |
| Independent DAG checker | `proofs/atlas/verify.py::verify_strategy` | Search-free replay |
| Exact values, small | `ground_truth/colval.cpp`, `literature/col_fastval.cpp` | Uses the x/x+* theorem; component splitting; width ≤ 5–6 |
| Exact values, large | `ground_truth/colout5.cpp` | Multithreaded bisection, TT best-move, symmetry dedupe, persistent component values (`-V`/`-W`), wall limit `-L` |
| Value sweeps | `ground_truth/sweep.py`, `launch.py` (detached launcher), `validate.py` | `validate.py` checks a solver against all recorded values |
| Family masks | `ground_truth/families.py`, `families_masks.json` | Exact (A, B) for every family and width |
| Comparison certificates | `ground_truth/colcert5.cpp`, `checkcert.cpp`, `verify_cert.py`; `bridge/src/certgen.cpp`, `bridge/check_dag.py` | Certificates for `G − q (+*)` and their checkers |
| 5 × 9 hybrid prover | `bridge/src/hyboard.cpp`, `hybrid.hpp`, `hylocal.cpp`, `decomp.cpp` | Expansion plus comparison closure |
| 5 × 9 package | `proofs/5x9/verify.py`, `assemble.py`, `negative_controls.py` | Package verifier (also `--file … --root pos`) |
| General CGT | `literature/cgt_core.py` | Canonical forms and Col on any graph |

Binaries were built into `/tmp/<stream>/`. Rebuild from source, since `/tmp`
does not persist.

## 8. Operational lessons

- **Background jobs die with a sandboxed parent shell.** Launch long runs
  with a double-fork or `setsid` launcher (`ground_truth/launch.py`) or with
  full permissions. Confirm the job started and check its log.
- **Wrong-threshold bisection steps dominate cost.** For `DX_8`, the `−1/8`
  test took 10.5 G nodes, while the correct threshold was cheap. Guess the
  right threshold from patterns first.
- **Search memory limits:** `decomp` aborts with "memo table full" on 5 × 9
  unless the table is enlarged.
- **zsh does not word-split `$var`;** use `${=var}` for argument lists.
- **Compute:** one 12-core, 18 GB machine. Seven agents at once was too many
  for large searches; two focused agents worked better.
- **Web search summaries hallucinated** "published 5×7/7×7 results". Verify
  against sources.
- **Stopping a subagent:** the `interrupt` option on resume was rejected as
  a string in this session. Kill its processes directly, or use the UI stop
  button.

## 9. Stream directories

| Directory | Contents |
| --- | --- |
| [`../../three_row/`](../../three_row/) | Complete 3 × n verification package |
| [`literature/`](literature/) | `LITERATURE.md`, `COL_VALUES.md`, `GENERAL_IDEAS.md`, code and runs |
| [`ground_truth/`](ground_truth/) | Definitions, solvers, value tables, `PROGRESS.md` |
| [`bridge/`](bridge/) | 5 × 9 research tools and `PROGRESS.md` |
| [`../../../5x9/`](../../../5x9/) | 5 × 9 package, partial (9/15 openings) |
| `aux_families/`, `x_families/` | Early value tools only; stopped before any results |
| `white_first/` | `K`-family tools (`wf_families.py`, `tabulate.py`, `decomp.py`, `survey.py`), values, and the `K_7` opening survey; `PROGRESS.md` |
