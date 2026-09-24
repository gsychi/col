# Col values are numbers or numbers plus star

Stream: literature and theory (round five). Written 2026-09-23.

Labels follow the round-five rules: **PROVED** (written proof, checked here),
**CITED** (statement read in the named source, exact location given),
**CITED-SECONDHAND**, **EVIDENCE** (finite computation), **CONJECTURE**,
**REFUTED**.

## 0. Statements other streams can use

Throughout, a *Col position* is a triple `(Γ, A, B)`: a finite simple graph
`Γ = (V, E)` and two arbitrary subsets `A, B ⊆ V` (Blue-legal and
White-legal cells). Blue at `v ∈ A` gives `(A∖N[v], B∖{v})`; White at
`v ∈ B` gives `(A∖{v}, B∖N[v])`. This is exactly the project's shadow-state
model with the grid replaced by any graph. **No reachability assumption is
made**: `A` and `B` are arbitrary, cells legal for neither player are
allowed, and so are Blue-only and White-only cells.

| Id | Statement | Status |
| --- | --- | --- |
| Thm 5 | Every Col position has value `x` or `x+*` for a dyadic rational `x`. | PROVED (§3); CITED: ONAG p. 93, Winning Ways vol. 1 pp. 47–48, Austin 1976 Thm 2.3 |
| Lem 4 | For `v ∈ A`: `G^{L,v} + * ≤ G`; if also `v ∉ B` then `G^{L,v} + 1 ≤ G`. For `v ∈ B`: `G ≤ G^{R,v} + *`; if also `v ∉ A` then `G ≤ G^{R,v} − 1`. | PROVED (§2); first half CITED: ONAG p. 93 |
| Lem 2 | Comparison principle on arbitrary graphs (the handoff §2 principle). | PROVED (§1) |
| Scope | Thm 5 covers every grid shadow state, every virtual region of a comparison, all disjoint sums of these, and such sums plus any dyadic numbers and stars. It does **not** cover arbitrary auxiliary games such as `↓ = {*|0}`. | PROVED (§3.3) |
| Tab 1 | For `G = x+ε*`: `G<q ⟺ x<q`; `G≤q ⟺ x≤q` (ε=0) or `x<q` (ε=1); `G+*≤q ⟺ x<q` (ε=0) or `x≤q` (ε=1). | PROVED (§4) |
| Cor 4.2 | `T_q(G)` ("`G≤q` and `G+*≤q`") `⟺ G<q ⟺ G+*<q ⟺ x<q`. | PROVED |
| Cor 4.3 | Outcome N `⟺ G=*`; outcome P `⟺ G=0`; outcome L `⟺ x>0`; R `⟺ x<0`. | PROVED |
| Cor 4.4 | White wins moving first (`G ⧏ 0`) `⟺ G ≤ *` `⟺` Blue loses moving first in `G+*`. | PROVED |
| Cor 5.1 | Every colour-symmetric position (in particular every empty board) is `0` or `*`. | PROVED; CITED: Fenner et al. 2015 §1.2 (uncoloured graphs) |
| Cor 5.2 | For the empty board `E`: each Blue opening has value `<0`, `=0` or `=*`; `E=*` iff some opening has value exactly `0`. So the odd×odd conjecture says: **no opening has value exactly 0**. | PROVED |
| Lem 5.3 | If `G = x+*`, some Blue option and some White option equal `x` exactly. | PROVED |
| §6 | Explosive vertex and explosive separator sets, deletable outright: `G = G − S` (ONAG p. 94); adjacent twins (ONAG p. 94); permission increments `≤1` (dead cell made Blue-legal) and `≤2` (White-only cell made shared). | PROVED |
| §6 | Permission increment `≤ 1+*` at a White-only cell. | REFUTED (1×5 `www..`, increment `1`; 2×3 increment `3/2`) |
| §6 | "If Blue wins moving first and has a shared legal cell, some shared-cell move wins." | REFUTED (`bob/.w.`) |

Everything computational is in §7; the proofs do not depend on it.

## 1. Setting, background facts, and the comparison principle

### 1.1 Background from short-game theory

Games are short (finite) partizan games. `G ≤ H` is Conway's recursive
order: `G ≤ H` iff no `G^L` satisfies `H ≤ G^L` and no `H^R` satisfies
`H^R ≤ G`. Write `G ⧏ H` for "not `H ≤ G`". The following standard facts are
used; F3 and F4 were read directly on ONAG p. 93 (page image, second
edition), the rest are textbook definitions and theorems (ONAG chapters 0–1
and 7; Winning Ways vol. 1 chapters 1–2; Siegel, *Combinatorial Game
Theory*, AMS GSM 146, chapter II).

- **F1.** `≤` is a preorder, compatible with `+`; `G ≤ G`; hence never
  `G ≤ G^L` and never `G^R ≤ G`. `−G` swaps the roles of the players.
- **F2.** Left (Blue) wins moving first in `G` iff `G ⧐ 0` (not `G ≤ 0`);
  Right (White) wins moving first iff `G ⧏ 0`. `G>0`, `G<0`, `G=0`, `G ∥ 0`
  are the outcome classes L, R, P, N.
- **F3 (simplest number rule, general form; ONAG p. 93).** If some number
  `z` satisfies `G^L ⧏ z ⧏ G^R` for all `G^L, G^R`, then `G` equals the
  simplest such `z`; in particular `G` is a number.
- **F4 (ONAG p. 93; Winning Ways vol. 1 p. 38).** For numbers `x`:
  `{x|x} = x+*`, and `x+*` is greater than every number `< x`, less than
  every number `> x`, and incomparable with `x`. Hence for numbers `y`:
  `y+* ≤ 0 ⟺ y < 0`, and `*+* = 0`.

### 1.2 Col positions as games

For `v ∈ V`, `N[v]` is the closed neighbourhood and `N(v) = N[v]∖{v}`.
`G(Γ, A, B)` denotes the game. Every move removes the played cell from
`A ∪ B`, so play has length at most `|A ∪ B|`; `|A ∪ B|` ("live cells") is the
induction parameter below.

**Lemma 1.1 (identical game trees; PROVED).**

1. *Negation.* `−G(Γ, A, B) = G(Γ, B, A)`.
2. *Disjoint union.* If `Γ` has no edge between `V1` and `V2 = V∖V1`, then
   `G(Γ, A, B) = G(Γ[V1], A∩V1, B∩V1) + G(Γ[V2], A∩V2, B∩V2)`.
3. *Dead cells.* If `d ∉ A ∪ B` then `G(Γ, A, B) = G(Γ − d, A, B)`.
4. *Inert edges.* If an edge `uv` has `{u,v} ⊄ A` and `{u,v} ⊄ B`, deleting
   it does not change the game.

*Proof.* In each case the two game trees are identical move for move. (1):
swapping `A` and `B` swaps the move rules. (2): a move at `v ∈ V1` changes
permissions only inside `N[v] ⊆ V1`. (3): `d` is never playable, and
removing `N[v]` or `{v}` from a set not containing `d` is unaffected by `d`.
(4): the edge acts only when a player moves at one endpoint while the other
endpoint is legal for that same player; since permissions only shrink, the
hypothesis persists forever and the edge never acts. ∎

Item 3 means a shadow-state cell that is legal for neither player is the
same as an absent vertex: ONAG's "tinted both ways" node that "might just
as well be erased from the map" (ONAG p. 92). Item 4 contains ONAG's remark
that an edge joining oppositely tinted nodes has no force (p. 92).

### 1.3 Simulation lemma and comparison principle

**Lemma 1.2 (simulation; PROVED).** Let `R` be a set of pairs of games such
that for every `(G, H) ∈ R`:

- (i) for every `G^L` there is an `H^L` with `(G^L, H^L) ∈ R`, and
- (ii) for every `H^R` there is a `G^R` with `(G^R, H^R) ∈ R`.

Then `G ≤ H` for every `(G, H) ∈ R`.

*Proof.* Induction on the sum of the heights of the game trees of `G` and
`H`. Let `(G,H) ∈ R`. Suppose some `G^L` had `H ≤ G^L`. Choose `H^L` by (i);
by induction `G^L ≤ H^L`, so `H ≤ H^L`, contradicting F1. Suppose some `H^R`
had `H^R ≤ G`. Choose `G^R` by (ii); by induction `G^R ≤ H^R`, so
`G^R ≤ G`, again contradicting F1. By the definition of `≤`, `G ≤ H`. ∎

**Lemma 2 (comparison principle; PROVED).** Let `Γ = (V, E)` and
`Γ' = (V, E')` with `E' ⊆ E`. Suppose `A ⊆ A'`, `B' ⊆ B`, and every edge in
`E ∖ E'` has at least one endpoint outside `B'`. Then

```math
G(Γ, A, B) \le G(Γ', A', B').
```

*Proof.* Let `R` be the set of all pairs `(G(Γ,A,B), G(Γ',A',B'))` meeting
the hypotheses (with `Γ, Γ'` fixed). Write `N` and `N'` for closed
neighbourhoods in `Γ` and `Γ'`; `N'[v] ⊆ N[v]`.

(i) Blue at `v ∈ A ⊆ A'` in both. New sets: `A∖N[v] ⊆ A∖N'[v] ⊆ A'∖N'[v]`;
`B'∖{v} ⊆ B∖{v}`; a deleted edge still has an endpoint outside `B'∖{v}`.

(ii) White at `v ∈ B' ⊆ B` in both. `A∖{v} ⊆ A'∖{v}`. If
`u ∈ B'∖N'[v]` were in `N[v]`, then `uv ∈ E∖E'` with both endpoints in `B'`,
which is excluded; hence `B'∖N'[v] ⊆ B∖N[v]`. The edge condition persists
because `B'` only shrinks. Lemma 1.2 applies. ∎

With `Γ'` the disjoint union of the regions this is exactly the handoff's
comparison principle, and by Lemma 1.1(2) the right side is the sum of the
region games. Adding any game `K` to both sides preserves it (F1). By
Lemma 1.1(1) there is a **dual**: if `E' ⊆ E`, `A' ⊆ A`, `B ⊆ B'`, and every
edge of `E∖E'` has an endpoint outside `A'`, then
`G(Γ', A', B') ≤ G(Γ, A, B)`.

Special cases, all PROVED by Lemma 2 or its dual: adding a Blue permission
or removing a White permission never decreases `G`; deleting an edge with a
White-illegal endpoint never decreases `G`; the colour duals. These are
ONAG's dictionary inequalities "hindering one's opponent is no harm" and
"let my people go" (ONAG p. 93; Austin 1976 Lemmas 2.1, 2.2).

## 2. The key inequality

**Lemma 4 (PROVED; first inequality CITED ONAG p. 93).** Let
`G = G(Γ, A, B)`.

1. If `v ∈ A`, then `G^{L,v} + * ≤ G`.
2. If `v ∈ A ∖ B` (Blue-only), then `G^{L,v} + 1 ≤ G`.
3. If `v ∈ B`, then `G ≤ G^{R,v} + *`.
4. If `v ∈ B ∖ A` (White-only), then `G ≤ G^{R,v} − 1`.

*Proof.* (1) Let `Γ°` be `Γ` with every edge at `v` deleted, and put
`P = G(Γ°, A∖N(v), B ∪ {v})`. In `Γ°` the vertex `v` is isolated, legal for
both players (`v ∈ A`, `v ∉ N(v)`), so by Lemma 1.1(2) it contributes `*`.
On `V∖{v}` the sets of `P` are `A∖N[v]` and `B∖{v}`, the sets of `G^{L,v}`,
in which `v` is dead; by Lemma 1.1(3) that part is `G^{L,v}`. Hence
`P = G^{L,v} + *`. Apply the dual comparison with `A' = A∖N(v) ⊆ A`,
`B' = B ∪ {v} ⊇ B`: every deleted edge `vu` has `u ∈ N(v)`, outside `A'`.
So `G^{L,v} + * = P ≤ G`.

(2) Same, with `B' = B`: now `v` is isolated and Blue-only, of value `1`.

(3), (4) Apply (1), (2) to `−G = G(Γ, B, A)` and use Lemma 1.1(1):
`(−G)^{L,v} = −(G^{R,v})`. ∎

Equivalently `G^{L,v} ≤ G + *` (since `−* = *`): **a Blue move never
improves the value by more than a star, and a move at a Blue-only cell costs
Blue at least one.** Dually, `G ≤ G^{R,v} − 1` at a White-only cell `v`:
White's private cells are a reserve worth at least one each. That last form
gives a sufficient condition for upper bounds that other streams may use:

```math
v \in B\setminus A \ \text{and}\ G^{R,v} \le q+1 \ \Longrightarrow\ G \le q .
```

## 3. The theorem

**Theorem 5 (Conway–Guy; PROVED).** Every Col position `G(Γ, A, B)` equals
`x` or `x+*` for some dyadic rational `x`.

*Proof.* Induction on `|A ∪ B|`. If `A ∪ B = ∅` then `G = 0`. Otherwise
every option has fewer live cells, so by induction each Blue option is
`a_i + ε_i*` and each White option is `b_j + δ_j*`, with numbers `a_i, b_j`
and `ε_i, δ_j ∈ {0,1}`.

By Lemma 4, `G^L + * ≤ G ≤ G^R + *`; adding `*` gives `G^L ≤ G^R` for
**every** pair of options. By F4 this means

```math
a_i + ε_i* \le b_j + δ_j* \iff
\begin{cases} a_i \le b_j & (ε_i = δ_j),\\ a_i < b_j & (ε_i \ne δ_j).\end{cases}
\tag{3.1}
```

Let `m = max a_i` (`−∞` if Blue has no move) and `M = min b_j` (`+∞` if
White has no move). By (3.1), `m ≤ M`.

*Case `m < M`.* Take any number `z` with `m < z < M`. For each Blue option,
`a_i + ε_i* − z` is a negative number plus possibly `*`, hence negative, so
`G^L ⧏ z`; symmetrically `z ⧏ G^R`. By F3, `G` is a number.

*Case `m = M = c`.* Some Blue option and some White option have number part
`c`. By (3.1) all options with number part `c`, on both sides, carry the
same star bit `β`.

- If `β = 0`, there are options `G^L = c` and `G^R = c`; Lemma 4 gives
  `c + * ≤ G ≤ c + *`, so `G = c + *`.
- If `β = 1`, there are options `G^L = G^R = c+*`; Lemma 4 gives
  `c ≤ G ≤ c`, so `G = c`. ∎

The last case needs neither dominated-option deletion nor reversibility;
otherwise the argument is the one outlined in Winning Ways (vol. 1 p. 48:
"every `G^L ≤` every `G^R`", then the simplicity rule, excluding forms such
as `{x | x+*}`).

### 3.1 Where it is stated in the literature

- ONAG (2nd ed., A K Peters 2001, reprinting the 1976 text), chapter 8,
  p. 93: "It appears that in COL the values that arise are very restricted
  in kind. Richard Guy and I have shown that they are all of the form `x` or
  `x + *` for various numbers `x`. For the inequalities below imply
  trivially that `G^L + * ≤ G ≤ G^R + *` for any COL position `G`, and from
  this the desired result follows by induction. We do not know if
  denominators of 16 or more can appear in `x`." **CITED** (page image).
  The "inequalities below" are dictionary item (1) on the same page.
- Winning Ways vol. 1 (2nd ed., 2001), chapter 2, "A Theorem about Col",
  pp. 47–48: "Each Col position has a value `z` or `{z|z} = z*` for some
  number `z`", with the tinted-graph notation, "the obvious imitation
  strategy that wins for Left as second player in the difference game", the
  consequence "every `G^L ≤` every `G^R`", and the simplicity rule. Page 51:
  "Nick Inglis has shown that there are Col positions with arbitrarily large
  denominators." **CITED** from an OCR text extract of a scan; the displayed
  formulas on p. 48 were illegible in that extract.
- R. Austin, *Impartial and Partisan Games*, MSc thesis, University of
  Calgary (supervisor R. K. Guy), June 1976, chapter 2: Lemma 2.1
  ("Hindering One's Opponent is No Harm"), Lemma 2.2 (edge deletion),
  Theorem 2.3 ("The value of any position `G` in Col is either `x` or
  `x+*`"), stating that the theory applies to arbitrary graphs. **CITED**
  (OCR text of the scanned thesis).
- Fenner, Grier, Messner, Schaeffer, Thierauf (ISAAC 2015, LNCS 9472,
  pp. 689–699; ECCC TR15-021), §1.2: the Col theorem "is easy to adapt" to
  show that Col on initially uncoloured graphs only takes the values `0` and
  `*`. **CITED** (ECCC text).

### 3.2 Hypotheses

The classical sources state the theorem for positions of Col on maps,
represented as graphs whose nodes are untinted, tinted black, tinted
white, or tinted both (ONAG p. 92; Winning Ways p. 47). Austin (p. 19 of the
thesis) notes the theory applies to arbitrary graphs. The proof above uses
nothing about the graph or the tints. The four node types are exactly the
four shadow-state cell types `o, b, w, .`.

### 3.3 Scope for the round-five streams (PROVED)

Covered, with no further argument:

- every shadow state `(A, B)` on any `h × w` grid, whether or not it is
  reachable from an empty board;
- every virtual region of a comparison (any masks, any induced subgraph,
  with cross-region edges deleted);
- every finite disjoint sum of these (a Col position on the disjoint union,
  Lemma 1.1(2));
- such sums plus any dyadic numbers and any number of stars, because
  `(x+ε*) + q + k* = (x+q) + (ε+k)*`. Number gadgets built as Col
  components (for example `bo = 1/2`) are Col positions anyway.

Not covered: games that are not Col positions or sums as above, for example
`↓ = {*|0}` used as a counterexample in `round4_star_bounds.md`, or any
hand-built auxiliary switch. The warnings in that file remain valid for such
games.

## 4. Consequences for the order and for turn bookkeeping

Let `G = x + ε*` and `H = y + η*` be values of Col positions (or of the sums
in §3.3), `q` a number.

**Table 1 (PROVED from F4).**

| Statement about `G` and `q` | `ε = 0` | `ε = 1` |
| --- | --- | --- |
| `G ≤ q` | `x ≤ q` | `x < q` |
| `G < q` | `x < q` | `x < q` |
| `G ≥ q` | `x ≥ q` | `x > q` |
| `G = q` | `x = q` | never |
| `G ∥ q` | never | `x = q` |
| `G + * ≤ q` | `x < q` | `x ≤ q` |
| `G ⧏ q`: White wins moving first in `G − q` | `x < q` | `x ≤ q` |
| `G ⧐ q`: Blue wins moving first in `G − q` | `x > q` | `x ≥ q` |

Between two such values: `G ≤ H` iff `x ≤ y` when `ε = η`, and iff `x < y`
when `ε ≠ η`. Sums add number parts and star bits mod 2.

**Corollary 4.1.** `G ≤ q` holds but `G < q` fails **only when `G = q`
exactly**. A nonpositivity proof that fails to give strictness has
identified an exact zero, not an infinitesimal.

**Corollary 4.2.** `T_q(G) ⟺ G < q ⟺ G+* < q ⟺ x < q`. (Round four defined
`T_q(G)` as `G ≤ q` and `G+* ≤ q`.)

**Corollary 4.3.** Outcome N iff `G = *`; outcome P iff `G = 0`; outcome L
iff `x > 0`; outcome R iff `x < 0`. A solver outcome certifies the exact
value in the N and P cases, and only the sign of `x` in the L and R cases.

**Corollary 4.4.** `G ⧏ 0` iff `G ≤ *` (both mean `x < 0`, or `x ≤ 0` with
`ε = 1`). That is: White wins moving first in `G` iff Blue loses moving
first in `G + *`. For general games only "`G ≤ * ⟹ G ⧏ 0`" holds
(`↓ ⧏ 0` but `↓ ≰ *`).

**Corollary 4.5 (the White-next rule).** After a Blue opening, the child
`K` must satisfy `K ⧏ 0`. For a Col child this means: `x_K < 0`, or `K = *`.
Equivalently, `K ≤ 0` and `K ≠ 0`, or `K = *`. If `K ≤ V` where `V` is a sum
of Col positions, numbers and stars with total `X + δ*`, the bound suffices
iff `X < 0`, or `X = 0` and `δ = 1`.

### 4.1 What this does to the round-four star bookkeeping

References are to [round4_star_bounds.md](../../round4_star_bounds.md) and
[round4_dx_progress.md](../../round4_dx_progress.md). Every game those notes
bound (DR, DV, DX, DJ, DD, RX, VX, XX, caps, separators, marked strips) is a
Col position, so §3.3 applies.

1. *Strictness / star stability.* Their one-way statements become
   equivalences: `T_q(G) ⟺ G < q ⟺ G + * < q`.
2. *Paired targets.* `T_1(RX_odd)`, `T_2(VX_odd)`, `T_1(XX_odd)` are
   **equivalent** to the round-three strict targets `RX_odd < 1`,
   `VX_odd < 2`, `XX_odd < 1`. The paired form adds nothing for genuine
   Col positions.
3. *The rejected extension.* `round4_star_bounds_check.py` deliberately
   refuses to pass from `RX < 1` to `RX + * < 1` at zero slack. For the
   actual Col position `RX` this step is **valid**: `RX < 1` means
   `x_RX < 1`, hence `RX + * < 1`. The checker is sound but more
   conservative than necessary.
4. *Numerical gap at equality.* If `c + Σ q_i = t` and one summand is a Col
   position with a strict bound `G_1 < q_1`, then its number part is
   `< q_1`, so the sum is `< t` whatever the star parity of the cap. The
   `↓` counterexample cannot arise among Col positions, numbers and stars.
5. *Staged rank `(width, stage)`.* The starred stage is automatic: once
   `G_n < q` is proved (Blue-first **and** White-first obligations),
   `G_n + * < q` follows. The stage index can be dropped.
6. *What does not disappear.* Proving `G_n < q` still needs a White-first
   argument (or a strictly smaller comparison bound). By Corollary 4.1 the
   only thing it must exclude is `G_n = q` exactly. No theorem here removes
   the White-first strictness work of the `white_first` stream.

### 4.2 Which handoff warnings simplify

- §1 and §29, "a next-player-winning outcome is not generically equal to
  star without additional structural facts", and §19F, "Outcome N means star
  in arbitrary partisan games": for Col positions (any graph, any masks) N
  **does** mean star and P means zero (Corollary 4.3). The warning remains
  for non-Col auxiliary games only.
- §11, "`DX_k ≤ 0` and `DX_k + * ≤ 0`": equivalent to `DX_k < 0`. The
  handoff's §32 observation that `DX_even < 0` can replace "the separate
  starred DX condition" is an equivalence, not just a sufficient
  replacement.
- §1, "after a Blue opening … merely showing the child ≤ 0 is not generally
  enough": still true, but the only failure is a child exactly equal to `0`
  (Corollary 4.5).
- §17, `V_n = 2L_n + *`: with `L_n = x + ε*`, `V_n = 2x + *`, so `V_n ≤ 0`
  iff `x_{L_n} < 0` and `V_n ⧏ 0` iff `x_{L_n} ≤ 0`. `L_12 = 0` gives
  `V_12 = *`, as recorded.
- §28–29 and every comparison-direction warning (`G ≤ V`, `V > 0` says
  nothing about `G`) are unchanged.

## 5. The empty board and colour symmetry

**Corollary 5.1 (PROVED).** If a graph automorphism `σ` maps `A` onto `B`
and `B` onto `A`, then `G ∈ {0, *}`. If `σ` is moreover a fixed-point-free
involution, `G = 0`.

*Proof.* `G = −G` by Lemma 1.1(1), so `x = −x`. For the second statement the
second player answers `v` with `σ(v)` (Tweedledum–Tweedledee; ONAG p. 95
states it for "a diagram which has a symmetry moving every node and
reversing any tints"). ∎

Every empty `m × n` board is therefore `0` or `*`; this matches Fenner et
al.'s remark for uncoloured graphs.

**Corollary 5.2 (PROVED).** Let `E` be colour-symmetric (e.g. an empty
board). Every Blue option `E^{L,v}` is `< 0`, `= 0`, or `= *`. Moreover
`E = *` iff some `E^{L,v} = 0`, and `E = 0` iff no `E^{L,v}` equals `0`.

*Proof.* Lemma 4 gives `E^{L,v} ≤ E + * ∈ {*, 0}`. If `E = 0` then
`E^{L,v} ≤ *`, i.e. `E^{L,v} < 0` or `E^{L,v} = *` (Table 1); and no option
of a zero game is `≥ 0`. If `E = *` then `E^{L,v} ≤ 0`, i.e. `< 0` or `= 0`,
and Lemma 5.3 gives an option equal to `0`. ∎

So the odd×odd conjecture is equivalent to: **no Blue opening on an empty
odd×odd board produces a position of value exactly zero.** Openings can
never have a positive number part.

**Lemma 5.3 (PROVED).** If `G = x + *`, some Blue option and some White
option equal `x` exactly.

*Proof.* `G ≰ x` (Table 1), so some `G^L ≥ x` or some Right option `x^R` of
the canonical number `x` has `x^R ≤ G`. The latter is impossible: `x^R > x`
is a number and `x^R ≤ x + *` would force `x^R < x`. So some `G^L ≥ x`;
Lemma 4 gives `G^L ≤ G + * = x`. Hence `G^L = x`. White is symmetric. ∎

**Corollary 5.4 (tempo structure; PROVED).** For `G = x + ε*` and a Blue
option `y + η*`: if `η = ε` then `y < x`; if `η ≠ ε` then `y ≤ x`. At a
Blue-only cell: `y ≤ x − 1`, strictly if `η ≠ ε`. So a move that keeps the
number part flips the star bit ("tempo move"). In a number position `G = x`,
a Blue option `x + *` is always reversible: by Lemma 5.3 it has a White
option equal to `x = G`.

**Corollary 5.5 (temperature).** Every Col position has temperature at most
`0`: numbers are cold and `x + *` is tepid. Huntemann's 2023 AMCAD slides
("Values, Temperatures, and Enumeration of Placement Games", BIRS workshop
23w2008) state that the boiling point of Col is `0` and credit Lexi Nash
with extending "numbers or numbers plus `*`" to many Col-like games; CITED
for the slide text, CITED-SECONDHAND for Nash's result (no paper found).

## 6. Further structure

### 6.1 Explosive vertices and separators (ONAG p. 94; PROVED here)

ONAG p. 94 (**CITED**): "if in some configuration the value is unaltered
both when we tint a certain node black and when we tint it white, then that
node is 'explosive' and may be deleted even when used to join the given
configuration to another."

**Proposition 6.1 (PROVED).** Let `G = G(Γ, A, B)` and let `V = C ∪ D` with
`C ∩ D = S` and no edge between `C∖S` and `D∖S`. Let `G_C` be the game on
`Γ[C]`, `G_C^b` the same with White removed on `S`, `G_C^w` with Blue
removed on `S`. If `G_C^b = G_C^w`, then

```math
G = G_C + G(Γ[D∖S], A∖C, B∖C) = G - S ,\qquad G_C = G_C^b = G_C^w = G_C - S ,
```

where `G − S` means `G(Γ, A∖S, B∖S)` (the cells of `S` made dead).

*Proof.* `G ≤ G(Γ, A, B∖S)` (removing White permissions). In that position
every edge between `S` and `D∖S` has a White-illegal endpoint in `S`;
deleting them (Lemma 2) and splitting (Lemma 1.1(2)) gives
`G ≤ G_C^b + G(D∖S)`. Dually `G ≥ G_C^w + G(D∖S)`. Monotonicity gives
`G_C^w ≤ G_C ≤ G_C^b`, so all three are equal and `G = G_C + G(D∖S)`.
`G_C − S` is `G_C^b` with Blue also removed on `S`, and `G_C^w` with White
also removed on `S`, so monotonicity gives `G_C^w ≤ G_C − S ≤ G_C^b`; hence
`G_C − S = G_C`. Finally `G − S` splits (Lemma 1.1(2), (3)) as
`(G_C − S) + G(D∖S)`, which is `G`. ∎

So an explosive separator set can be deleted outright, whatever its size;
the hypothesis only concerns the side `C`.

The handoff's §18 identity (two shared leaves on one vertex `x`) is ONAG's
p. 94 figure "blob with a node carrying two untinted pendant nodes = blob
with that node deleted": the fork `C = {x, ℓ1, ℓ2}` has `C^b = C^w = 0`
whatever the tint of `x`. ONAG p. 95 lists more explosive nodes: a node of
an attached cycle, "any node in an untinted chain with at least three
others on each side", and others marked by lightning bolts. In a full grid
no single cell is a cut vertex, so Proposition 6.1 applies only after play
has created cut vertices or separators.

### 6.2 Adjacent twins (ONAG p. 94; PROVED here)

ONAG p. 94 (**CITED**): "if two untinted nodes are joined to each other,
and to the same set of the remaining nodes, we may tint one black and the
other white."

**Proposition 6.2 (PROVED).** Let `u ~ v` with `N[u] = N[v]`.

(a) If `u, v ∈ A∖B`, then `G = G(Γ, A∖{v}, B)`; dually for White-only.

(b) If `u, v ∈ A∩B`, then `G = G(Γ, A∖{v}, B∖{u})`.

*Proof.* The transposition `σ = (u v)` is a graph automorphism, and
`N[w]` is `σ`-invariant for every `w`, because `N[u] = N[v]` and every
other `w` is adjacent to both twins or to neither. We use the elementary
criterion (proved like Lemma 1.2): *if every `G^L` has some `H^L ≥ G^L` and
every `H^R` has some `G^R ≤ H^R`, then `G ≤ H`.*

(a) `G(A∖{v}, B) ≤ G(A, B)` is monotonicity. For the reverse, Lemma 1.2
with `R` = all pairs `(G(A,B), G(A∖{v},B))` with `u, v ∈ A∖B`, together
with all identical pairs. Blue at `w` in the first game:

- `w ∈ {u, v}`: the child is `(A∖N[u], B)` (as `v ∉ B`, `N[v] = N[u]`);
  Blue at `u` in the second game gives the same position.
- `w ∈ N(u)∖{v}`: both twins leave `A`; Blue at `w` in the second game
  gives the identical child `(A∖N[w], B∖{w})`.
- `w ∉ N[u]`: copy `w`; the twins stay Blue-only, and the pair is in `R`.

White at `w ∈ B` in the second game (`w ≠ u, v`): copy `w`; twins stay
Blue-only in both, so the pair is in `R`. Hence `G(A,B) ≤ G(A∖{v},B)`.

(b) Let `G' = G(A∖{v}, B∖{u})`. We prove `G ≤ G'` by induction on
`|A ∪ B|`, using the criterion.

Blue moves in `G` at `w ∈ A`:

- `w = v`: child `X = (A∖N[u], B∖{v})`. Blue at `u` in `G'` gives
  `Y = (A∖N[u], B∖{u})`. `σ` fixes `A∖N[u]` and maps `B∖{v}` to
  `B∖{u}`, so `X = Y`.
- `w = u`: Blue at `u` in `G'` gives the identical child `(A∖N[u], B∖{u})`.
- `w ∈ N(u)∖{v}`: child `X = (A∖N[w], B∖{w})`. Blue at `w` in `G'` gives
  `(A∖N[w], B∖{u,w})`, which is `X` with White removed at `u`, hence `≥ X`.
- `w ∉ N[u]`: copy `w`. The children are `X` and `X'` (the construction of
  (b) applied to `X`, where both twins are still shared), and `X ≤ X'` by
  induction.

White moves in `G'` at `w ∈ B∖{u}`:

- `w = v`: child `(A∖{v}, B∖N[u])`, identical to White at `v` in `G`.
- `w ∈ N(u)∖{v}`: child `Y = (A∖{v,w}, B∖N[w])`. White at `w` in `G`
  gives `X = (A∖{w}, B∖N[w])`, where both twins are Blue-only; part (a)
  gives `X = Y`.
- `w ∉ N[u]`: copy `w`; induction gives `X ≤ X'` as before.

So `G ≤ G'`. Applying this to `−G = G(B, A)` gives
`G(B, A) ≤ G(B∖{v}, A∖{u})`, i.e. `G(A∖{u}, B∖{v}) ≤ G`; applying `σ`
turns the left side into `G'`. ∎

In a grid, adjacent cells have no common neighbour, so `N[u] = N[v]` forces
the live component to be an isolated domino. The proposition is recorded
for general virtual graphs only.

### 6.3 How much one permission is worth (PROVED, with one REFUTED claim)

**Proposition 6.3 (PROVED).** Let `u ∉ A`.

1. If `u ∉ B`: `G(A,B) ≤ G(A∪{u}, B) ≤ G(A,B) + 1`.
2. If `u ∈ B`: `G(A,B) ≤ G(A∪{u}, B) ≤ G(A,B) + 2`.

*Proof.* Lower bounds: monotonicity. (1) Compare `P = G(Γ, A∪{u}, B)` with
`Q + 1 = G(Γ, A, B) + ` (an isolated Blue-only vertex). Use Lemma 1.2 with
the invariant: either the isolated vertex is present, `A_P ⊆ A_Q ∪ {u}` and
`B_Q ⊆ B_P`; or it has been used, `A_P ⊆ A_Q`, `B_Q ⊆ B_P`; always
`u ∉ B_Q`. Blue at `u` in `P` is answered by Blue at the isolated vertex:
`A_P∖N[u] ⊆ A_Q` and `B_Q ⊆ B_P∖{u}` because `u ∉ B_Q`. Blue at `v ≠ u` is
copied (`v ∈ A_Q`). White's moves in `Q` are copied in `P` (`u ∉ B_Q`, so
`u` is never the copied cell). All inclusions persist. (2) Removing White's
permission at `u` first: `G(A∪{u},B) ≤ G(A∪{u}, B∖{u}) ≤ G(A, B∖{u}) + 1`
by (1), and `G(A, B∖{u}) ≤ G(A,B) + 1` by the colour dual of (1) (valid as
`u ∉ A`). ∎

**Claim 6.4 (REFUTED).** "If `u ∈ B∖A` then `G(A∪{u}, B) ≤ G(A,B) + 1 + *`."
A random search (60 s) found no counterexample and the single White-only
cell (`−1` becomes `*`) attains `1+*`, but the exhaustive run finds
failures. Smallest, checked by hand: the path `www..` (1×5; cells 0–2
White-only, 3–4 dead), `u` = cell 1. Before: White has two moves (an end,
then the other end), `G = −2`. After making `u` shared: Blue at `u` leaves
two isolated White-only cells (`−2`); White at an end leaves a Blue-only
cell and a White-only cell (`1 − 1 = 0`), White at `u` leaves nothing, so
every White option is `0`. So
`G' = {−2 | 0} = −1`, an increment of exactly `1`, and `1 ≰ 1+*`. The
exhaustive maximum increment at a White-only cell is `3/2`, on 2×3, 2×4 and
3×3 alike; a 2×3 witness is `ow./ww.` with `u` the bottom-middle cell.
Failure counts of the claim: 32/1,280 (1×5), 164/6,144 (1×6), 376/6,144
(2×3), 8,728/131,072 (2×4), 34,754/589,824 (3×3). Proposition 6.3(2)
(`≤ 2`) is the best proved bound; whether `2` is attained is open.
Proposition 6.3(1) and the upper bound of 6.3(2) had 0 failures on all of
these grids.

### 6.4 Shared-cell sufficiency is false (REFUTED)

Claim tested: "if Blue wins moving first and some Blue-legal cell is also
White-legal, some winning Blue move is at a shared cell." Counterexample on
the 2×3 grid, found by exhaustive search:

```text
bob
.w.
```

Value `1`. Blue at the shared centre-top cell leaves only the White-only cell
(value `−1`, White to move wins). Blue at either Blue-only corner leaves
`b` plus a White-only domino, `1 + (−1) = 0`, a win for Blue. Exhaustive
failure counts: 10 of 1,549 relevant 2×3 states, 664 of 109,772 on 3×3.

## 7. Computational checks

All code is in this directory; runs used one thread.

- [cgt_core.py](cgt_core.py): general canonical forms (dominated deletion,
  reversible bypass, Conway order); no Col-specific assumption. Sanity
  checks reproduce `↑`, `*2` and `{1|0}` as non-numbers, and every Linear Col
  value in Uiterwijk's Theorem 2 (up to length 7). `SumOutcome` certifies a
  claimed value by plain minimax on `G − x − ε*`, independently of the
  canonical-form code.
- [col_values_exhaustive.py](col_values_exhaustive.py): **every** shadow
  state of 20 small graphs, 640,148 states in total: grids 1×1–1×7, 2×2,
  2×3, 2×4, 3×3 (all 262,144 states), cycles `C_3`–`C_7`, `K_{1,4}`, `K_4`,
  `K_{2,3}`, and the 9-vertex cross. Zero failures of: value is `x` or
  `x+*`; all four inequalities of Lemma 4 at every option; Lemma 5.3;
  Corollary 4.3. Largest denominator seen: 8 (3×3, 2×4, 1×6, 1×7, `C_7`,
  cross).
- [col_values_check.py](col_values_check.py): random positions on random
  graphs (≤10 vertices, three edge densities) and random grid subgraphs
  (up to 4×4 and 3×5), random masks, plus random explosive-vertex and twin
  instances. Seed 1, 60 s: see `col_values_check_seed1.json`.
- [col_values_extra.py](col_values_extra.py): Proposition 6.3 and
  Claim 6.4, exhaustively over grids 1×5, 1×6, 2×3, 2×4, 3×3 and every cell
  `u`; explosive separator sets (Proposition 6.1, `|S| ≤ 2`, checking both
  `G = G_C + (D∖S)` and `G = G − S`) on random graphs. Results:
  `col_values_extra.json`.
- [col_fastval.cpp](col_fastval.cpp): a fast grid evaluator that **uses**
  Theorem 5 (values are stored as a fixed-point number and a star bit, and
  combined by the two cases of the proof), aborting if any theorem
  conclusion (`m ≤ M`, a common star bit) fails. It never aborted.
  [fastval_crosscheck.py](fastval_crosscheck.py) compares it with
  `cgt_core.py` on 1,950 random grid states from 2×3 to 4×4: 0 mismatches.
  It is used for the empty-board data in §5 of
  [GENERAL_IDEAS.md](GENERAL_IDEAS.md).

EVIDENCE only; the proofs above do not rely on any of it.

## 8. Things that did not work or remain open

- ONAG (p. 93, 1976) did not know whether denominators `≥ 16` occur;
  Winning Ways (p. 51) reports Nick Inglis's result that denominators are
  unbounded (CITED-SECONDHAND for Inglis's proof, which I did not find).
  Here, small grids gave denominators up to 8 only; this is not a bound.
- No lower bound of the form `G^{L,v} ≥ G − c` exists: a Blue move can be
  arbitrarily bad (Blue at the centre of a star whose leaves are Blue-only).
- The theorem converts every sign question into "number part and star bit"
  but gives no way to compute the number part of large boundary games; it
  removes bookkeeping, not the induction.
