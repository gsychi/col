# Three tested bridge ideas: coupled corners, staircase strips, and height peeling

Status: **one surviving marked-position proposal with exact finite evidence,
and two proved infinite obstructions to precisely specified constructions**.
None asserts positivity of an actual empty rectangle or completes the five-row
induction. This continues [the round-three corner analysis](round3_corner_dialogue.md).

## 1. Keep the interaction between a center opening and a corner reply

The failed local response to Blue `(2,n−3)` should not be confused with a
different, long-range reply to a central opening. Define `M_n`, for odd n,
to be the actual empty `5×n` permission position after

```text
Blue (2,(n−1)/2), White (0,0).
```

No edge is cut and no permission is relaxed. The proposed sufficient target
is `M_n≤0`: Blue is next. This would answer this one class of empty-board
openings with adaptive play covering all subsequent local and remote moves.
It is not a target for all openings and is not established at arbitrary width.

**Exact finite result.** On `5×5`, the only winning White replies to the center
Blue opening are the four corners, and each leaves exact value zero. The five
dihedral orbits of possible replies have representatives:

| White reply | Proved statement |
|---|---|
| `(0,0)` | resulting actual game is zero |
| `(0,1)` | Blue wins next by `(0,0)` |
| `(0,2)` | Blue wins next by `(0,0)` |
| `(1,1)` | Blue wins next by `(0,0)` |
| `(1,2)` | Blue wins next by `(0,0)` |

The other 19 cells follow by the symmetries fixing the center. This is a
complete classification of these White replies, not a classification of
all empty-board openings. Unlike the earlier prescribed second corner move,
the zero certificate after a corner reply permits White to adapt to every
subsequent Blue move.

The root after the corner reply is `(A,B)=(33408894,33550300)`. Two stored
second-player DAGs prove both inequalities. Three other new DAGs certify
the displayed Blue continuations; the `(0,2)` case reuses its independently
bound round-three artifact. In total the six replayed DAGs have 47,977
checkpoints and 234,523 edges. All roots are rebuilt from the actual moves
by the checker.

**Further independently certified finite results:** `M_3<0` and `M_7≤0`.
Two small DAGs certify the width-three Blue-next loss and its White-first
witness `(0,2)`, totaling 205 checkpoints and 623 edges. The width-seven
Blue-next loss has a larger response DAG with 447,623 checkpoints and
3,306,842 edges. It uses a separate zero-offset schema checked against actual
coordinate-set moves, with complete reply coverage, live-cell rank descent,
reachability, and the fixed root `(34342501374,34359607164)` on `5×7`.
The compressed artifact is about 5.64 MB. It does not depend on the discovery
solver during checking.

The width-seven opposite starting-color query exhausted its bound, so no
equality or strictness assertion is made for `M_7`. The surviving problem is
to find a width-decreasing construction for the coupled marked family,
rather than replace it with the already unsuitable uniform one-ended OX
target. The three finite widths do not prove that target at arbitrary width.

## 2. A staircase between zero square tiles cannot supply the bridge

A natural way to retain more interaction is to leave a whole one-cell-wide
staircase, while filling both sides with zero `2×2` contracts. The two sides
may have different checkerboard phases. This allows adjacent White-legal
cells on the path and therefore lies outside the earlier independent-White
support obstruction.

Take `n=2N+1≥3` and even columns `a=2A≤b=2B`. The retained path runs

```text
(0,0) ... (0,a), (1,a), (2,a) ... (2,b), (3,b), (4,b) ... (4,n−1).
```

It is an induced path of length `n+4=2p−1`, where `p=N+3`. Tile its complement
with `2×2` squares in these four rectangular bands:

| Rows | Columns |
|---|---|
| 1,2 | `0,...,a−1` |
| 3,4 | `0,...,b−1` |
| 0,1 | `a+1,...,n−1` |
| 2,3 | `b+1,...,n−1` |

Keep Blue legal everywhere. On every square, an opposite pair of shared cells
and two Blue-only cells gives a zero contract. Give the retained path every
White permission compatible with these square supports. Any later retirement
of path White permissions only makes the comparison less favorable.

**Theorem.** For every odd `n≥3` and every indicated pair of turns, this
comparison is not nonpositive, even after optimizing both side phases.

The proof uses two elementary lemmas.

**Alternating-path lemma.** Let `T_p` be the path with `2p−1` vertices, Blue
legal everywhere and White legal at the p alternating vertices including
both ends. Then `T_2=0`, and `T_p>0` for every `p≥3`.

To prove `T_p≥0`, first suppose p is even. Blue, playing second, restricts
play to the independent shared vertices and answers every White move there.
If p is odd and at least three, number these shared vertices `0,...,p−1`.
On the first response Blue occupies an even-numbered shared vertex not
already occupied by White; there are at least two choices before White's
first move. Continue answering on unused shared vertices. White eventually
occupies `(p+1)/2` shared vertices. That set cannot be independent in the
auxiliary p-vertex path: its unique maximum independent set consists of the
even-numbered vertices, one of which Blue took. Thus White has occupied two
consecutive shared vertices. The private Blue vertex between them remains
Blue-legal, because neither adjacent shared vertex is Blue. Blue takes it
after White's last shared move and wins.

For a Blue-first win when `p=3`, take the middle shared vertex; the remainder
is two isolated stars, hence zero, with White next. For `p≥4`, take an end
shared vertex. Its adjacent private vertex dies, leaving exactly `T_(p−1)`,
which is nonnegative. This proves strict positivity. The `p=2` identity is
the three-vertex shared-twin zero module.

**Path-support lemma.** On any odd path of length `2p−1`, let J be its p
alternate vertices, keep Blue legal everywhere, and let White's legal set
be W. Restrict Blue to J and remove all edge restrictions on White. This is
a valid lower comparison: J was already independent, so deleting edges adds
only White options. The resulting edgeless game has value

```math
p-|W|+(|J\cap W|\bmod2)*.
```

Consequently the path is strictly positive if `|W|<p`; and it cannot be
nonpositive if `|W|=p` with odd `|J∩W|`. The alternating-path lemma handles
the remaining case W=J, even when p is even.

To apply these lemmas, note that each connected side of the tiled region
must use one global checkerboard phase. Opposite phases on two adjacent
squares put White-legal cells at both ends of a seam edge. There are at most
two connected sides, so only four phase pairs need consideration.

If both sides use the majority phase, the path's maximal White set is J.
If both use the minority phase, it consists of the `p−1` minority path
vertices, except when the path passes through an additional board corner.
That happens only at `a=b=0` or `a=b=n−1`; the corner adds one majority vertex,
so the maximal support has size p and odd intersection with J.

For opposite phases with both sides nonempty, suppose the lower-left side
uses majority and upper-right uses minority. Directly counting the five
path segments gives

```math
|W|=N+1+A-B+\mathbf1_{A=0}+\mathbf1_{A<B}<N+3=p,
```

where `B>0` and `A<N`. The other opposite phase is its half-turn image.
If one side is empty, this reduces to one of the uniform-phase cases above.
The two lemmas exclude nonpositivity in every case. ∎

Allowing more White permissions inside a zero square does not evade this
obstruction. Every nonpositive full-Blue square is exactly zero: the full-shared
square is zero, and restricting White can only increase its value. An exhaustive
four-vertex game-order check also proves that every such mask contains an
opposite shared pair. Retire the extra square White permissions, preserving
its value zero, and give the path all the newly seam-compatible White
permissions. Enlarging that path support can only lower the total comparison.
The maximally favorable path in the theorem still is not nonpositive, so the
original comparison cannot have been nonpositive either. This scope requires each square itself to be
nonpositive; it does not cover a signed balance of positive and negative
larger tiles or several interacting retained paths.

## 3. Peeling two rows while keeping the rest genuinely empty

Another candidate is to retain an empty upper odd-height rectangle and
handle two lower rows separately. For height five this would invoke the
proved empty `3×n` theorem without changing its hypotheses.

**Theorem.** For every odd width `n≥3`, an actual Blue opening at the lower-left
corner cannot be answered by this construction: after any White reply
consistent with keeping the upper rectangle genuinely empty, the isolated
two-row upper-comparison cap is at least 1.

The argument applies at any height at least three. Let the retained rectangle
consist of all but the two bottom rows. To keep every retained cell White-legal,
White's reply must be in the bottom row: a move in the retained rectangle
occupies one of its cells, and a move in the next-to-bottom row forbids a
retained neighboring cell. The Blue corner is already in the bottom row.

At the seam, the retained rectangle has full White support, so every White
permission in the upper row of the two-row cap must be retired. Number cap
columns `0,...,2m`, where `n=2m+1`. After Blue's bottom-left opening, Blue can
still use columns `1,...,2m` of the upper cap row; White can use only the
bottom row, where column 0 is occupied. White's reply is at some bottom
column `w≥1`.

For a lower bound on this cap, restrict Blue to an independent set of m
upper-row cells. These are private Blue cells. White's remaining bottom-row
cells form the path `1,...,2m` with the closed neighborhood of w removed.
Their independence number is exactly `m−1`, for every w, as follows by summing
the capacities of the two intervals on either side. Opposite-color vertical
edges cause no interaction. The resulting game has exact value

```math
m-(m-1)=1.
```

Thus the strongest permission comparison at this fixed seam is already at
least 1 after the White reply. Additional Blue permissions or retired White
permissions cannot improve the bound. For height five the empty `3×n`
component is zero, so this direct construction cannot yield a nonpositive
total. This proves failure of the comparison, not positivity of the actual
board, whose cross-seam interaction was discarded.

A broader finite check tried every Blue opening in the lower two rows and
every allowed bottom-row White reply at widths 3,5,7,9. All 304 resulting
two-row caps are not nonpositive. Only the corner-opening class above is
claimed for arbitrary width. Central three-row retention is even more
restrictive: on a height-five board every possible White move either occupies
a retained cell or prohibits a retained neighbor, so no reply leaves that
full-width central rectangle genuinely empty.

## Verification and remaining route

Run:

```sh
python3 proofs/construction/research/round4_bridge_check.py
```

The checker independently replays nine root-bound DAGs, checks exact
game order on the finite path/tile/cap instances, and verifies 3,260 staircase
interfaces and support counts. The all-width conclusions use the symbolic
arguments above; finite checks do not establish them by extrapolation.

The DAG files are in `round4_bridge_certificates/`, except for the explicitly
reused round-three `(0,2)` reply artifact. The new large exporter is
`round4_bridge_export.cpp`; `round4_bridge_probe.cpp` and its saved JSON log
remain discovery-only tools and are not imported by the checker.

[`manifest.json`](round4_bridge_certificates/manifest.json) explicitly maps all
nine roots and distinguishes the large zero-offset schema from the existing
dyadic schema. The eight new artifacts have 491,123 checkpoints and 3,520,038
edges; the reused artifact has 4,682 checkpoints and 21,950 edges. The total
is 495,805 checkpoints and 3,541,988 edges. The checker validates the manifest
against the artifacts it has replayed and prints these counts separately.

The coupled marked family M remains an admissible proposal, with no claimed
closure. A successful bridge must retain additional interaction, use more
than one interacting path, combine tiles with signed values, or change the
state family. The two obstructions specify exactly which simpler variants
can be discarded. The arbitrary-width auxiliary induction and its White-first
strictness obligations remain separate unfinished tasks.
