# A central repair region: finite controller and a certified width-three limit

Status: **proved obstruction to a precisely specified strategy class**,
with an independently checked finite counterstrategy and a symbolic lift.
The wider controller search remains experimental and unresolved. No claim
is made that an ordinary empty board is a first-player win.

## The candidate class

On an empty odd `h×n` rectangle, let tau be half-turn rotation and let C be
the central k full-height columns, with k odd and `n≥k+2`. Outside C, maintain
the implication `tau(A)⊆B`: every reflected Blue-legal exterior cell remains
White-legal. A proposed White strategy obeys two rules:

1. After a Blue move outside C, immediately answer at its half-turn image.
2. After a Blue move inside C, answer anywhere inside C, provided the reply
   preserves that exterior implication.

The second rule allows arbitrary nonmirror repairs inside the cap. It does
not require a mirror invariant inside C. This is consequently a larger class
than pure mirroring, and represents a natural finite local repair proposal.

Let the five (or h) paired cells just outside C be ports. A move at a port
followed by its reflected reply removes one Blue permission at the adjacent
cap cell and one White permission at the reflected cap cell. Track port
occupations and which outside Blue orientations have been forbidden by
Blue stones at the cap boundary. Neighboring outside stones of the same
color also forbid further port events.

A special White reply at a cap boundary is safe whenever the **reflected
outside Blue cell is already illegal**. Occupation of its entire port pair
is only one sufficient reason. The outside White permission may still be
present: removing it is harmless when there is no reflected Blue permission
to support. Confusing these two permission conditions would make the
controller unnecessarily restrictive.

The discovery implementation
[round3_central_controller.py](round3_central_controller.py) encodes these
states. An affirmative finite controller, independently certified, would
suffice for every larger odd n: other exterior moves are mirrored, and
their extra restrictions can only remove possible port events. A terminal
state can switch to unrestricted mirroring once the fixed center is
Blue-illegal and `tau(A)⊆B` holds everywhere. All cap and port transitions
decrease `(number of live cap cells + number of unused port pairs)`;
otherwise invisible exterior pairs decrease the number of live exterior
cells. This is a well-founded lexicographic rank.

## Width-three repair cannot work, even with all safe local replies

**Theorem.** For `h=3` or `h=5` and every odd `n≥5`, no White strategy in
the above class with `k=3` answers every legal Blue continuation.

The supplied finite counterstrategies have the following exact mappings:

| Height | Certificate | DAG states | DAG edges |
| --- | --- | ---: | ---: |
| 3 | `round3_central_counter_3_3.json.gz` | 21 | 29 |
| 5 | `round3_central_counter_5_3.json.gz` | 253 | 462 |

These are counterstrategies to the policy class, not ordinary minimax
certificates for the unrestricted board. At each cap Blue move, every legal
White cap reply preserving the exterior implication is included. At a port
move, the policy prescribes the reflected reply. Every branch eventually
has a legal Blue cap move with no reply permitted by the policy.

For height five, the certificate begins with Blue at the top of the left
port column, then the top of the right port column, with White's prescribed
bottom-corner reflections. Blue then plays at the board center. For height
three, just the first port pair precedes the center opening. The later
adaptive moves and all White alternatives are in the DAGs.

**Symbolic lift.** Every move in either certificate lies in the cap or one
of its two adjacent port columns. This five-column induced grid is identical
at every larger odd width. Initially all additional exterior cells are
empty. None is ever played in the counterstrategy; symmetric port moves may
change their permissions but cannot change the legality of a move in the
five-column window. Half-turn maps the window to itself. Cap White replies
affect exterior permissions only at the adjacent ports, so the complete
set of replies satisfying the exterior implication is also independent of n.
Thus the same finite counterstrategy embeds at every odd `n≥5`.

The independent checker reconstructs actual coordinate-set permissions on
whole boards, rather than trusting the search's port-state abstraction. It
checks every legal Blue move, every forced port reflection, the **complete**
set of safe cap White replies, the exterior implication, rank descent and
reachability. As implementation regressions it performs the reconstruction
at widths 5, 7 and 11. The all-width conclusion comes from the locality
argument above, not from those three widths.

The obstruction even holds in the already solved three-row setting. It
therefore demonstrates a limitation of this local repair policy, not a
contradiction to the empty `3×n` theorem or evidence against the five-row
conjecture. A successful strategy can use a wider region, depart from
mirroring after an exterior opening, or temporarily allow exterior defects
while explicitly controlling their later repair.

## Discovery status and reproduction

The five-row, five-column central controller is **Unknown** at 500,000 states.
That budget is not a negative result. No winning strategy or counterstrategy
for that case has been certified.

Verify the two supplied counterstrategies without search:

```sh
python3 proofs/construction/research/round3_central_check.py
```

Reproduce the discovery runs, if desired:

```sh
python3 proofs/construction/research/round3_central_controller.py 5 3 --budget 1000000 --export
python3 proofs/construction/research/round3_central_controller.py 3 3 --budget 1000000 --export
python3 proofs/construction/research/round3_central_controller.py 5 5 --budget 500000
```

The verified five-row DAG has 253 abstract nodes. Reconstructing full occupied
positions distinguishes 264 states and 476 transitions; the three-row DAG
similarly reconstructs to 24 states and 31 transitions. This is expected:
different actual histories can share the same sufficient controller state.
