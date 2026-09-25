# Certified Col tile atlas: mathematics and scope

Date: September 5, 2026.

## Rules and notation

Normal-play Col on an orthogonal rectangular grid. A player may not place a stone adjacent to one of their own stones; no legal move means a loss. In a shadow, `o` is legal for both roles, `b` for Blue only, `w` for White only, and `.` for neither. These characters are permissions, not stones. Blue is the positive CGT player. All cell and port masks use zero-based row-major indices; port bit 0 is the topmost/leftmost cell.

This packet builds on the supplied one-sided tiling and numeric-certificate packages. Their original checkers were rerun. No result below relies on the unfinished production DFS or a presumed odd-rectangle theorem.

## 1. Monotonicity and why the full-Blue safe roots are exactly zero

On a fixed graph, if A is contained in A' and B' is contained in B, then

    G(A,B) <= G(A',B').

One proof is the comparison-game copy strategy. In G(A',B') - G(A,B), answer each Right move in the other copy at the same vertex. The required legal-set inclusions are preserved under identical placement updates, so Left can always answer Right. This establishes the game-order inequality, not just one outcome comparison.

Let H = G(V,V), and suppose a certificate proves G(V,W) <= 0 for some W contained in V. Monotonicity gives H <= G(V,W) <= 0. But H is self-conjugate, so H=-H and therefore H=0. It follows that

    0 = H <= G(V,W) <= 0,

and hence G(V,W)=0. This is why a single Blue-first-losing certificate establishes an **exact zero** for every full-Blue root in this catalog. It does NOT establish exact zero for arbitrary partial checkpoints.

Once one such safe root is known on a shape, every full-Blue root on that shape is nonnegative. An unsafe root, certified Blue-first winning, is consequently strictly positive (possibly nonnumerical), not necessarily a particular positive rational.

## 2. Complete 5x4 classification

Blue retains all 20 cells. White can be allowed any subset of the 20 cells: 2^20 = 1,048,576 possibilities.

The independent checker certifies:

- 175 of these positions are exactly zero.
- The other 1,048,401 are strictly positive and Blue wins with either starting player.
- The zero set is generated upward by 14 inclusion-minimal White supports.
- The unsafe set is generated downward by 88 inclusion-maximal White supports.

Every minimal safe root has a complete finite response DAG. Every maximal unsafe root has a checked winning Blue opening followed by a complete White-first-losing response DAG. The checker explicitly enumerates the two monotone closures, verifies they are disjoint and cover all 2^20 masks, and verifies the claimed frontiers are irredundant. No inference is made from a timed-out scan.

The 14 minimal safe supports form four orbits under horizontal/vertical reflection. Their diagrams are in CATALOG.md. They require 15, 16, or 17 White-available cells; their supersets give the 175 safe masks.

### A useful no-go theorem

Among all 175 safe 5x4 roots, no pair has compatible White supports along an aligned horizontal seam, and no pair has compatible supports along an aligned vertical seam.

Thus **no chain of individually safe, full-Blue, permanently White-restricted 5x4 rectangles can be composed through straight, full-side seams by the present one-sided lemma**, even using different patterns in successive rectangles.

This excludes only that construction class. It does not exclude signed tiles, positions with Blue defects, partial/stepped contacts, different neighboring shapes, or coordinated/adaptive strategies. It does not claim that the unrestricted 5x4 rectangle is first-player winning.

## 3. Exact positive and negative 5x4 values

Let P be the alternating five-row extrusion:

    ooob
    booo
    ooob
    booo
    ooob

Its masks are Blue 1048575 and White 518119. The new checker verifies two complete losing certificates for P-3/4 (one for each starting player), establishing

    P = 3/4.

This is stronger than the previous refutation showing merely that Blue wins it. Its west/east White masks are 10101 and 01010 (written top-to-bottom), which are disjoint: it is physically self-compatible, but costs +3/4 per copy rather than zero.

Every Blue opening in a cell with row+column odd leaves value -1. Six representatives, plus top-bottom reflection, cover all ten such openings. Blue at the middle-left cell (2,0), cell 8, leaves value +1/2. The remaining nine openings are certified outcome N: the next player wins. Their exact values are not asserted; in particular, outcome N is not silently replaced by the nimber star.

All numerical equalities are independently checked by proving that G-q is zero. All N outcomes have a winning first move and checked continuation certificate for each starting actor.

### A signed two-block consequence

After an odd-parity Blue opening in one P tile, two consecutive P tiles have a virtual value

    -1 + 3/4 = -1/4.

Their seam is safe for White. Actual cross-seam Blue restrictions only improve White's position, so the actual post-opening game is at most -1/4. On an empty 5x8 board, choose a horizontal reflection so any specified opening has odd parity in these coordinates. Therefore **every one-Blue-stone position on 5x8 is strictly negative**. This is an additional bounded-width construction, not a proof for every five-row width.

One negative opening does not pay for arbitrarily many positive P tiles: k tiles yield the upper bound -1+(k-1)*3/4, useful by sign only for k=1 or k=2.

## 4. One-sided weighted composition

For embedded virtual tiles, require:

1. every actual Blue move is allowed in its virtual tile;
2. every virtual White move is actually available;
3. no edge crossing tiles has two White-available endpoints.

The coordinate simulation gives G_actual <= sum T_i. If T_i <= u_i is a certified numerical upper bound for each tile, then G_actual <= sum u_i. A nonpositive sum certifies a loss for Blue to move; a strictly negative sum certifies a White win regardless of the next actor.

The same-block response rule is sufficient when every tile is independently Blue-first losing. Signed compensation may need moves in different tiles. Compatible endpoints are still mandatory. Matching numerical totals alone does not justify cutting arbitrary graph edges.

## 5. Infinite tile families derived without further DFS

Write E4 for the original `ooob/booo/ooob` zero tile. It is covered by the stronger minimal support `ooob/bobo/ooob` in this atlas.

### Three-row E tiles of every width divisible by four

Let E_(4k), k>=1, allow Blue everywhere and White everywhere except middle-left, top-right, and bottom-right. Divide it into k E4 tiles and voluntarily retire the extra internal boundary cells. The virtual tiles are compatible and zero, while actual White has at least their permissions. Thus E_(4k)<=0, and the full-Blue lemma makes it exactly zero.

This supplies E8, E12, E16, ... analytically. It does not supply E6.

### Three-row J connectors in three residue classes

Let J_n forbid White only at the middle-left and middle-right cells (one cell when n=1). Its other cells are available to both players.

The atlas certifies J2 by rotating the 2x3 primitive, J4 directly, and F1=J1 by rotating the 1x3 primitive. Hence:

    J_(4k+1): E4^k + F1,       k>=0;
    J_(4k+2): E4^k + J2,       k>=0;
    J_(4k):   E4^(k-1) + J4,   k>=1.

All seams pair White masks 010 with 101, and the target J_n only gives White additional interior permissions. These are exact-zero connector families for n mod 4 in {0,1,2}. Their two exposed White masks are 101, so two J tiles are not directly self-compatible. No n=3 mod4 conclusion is made.

### Even-by-even checkerboard tiles

A 2x2 block with Blue everywhere and White on either checkerboard diagonal is zero. Tile any even-by-even rectangle by 2x2 blocks, using the same global White checkerboard class. White has no adjacency across any seam. Therefore **every even-by-even rectangle remains zero with White restricted to either one of its two checkerboard classes**. This is a boundary-support theorem stronger than simply knowing the unrestricted rectangle is zero.

These statements describe constructions for arbitrary parameters. The 176 concrete embedding tests are implementation checks, not the basis for extrapolating to infinite families.

## 6. Atlas scope and solver use

Twenty-one shapes are classified completely for full Blue legality and arbitrary White permissions: 1x2 through 1x8; 2x2 through 2x8; 3x3 through 3x7; 4x4; and 5x4. Transposition/rotation gives their corresponding orientations. This is **not** an exhaustive classification of all four-state-per-cell Col positions.

There are 49 primitive zero supports, generating 1,682 safe full-Blue roots across the listed shapes. The proof frontiers consist of 467 certificates with 436,703 checkpoints and 1,861,429 universally covered move/response edges.

The additional numerical/outcome packet uses 26 certificates with 44,818 checkpoints and 204,816 response edges. Combined: 493 certificates, 481,521 checkpoints, and 2,066,245 response edges.

The derived partial-state file contains 152,473 distinct nonterminal checkpoints with at least four live cells. Each has a certified **upper bound 0**, not necessarily value 0. The masks are relative to the checkpoint's first and second roles; some came from original White-first counterstrategies and have correspondingly exchanged color labels. A record references its exact source certificate and node index.

For a partial-tile match, require actual_Blue subset_of certified_Blue and certified_White subset_of actual_White. Retain the certified White support at its ports. A whole-board result requires a complete compatible cover and valid bound arithmetic. Failed coverage is inconclusive.

## 7. Trust and remaining work

Generation uses exhaustive finite minimax; verification uses independently written coordinate sets, legal-response coverage, closure, and strict descent. The lattice coverage proof uses monotonicity and checks every permission mask. No probabilistic hash identity is trusted. These results are computer-assisted, not externally peer reviewed or proof-assistant formalized.

Larger exploratory 3x8, 4x6 and 5x6 scans are retained separately as raw discovery data with explicit unknown results. They are not part of the 21 complete classifications or the certified tile counts.
