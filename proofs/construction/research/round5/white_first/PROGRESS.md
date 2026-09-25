# White-first stream: progress log

## 2026-09-23 (session 1, earlier agent)

Tooling (discovery only, scratch in /tmp/white_first): an exact-value solver
(`colsolve.cpp`) that folds small components into number+star offsets and
checks the number-or-number-plus-star form at every node. It reproduces the
handoff values DD_7=-1, DX_2,4,6=-1,-1/2,-1/4, DR_2=DR_4=-1/2.

EVIDENCE (discovery values, not yet certified):

- DD_3 = DD_5 = DD_7 = -1. One-ended D_k (neutral far end): 0,0,-1/2,0,-1/2,0,-1/2 for k=1..7.
- White first moves in DD_n (row,col), child value:

| n | winning (child = 0) | losing (child value) |
| --- | --- | --- |
| 3 | (0,0),(1,1),(2,0) | (0,1)=3/2, (2,1)=2 |
| 5 | (0,0),(0,2),(1,1),(2,0),(2,2) | (0,1)=3/2,(1,2)=3/2,(2,1)=2 |
| 7 | (0,0),(0,2),(1,1),(1,3),(2,0),(2,2) | (0,1)=3/2,(1,2)=3/2,(0,3)=1,(2,1)=2,(2,3)=2 |

## 2026-09-24 (session 2, this agent)

- 10:50 Read HANDOFF, COL_VALUES, GENERAL_IDEAS §3–4, five_row_boundary_induction,
  col_research_handoff §7–13, ground_truth tools. Rebuilt colout5, colcert5,
  checkcert, colval into /tmp/white_first from ground_truth sources.
- 10:55 `wf_families.py`: masks incl. new letter K (self-test: KD_n equals
  DD_n after White (2,0) for n = 1..12; all other letters agree with
  ground_truth/families.py).
- 10:57 **K_n values (EVIDENCE, colval n ≤ 5, colout5 n ≥ 6, P-outcome at value):**
  K_1..K_9 = 1, 2, 0, 1, 0, 1, **0**, 1, **0**.
  K_7 = 0 (1 s), K_8 = 1 (20 s), K_9 = 0 (392 s, 4 threads).
  So `K_n ≤ 0` holds at n = 3, 5, 7, 9 (tight: equality each time).
  Route alive. Next: certificates for K_3, K_5, K_7 (Blue-first loss at 0),
  then Blue-opening case table for K_n.

## 2026-09-24 (parent agent, direct)

- 12:20 Lemma A (PROVED): `G ≤ k`, k ≥ 0 integer, is Blue-first; fractional or
  negative bounds are what force White-first witnesses. Negative integers
  come from reserve moves (Lemma 4(4)). See INTEGER_BOUNDS.md.
- 12:22 Reserve move worth exactly 1: KQ_n − DQ_n = 1 for Q ∈ DUVXRJ,
  widths 3–6 (EVIDENCE). So K_n ≤ 0 ⟺ DD_n ≤ −1.
- 12:40 `int_reply_test.py 7`: 18/19 K_7 opening classes close under integer
  bounds with ≤ 2 seams (10 no-reply at −1, 8 after one reply at 0). (1,3)
  fails for all 9 winning replies (best +1). runs/int_reply_K7*.
