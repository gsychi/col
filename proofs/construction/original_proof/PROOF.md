# A computer-assisted proof for the empty 3 × 15 Col board

> **Scope note:** This is the original finite `3 × 15` certificate proof and
> remains useful as a standalone replayable artifact. Its statement that the
> general `4k+3` family is unsettled is historical; the later all-width
> induction is recorded in
> [`../empty_3xn_theorem.md`](../empty_3xn_theorem.md).

## 1. Statement and conventions

**Theorem.** Under normal-play Col rules, the empty 3 × 15 grid is a
second-player win. Equivalently, its normal-play combinatorial-game value is
zero.

The proof below is independent of any previous partial production search.
It consists of a mathematical composition lemma, a finite opening case table,
and independently checked local strategy DAGs.

Rows are numbered 0, 1, 2, columns 0 through 14, and cell `(r,c)` has index
`15*r+c`. Blue moves first. White is the second player. A player may occupy an
unoccupied cell only if none of its adjacent cells contains that player's own
stone. Orthogonal grid adjacency is used. A player with no legal move loses.

For a shadow position, `A` is Blue's legal set and `B` White's legal set. Its
transition rules are exactly:

- Blue at `v`: `(A \ ({v} ∪ N(v)), B \ {v})`.
- White at `v`: `(A \ {v}, B \ ({v} ∪ N(v)))`.

All legal sets shrink. A cell illegal now cannot become legal later.

Shadow notation used below:

```text
o : legal for both players
b : Blue-only
w : White-only
. : legal for neither
```

These are legal-move symbols, not placed-stone symbols.

## 2. Local second-player certificates

A local certificate is a finite set of Blue-to-move checkpoints `(A,B)`.
For each checkpoint it lists one White response for **each** legal Blue move,
in ascending cell order. The two moves must lead to another checkpoint in
the certificate. A checkpoint with no Blue moves has no listed responses.

The checker verifies legality and closure, and checks that the number of
live cells `|A ∪ B|` decreases by at least two along every such two-ply edge.

**Local certificate lemma.** Every checkpoint in a valid certificate is
Blue-first losing.

**Proof.** Induct on `|A ∪ B|`. If Blue has no move, Blue loses. Otherwise,
whatever Blue plays, the listed legal White response reaches a checkpoint
with fewer live cells. Induction supplies White's remaining strategy. This
proves the statement for every possible Blue continuation, not merely one
sampled play. ∎

No guessed numerical game value, empirical periodicity, or unexplored search
branch is used by this lemma.

## 3. One-sided relaxation and composition

Let an actual Blue-to-move position have legal sets `(A,B)`. Choose disjoint
rectangular blocks and local virtual legal sets `(A_i,B_i)`. Map each local
cell back to its location on the actual board, and write their unions as
`A*` and `B*`.

Suppose:

1. `A ⊆ A*`: the virtual position does not remove any actual Blue move.
2. `B* ⊆ B`: the virtual position gives White no unavailable move.
3. For each grid edge crossing between different blocks, its two endpoints
   are **not both in B***.
4. Each local root `(A_i,B_i)` has a valid Blue-first-losing certificate.

Uncovered cells have neither virtual legality and cannot contain an actual
Blue legal move under condition 1.

**One-sided tiling lemma.** Under these four conditions, White wins the actual
position when Blue is to move.

**Proof.** White commits to using only `B*`. Since legal sets only shrink,
condition 3 ensures that White never has a relevant same-color adjacency
between blocks. Thus deleting all cross-block edges cannot free any White
move that would be blocked by another block.

Deleting cross-block edges can only remove restrictions on Blue. Likewise,
condition 1 may give virtual Blue additional moves. Therefore every actual
Blue move can be simulated in its corresponding virtual block. More
formally, after every pair of actual and virtual moves, actual Blue legality
remains contained in virtual Blue legality, and virtual White legality
remains contained in actual White legality.

Whenever Blue moves in block `i`, White uses that block's certified response.
The response is legal on the actual board: it is locally legal, available
under condition 2 and its preserved inclusion, and cannot conflict with
White stones across a block boundary. All other virtual blocks remain at
Blue checkpoints; the played block reaches another Blue checkpoint.

Each round consumes at least two live cells. Eventually Blue has no legal
move. White never fails to provide an answer beforehand. ∎

**Important distinction.** We are not claiming arbitrary edge deletion
preserves Col value. We delete only edges that, after White's voluntary
restrictions, can constrain Blue alone. This is a relaxation in Blue's favor,
and White still wins it.

## 4. The complete 16-case first-response table

The transformations `(r,c) -> (2-r,c)` and `(r,c) -> (r,14-c)` preserve the
empty board and the rules without changing player colors. Every first Blue
move is equivalent to exactly one representative with row 0 or 1 and column
0 through 7.

For each representative, White makes the following move. Coordinates are
zero-based. For nonrepresentative openings, apply the same reflection to the
listed response and all subsequent tile moves.

| Blue first | White response | White cell | Virtual block widths |
| --- | --- | ---: | --- |
| (0,0) | (2,2) | 32 | 3 + 4 + 4 + 4 |
| (0,1) | (1,2) | 17 | 3 + 4 + 4 + 4 |
| (0,2) | (0,4) | 4 | 7 + 4 + 4 |
| (0,3) | (0,5) | 5 | 7 + 4 + 4 |
| (0,4) | (2,6) | 36 | 7 + 4 + 4 |
| (0,5) | (1,4) | 19 | 4 + 3 + 4 + 4 |
| (0,6) | (2,4) | 34 | 4 + 7 + 4 |
| (0,7) | (2,7) | 37 | 4 + 7 + 4 |
| (1,0) | (0,1) | 1 | 3 + 4 + 4 + 4 |
| (1,1) | (0,2) | 2 | 3 + 4 + 4 + 4 |
| (1,2) | (0,0) | 0 | 3 + 4 + 4 + 4 |
| (1,3) | (0,4) | 4 | 7 + 4 + 4 |
| (1,4) | (0,5) | 5 | 4 + 3 + 4 + 4 |
| (1,5) | (0,0) | 0 | 7 + 4 + 4 |
| (1,6) | (0,5) | 5 | 4 + 3 + 4 + 4 |
| (1,7) | (0,8) | 8 | 7 + dead column + 7 |

`manifest.json` specifies every block's location and exact two legality
masks. For each case, `verify.py` independently reconstructs the actual
position after the opening and response and checks all four conditions of
the one-sided tiling lemma. It then checks that the 16 representative orbits
cover all 45 cells.

The root proof uses 22 distinct local certificates, with 22,357 checkpoints
and 91,623 Blue-move/White-response edges. Their largest board is 3 × 7.

Thus, for **every** possible first Blue move, White has a legal response
leaving a position in which every subsequent Blue move has a legal
certified White answer. This proves the theorem. ∎

### The center case in particular

After Blue at `(1,7)`, White plays `(0,8)` and never uses `(0,7)` or `(2,7)`.
Those two cells are already Blue-illegal because of Blue's middle stone;
retiring them makes the entire central column unavailable in the virtual
position.

Before White's response, the right seven-column block is

```text
ooooooo
woooooo
ooooooo
```

and the left block is its left-right reflection. The checked strategy for
the left block is Blue-first losing. White's move at the top-left of the
right block produces another checked Blue-first-losing root. The two blocks
are now independent, so White answers inside whichever block Blue chooses.

## 5. The formerly blocked three-stone position

This provides a much smaller standalone certificate for the precise state
that had stalled the production search:

```text
Blue stones:  0, 14
White stones: 44
White to move
```

**White plays cell 12**, the top-row cell in column 12.

White subsequently declines to use the following cells:

```text
3, 7, 11, 19, 23, 27, 33, 37, 41.
```

Some are already White-illegal; listing them again does no harm.

Cut between columns 3/4, 7/8, and 11/12. At each cut, White has retired the
top and bottom cells immediately to the left and the middle cell immediately
to the right. Consequently, every crossing edge has a White-forbidden
endpoint. The last column, column 14, is already dead for both players.

The four virtual blocks, from left to right, are exactly:

```text
 A4      E4      E4     B2
.wob    ooob    ooob    ..
wooo    booo    booo    bo
ooob    ooob    ooob    ob
```

Each tile is Blue-first losing. Their local roots and complete certificate
sizes are:

| Tile | Width | Blue mask | White mask | Checkpoints | Response edges |
| --- | ---: | ---: | ---: | ---: | ---: |
| A4 | 4 | 4076 | 2038 | 59 | 157 |
| E4 | 4 | 4095 | 2023 | 152 | 470 |
| B2 | 2 | 60 | 24 | 4 | 6 |

Masks are zero-based row-major within the individual tile.

There are only **215 distinct checkpoints and 633 response edges** across
these three lemmas. E4 is used twice but its certificate is stored once.

Apply the one-sided tiling lemma. White answers in the same block as Blue;
therefore Blue loses the post-12 position. Hence White wins the original
three-stone position.

This is not the four-corner response at cell 30, and it does not assume the
false hypothesis that the four-corner Q15 position has value zero.

## 6. A parameterized consequence for the blocked-state family

**Theorem.** For `n = 4k+3`, `k >= 1`, consider the 3 × n position with Blue
stones at the two top corners and a White stone at the bottom-right corner.
With White to move, White has a winning strategy.

**Proof.** White plays `(0,n-3)`. This is unoccupied and not adjacent to the
existing White stone. Partition the first `n-1` columns as

```text
A4 + (k-1 copies of E4) + B2.
```

At each internal cut, White retires the outer two cells on the left and the
middle cell on the right. The final physical column is dead: its top and
bottom cells are occupied, and its middle cell is blocked for Blue by the
top Blue corner and for White by the bottom White corner.

The left boundary, every repeated interior block, and the final two-column
block have exactly the three shadow patterns displayed above. The local
boundary rule removes every White cross-block interaction independently of
how many interior blocks there are.

The three finite certificates and the one-sided tiling lemma therefore give
a winning strategy for every `k >= 1`. ∎

This is a genuine parametric conclusion, not a claim of periodicity inferred
from finitely many widths: the repeated block is structurally identical for
every `k`, and the proof describes the legal strategy explicitly.

## 7. A parameterized consequence for empty strips

The one-column tile F1 is also Blue-first losing:

```text
o
b
o
```

Its masks are Blue `7`, White `5`, with three checkpoints and three response
edges.

**Theorem.** Every empty 3 × (4k+1) Col board, `k >= 0`, is a second-player win.

**Proof.** Divide the board into `k` copies of E4 followed by F1. Blue retains
every cell as a legal opening; White voluntarily avoids the `b` cells in
these tiles. At every internal boundary, E4 forbids White on the outer cells
of the left boundary endpoint, and the next tile forbids White on its middle
left endpoint. Thus no cross-block edge has two White-legal endpoints.

All tiles have certified Blue-first-losing strategies. Apply the one-sided
tiling lemma from the empty Blue-to-move board. When `k=0`, F1 alone proves
the 3 × 1 case. ∎

This theorem does not settle the empty 3 × (4k+3) family in general. The
3 × 15 result above is separately covered by all 16 opening cases.

## 8. What is checked, and what is not claimed

The supplied Python verifier uses only integer sets, grid neighborhoods,
JSON, gzip, and checksums. It validates every local branch, not a probabilistic
sample. It does not call the minimax generator. Certificate root masks are
not merely accepted as a claim: their complete response graphs are checked.

The C++ generator can be rerun independently; its role is to find finite
strategies, not to serve as a trusted oracle in the proof. The tests also
exercise corruption rejection and legal play on the actual 45-cell board.

The finite proof has **not** been translated into a proof assistant and has
not undergone external peer review. It is a discrete, reproducible,
computer-assisted strategy proof with a small independently written checker.

No theorem for every odd-by-odd rectangle is claimed. No upper bound on the
production solver's unmodified full-search runtime is inferred from this
certificate's checking time.
