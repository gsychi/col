# Beyond end-caps: construction research for Col

Research date: September 5, 2026.

This packet separates previously verified results, new certificate-checked local results, new parametric deductions, and proposed research directions. It does not claim the general odd-rectangle theorem.

## 1. Starting point

The supplied `col_3x15_proof` package was extracted and its original `verify.py` rerun successfully: all 45 openings are covered by its 16 representatives and 25 local certificates. Its existing one-sided tiling lemma is the foundation, not the earlier speculative symmetry or separator identities.

Use `o` for both players legal, `b` for Blue-only, `w` for White-only, and `.` for neither. These are legality states, not stones. Positive game values favor Blue; negative values favor White. Blue-to-move losing means G <= 0, not necessarily G = 0.

A physical outer boundary needs no neighboring tile. Interface compatibility is required only where two tiles actually touch; a nonzero outgoing boundary mask is not intrinsically a nonaccepting terminal state.

## 2. Newly checked local facts

The new file `number_certificates.py` generates finite strategy certificates for a grid game plus a canonical dyadic number, and checks them without minimax. The checker uses coordinate sets for grid updates. It checks every move of the first player, the legality of the stored reply, closure, and a decreasing rank. Exact equality to q is established by verifying that G-q and its conjugate are both first-player losses.

### 2.1 The strongest compatible three-column right cap is +1/4

Let C3 be:

```
ooo
boo
ooo
```

Blue is legal on every square. White is forbidden only at the middle cell of the left column. Its masks are Blue 511, White 503.

The checked comparisons establish:

    C3 = 1/4.

The two certificates for C3 - 1/4 and its conjugate contain 85 and 98 checkpoints, respectively. This is not inferred from sampled play or assumed numberness.

Why this cap matters: the old E4 tile has White legal only in the middle row at its right boundary. Therefore the next tile must forbid White at the middle-left square. C3 grants White every other square, so it is the most favorable possible cap under this particular boundary condition, while preserving all of Blue's empty-board moves.

Consequently, **no further White-only restriction can turn this same three-column terminal construction into a Blue-first loss**. Any such restriction only improves Blue's position relative to C3. One must change the interface, give the cap a Blue-legality defect, compensate it elsewhere, or coordinate play across the interface.

This is a no-go result for one construction class, not for empty boards of width 4k+3.

### 2.2 An alternative zero connector

The following J4 tile has exact value zero:

```
oooo
boob
oooo
```

Its masks are Blue 4095, White 3951. The checked comparisons against zero cover both starting players.

Using bits 0 and 2 for the two outer rows, its left and right White masks are both 101. Compare:

- E4: left 101, right 010.
- The left-right reflection of E4: left 010, right 101.
- J4: left 101, right 101.
- F1: left 101, right 101, but width 1 instead of 4.

Thus tiles have roles beyond "bulk" and "end-cap": J4 and F1 can act as changes between two repeating interface patterns.

### 2.3 The bulk permits another permanent White restriction

The following tile also has exact value zero:

```
ooob
bobo
ooob
```

Masks: Blue 4095, White 1959. It uses a subset of the old E4 White cells while retaining value zero. Its outer ports are unchanged, so this alone does not add a new vertical-interface transition. It is evidence that a library should keep useful minimal White-support strategies, rather than only one generous legal mask.

### 2.4 A real negative budget from a Blue opening

The original E4 is:

```
ooob
booo
ooob
```

It has exact value zero. If Blue plays its top-row, column-1 square, the resulting local shadow is:

```
...b
bwoo
ooob
```

Masks: Blue 4056, White 2021. The checked value is exactly -1.

In fact, each of the six E4 cells with local row+column odd has a post-Blue value of -1. Four local comparisons, plus top-bottom reflection, cover them all. The comparisons are included in this packet.

Therefore a -1 opened block can compensate a +1/4 cap:

    -1 + 1/4 = -3/4 < 0.

This demonstrates why requiring every tile independently to be Blue-first losing is unnecessarily restrictive after an opening.

### 2.5 The naive five-row extrusion fails

Simply extending the E4 alternating restriction pattern vertically gives:

```
ooob
booo
ooob
booo
ooob
```

On this restricted 5x4 board, **Blue wins by playing cell 8**, i.e. row 2, column 0 in zero-based row-major coordinates. A checked White-first-losing certificate for the child contains 541 checkpoints and 1,830 reply edges.

This does not say the empty 5x4 board is a first-player win. It says these particular voluntary White restrictions destroy its second-player strategy. Height lifting needs its own interfaces and local certificates.

## 3. A general weighted composition theorem

The original one-sided construction uses virtual blocks with:

    actual Blue legality ⊆ virtual Blue legality,
    virtual White legality ⊆ actual White legality,

and no cross-block edge with two White-legal endpoints.

The simulation proof works with an arbitrary extra disjoint game present as well. Thus it gives game-order domination:

    G_actual <= sum_i T_i.

Suppose each tile has a certified numerical upper bound T_i <= u_i. Then:

    G_actual <= sum_i u_i.

Consequences:

- If sum_i u_i <= 0, Blue loses when Blue is next.
- If sum_i u_i < 0, White wins with either starting player.

The bound does not require each T_i to be a number: a correctly certified numeric upper bound is sufficient. A win/loss bit alone is not an exact numeric value. Fuzzy games must not be silently treated as numbers.

For a fixed-height strip and a fixed finite tile library, construction search becomes a minimum-cost path problem. A state is a column position plus the outgoing White boundary mask. A tile may attach when incoming_mask & tile_left_mask == 0; it advances by its width, outputs its right mask, and adds its bound to the path cost. At an identical interface and position, the smaller accumulated numeric upper bound dominates the larger one.

This generalizes the existing Boolean tiling DP to a weighted DP. Its finite interface state is a property of the certified construction class, not a proof that arbitrary Col games have finite-state summaries.

## 4. New parametric opening result: every odd three-row strip

### Theorem

Let n be positive and odd. On the empty 3xn board, place one Blue stone at (r,c) with r+c odd. The resulting game is strictly negative: White wins regardless of which player moves next.

This proves a family of one-stone positions, not the entire empty odd-strip conjecture.

### Proof for n = 4k+1

Use k copies of E4 followed by F1. If the opening lies in an E4 block, its local parity is odd, so that block becomes -1. All other E4 blocks and F1 have value zero. If it lies in F1, odd parity forces the middle square; its residual game consists of two White-only isolated cells, with value -2.

Cross-block White compatibility is unchanged or improved by Blue occupying a cell. Cross-block effects on Blue are ignored only in the virtual position, making Blue stronger. Therefore the actual position is at most -1, or at most -2 in the F1 case, and is strictly negative.

### Proof for n = 4k+3, k >= 1

Use k E4 blocks followed by C3. Choose this layout or its horizontal reflection so that the Blue opening does not lie in the three-column cap. This is always possible for n >= 7, because the leftmost and rightmost three-column caps are disjoint.

An odd-width horizontal reflection preserves row+column parity. Thus the opened E4 block again has value -1, the other E4 blocks have value zero, and C3 contributes +1/4. The total virtual game is -3/4, so the actual game is strictly negative.

### Small cases

For n=1, the only odd-parity opening is the middle of a three-cell path, leaving two White-only moves. For n=3, all odd-parity openings are edge-middle squares of the 3x3 square. Their one-stone games are exactly -2; the two numerical comparison certificates for a representative are included.

This completes the parameterized construction.

`minority_openings.py` additionally checks 3,876 concrete embeddings for all odd widths through 101. This is an implementation test. The unbounded result follows from the repeated-block proof above, not from the finite range.

## 5. Two-sided bulk arrangements

F1 need not be a terminal tile. Write Ebar for the horizontal reflection of E4. Then:

    E4^a F1 Ebar^b

is a valid one-sided construction for every a,b >= 0. Adjacent White masks are disjoint:

    E4 right 010 vs F1 left 101,
    F1 right 101 vs Ebar left 010,
    repeated Ebar: 101 vs 010.

Its width is 4(a+b)+1. This proves the same dimension family as the old construction, but allows its one-column part to sit in the interior. Likewise E4^a J4 Ebar^b gives a certified family of width 4(a+b+1).

This distinction is important for embedding constructions around prescribed openings, existing stones, holes, and special local interfaces. It does not make arbitrary four-column deletion valid.

## 6. Bounded scans performed

### Existing opening-tile library

The original 25 roots, together with their horizontal/vertical reflections, were tested as a root library after a chosen first White response on several odd widths. All representative openings were covered for widths 3,7,11,15. The coverage was 19/20 for width 19, 22/24 for width 23, and 29/32 for width 31. The failures in those widths were interior middle-row openings at specific column residues; for width 19 the missing representative was (1,7).

These failures concern this exact library and one-response search. They do not disprove a strategy, a larger library, a signed tiling, or a multi-round construction. In particular, failure of this restricted post-response lookup on some width-4k+1 openings does not contradict the already proved whole-board E4/F1 strategy: its subsequent checkpoint states are not all stored as library roots.

### Boundary-only root screens

For height three, widths 1 through 7, and every pair of 3-bit White boundary masks, all 448 maximal-interior root cases were solved. The 3-column root with any missing White boundary square is not Blue-first losing; the quarter-valued cap is a specific exact strengthening of this observation.

For height five, widths 1 through 4, analogous screens found no self-compatible repeatable tile. One capped 5x4 case needed a follow-up larger budget and was resolved as Blue-first winning. This is a limited catalog result, not a no-go theorem for height-five constructions.

### Small two-dimensional rectangular covers

Minimal safe White masks were enumerated for rectangles of shapes 1x2 through 1x5, 2x2 through 2x5, 3x3, and 3x4. Their rotations and the original opening tile library were used in bounded two-dimensional covering experiments. They did not give a complete 5x5 construction. Some 5x7 and 7x9 opening cases were covered, but no new wider empty-board theorem is claimed. The 7x9 run reached the search cap on some openings.

## 7. Prioritized broader construction types

### A. Signed tiles and numerical budgets

Allow a locally Blue-favorable cap when another certified tile compensates it. The checked -1 and +1/4 example provides an immediate test case. Learn upper bounds first rather than full canonical game values.

A useful next deliverable is a weighted version of `tiling_search.py`, with exact dyadic arithmetic and a witness for every accepted bound. This applies to arbitrary partial positions and any fixed height with a suitable tile library.

### B. Interface libraries rather than a single repeated tile

Enumerate distinct left/right support pairs and their certified costs. Store Pareto-minimal White supports and useful numeric bounds. Search compatible cycles, phase changes, starts, and finishes.

Repeated cycles prove length families constructively. Two repeatable cycles of widths p and q at the same interface give lengths n0+a*p+b*q. The common divisor controls eventual reachable residue classes. A finite collection of test outcomes alone does not establish such a cycle theorem.

### C. Opening-dependent interior kernels

Let the first move determine where the exceptional tile sits. Use independently repeatable regions to its left and right, rather than force the entire opening defect into a physical end-cap.

For a full parametric proof one must cover every row and both boundary distances, including finite near-edge exceptions, not only a list of successful widths. The minority-opening theorem is a concrete successful instance; majority-parity openings remain a separate task.

### D. Irregular cuts and two-dimensional mosaics

The one-sided simulation does not require rectangular blocks. Disjoint finite vertex sets with checked local adjacencies are enough. L-shaped, stepped, notched and mixed-orientation regions can route boundaries around actual stones or through cheap-to-retire White cells.

The combinatorial design problem is: partition actual Blue moves, pick certified virtual blocks, and cover every cross-block White interaction by retiring at least one endpoint. This is a constrained vertex-cover/tiling problem, not unrestricted edge deletion.

The certificate checker should use the actual embedded graph and inspect every cross-region edge. Searching candidates with SAT or integer programming would be safe because only the final witness, not the optimizer, needs to be trusted.

### E. Height-growing bands and corner junctions

Seek four-sided contracts for reusable rectangles: north/south/east/west White support masks and a numerical upper bound. A height-lifting theorem must preserve those interfaces, not merely the outcome of the smaller board.

Straight bands are not sufficient on their own. Corners where horizontal and vertical seams meet require certified junction tiles. Test height increments 2,4,6 rather than assume adding two rows is the natural step. The checked failed 5x4 extrusion demonstrates why this is a new lemma, not an automatic consequence of E4.

### F. Hybrid reflection and local tiles

Use reflection or conjugate pairing for a large easy region and small certified tiles for the unmatched center, boundary, or corner defects. Pairings can be treated as symbolic zero-valued macrotiles, provided their actual White boundary behavior remains compatible with neighboring regions.

Do not assume that restricting White at an interface preserves the pairing strategy. That is exactly what the interface certificate must establish.

### G. Adaptive retiling and finite interface protocols

A fixed mask may retire more White cells than necessary. A stronger protocol can allow an interface cell until a neighboring White move makes it unsafe, then change the local certified state.

Every such change must land in a checked successor family. Raw boundary masks do not summarize arbitrary interiors; a genuinely finite protocol requires a closure certificate. A practical intermediate step is a small exact AND/OR prefix whose leaves have ordinary one-sided tilings.

### H. Other board geometries

The same composition lemma applies to arbitrary finite graphs. For a cylinder, the final interface must also match the first; there is no free physical end. For example, E4 repeated around a three-row cylinder of circumference 4k has compatible wraparound White masks. This is an illustrative consequence, not a claim of novelty relative to ordinary even-size pairing.

Holes and existing stones can help an embedding by deleting Blue moves, but may also remove needed White replies. Both mask inclusions must always be checked.

## 8. Scope and trust

The original 3x15 result and original families are unchanged. This pass adds checked local numerical identities, a failed height-lift certificate, and the parameterized minority-opening result. It does not prove all empty 3x(4k+3) strips or all odd-by-odd rectangles.

All new claims are computer-assisted mathematical constructions with a search-free checker. They have not been externally peer reviewed or formalized in a proof assistant. Experimental coverage failures and node-budget cutoffs are explicitly not game-outcome claims.
