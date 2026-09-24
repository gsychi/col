import ColProof.Main

/-!
# The theorem for Col played with stones

Here the game is stated with the literal rule: players alternately place a
stone of their colour on an empty cell of the board, never orthogonally next
to a stone of their own colour, and a player with no legal placement loses.
`StoneLoses R M O` says the player to move, whose stones are `M`, loses
against the opponent with stones `O` on the region `R`.
-/

namespace Col

/-- A placement at `v` is legal for the owner of stones `M` against stones `O`. -/
def legal (R M O : Board) (v : Cell) : Prop :=
  R v ∧ ¬ M v ∧ ¬ O v ∧ ∀ u, M u → ¬ adj u v

def addStone (S : Board) (v : Cell) : Board := fun u => S u ∨ u = v

/-- Every legal placement `v` of the mover has a legal answer `reply v`
after which the mover loses again. -/
inductive StoneLoses (R : Board) : Board → Board → Prop
  | intro {M O : Board} (reply : ∀ v, legal R M O v → Cell)
      (answer : ∀ v (hv : legal R M O v), legal R O (addStone M v) (reply v hv))
      (next : ∀ v (hv : legal R M O v), StoneLoses R (addStone M v) (addStone O (reply v hv))) :
      StoneLoses R M O

theorem stoneLoses_of_loses {R : Board} {X Y : Board} (h : Loses adj X Y) :
    ∀ M O, (∀ u, X u ↔ legal R M O u) → (∀ u, Y u ↔ legal R O M u) → StoneLoses R M O := by
  induction h with
  | intro reply hlegal next ih =>
    intro M O hX hY
    refine StoneLoses.intro (fun v hv => reply v ((hX v).2 hv)) (fun v hv => ?_) (fun v hv => ?_)
    · have hXv := (hX v).2 hv
      obtain ⟨hYw, hwv⟩ := hlegal v hXv
      have ⟨hRw, hOw, hMw, hadjw⟩ := (hY _).1 hYw
      exact ⟨hRw, hOw, fun h => h.elim hMw hwv, hadjw⟩
    have hXv := (hX v).2 hv
    let w := reply v hXv
    refine ih v hXv _ _ (fun u => ?_) (fun u => ?_)
    · simp only [afterX, legal, addStone]
      rw [hX u]
      simp only [legal]
      constructor
      · intro ⟨⟨hR, hM, hO, ha⟩, hnv, hnw⟩
        refine ⟨hR, fun h => h.elim hM fun e => hnv (Or.inl e), fun h => h.elim hO hnw, ?_⟩
        intro x hx
        rcases hx with hx | rfl
        · exact ha x hx
        · exact fun h => hnv (Or.inr h)
      · intro ⟨hR, hM, hO, ha⟩
        exact ⟨⟨hR, fun h => hM (Or.inl h), fun h => hO (Or.inl h), fun x hx => ha x (Or.inl hx)⟩,
          fun h => h.elim (fun e => hM (Or.inr e)) (fun h => ha v (Or.inr rfl) h), fun e => hO (Or.inr e)⟩
    · simp only [afterY, legal, addStone]
      rw [hY u]
      simp only [legal]
      constructor
      · intro ⟨⟨hR, hO, hM, ha⟩, hne, hnw⟩
        refine ⟨hR, fun h => h.elim hO fun e => hnw (Or.inl e), fun h => h.elim hM hne, ?_⟩
        intro x hx
        rcases hx with hx | rfl
        · exact ha x hx
        · exact fun h => hnw (Or.inr h)
      · intro ⟨hR, hO, hM, ha⟩
        exact ⟨⟨hR, fun h => hO (Or.inl h), fun h => hM (Or.inl h), fun x hx => ha x (Or.inl hx)⟩,
          fun e => hM (Or.inr e), fun h => h.elim (fun e => hO (Or.inr e)) (fun h => ha w (Or.inr rfl) h)⟩

/-- **Main theorem (stone form).** On the empty `3 × n` board, the player who
moves first loses Col, whichever colour that is. -/
theorem three_by_n_stones (n : Nat) : StoneLoses (board n) (fun _ => False) (fun _ => False) :=
  stoneLoses_of_loses (three_by_n n) _ _
    (fun u => ⟨fun h => ⟨h, id, id, fun _ h => h.elim⟩, fun h => h.1⟩)
    (fun u => ⟨fun h => ⟨h, id, id, fun _ h => h.elim⟩, fun h => h.1⟩)

end Col
