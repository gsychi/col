> **Latest status (2026-09-23):** see the
> [round-five handoff](round5/HANDOFF.md) first. It supersedes the "not
> solved" and "next direction" sections below where they conflict: the 3×n
> package is fully machine-checked, Col values are proved to be `x` or `x+*`,
> five-row exact values reach widths 7–9, and 5×9 is partly certified.
>
> **Repository context:** This handoff is the broader research map supplied
> after the all-width proof write-up. The theorem and its six-case induction
> are documented separately in
> [`../empty_3xn_theorem.md`](../empty_3xn_theorem.md). This file preserves the
> game conventions, gadget context, five-row results and obstructions, and
> proposed next targets. The five-row program and general odd-by-odd target
> remain open.

# Col Research Handoff: 3×n Proof, Five-Row Program, Obstructions, and Next Targets

## 0. Goal of the project

We are studying normal-play **Col** on rectangular grid graphs.

The ultimate conjectural target is roughly:

> Empty odd-by-odd rectangular Col boards are second-player wins / have value \(0\).

The major completed result is much stronger than the original computational \(3\times15\) target:

$$
\boxed{\text{Every empty }3\times n\text{ Col board has value }0.}
$$

Thus every \(3\times(4k+1)\) and \(3\times(4k+3)\) board is solved for arbitrary width.

The current research frontier is **height 5** and, beyond that, some possible general height-lifting mechanism. There is **not yet** a theorem for every empty \(5\times n\), every odd \(5\times n\), or arbitrary odd-by-odd rectangles.

---

# 1. Game conventions

Blue is Left / the positive player. White is Right / the negative player.

A player may not place a stone adjacent orthogonally to a stone of their own color. A player with no legal move loses.

A position can be represented by two legality sets:

* \(A\): cells currently legal for Blue;
* \(B\): cells currently legal for White.

For a cell \(v\), let \(N[v]\) be \(v\) together with its orthogonal neighbors.

Then:

$$
\text{Blue at }v:
(A,B)\mapsto(A\setminus N[v],B\setminus\{v\}),
$$

$$
\text{White at }v:
(A,B)\mapsto(A\setminus\{v\},B\setminus N[v]).
$$

Permission diagrams use:

* `o`: legal for both;
* `b`: Blue only;
* `w`: White only;
* `.`: neither.

These are **permissions, not stones**.

CGT interpretation:

* \(G\le0\): Blue loses if Blue moves next.
* \(G<0\): White wins regardless of who moves first.
* \(G=0\): second-player win.
* \(*=\{0\mid0\}\), so \(*\ne0\), but \(*+*=0\).

Be very careful with turn order. After a Blue opening, White is next, so merely showing the child \(\le0\) is not generally enough unless White has already made a reply. A strictly negative bound immediately after Blue's move is sufficient.

---

# 2. Core comparison principle

This is the fundamental proof tool.

Partition an actual position into disjoint virtual regions \(T_i\), optionally separated by dead gaps.

Let the union of virtual Blue legalities be \(A^\*\), and virtual White legalities be \(B^\*\).

Require:

1. Every actual Blue move remains available virtually:

   $$
   A_{\rm actual}\subseteq A^\*.
   $$

2. Every virtual White move is genuinely available:

   $$
   B^\*\subseteq B_{\rm actual}.
   $$

3. For every grid edge crossing between two virtual regions, at least one endpoint is permanently White-unavailable virtually.

Then ignore all cross-region edges. The virtual position is a disjoint sum and

$$
\boxed{
G_{\rm actual}\le\sum_i T_i.
}
$$

Intuition: we are allowed to strengthen Blue and restrict White. Ignoring cross-region edges can only make Blue stronger provided those ignored edges cannot create extra White legality.

This is a true game-order inequality, not merely an outcome argument, and it remains valid with auxiliary dyadic numbers/stars added.

This principle is the basis of almost every construction below.

---

# 3. Completed theorem: every empty \(3\times n\) board is zero

## The theorem

For all \(n\ge1\),

$$
\boxed{H_n=0}
$$

where \(H_n\) is the ordinary empty \(3\times n\) Col board.

This is a **computer-assisted mathematical proof**:

* a finite set of small games/tiles is exhaustively certified;
* an ordinary written induction proves the unbounded family;
* finite testing of large widths is only regression testing, not extrapolation.

---

# 4. Three-row reusable gadgets

The central finite gadgets include:

* \(E_4\), width 4, upper bound \(0\);
* \(\bar E_4\), horizontal reflection, upper bound \(0\);
* \(F_1\), width 1, upper bound \(0\);
* \(J_5\), width 5, upper bound \(0\);
* \(K_{\rm corner}\), width 3, upper bound \(0\);
* \(K_{\rm outer2}\), width 7, upper bound \(0\);
* \(K_{\rm outer4}\), width 7, upper bound \(0\);
* \(T_{\rm middle1}\), width 6, upper bound \(0\);
* \(Z_7\), width 7, upper bound \(0\).

For example,

```text
E4:

ooob
booo
ooob
```

and

```text
Ebar4:

booo
ooob
booo
```

Boundary masks are used to guarantee that White cannot interact across tile seams.

There is also a three-column cap \(C_3\) with

$$
C_3\le\frac14.
$$

Most importantly, after Blue opens an odd-local-parity square in \(E_4\), the opened tile has

$$
E_4^{\rm opened}\le-1.
$$

These are certified game-order inequalities, not guessed numerical values.

---

# 5. How the three-row proof works

## Even widths

A half-turn is a fixed-point-free automorphism. The second player responds at the half-turned cell.

The color-symmetric invariant guarantees legality of the reply.

Thus every even-width \(3\times n\) is \(0\).

## Width \(4k+1\)

Use

$$
E_4^kF_1.
$$

All pieces are nonpositive; seam masks are compatible.

Therefore

$$
H_{4k+1}\le0.
$$

The empty board is self-conjugate, so it must equal \(0\).

## Width \(4k+3\)

Widths 3, 7, and 11 are independently certified bases.

For \(n=4k+3\ge15\), normalize a Blue opening by horizontal/vertical reflection to

$$
r\in\{0,1\},
\qquad
0\le c\le2k+1.
$$

Then six cases cover every first move.

### Odd checkerboard parity

If \(r+c\) is odd, use

$$
E_4^kC_3.
$$

The opened \(E_4\) contributes at most \(-1\), and the cap contributes \(+1/4\):

$$
G\le-1+\frac14=-\frac34<0.
$$

So White already wins from the post-Blue position.

### Outer-row special cases

Various congruence classes of \(c\) are handled with:

$$
K_{\rm corner}\bar E_4^k,
$$

$$
E_4^aK_{\rm outer2}\bar E_4^b,
$$

or

$$
E_4^aK_{\rm outer4}\bar E_4^b.
$$

White has an explicit local response and the entire post-reply board is dominated by a sum of nonpositive certified games.

### Middle row, \(c\equiv1\pmod4\)

Use

$$
E_4^aT_{\rm middle1}E_4^bJ_5.
$$

Again the virtual sum is nonpositive.

### Middle row, \(c\equiv3\pmod4\): the recursive case

This is the important conceptual step.

Blue opens at

$$
(1,c).
$$

White responds at

$$
(0,c+1).
$$

Blue's middle-row stone makes **all three cells of column \(c\) Blue-illegal**.

White voluntarily retires the two remaining outer cells of column \(c\).

Thus column \(c\) becomes a completely dead separator.

The left region has width \(c\). Restore any Blue permissions removed at its right boundary. This only strengthens Blue, and turns the virtual left side into an ordinary empty \(3\times c\) board:

$$
H_c.
$$

Since \(c<n\), strong induction gives

$$
H_c=0.
$$

The right side has width

$$
s=n-c-1\equiv3\pmod4
$$

and is covered by

$$
Z_7\bar E_4^{(s-7)/4}.
$$

Therefore

$$
G_{\rm after\ White}
\le
H_c+Z_7+\sum\bar E_4
\le0.
$$

The only recursive call is to a **strictly smaller ordinary empty rectangle**.

This dead-column macrotile is what closed the previous obstruction at interior middle-row openings.
Hence all first moves are answered, \(H_n\le0\), and color symmetry gives \(H_n=0\).

---

# 6. Why height 5 is genuinely harder

Do NOT assume the \(3\times n\) recursive trick lifts directly.

In height 3, Blue at the middle cell of a column kills that entire column for Blue.

In height 5, Blue at the center kills only rows \(1,2,3\); rows \(0,4\) may remain legal.

Therefore a single center move does **not** create a free dead-column separator.

This is the central geometric reason the three-row proof does not automatically height-lift.

A generalized proof needs richer boundary states, a wider separator, an adaptive boundary protocol, or a different comparison principle.

---

# 7. Exact five-row separator catalog

A major step was to stop asking only for zero-valued separator columns and instead enumerate all possible one-column contracts.

After a Blue opening in row \(r\), the separator column has some remaining Blue permissions. We can voluntarily choose a subset of remaining White permissions.

Across the five possible opening rows and 16 White subsets there are 80 contracts.

All 80 were exactly evaluated as short games.

Observed values included:

$$
-\frac32,-1,-\frac12,-\frac12+*,-\frac14,0,*,
\frac12,1,1+*,2.
$$

The key lesson:

> The numerically best separator is not automatically the best separator. Its **boundary support** matters equally because it determines the side games.

For a center opening, examples include:

```text
o...o     value 0
bw.wb     value 0
ow.wo     value -1
```

but each requires different White exclusions on adjacent side regions.

---

# 8. The D-family: first useful five-row boundary state

Define \(D_n\) on a \(5\times n\) strip with first column

```text
o
b
w
b
o
```

i.e.

$$
D=\texttt{obwbo}.
$$

All later columns are neutral.

Equivalently:

* Blue lacks row 2 at the restricted end;
* White lacks rows 1 and 3.

Initially certified:

$$
D_1=0,
\quad
D_2=0,
\quad
D_3=-\frac12,
\quad
D_4=0,
\quad
D_5<0.
$$

A useful center-opening decomposition on \(5\times7\) was:

$$
\bar D_3
+
(\texttt{bw.wb})
+
D_3.
$$

Since the center separator is zero,

$$
-\frac12+0-\frac12=-1.
$$

Thus that actual opened \(5\times7\) position is \(\le-1\).

This demonstrated that five-row signed separator decompositions can genuinely work.

---

# 9. Endpoint-state framework

The research then evolved from one-ended \(D_n\) into two-ended boundary-state families.

The important endpoint column patterns are:

| State | pattern top→bottom |
| ----- | ------------------ |
| \(D\) | `obwbo`            |
| \(U\) | `wbobo`            |
| \(V\) | `bwbob`            |
| \(X\) | `bowob`            |
| \(R\) | `wobob`            |
| \(J\) | `owobo`            |

Notation:

* \(DU_n\): D on one end and U on the other;
* \(DV_n\);
* \(DX_n\);
* \(DR_n\);
* \(DJ_n\);
* \(DD_n\).

A lone \(X_n\), \(R_n\), etc. means one restricted end and one neutral end.

At width one, end restrictions intersect rather than being counted twice.

---

# 10. Six-case reduction for every Blue opening in \(DD_n\)

This is probably the strongest unfinished five-row result.

For odd \(n\), every legal Blue first move in \(DD_n\) can be reduced parametrically to smaller boundary games.

Let Blue open at \((r,c)\), normalize vertically to \(r\in\{0,1,2\}\), and define

$$
a=c,
\qquad
b=n-c-1.
$$

Then:

| Blue opening   | White reply | separator |    value | bound                 |
| -------------- | ----------- | --------- | -------: | --------------------- |
| \(r=0,c\) odd  | none        | `.wbob`   |    \(0\) | \(DU_a+DU_b\)         |
| \(r=0,c\) even | \((2,c)\)   | `...bo`   |  \(1/2\) | \(DR_a+\frac12+DR_b\) |
| \(r=1,c\) even | none        | `w.wbo`   | \(-3/2\) | \(DV_a-\frac32+DV_b\) |
| \(r=1,c\) odd  | none        | `...ob`   |  \(1/2\) | \(DJ_a+\frac12+DJ_b\) |
| \(r=2,c\) even | \((0,c)\)   | `....o`   |    \(*\) | \(DX_a+*+DX_b\)       |
| \(r=2,c\) odd  | none        | `bw.wb`   |    \(0\) | \(DD_a+DD_b\)         |

This reduction is **parameterized and valid for arbitrary width**. It does not come from testing finitely many widths.

This means the Blue-first part of a possible \(DD\) induction has essentially been reduced to proving the auxiliary families.

---

# 11. Conditional \(DD\) induction

An early sufficient target was:

For positive odd \(k\),

$$
DU_k<0.
$$

For positive even \(k\),

$$
DV_k\le\frac12,
$$

$$
DR_k\le-\frac12,
$$

$$
DX_k\le0
\quad\text{and}\quad
DX_k+*\le0.
$$

For positive odd \(k\),

$$
DJ_k<-\frac14.
$$

Together with smaller-width \(DD\) negativity/nonpositivity, these imply

$$
DD_n\le0.
$$

The six cases combine numerically:

* U case: negative + negative;
* V case:

  $$
  \frac12-\frac32+\frac12=-\frac12;
  $$
* R case:

  $$
  -\frac12+\frac12-\frac12=-\frac12;
  $$
* J case:

  $$
  <-\frac14+\frac12-\frac14=0;
  $$
* X case: absorb the separator star using one side's \(DX+*\le0\);
* D case: two smaller odd \(DD\) games, one strictly negative.

This gives a complete **conditional Blue-first induction step** for \(DD_n\).

Important: it does **not** automatically propagate \(DD_n<0\). A separate uniform White-first argument is needed to establish strictness.

---

# 12. Improvement to the DR requirement

The original conditional proof demanded

$$
DR_k\le-\frac12.
$$

A better boundary response weakened this.

If Blue opens at the top-left corner of \(DD_n\), instead of White playing the same-column middle cell, White can play the **bottom-left corner**.

The resulting first column has two opposite private cells whose values cancel, producing zero separator cost, and the rest is an \(RD_{n-1}\), i.e. reflected \(DR_{n-1}\).

Thus

$$
G_{\rm after\ reply}\le DR_{n-1}.
$$

This lets the uniform sufficient DR hypothesis be weakened to

$$
\boxed{DR_k\le-\frac14}
$$

at positive even widths:

for an interior opening,

$$
-\frac14+\frac12-\frac14=0,
$$

while boundary openings incur no \(+1/2\) separator cost.

Use this corrected \(-1/4\) target rather than the older \(-1/2\) target.

---

# 13. Finite five-row certificates already obtained

At various stages we independently certified:

$$
DD_7=-1.
$$

$$
DX_2=-1,\qquad
DX_4=-\frac12,\qquad
DX_6=-\frac14.
$$

$$
DR_2=DR_4=DR_6=-\frac12.
$$

$$
DU_k\le-\frac18
\quad
(k=1,3,5,7).
$$

$$
DV_k\le\frac12
\quad
(k=2,4,6).
$$

$$
DJ_1=-\frac12+*,
\qquad
DJ_3=-\frac34,
\qquad
DJ_5=-\frac58.
$$

Also:

$$
X_2=*,
\quad
X_4=0,
\quad
X_6>0,
$$

and

$$
R_2=*,
\quad
R_4=0,
\quad
R_6>0.
$$

Thus the tempting claim that one-ended X or R families remain zero is **false**.

Likewise,

$$
J_1=*,
\quad
J_3=0,
\quad
J_5=*.
$$

So symmetry of a boundary game must not be casually interpreted as zero.

---

# 14. Horizontal reduction into three-row cores

We then tried exploiting the solved \(3\times n\) world by peeling off two rows as a checkerboard-zero band.

Define restricted three-row cores \(H_n,P_n,L_n,C_n\).

For positive even \(n\):

$$
DR_n\le H_n,
$$

$$
DV_n\le P_n,
$$

$$
DX_n\le L_n.
$$

For positive odd \(n\):

$$
DD_n\le C_n+\frac12.
$$

These are genuine arbitrary-width comparison theorems.

The mechanism is:

* restrict White in a two-row band to one checkerboard class;
* partition it into \(2\times2\) squares;
* each square is zero;
* impose seam restrictions on the remaining three-row core.

This was a very promising attempt to reduce five-row boundary families to specialized three-row games.

---

# 15. The L-family

The most important projected three-row core became \(L_n\).

For positive even \(n\), \(L_n\) is a \(3\times n\) permission game with:

Blue forbidden at:

$$
(0,0),\quad(0,n-1).
$$

White forbidden at:

$$
(1,0),\quad(2,n-1),
$$

and at every

$$
(0,c)\quad\text{with }c\text{ odd}.
$$

Small exact values originally looked spectacular:

$$
L_2=-1,
$$

$$
L_4=-\frac12,
$$

$$
L_6=-\frac14,
$$

$$
L_8=-\frac18,
$$

$$
L_{10}=-\frac1{16}.
$$

This strongly suggested a beautiful formula

$$
L_{2k}=-2^{1-k}.
$$

That conjecture is **false**.

---

# 16. Major obstruction: \(L_{12}=0\)

The exact value is

$$
\boxed{L_{12}=0}.
$$

Even worse for that proof route:

$$
\boxed{L_n\ge0
\quad\text{for every even }n\ge12.}
$$

And for every even \(n\ge14\),

$$
\boxed{
L_n
\ge
\frac14
\left\lfloor
\frac{n-14}{10}
\right\rfloor.
}
$$

So \(L_n\) eventually has arbitrarily large certified positive lower bounds.

Examples:

$$
L_{24}\ge\frac14,
$$

$$
L_{34}\ge\frac12,
$$

$$
L_{100}\ge2.
$$

Therefore the strategy

$$
DX_n\le L_n
$$

cannot prove a uniformly negative or even uniformly nonpositive bound for \(DX_n\).

This route is **mathematically dead**, not merely computationally unfinished.

---

# 17. Infinite obstruction to the fixed DD horizontal projection

Consider the middle-row construction on

$$
DD_{2n+1},
$$

with Blue at \((2,n)\) followed by White at \((0,n)\).

The vertical split gives

$$
G_{\rm after\ reply}
\le
DX_n+*+DX_n.
$$

If each \(DX_n\) is then replaced by the fixed checkerboard horizontal projection into \(L_n\), the resulting specific virtual game is

$$
V_n=2L_n+*.
$$

For \(n=12\),

$$
V_{12}=*.
$$

For every even \(n\ge12\), because \(L_n\ge0\), Blue can take the separator star first and leave White moving in a nonnegative game.

Thus this exact relaxed construction fails for

$$
DD_{25},DD_{29},DD_{33},DD_{37},\ldots
$$

and in fact for the entire corresponding infinite family.

CRITICAL LOGIC WARNING:

$$
G_{\rm actual}\le V_n.
$$

Showing that the *larger virtual game* \(V_n\) is Blue-winning does **not** show the actual DD position is Blue-winning.

So this is:

* a proof that this particular comparison construction fails;
* **not** a counterexample to the DD conjecture;
* **not** a counterexample to empty odd rectangles.

---

# 18. Other useful exact identity: explosive/live-node deletion

Suppose \(u,v\) are two distinct shared cells whose only live neighbor is the same vertex \(x\).

Then the exact Col value is unchanged if all three \(u,v,x\) are deleted:

$$
\boxed{
G=G-\{u,v,x\}.
}
$$

The outside neighborhood of \(x\) may be arbitrary.

Reason:

* if opponent enters one leaf, reply in the other leaf;
* if opponent enters \(x\), reply in one leaf;
* then use copy strategy on the common outside graph.

This is an exact identity rather than a one-sided comparison.

Consequences include simplification of T-shaped or cross-shaped structures and possible recursive graph decompositions without imposing permanent White restrictions at every seam.

This mechanism may be highly relevant for future generalized proofs.

---

# 19. Failed or dangerous shortcuts

A future agent must NOT silently use any of the following.

## A. “Any partially occupied \(3\times n\) is zero”

False / unjustified.

The theorem is for the **ordinary empty rectangle**. Boundary permissions and holes matter.

## B. “A bounding box with holes is an empty rectangle”

False.

## C. Cutting interactions without checking White seam support

Invalid.

Every removed cross-region White interaction must be justified by a permanently White-forbidden endpoint.

## D. “The \(3\times3\) end cap can just be appended”

This was one of the early failed intuitions. The actual \(4k+3\) proof needs the certified exceptional tiles and recursive dead-column macrotile.

## E. “A middle move kills a column at arbitrary odd height”

False.

True only in height 3.

## F. “Outcome N means star in arbitrary partisan games”

Not in general.

For genuine Col positions there is a classical Conway/Guy result that Col values are numbers or number-plus-star, but auxiliary games and arbitrary constructions must stay within scope.

## G. “A fixed boundary state stays numerically stable when neutral columns are inserted”

False.

Example:

$$
DX_4=-\frac12,\qquad
DX_6=-\frac14.
$$

Likewise X and R change behavior with width.

## H. “Two symmetry axes whose fixed paths are zero imply the whole graph is zero”

False.

A checked symmetric induced-grid counterexample exists.

## I. “Failure to find a construction proves a loss”

Never.

Solver budget exhaustion or no witness in a bounded palette means **Unknown**, unless the searched construction class was exhaustively characterized and the claim is explicitly restricted to that class.

---

# 20. Why simple height extrusion failed

A natural idea was:

> Take a certified \(3\times4\) zero tile and add two rows to make a reusable \(5\times4\) tile.

This was tested and did not produce the seam-compatible White supports required by the comparison theorem.

The broader lesson is:

> Height-lifting requires four-sided interface information, not just a scalar game value.

A reusable height-lifting rectangle probably needs a contract specifying at least:

* north White support;
* south White support;
* west White support;
* east White support;
* numerical upper bound;
* behavior under corner junctions.

Straight bands alone are insufficient because horizontal and vertical seams meet at corners.

Promising height increments should not automatically be assumed to be \(+2\); \(+4\) or \(+6\) might yield better interfaces.

---

# 21. Static mosaic searches already attempted

Several bounded palettes of:

* certified rectangles;
* T pieces;
* cross pieces;
* bent three-cell pieces;
* singleton stars;
* zero/star cancellation patterns;

were searched for compatible full covers.

No covers were found in those palettes for several small targets including

$$
5\times5,\quad
5\times7,\quad
5\times9,\quad
7\times7,\quad
7\times9.
$$

These are useful negative engineering results but **not** general impossibility theorems.

Likewise, various fixed-reply, mirror, paired-end, repeatable-block, and neutral-tail controllers were tried.

Do not simply rerun the same fixed static palette expecting magic.

---

# 22. Where the five-row program currently stands

We have accomplished something substantial:

### Solved

1. Exact all-width theorem for empty \(3\times n\).
2. General one-sided comparison machinery.
3. Exact finite certificate infrastructure.
4. Complete catalog of single-column five-row separators.
5. Useful boundary family \(D\).
6. Two-ended state system \(D,U,V,X,R,J\).
7. A complete parameterized six-case reduction for **every Blue opening in \(DD_n\)**.
8. Multiple small-width certificates supporting the required auxiliary inequalities.
9. Arbitrary-width horizontal comparisons into three-row cores.
10. A better DR boundary response reducing the required uniform bound to \(-1/4\).
11. Exact node-deletion identity.
12. A rigorous infinite obstruction killing the fixed \(L\)-projection route.

### Not solved

1. Full \(D_n\) induction.
2. Full \(DD_n\) induction.
3. Uniform strict negativity needed to propagate some DD hypotheses.
4. Arbitrary-width \(DU,DV,DR,DX,DJ\) bounds.
5. Bridge from boundary-family theorem back to every empty \(5\times n\) opening.
6. Full empty \(5\times n\).
7. Any general \(5\to7\) height lift.
8. Arbitrary odd-by-odd rectangles.

---

# 23. Most promising next research direction

The old strategy of reducing everything through a **fixed checkerboard projection into \(L_n\)** should be abandoned.

The next attempt should probably focus on **adaptive finite interfaces**.

The desirable object is not necessarily one tile with a fixed White boundary mask.

Instead, define a finite set of interface states \(S\), where a region has a certified game bound plus a boundary state.

Moves near the boundary can cause the state to transition:

$$
S_i\xrightarrow{\text{move}}S_j.
$$

The goal is a finite closed protocol:

* every Blue move from every certified state has an allowed White response;
* after the response, the position decomposes into smaller regions whose states belong to the same finite family;
* width strictly decreases or another well-founded rank decreases.

This is essentially a finite-state induction / automaton proof rather than a static tiling proof.

Why this is promising:

* fixed masks may unnecessarily retire White cells;
* the \(L_n\) obstruction arose partly because too much interaction was thrown away;
* an adaptive interface could preserve useful cross-boundary options until they actually become unsafe.

A useful computational search would therefore search for a **closed boundary-state graph**, not merely a repeated tile.

---

# 24. Another promising direction: derive recurrences directly on five-row boundary games

The six-case \(DD\) reduction indicates that the correct induction object may be a **mutually recursive family of boundary states** rather than the ordinary empty board.

Potential program:

1. Start with

   $$
   D,U,V,X,R,J.
   $$

2. Enumerate every relevant Blue and White opening type under symmetry.

3. Generate all safe separator choices.

4. Record resulting smaller boundary states.

5. Search for a finite closed subset of states.

6. Associate symbolic bounds such as

   $$
   \le0,\quad
   <0,\quad
   \le\frac12,\quad
   \le-\frac14,\quad
   \le q+*
   $$

   rather than insisting on exact values.

7. Solve the induced system of inequalities/recurrences.

8. Only after obtaining a symbolic closed system generate local certificates for finite exceptional cases.

The state search should respect **turn information** explicitly.

---

# 25. Do not over-optimize scalar tile values

A separator with value \(-1\) can be worse globally than one with value \(0\) if its interface forces expensive restrictions on both side regions.

Search objective should therefore consider a vector like:

$$
(\text{game bound},
\text{left White support},
\text{right White support},
\text{Blue exclusions},
\text{state class})
$$

rather than scalar value alone.

Pareto-optimal interface contracts are more relevant than numerically minimal separators.

---

# 26. Potential use of three-row theorem going forward

The completed \(3\times n\) theorem remains useful, but avoid over-projecting onto specialized permission cores.

Good uses:

* whenever a virtual region is genuinely relaxed to a full empty \(3\times m\) rectangle;
* when a separator completely disconnects a three-row component;
* as a macrostate in recursive constructions;
* for regions where restoring Blue permissions and restoring White permissions is directionally valid.

Bad use:

* assuming a restricted three-row family behaves like the empty theorem;
* throwing away interactions to manufacture an arbitrary \(3\times n\) box.

The magical aspect of the \(3\times(4k+3)\) proof is that the recursive side can be relaxed to an **actual empty board**, not merely a weird boundary game.

Try to create similar situations in height 5.

---

# 27. Search ideas worth exploring

## 27.1 Wider separators

A 1-column separator may be too weak in height 5.

Search 2-, 3-, or 4-column separators whose post-response Blue legality becomes sufficiently dead to partition the board.

Optimize the resulting side boundary states, not just separator value.

## 27.2 Two-move or delayed separators

Maybe White should not create the full separator immediately.

Permit a bounded local dialogue:

$$
B_1,W_1,B_2,W_2,\ldots
$$

inside a small neighborhood until a certified separator emerges.

The result could be a small AND/OR strategy gadget with leaves that enter the known boundary-family induction.

## 27.3 Explosive-node simplification

Search for moves creating shared pendant leaves so the exact deletion identity can eliminate live articulation vertices.

This may create separators dynamically without permanently restricting White.

## 27.4 Pairing plus local defect repair

Use reflection or conjugate pairing for a large region, with a small certified gadget handling an unmatched center/boundary defect.

But interface behavior of the paired region must itself be certified.

## 27.5 Four-sided boundary algebra

Develop a tile algebra where every rectangle records N/S/E/W White supports and an upper bound.

Composition horizontally and vertically should become explicit compatibility operations.

Corner-junction tiles may be essential.

## 27.6 Search state closure instead of values

Given a finite candidate set of boundary masks, compute which states map to which states under legal opening/reply templates.

Try to identify a strongly connected / inductively closed family with a descending width parameter.

---

# 28. Verification philosophy

The research intentionally separates:

### Discovery

May use:

* minimax;
* SAT/MIP;
* exhaustive enumeration;
* heuristic search;
* transfer/state search.

### Proof

Every accepted finite claim should have an independent search-free verifier that checks:

* root geometry;
* all legal moves of the player being universally quantified;
* supplied legal replies;
* correct successor checkpoint;
* strict decrease of a finite rank;
* auxiliary dyadic/star moves;
* boundary masks;
* seam compatibility;
* width-decreasing recursive calls.

Finite regression testing at widths up to 100 or 10,000 is useful but must never be presented as the proof of an infinite theorem.

The completed \(3\times n\) proof used 26 ordinary response-DAG certificates plus five numerical certificates, covering 44,664 checkpoints and 191,527 universally checked move-response edges.

The later five-row work produced much larger independent certificate collections as well; certificate volume is not itself the theorem—the written parameterized reductions are what turn finite certificates into infinite claims.

---

# 29. Important logical direction reminders

If

$$
G_{\rm actual}\le V,
$$

then:

* \(V\le0\) proves \(G_{\rm actual}\le0\);
* \(V<0\) proves \(G_{\rm actual}<0\).

But:

* \(V>0\) tells you essentially nothing about the sign of \(G_{\rm actual}\).

This issue is especially important in the \(L_n\) obstruction.

Likewise:

* a Blue-first losing certificate proves \(\le0\);
* it does not prove equality;
* to prove \(=0\), obtain both \(\le0\) and \(\ge0\), or use valid self-conjugacy together with one inequality;
* a next-player-winning outcome is not generically equal to star without additional structural facts.

---

# 30. Suggested immediate assignment for a new AI research agent

The highest-value concrete task is:

> **Find a finite adaptive boundary-state induction for the five-row \(DD/D\) system that avoids the fixed \(DX\to L\) checkerboard projection.**

More concretely:

1. Reconstruct the states

   $$
   D,U,V,X,R,J.
   $$

2. Treat the existing six-case \(DD_n\) reduction as fixed trusted infrastructure.

3. Focus first on the unresolved auxiliary families

   $$
   DU,\ DV,\ DR,\ DX,\ DJ.
   $$

4. Use the corrected target

   $$
   DR_{2m}\le-\frac14,
   $$

   not the obsolete \(-1/2\) requirement.

5. Do **not** attempt to prove \(DX_n\le0\) by \(DX_n\le L_n\); that route has been rigorously obstructed.

6. Search for:

   * alternate separators;
   * adaptive interface states;
   * short bounded local reply sequences;
   * exact deletion/explosive-node reductions;
   * decompositions retaining more cross-boundary interaction.

7. Require every recursive construction to call only strictly smaller width/state-rank objects.

8. Keep Blue-first and White-first obligations separate.

9. If a candidate finite state system closes, formulate the induction symbolically first.

10. Then generate finite certificates only for:

    * base widths;
    * exceptional local gadgets;
    * numerical compensation inequalities.

A second high-value task is:

> Find a direct bridge from ordinary empty \(5\times(2k+1)\) boards into a solved family of restricted two-ended states without losing the sign needed for White.

The research should prioritize **structural induction** over brute-force larger widths.

---

# 31. Bottom-line research status

The project has moved well beyond “solver evidence.”

There is now a rigorous infinite theorem:

$$
\boxed{3\times n=0\text{ for all }n.}
$$

The five-row work has identified what a generalized proof likely needs:

* boundary-conditioned induction;
* signed CGT compensation;
* explicit seam contracts;
* mutual recursion among boundary states;
* adaptive rather than purely static interfaces.

It has also rigorously eliminated several attractive but invalid shortcuts.

The frontier is not “prove a random giant \(5\times n\) instance.”

The frontier is:

$$
\boxed{
\text{Find the right finite closed boundary-state system for height 5.}
}
$$

If that succeeds, the same conceptual machinery may suggest how to treat height 7 and eventually arbitrary odd heights.


---

# 32. Repository continuation: September 22, 2026

The next research step is recorded in
[five_row_boundary_induction.md](five_row_boundary_induction.md), with a complete
six-case dependency table, endpoint and empty-side handling, turn order, and
strictness requirements. This is a partial advance, not a closed induction.

New local separator comparisons improve two cases: an outer-even opening uses
`..obo=0` with R/R interfaces (or `..wbo=-1/2` at an endpoint), and a center-even
opening uses `o...o=0` with X/X interfaces. Neither needs a White reply before
comparison. Therefore `DR_even<0` and `DX_even<0` are alternative sufficient
targets for DD, replacing the fixed DR margin and the separate starred DX
condition in these new constructions. The original stated targets still
suffice; arbitrary-width strict negativity for those families remains open.

The continuation proves two precisely scoped interface obstructions. An
immediate White-first DD interval reduction cannot produce a strictly smaller
two-ended recursive rectangle of width at least two using only the six named
endpoint letters: White moves and admissible comparisons cannot create the
required White-only cells. For DX, an off-center opening followed by any one
White reply cannot close a one-column split using only the original six
D-ended pair families. Both are symbolic legality arguments, not conclusions
from bounded search. See the [White-first note](five_row_white_first.md) and
[DX/interface note](dx_boundary_obstruction.md).

New independently checked response-DAG certificates establish `DD_1=0`,
`DD_3<0` (including an explicit White-first witness), the width-one DU/DJ
targets, local separator values, and `DT_2=0` for `T=bobob`. In particular,
`DD_3` needs a direct base: its center-opening split only gives `DD_1+DD_1=0`
with White next. The uniform larger-width White-first DD obligations and the
empty-five-row bridge are still unresolved.

The [provenance audit](five_row_certificate_provenance.md) maps available older
roots and finite base assemblies and explicitly lists missing later mappings,
including `T_middle1`, seam-compatible `Z7`, and the historical five-row/L
collections. Those are artifact gaps, not refutations of the mathematical
arguments supplied above. The fixed L-projection obstruction remains in force.

---

# 33. Second continuation: general reductions and delayed boundaries

The current synthesis is
[round2_research_progress.md](round2_research_progress.md), with exact artifact
mappings and a seven-checker reproduction command. This is another partial
advance; no finite mutually recursive auxiliary system has closed.

A new exact shared-twin module identity applies to arbitrary finite Col
permission graphs: an even independent shared set I with identical live
neighborhood H can be deleted together with H if both players' independent
capacities inside H are at most |I|. In an induced grid, every pair of shared
false twins qualifies. A concrete delayed corner dialogue uses this identity
to remove a `3×3` corner and then compares with a width-`n−3` X-boundary game
plus star. A smaller White-support cap preserves the same star value and
avoids an unnecessary new endpoint. Other Blue continuations remain open.

For every even `n≥6`, an explicit five-round sequence defeats a DX policy
restricted to horizontal or half-turn mirrored replies, including adaptive
choices between them. The exact remaining game is `0+0+2`, with Blue next.
This eliminates reactive mirroring and controllers forcing that policy away
from two-column end caps; it does not prove DX positive. A finite proactive
cap-controller formulation remains viable, with a width-three horizontal
search still Unknown. Strictness requires its own White-first obligation.

The White-first DD work now has a complete conditional assembly using a
parity-aware central White opening, marked-strip F families, and stronger
ordinary numerical margins. All endpoint, adjacent-column, and same-column
cases are covered with decreasing width. The F families and stronger bounds
are unproved; in particular the assembly does not propagate the stronger DD
margin it assumes. The simpler corner phase is refuted by the independently
certified `E_X^0(4)=1/2`. The X-phase domain is explicitly restricted to legal
center-opening calls, not every superficially compatible marked strip.

A sharp support theorem proves that after one Blue opening, White moves and
admissible upper comparisons alone cannot embed a full-height two-ended
shared-interior rectangle of width at least three when each end requires a
White-only cell. Hence a future empty-board bridge needs one-ended states,
interior exclusions, more Blue play, or another geometry even if DD closes.
A separate bounded-round reflection-axis obstruction applies at arbitrary
height to its precisely stated construction class.

All new numerical and policy certificates are checked independently of their
searches by `round2_verify.py`; discovery outputs retain their separate status.
Earlier missing provenance mappings have not been recovered, and the fixed
L-projection obstruction remains unchanged. The literal all-positive-odd-area
claim also needs the `1×1=*` exception; no general theorem is asserted here.

---

# 34. Third continuation: wider caps and complete conditional continuations

The latest synthesis is
[round3_research_progress.md](round3_research_progress.md). The auxiliary
induction remains open, but there are new positive reductions using bounded
wider regions and independently proved limits on narrower constructions.

For the required marked-X states `F_X(k,k−2,2)`, even `k≥6`, every Blue row
in column `k−4` reduces through a four-column cap to `DR_(k−4)`,
`DV_(k−4)−1`, or `DX_(k−4)`. All are strictly negative under the original
auxiliary targets, with White next and decreasing even width. In the first
instance, the center opening has actual upper bound `DX_2=−1`, while every
immediate one-column permission cut in the explicitly enumerated class has
a nonnegative virtual game. This is a constructive repair of that exact
loss of interaction, not a claim that the whole F induction is complete.

Anchored three-column D caps also improve DX column-2 opening bounds:
their R, V and X choices have exact values `−1,−2,−1`. Thus
`RX_odd<1`, `VX_odd<2`, and `XX_odd<1`, at odd widths at least three,
would settle this opening class. These are new conditional targets;
neither their arbitrary-width bounds nor all other DX openings are proved.

The corner construction now has a complete conditional continuation.
After Blue `(2,n−3)` and White `(0,n−3)` in `(P,Q)_n`, with Q neutral or D,
a safe X cut gives `PX_(n−3)+C_Q`, where `C_O=0` and `C_D=−1+*`.
With Blue next, `PX_(n−3)≤0` alone handles every subsequent Blue move by
component strategies. The old fixed second White reply and its extra star
compensation are unnecessary. For an ordinary board P is neutral, so this
still requires a one-ended target. On ordinary 5×5 the initial White reply
actually loses; its independently certified continuation refutes that
specific policy at width five, not the empty-board conjecture.

A shifted checkerboard sequence defeats DX controllers forcing horizontal
or half-turn responses outside three-column end caps for every even `n≥8`:
the exact remaining game is again 2 with Blue next. Separate finite
counterstrategies, with a symbolic locality lift, rule out confining all
safe repairs to three central columns while mirroring every exterior move,
for heights 3 and 5 at every odd width at least five. These are precise
policy obstructions, not sign conclusions for the unrestricted games.

At arbitrary odd dimensions, a new independent-support lemma proves that
a full-Blue comparison with independent White support can be nonpositive
only if that support is the unique maximum checkerboard class and has even
size. The particular even shared-block zero-partition theorem from the
previous round tiles an odd rectangle only for 1×3 or 3×1. This limits a
static use of the module identity without invalidating its exact dynamic
applications.

All five new checkers pass: 88 numerical DAGs plus two central-policy DAGs,
alongside independent exact game-order and geometry checks. Reproduce them
with `round3_verify.py`. Every new numerical root is mapped; earlier missing
artifact mappings remain as previously recorded. Bounded raw searches and
Unknown controller results remain experimental, and the disproved fixed-L
projection is not used. The finite recursive closure, required strictness,
ordinary-board bridge and arbitrary-height construction are still incomplete.

---

# 35. Fourth continuation: paired endpoint clauses and coupled corner states

The latest synthesis is
[round4_research_progress.md](round4_research_progress.md). It records new
positive width-decreasing clauses and additional candidate obstructions;
the auxiliary induction and the full empty-board bridge remain open.

Marked D-ended phases now have row-complete caps of widths two, three and
four whenever the parity-correct White mark lies inside the cap and Blue
opens at its first column. Odd-width residuals return DU, DJ and DD with
cap bounds 0, 1/4 and 0; even residuals return DR, DV and DX with cap bounds
0, −1 and 0. Require odd residual width L≥3 and even residual width L≥2.
All post-Blue comparisons are strictly negative under the
original auxiliary targets and smaller-width DD strictness. Further U/J
endpoint-marked caps satisfy the same table. On the required X diagonal,
all Blue rows in the marked column now close through a two-column cap,
complementing round three's column two places earlier. Three explicit
seam-safe White replies give additional nonpositive post-reply bounds.
These local successes do not close the entire marked system or propagate
the stronger quantitative DD assumption of the round-two assembly.

Define `T_q(G)` by `G≤q` and `G+*≤q`. General short-game algebra proves both
comparisons strict and makes star stability explicit. The three proposed
paired targets `T_1(RX_odd)`, `T_2(VX_odd)`, `T_1(XX_odd)` have independently
certified width-three bases. Center-row openings at distances one, two and
three from their X endpoint return respectively the same family at width
`n−2`, the D-interface family minus one at width `n−3`, and the same family
plus star at width `n−4`. The original DR/DV/DX bounds and smaller paired
targets discharge these eighteen conditional clauses. Other opening rows,
deep interior columns and uniform White-first witnesses remain open.
Consuming the auxiliary star at the same width requires a separately proved
unstarred White-first witness; a staged `(width,stage)` rank makes that
noncircular obligation explicit.

At `XX_7` after Blue `(2,3)`, every immediate one-column permission cut in
the exhaustively specified class gives a virtual game at least 1. A
four-column X cap has exact value star and improves the actual upper bound
to `XX_3+*=1/2+*<1`. This is a proved repair of that comparison failure,
not a claim that the actual XX target fails.

A different bridge proposal retains every interaction after an ordinary
central Blue opening and a corner White reply. Let M_n be the resulting
actual position. Independent certificates establish `M_3<0`, `M_5=0` and
`M_7≤0`. On 5×5 the four corners are exactly the winning White replies to
central Blue. The larger M7 certificate uses a separate coordinate-set,
zero-offset verifier and covers every Blue continuation. Its opposite-start
outcome remains Unknown. There is no arbitrary-width M recursion yet, and
even one would cover only the central-opening class.

Two new symbolic obstructions rule out, on their precise scopes, a single
monotone staircase surrounded by individually nonpositive 2×2 square tiles,
and peeling two bottom rows after a corner opening while retaining a
genuinely empty upper rectangle. The first allows adjacent White path
supports and independent phases on the two sides. The second gives a cap
lower bound of one for every eligible White reply and every odd width ≥3.
These are failures of comparison constructions, not positive actual boards.
Separate finite exact-star examples refute proposed generalizations to
perfect-matching bipartite graphs, even bipartite graphs with a spanning
path, and doubly symmetric row/column-convex odd shapes. None is an ordinary
rectangle counterexample.

Reproduce all six independent checkers with `round4_verify.py`. They replay
99 response DAGs, including one explicitly reused round-three artifact,
with 529,093 checkpoints and 3,672,781 edges, plus exact-order and geometry
checks. The manifests bind all new roots; the verification record hashes
the evidence and helper dependencies. Earlier missing artifact mappings
remain as documented, independently of the mathematical arguments. No
fixed-L projection or finite-width extrapolation is used. The literal
all-positive odd-area claim still requires the `1×1=*` exception.
