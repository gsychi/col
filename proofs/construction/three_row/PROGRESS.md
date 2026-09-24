# Stream progress: 3 × n verification package

Stream directory: `proofs/construction/three_row/` (only directory written).

## Log

### 2026-09-23 13:30 — orientation
- Read `empty_3xn_theorem.md`, `five_row_certificate_provenance.md`,
  handoff §1–5 and §28–29, `proofs/3x15/{PROOF.md,verify.py}`,
  `proofs/atlas/verify.py`, `number_certificates.py`, `provenance_check.py`,
  `original_proof/manifest.json`, the n = 3, 7, 11 records of
  `existing_library_scan.json`, and `incoming/check.py`.
- `incoming/SHA256SUMS` re-checked: all three files OK.
- `incoming/z7old.json.gz` is node-for-node identical (same JSON) to
  `original_proof/certificates/tile_76ba798e4bc4.json.gz`; the package uses one
  copy for the physical-right-edge Z7 role.
- Hand-decoded every gadget root from the theorem's case geometry; all roles
  listed in the task match the stated local moves and seams (details go into
  `manifest.json` and `PROOF_CHECKLIST.md`).

### 13:32 — certificates copied
- 18 ordinary files, 10 numerical files and the base-witness JSON copied
  byte-for-byte (`cmp` against sources) into `certificates/`.

### 13:45 — verifier green
- `verify.py` (stdlib only, no search) passes: 21 ordinary DAGs (18 files +
  3 reflections; 20,575 checkpoints, 82,899 edges), 12 dyadic DAGs (10 files
  + 2 reflections; 1,064 checkpoints, 3,130 edges), 17 roles, bases 3/7/11,
  6,651 assemblies over widths 1..203 (≈10 s). Also green to width 403.
- Finding: normalized openings have row 0 or 1, so case 1 only ever needs the
  four opened-E4 bounds (0,1), (0,3), (1,0), (1,2). The row-2 bounds are
  supplied anyway (vertical reflections, replayed in full) and exercised by
  an un-normalized row-2 check.
- Finding: every local window appears already at n = 15; every seam type by
  n = 19 (E4|K_outer4 needs a ≥ 1, first at n = 19).
- Diagnostic: the six cases fail at n = 7 for (1,1), (1,3) and at n = 11 for
  (1,5); the stored bases are essential, and the step correctly starts at 15.

### 13:55 — negative controls
- `negative_controls.py`: 15/15 corruptions rejected for the expected reason
  (old Z7 before E4bar, wrong replies in cases 3 and 6, flipped port, flipped
  mask bit, left-port-111 K_outer4 after E4, corrupted reply, byte flip,
  tampered reflection, missing odd-cell bound, wrong-direction numeric
  certificate, weakened cap, case 5 at k = 2, missing 3x11 base, dropped base
  answer).

### 14:20 — documentation and final run
- `PROOF_CHECKLIST.md`: comparison principle with a proof of the game-order
  form (needed by case 1), locality lemma, per-case symbolic tables (layout,
  width arithmetic, parameter bounds, window, seams, bookkeeping), coverage,
  induction, and why the sweep is a regression test.
- `README.md`: role table, findings, discrepancies D1–D9 with exact
  replacement text for `empty_3xn_theorem.md` (not edited), controls, limits.
- Final run: `verify.py` VERIFIED (≈10 s), negative controls 15/15,
  `shasum -c` 34/34 OK. No files written outside this directory; scratch in
  `/tmp/three_row/` removed.

## Status
Complete. No mathematical gap found in the six-case induction; all roles bound.
