# A uniform mirror trap and a finite cap-controller framework

Status: **proved obstruction to precisely specified mirror policies, plus a
proved conditional interface reduction**. Neither result is a counterexample
to DX negativity or to empty odd rectangles. This note continues the
[expanded DX study](round2_dx_progress.md).

## Exact mirror invariant

For a fixed-point-free involutive graph automorphism tau, let

```math
\Delta=\tau(A)\setminus B.
```

If Delta is empty and Blue is next, White wins by responding to v at tau(v).
Extra White permissions cause no problem: equality is unnecessary. After a
legal mirrored pair,

```math
A'=A\setminus N[v]\setminus\{\tau(v)\},\quad
B'=B\setminus\{v\}\setminus N[\tau(v)],
```

and exactly

```math
\Delta'=\Delta\setminus\left(N[\tau(v)]\cup\{v\}\right).
```

Thus ordinary paired replies cannot create defects. Blue's new stone cannot
occupy tau(v), because tau has no fixed vertex; the reply is legal whenever
tau(v) belongs to the pre-move White set. This argument does not assume that
the current occupied stones are symmetric. For an arbitrary legal White
reply u after v,

```math
\Delta'\subseteq\Delta\cup N[u]\cup\{v\}.
```

These identities are also checked on every mirrored edge in the finite
controller DAG verifier described below.

## An infinite obstruction to reactive mirroring

Let

```text
C    = wbwbw,
Cbar = bwbwb = conjugate(C).
```

These are permission masks, not occupied columns. The occupied columns in
the following construction induce C and Cbar on their neighboring columns.

**Theorem.** For every even `n>=6`, a White policy on `DX_n` that answers each
of the next five Blue moves by either its horizontal reflection or its
half-turn image reaches a position of exact value 2, with Blue next.
This remains true if White chooses between the two reflections adaptively
whenever both replies are legal.

Blue's five prescribed moves are:

| Round | Blue move |
| --- | --- |
| 1 | `(0,2)` |
| 2 | `(1,n-3)` |
| 3 | `(2,2)` |
| 4 | `(3,n-3)` |
| 5 | `(4,2)` |

**Proof.** Columns 2 and `n-3` are distinct neutral columns for every even
`n>=6`. Blue uses even rows in column 2 and odd rows in column `n-3`.
Either reflection sends each of these cells to the opposite column, at
either the same row or row `4-r`. Reflection of rows preserves parity.
Therefore every proposed White response is on the opposite checkerboard:
odd rows of column 2 or even rows of column `n-3`.

All five Blue moves are legal. They are distinct and have no same-color
adjacency, including when the two columns are adjacent at n=6. Each round
has an available reflected White response: the row pairs `{0,4}` and `{1,3}`
each supply two distinct choices used over two rounds, while row 2 is used
only once. All unoccupied proposed White responses are legal because their
checkerboard class has no internal edges. After five rounds the two columns
are fully occupied, with the same color pattern regardless of White's legal
reflection choices.

These occupied columns disconnect the remaining board into three genuine
components. Their permissions are exactly

```math
(D,C)_2\; +\; (C,\overline C)_{n-6}\; +\; (\overline C,X)_2.
```

At n=6 the middle component is empty, with value zero. At larger even n it
has positive even width, and is zero by horizontal mirror pairing: its two
endpoint masks are color conjugates. This is the general conjugate-end
cancellation theorem proved in [round2_dx_progress.md](round2_dx_progress.md).
The finite caps have independently certified exact values

```math
(D,C)_2=0,\qquad(\overline C,X)_2=2.
```

The actual remaining game is therefore `0+0+2=2`. No one-sided relaxation
has been used in this last equality. Blue is next after the fifth White
reply and wins. ∎

Consequences for candidate controllers:

* A policy that mirrors whenever either of these reflected replies is legal,
  and reserves exceptional replies only for blocked mirrors, fails at every
  even width n>=6.
* A policy that forces such mirroring whenever Blue plays outside the two
  outermost columns at each end also fails at every even n>=6. All five
  Blue moves are outside those four endpoint columns.
* Any successful controller subject to those attempted rules must make a
  proactive nonmirror reply during this sequence. Waiting for an illegal
  mirror response never triggers a repair.

These are obstructions to the stated **response policies**. They do not
show that the original DX position is positive. A different White reply
before the trap is complete may win, and a controller covering more columns
or carrying a different state may succeed.

## A finite proactive-repair requirement at width four

A separate exact controller test permits arbitrary White replies when the
fixed reflected reply is blocked, and up to t proactive exceptions when that
reply is available. Replies are allowed anywhere on `DX_4`.

Independent response DAGs establish:

| Reflection | Proactive exceptions allowed | Result |
| --- | --- | --- |
| Horizontal | 0 | Blue counterstrategy exists |
| Horizontal | 1 | Blue counterstrategy exists |
| Horizontal | 2 | White strategy exists |
| Half-turn | 0 | Blue counterstrategy exists |
| Half-turn | 1 | Blue counterstrategy exists |

The positive result finishes each terminal subtree using the exact condition
`tau(A) subset B`, rather than by further minimax. Every nonterminal response
strictly decreases the number of live board cells, and a proactive exception
decreases its remaining allowance. This proves that two proactive exceptions
are both necessary and sufficient in the specified horizontal policy class
at width four. It does not establish a bounded exception count at other
widths.

The independent checker
[round2_dx_verify_mirror.py](round2_dx_verify_mirror.py) uses coordinate sets,
checks every legal Blue move in a supplied White strategy, or every allowed
White response in a supplied Blue counterstrategy, checks reachability and
descent, and directly verifies all terminal mirror invariants. It does not
import the strategy search.

```text
Verified five mirror-policy DAGs: 12756 states, 38505 transitions, 964 terminal mirror invariants.
```

## A precise finite interface problem for larger caps

Here is a sufficient finite controller problem for proving `DX_n<=0`
uniformly at all even `n>=2k+2`. It remains unsolved in this research pass.

Take an integer `k>=1` and the leftmost and rightmost k columns as disjoint caps, reflected into
one another. The remaining even-width middle region is handled by ordinary
horizontal mirrored replies whenever Blue plays there. Track both permission
sets in the caps. Also track the five paired cells immediately outside the
inward cap edges: each reflected pair is either unused, Blue-on-left plus
White-on-right, or White-on-left plus Blue-on-right.

The finite abstract transitions are:

1. **Cap opening.** Quantify over every Blue-legal cap move. White may reply
   at its legal mirror, or at another cap cell whose outside neighbor is
   absent or already occupied. Other special replies on the inward cap edge
   are excluded because they could create an untracked external defect.
2. **Port event.** Blue plays an unused outside-port pair on one side and
   White mirrors. Delete Blue permission at that side's cap neighbor and
   White permission at the reflected cap neighbor. Mark the outside pair
   occupied with its orientation. Same-color orientations may not occupy
   adjacent outside rows. Ignoring additional restrictions from the rest of
   the middle region grants the abstract adversary more possible events.
3. **Other middle moves.** They have no effect on cap permissions or outside
   port occupation; the ordinary mirror invariant handles them.

For any special cap reply, the external mirror invariant is preserved:
away from the inward edge no external White permission is changed; at a
port with an occupied outside pair its external neighbor was already dead.
A legal mirrored cap reply preserves the external invariant by the exact
set identity. Thus all untracked middle moves have legal mirrored replies.

**Conditional cap-controller lemma.** A winning strategy in this finite
adversarial-port problem proves `DX_n<=0` for every even `n>=2k+2`.
Actual middle play yields a subset of the abstract port events; cap
permissions evolve exactly as in the abstract controller. End at any state
with no cap defects, because then the whole board satisfies the mirror
invariant. All relevant transitions descend in

```math
\left(|A_{cap}\cup B_{cap}|+5-\#\text{occupied port pairs},
      \#\text{live middle cells}\right)
```

ordered lexicographically. A cap round reduces the first coordinate; a new
port event reduces its unused-pair term; an otherwise invisible middle
round reduces the second coordinate. The proof of a positive controller
must cover every port event and every legal cap Blue move, not just the
events seen during search. Strict negativity additionally requires a
separate White-first witness.

The discovery implementation is [round2_dx_caps.py](round2_dx_caps.py), with
the `--legal-ports` flag enabling the paired occupation and row-legality
constraints. An earlier independent-deletion abstraction was too permissive:
it allowed impossible repeated occupancy of both orientations in a pair.
Only the paired model above is proposed as the useful next search target.
Even this model deliberately grants extra environmental events, so a failed
search need not refute a controller operating with more detailed exterior
information.

The port history is collision-safe: special replies stay inside the caps,
so an actual move occupying a tracked external cell is always immediately
paired with occupation of its reflected mate. A marked pair therefore has
both cells occupied. Conversely the model intentionally omits some external
legality restrictions. In particular, with half-turn reflection and a
two-column middle, a horizontal edge can join cells from different reflected
pairs and impose additional same-color conflicts. Cap stones and more distant
middle play can also forbid prospective port moves. Ignoring these constraints
adds adversarial events; it does not remove an actual event or invalidate a
positive controller certificate. It makes a negative abstract search less
conclusive. The `--legal-ports` name refers only to the tracked paired occupancy
and within-column row constraints, not a complete external-game model.

Final bounded discovery status for the paired-port model:

| Cap width | Reflection | Search status |
| --- | --- | --- |
| 2 | Horizontal | Exhausted this finite abstract strategy search; no winning controller |
| 2 | Half-turn | Exhausted this finite abstract strategy search; no winning controller |
| 3 | Half-turn | Exhausted this finite abstract strategy search; no winning controller |
| 3 | Horizontal | **Unknown** after the 3,000,000-state budget |

These controller-search outcomes are experimental; no independent port-model
strategy or counterstrategy certificate was produced. In particular the
Unknown case is still a viable research candidate. The separately certified
five-move mirror trap and width-four policy results do not depend on these
search outputs.

## Checks

```sh
python3 proofs/construction/research/round2_dx_check.py
python3 proofs/construction/research/round2_dx_verify_mirror.py
```

The first checks 32 exact-bound DAGs (3,664 checkpoints, 12,679 checked
response edges), including both numerical trap caps, and exercises 52 finite
assembly branches. Those assemblies are regressions of the explicit
all-width construction above. The second checks the five finite
proactive-repair policy certificates. Neither checker treats a search budget
limit as a negative conclusion.
