# Col on grids: what the literature knows

Stream: literature and theory (round five). Searched and read 2026-09-23.

Labels: **VERIFIED** = I read the statement in the source itself (page
image, publisher PDF or author preprint), at the location given.
**CITED-SECONDHAND** = only seen as a citation or summary in another source.
**NOT ACCESSED** = located but could not be read.

## 1. Bottom line

- **The odd×odd conjecture is open in the literature.** The most recent
  paper devoted to rectangular Col (Uiterwijk, ACG 2021, published 2022)
  lists odd×odd Col as outcome class "?" and says no general strategy is
  known. VERIFIED (§2.1). Searches for later work (2022–2026) found no
  resolution and no statement of the conjecture elsewhere.
- **Published computer solutions of empty odd×odd boards** stop at 3×3, 3×5,
  3×7, 3×9 and 5×5 (all value 0), credited to Demeur's 2020 BSc thesis.
  CITED-SECONDHAND: the thesis itself was not found online.
- **No published solution of 5×7, 5×9 or 7×7 was found.** A web-search
  summary claimed "5×7 and 7×7 are second-player wins" and cited the
  Uiterwijk paper; the paper says nothing of the kind (checked against the
  full text). Treat such claims as search-engine artifacts. The repository's
  own solver outputs are the only 5×7 evidence I know of; they are not
  literature.
- **The number-or-number-plus-star theorem** (Conway–Guy) is in ONAG p. 93
  and Winning Ways vol. 1 pp. 47–48, and in Austin's 1976 thesis. VERIFIED.
  Its proof and consequences are written out in [COL_VALUES.md](COL_VALUES.md).
- The 3×n theorem proved in this repository (every empty 3×n board is 0)
  goes beyond the published record, where only 3×3…3×9 appear.

## 2. Sources on Col on rectangular boards

### 2.1 Uiterwijk, ACG 2021 (the main modern source)

J. W. H. M. Uiterwijk, "Solving Bicoloring-Graph Games on Rectangular
Boards – Part 1: Partisan Col and Snort", *Advances in Computer Games*
(ACG 2021), LNCS 13262, Springer 2022, pp. 96–106,
doi:[10.1007/978-3-031-11488-5_9](https://doi.org/10.1007/978-3-031-11488-5_9).
Author preprint:
<https://icga.org/wp-content/uploads/2021/11/ACG_2021_paper_3.pdf>
(read in full; section numbers below are the preprint's).

VERIFIED from the preprint:

- Abstract: "For Col on general odd × odd boards we found no applicable
  strategy, though all experimental data show second-player wins."
- Theorem 1 (§3.1): every empty m×n Col board with m or n even is a
  second-player win (value 0), by the half-turn copy strategy.
- §3.2: "Demeur [4] proved that the 3 × 3, 3 × 5, 3 × 7, 3 × 9, and 5 × 5
  boards are second-player wins (CGT value 0), but his analyses show no
  general applicable winning strategy for either player on odd × odd
  boards." Also: the second player "cannot use the centre strategy, since
  the first player can at some moment color the centre".
- Theorem 2 (§3.3): empty Linear Col chains of length n > 1 have value 0,
  proved by induction over tinted chains. The paper notes Winning Ways
  vol. 1 pp. 49–50 gives the Linear Col values without proof.
- §2: "Conway [3] has proven that in Col every position has as value a
  number (z) or a number plus ∗ (notation z∗)."
- §4: Snort is completely solved on rectangles by symmetry (P if both sides
  even, N otherwise); Linear Snort values up to n = 9 are listed.
- §5, Table 1: Col is P for even×even and odd×even, "?" for odd×odd; "for
  odd × odd Col we do know that some instances are second-player wins, but
  do not know if first-player wins also occur." Future work: "finding
  optimal strategies for odd × odd Col boards with both dimensions ≥ 3."
- Introduction: Demeur's thesis "reports solving many Col and Snort boards
  with sizes up to some 30 squares, based on αβ search." Values were
  cross-checked with CGSuite, using Huntemann's Snort code adapted to Col.

Part 2 (same volume, pp. 107–117,
doi:[10.1007/978-3-031-11488-5_10](https://doi.org/10.1007/978-3-031-11488-5_10);
preprint <https://icga.org/wp-content/uploads/2021/11/ACG_2021_paper_4.pdf>),
VERIFIED: impartial versions iCol and iSnort. Odd×odd iCol is a
**first-player** win: colour the centre, then play the half-turn image in
the *same* colour ("centre-same"). Even-sided boards are P by "centre-opp".
Linear iCol/iSnort: even length 0, odd length `*`. Relevance: this is the
impartial analogue where the centre defect is harmless; in partisan Col the
same-colour reply is illegal next to the centre, which is exactly where the
mirror strategy breaks (see [GENERAL_IDEAS.md](GENERAL_IDEAS.md) §2).

### 2.2 Demeur 2020

E. Demeur, *Solving COL and SNORT on Different Graphs Efficiently*, BSc
thesis, Department of Data Science and Knowledge Engineering, Maastricht
University, 2020. **NOT ACCESSED**: not on the Maastricht thesis pages I
could reach or elsewhere online. Everything attributed to it is
CITED-SECONDHAND via Uiterwijk §1 and §3.2.

### 2.3 On Numbers and Games

J. H. Conway, *On Numbers and Games*, Academic Press 1976; 2nd ed. A K
Peters 2001. Chapter 8, the Col and Snort section, pp. 91–96 of the 2nd
edition. Read as page images from a course scan
(<https://sites.math.rutgers.edu/~zeilberg/EM13/onag2.pdf>). VERIFIED:

- p. 91: Col and Snort introduced; Col credited to Colin Vout, Snort to
  Simon Norton.
- p. 92: the tinted-map representation; a node tinted both ways "might just
  as well be erased from the map"; an edge joining oppositely tinted nodes
  has no force.
- p. 93: the dictionary inequalities ("hindering one's opponent is no harm",
  "let my people go"), then: "Richard Guy and I have shown that they are
  all of the form x or x + * … the inequalities below imply trivially that
  G^L + * ≤ G ≤ G^R + * … We do not know if denominators of 16 or more can
  appear in x."
- p. 94: chains and their values; the adjacent-twin tinting rule; the
  explosive-node principle; the fork deletion (two untinted pendant nodes
  on one node), which is the handoff §18 identity.
- p. 95: further explosive nodes (a node of an attached cycle; a node of an
  untinted chain with at least three others on each side; others marked
  with lightning bolts); a table of small values; a diagram with a
  tint-reversing fixed-point-free symmetry has value 0.

No grid (m×n with m, n ≥ 3) result is stated.

### 2.4 Winning Ways

E. R. Berlekamp, J. H. Conway, R. K. Guy, *Winning Ways for your
Mathematical Plays*, vol. 1, 2nd ed., A K Peters 2001, chapter 2. VERIFIED
from an OCR text extract of a scan (scribd document 45496369; formulas on
p. 48 partly illegible) plus the publisher's table-of-contents preview:

- pp. 37–39: "Col", "A Star is Born", "Col Contains Such Values" (small
  maps with values `*`, `1/2`, etc.).
- pp. 47–48: "A Theorem about Col": "Each Col position has a value z or
  {z|z} = z* for some number z", proof outline via the imitation strategy
  in the difference game and "every G^L ≤ every G^R".
- pp. 48–51: "Col-lections and Col-lapsings": rules 1–8 for simplifying
  maps (tinted-node deletion, twins, explosive nodes, chains). p. 51: "Nick
  Inglis has shown that there are Col positions with arbitrarily large
  denominators" (Inglis's proof: CITED-SECONDHAND, not found).
- pp. 49–50: Linear Col values (per Uiterwijk; the OCR extract confirms the
  chain discussion but not every value).

No grid result is stated.

### 2.5 Austin 1976

R. B. Austin, *Impartial and Partisan Games*, MSc thesis, University of
Calgary, 1976 (supervisor R. K. Guy). VERIFIED from OCR of the scanned
thesis: chapter 2, Lemma 2.1 ("Hindering One's Opponent is No Harm"),
Lemma 2.2 (edge deletion), Theorem 2.3 ("The value of any position G in
Col is either x or x+*"), with the remark that the theory applies to
arbitrary graphs.

## 3. Complexity results

- S. A. Fenner, D. Grier, J. Messner, L. Schaeffer, T. Thierauf, "Game
  Values and Computational Complexity: An Analysis via Black-White
  Combinatorial Games", ISAAC 2015, LNCS 9472, pp. 689–699; ECCC TR15-021.
  VERIFIED (ECCC text): Col on (uncoloured) general graphs is
  PSPACE-complete; such positions only take values `0` and `*` (§1.2,
  "easy to adapt" the Col theorem); a black-white version is
  P^NP[log]-complete. They note an earlier hardness claim attributed to
  Cincotti 2009 was a mistaken citation.
- K. Burke, R. A. Hearn, "PSPACE-Complete Two-Color Planar Placement Games",
  arXiv:[1602.06012](https://arxiv.org/abs/1602.06012); *Int. J. Game
  Theory* 48 (2019). VERIFIED (abstract/arXiv text): Col, NoGo and Fjords are
  PSPACE-complete on planar graphs.
- K. Burke and C. Tennenhouse, Col is PSPACE-complete on triangular grid
  graphs, arXiv:[2501.06574](https://arxiv.org/abs/2501.06574) (2025;
  author list as recorded in my search notes, title paraphrased).
  VERIFIED (arXiv text): reduction from Bounded Two-Player Constraint
  Logic with 8×8 gadgets; "the most structured graph family that Col is
  known to be computationally hard for".
- T. J. Schaefer, "On the complexity of some two-person perfect-information
  games", *J. Comput. Syst. Sci.* 16 (1978): Snort and Node Kayles
  PSPACE-complete. CITED-SECONDHAND (via the papers above).

Relevance: hardness is for adversarial initial colourings of structured
graphs; it does not bear on empty square grids, but it does warn that no
polynomial-size family of local rules can decide **arbitrary** grid shadow
states unless PSPACE collapses. The square grid itself is not known to be
hard.

## 4. Other Col and placement-game work

- "The Game of Col on Complete k-ary Trees", Zenodo,
  doi:[10.5281/zenodo.1057888](https://doi.org/10.5281/zenodo.1057888).
  Located; author and content not verified. NOT ACCESSED in detail.
- S. Huntemann, *The Class of Strong Placement Games: Complexes, Values,
  and Temperature*, PhD thesis, Dalhousie 2018,
  <http://hdl.handle.net/10222/74151>. VERIFIED (abstract/contents): Col and
  Snort as strong placement games; simplicial-complex view; temperature.
- S. Huntemann, "Values, Temperatures, and Enumeration of Placement Games",
  slides, BIRS workshop 23w2008 (2023). VERIFIED (slide text): boiling point
  of Col is 0; credits Lexi Nash with extending "numbers or numbers plus *"
  to many Col-like games (Nash's result: CITED-SECONDHAND).
- S. Huntemann and L. Nash, polynomial profiles of placement games
  (*Integers* 2022, arXiv:[2111.09349](https://arxiv.org/abs/2111.09349));
  J. I. Brown et al., a note on polynomial profiles (*Games of No Chance 5*,
  MSRI). VERIFIED (abstracts only): counting positions by number of pieces;
  no values of grid boards.
- Combinatorial game theory blog
  (<https://combinatorialgametheory.blogspot.com>, posts in 2011 and 2024):
  small Col puzzles; no grid results.

## 5. Techniques from the literature that could transfer

Each is followed up, with a falsification test, in
[GENERAL_IDEAS.md](GENERAL_IDEAS.md).

1. **Symmetry (Tweedledum–Tweedledee).** Proves every board with an even
   side (Uiterwijk Thm 1; ONAG p. 95). Fails on odd×odd only through the
   centre. Partial repairs studied here and in round 3.
2. **Explosive nodes and deletion rules** (ONAG pp. 94–95; WW rules 1–8).
   Proved in general form in COL_VALUES.md §6 (explosive separator sets can
   be deleted). They need cut vertices or small separators, which a full
   grid lacks until play creates them.
3. **Numbers-only arithmetic.** Because every position is `x` or `x+*`,
   comparisons reduce to number parts and one parity bit (COL_VALUES.md §4).
   This is what makes sums of boundary regions tractable.
4. **Induction over tinted chains** (Uiterwijk Thm 2): the only published
   all-length proof. It is one-dimensional; the repository's 3×n theorem is
   its two-dimensional analogue with certified tiles.
5. **Centre-same strategy for iCol** (Part 2): shows exactly what fails in
   the partisan game: the centre stone is a defect the mirror cannot absorb.

## 6. Access notes

Could not access: Demeur's thesis; Inglis's unbounded-denominator proof;
the full text of the k-ary-tree paper; the Springer versions of Uiterwijk's
papers (the author preprints were used; page ranges are from Springer's
metadata). Winning Ways was read only through an OCR extract, so exact
wording of displayed formulas on p. 48 is unconfirmed.
