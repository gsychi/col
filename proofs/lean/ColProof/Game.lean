/-!
# Col as a game on legality sets

Cells are pairs `(row, column)` of natural numbers. A position is described by
the set of cells where each player may still legally play (the rule of Col
depends on stones only through these sets). When a player places a stone at
`v`, she loses every cell in the closed neighbourhood of `v`, and the
opponent loses `v` itself.

`Loses G X Y` says: the player to move, with legal cells `X`, loses against
an opponent with legal cells `Y`, on a board whose adjacency is `G`. It is
an inductive predicate, so every proof of it is a finite winning strategy for
the opponent.
-/

namespace Col

abbrev Cell := Nat × Nat
abbrev Board := Cell → Prop

/-- Orthogonal adjacency of the grid `ℕ × ℕ`. -/
def adj (u v : Cell) : Prop :=
  (u.1 = v.1 ∧ (u.2 + 1 = v.2 ∨ v.2 + 1 = u.2)) ∨
  (u.2 = v.2 ∧ (u.1 + 1 = v.1 ∨ v.1 + 1 = u.1))

instance (u v : Cell) : Decidable (adj u v) := by unfold adj; infer_instance

theorem adj_symm {u v : Cell} : adj u v → adj v u := by
  unfold adj; omega

/-- Legal cells of the player who just moved at `v`, after the reply `w`. -/
def afterX (G : Cell → Cell → Prop) (X : Board) (v w : Cell) : Board :=
  fun u => X u ∧ ¬ (u = v ∨ G v u) ∧ u ≠ w

/-- Legal cells of the replying player, after the move `v` and her reply `w`. -/
def afterY (G : Cell → Cell → Prop) (Y : Board) (v w : Cell) : Board :=
  fun u => Y u ∧ u ≠ v ∧ ¬ (u = w ∨ G w u)

/-- The player to move (legal cells `X`) loses against the opponent (legal
cells `Y`): every move `v` has a legal reply `w ≠ v` after which the mover
loses again. -/
inductive Loses (G : Cell → Cell → Prop) : Board → Board → Prop
  | intro {X Y : Board} (reply : ∀ v, X v → Cell)
      (legal : ∀ v (hv : X v), Y (reply v hv) ∧ reply v hv ≠ v)
      (next : ∀ v (hv : X v), Loses G (afterX G X v (reply v hv)) (afterY G Y v (reply v hv))) :
      Loses G X Y

theorem Loses.mk' {G : Cell → Cell → Prop} {X Y : Board}
    (h : ∀ v, X v → ∃ w, Y w ∧ w ≠ v ∧ Loses G (afterX G X v w) (afterY G Y v w)) :
    Loses G X Y :=
  Loses.intro (fun v hv => Classical.choose (h v hv))
    (fun v hv => ⟨(Classical.choose_spec (h v hv)).1, (Classical.choose_spec (h v hv)).2.1⟩)
    (fun v hv => (Classical.choose_spec (h v hv)).2.2)

theorem Loses.elim {G : Cell → Cell → Prop} {X Y : Board} (h : Loses G X Y) :
    ∀ v, X v → ∃ w, Y w ∧ w ≠ v ∧ Loses G (afterX G X v w) (afterY G Y v w) := by
  cases h with
  | intro reply legal next => exact fun v hv => ⟨reply v hv, (legal v hv).1, (legal v hv).2, next v hv⟩

/-- A player with no legal move loses. -/
theorem Loses.of_empty {G : Cell → Cell → Prop} {X Y : Board} (h : ∀ u, ¬ X u) : Loses G X Y :=
  Loses.mk' fun v hv => absurd hv (h v)

theorem Loses.congr {G : Cell → Cell → Prop} {X Y X' Y' : Board} (h : Loses G X Y)
    (hX : ∀ u, X' u ↔ X u) (hY : ∀ u, Y' u ↔ Y u) : Loses G X' Y' := by
  have e1 : X' = X := funext fun u => propext (hX u)
  have e2 : Y' = Y := funext fun u => propext (hY u)
  subst e1 e2
  exact h

/-- **Comparison principle.** Suppose the mover wins no more in the actual
position `(A, B)` on `G` than in a virtual position `(A', B')` on a graph
`G' ⊆ G`: the mover keeps every move (`A ⊆ A'`), the opponent gains none
(`B' ⊆ B`), and no deleted edge joins two cells that are virtually legal for
the opponent. If the mover loses the virtual position, she loses the actual
one. -/
theorem Loses.compare {G G' : Cell → Cell → Prop} (hsub : ∀ u v, G' u v → G u v)
    {A' B' : Board} (h : Loses G' A' B') :
    ∀ {A B : Board}, (∀ u, A u → A' u) → (∀ u, B' u → B u) →
      (∀ u w, G w u → ¬ G' w u → B' u → B' w → False) → Loses G A B := by
  induction h with
  | intro reply legal next ih =>
    intro A B hA hB hcut
    refine Loses.mk' fun v hv => ?_
    have hv' := hA v hv
    refine ⟨reply v hv', hB _ (legal v hv').1, (legal v hv').2, ih v hv' ?_ ?_ ?_⟩
    · intro u ⟨hu, hnv, hnw⟩
      exact ⟨hA u hu, fun h => hnv (h.elim Or.inl fun h => Or.inr (hsub _ _ h)), hnw⟩
    · intro u ⟨hu, hne, hnw⟩
      refine ⟨hB u hu, hne, fun h => ?_⟩
      rcases h with h | h
      · exact hnw (Or.inl h)
      · by_cases h' : G' (reply v hv') u
        · exact hnw (Or.inr h')
        · exact hcut u _ h h' hu (legal v hv').1
    · intro u w' h1 h2 h3 h4
      exact hcut u w' h1 h2 h3.1 h4.1

/-- **Relabelling.** A position whose cells are carried to new places by a
map that is injective on the relevant region and preserves adjacency there is
the same game. `g` maps new cells to old ones; `f` is a section of `g` on the
old supports. -/
theorem Loses.pull {G H : Cell → Cell → Prop} {X Y : Board} (h : Loses G X Y)
    (g f : Cell → Cell) (P : Cell → Prop) :
    ∀ {X' Y' : Board},
      (∀ u, X' u ↔ P u ∧ X (g u)) → (∀ u, Y' u ↔ P u ∧ Y (g u)) →
      (∀ u, X u ∨ Y u → P (f u) ∧ g (f u) = u) →
      (∀ u u', P u → P u' → g u = g u' → u = u') →
      (∀ u u', P u → P u' → (H u u' ↔ G (g u) (g u'))) →
      Loses H X' Y' := by
  induction h with
  | intro reply legal next ih =>
    rename_i X Y
    intro X' Y' hX hY hsec hinj hadj
    refine Loses.mk' fun v hv => ?_
    have ⟨hPv, hXv⟩ := (hX v).1 hv
    let w := reply (g v) hXv
    have ⟨hYw, hwv⟩ := legal (g v) hXv
    have ⟨hPfw, hgfw⟩ := hsec w (Or.inr hYw)
    have key : ∀ u, P u → (u = f w ↔ g u = w) := fun u hPu =>
      ⟨fun e => e ▸ hgfw, fun e => hinj u (f w) hPu hPfw (by rw [e, hgfw])⟩
    refine ⟨f w, (hY _).2 ⟨hPfw, by rw [hgfw]; exact hYw⟩, fun e => hwv (by
      have := congrArg g e; rw [hgfw] at this; exact this), ?_⟩
    refine ih (g v) hXv ?_ ?_ ?_ hinj hadj
    · intro u
      constructor
      · intro ⟨hu, hnv, hnw⟩
        have ⟨hPu, hXu⟩ := (hX u).1 hu
        refine ⟨hPu, hXu, fun h => hnv ?_, fun e => hnw ((key u hPu).2 e)⟩
        rcases h with h | h
        · exact Or.inl (hinj u v hPu hPv h)
        · exact Or.inr ((hadj v u hPv hPu).2 h)
      · intro ⟨hPu, hXu, hnv, hnw⟩
        refine ⟨(hX u).2 ⟨hPu, hXu⟩, fun h => hnv ?_, fun e => hnw ((key u hPu).1 e)⟩
        rcases h with h | h
        · exact Or.inl (h ▸ rfl)
        · exact Or.inr ((hadj v u hPv hPu).1 h)
    · intro u
      constructor
      · intro ⟨hu, hne, hnw⟩
        have ⟨hPu, hYu⟩ := (hY u).1 hu
        refine ⟨hPu, hYu, fun e => hne (hinj u v hPu hPv e), fun h => hnw ?_⟩
        rcases h with h | h
        · exact Or.inl ((key u hPu).2 h)
        · exact Or.inr ((hadj (f w) u hPfw hPu).2 (by rw [hgfw]; exact h))
      · intro ⟨hPu, hYu, hne, hnw⟩
        refine ⟨(hY u).2 ⟨hPu, hYu⟩, fun e => hne (e ▸ rfl), fun h => hnw ?_⟩
        rcases h with h | h
        · exact Or.inl ((key u hPu).1 h)
        · have := (hadj (f w) u hPfw hPu).1 h
          rw [hgfw] at this
          exact Or.inr this
    · intro u hu
      rcases hu with hu | hu
      · exact hsec u (Or.inl hu.1)
      · exact hsec u (Or.inr hu.1)

/-- **Sums.** Two positions on disjoint, non-adjacent regions: if the mover
loses each, she loses their union (the opponent answers in the same region). -/
theorem Loses.union {G : Cell → Cell → Prop} {X1 Y1 X2 Y2 : Board}
    (h1 : Loses G X1 Y1) (h2 : Loses G X2 Y2)
    (hdisj : ∀ u, (X1 u ∨ Y1 u) → (X2 u ∨ Y2 u) → False)
    (hsep : ∀ u u', (X1 u ∨ Y1 u) → (X2 u' ∨ Y2 u') → ¬ G u u' ∧ ¬ G u' u) :
    Loses G (fun u => X1 u ∨ X2 u) (fun u => Y1 u ∨ Y2 u) := by
  induction h1 generalizing X2 Y2 with
  | intro r1 l1 n1 ih1 =>
    rename_i X1 Y1
    induction h2 with
    | intro r2 l2 n2 ih2 =>
      rename_i X2 Y2
      refine Loses.mk' fun v hv => ?_
      rcases hv with hv | hv
      · -- Blue moved in the first region; answer there.
        let w := r1 v hv
        have ⟨hw, hwv⟩ := l1 v hv
        refine ⟨w, Or.inl hw, hwv, ?_⟩
        have := ih1 v hv (Loses.intro r2 l2 n2)
          (fun u a b => hdisj u (a.elim (fun h => Or.inl h.1) fun h => Or.inr h.1) b)
          (fun u u' a b => hsep u u' (a.elim (fun h => Or.inl h.1) fun h => Or.inr h.1) b)
        refine this.congr (fun u => ?_) (fun u => ?_)
        · constructor
          · intro ⟨hu, hnv, hnw⟩
            exact hu.elim (fun h => Or.inl ⟨h, hnv, hnw⟩) Or.inr
          · intro hu
            rcases hu with ⟨h, hnv, hnw⟩ | h
            · exact ⟨Or.inl h, hnv, hnw⟩
            · refine ⟨Or.inr h, fun e => ?_, fun e => ?_⟩
              · rcases e with e | e
                · exact hdisj u (Or.inl (e ▸ hv)) (Or.inl h)
                · exact (hsep v u (Or.inl hv) (Or.inl h)).1 e
              · exact hdisj u (Or.inr (e ▸ hw)) (Or.inl h)
        · constructor
          · intro ⟨hu, hne, hnw⟩
            exact hu.elim (fun h => Or.inl ⟨h, hne, hnw⟩) Or.inr
          · intro hu
            rcases hu with ⟨h, hne, hnw⟩ | h
            · exact ⟨Or.inl h, hne, hnw⟩
            · refine ⟨Or.inr h, fun e => hdisj u (Or.inl (e ▸ hv)) (Or.inr h), fun e => ?_⟩
              rcases e with e | e
              · exact hdisj u (Or.inr (e ▸ hw)) (Or.inr h)
              · exact (hsep w u (Or.inr hw) (Or.inr h)).1 e
      · -- Blue moved in the second region; answer there.
        let w := r2 v hv
        have ⟨hw, hwv⟩ := l2 v hv
        refine ⟨w, Or.inr hw, hwv, ?_⟩
        have := ih2 v hv
          (fun u a b => hdisj u a (b.elim (fun h => Or.inl h.1) fun h => Or.inr h.1))
          (fun u u' a b => hsep u u' a (b.elim (fun h => Or.inl h.1) fun h => Or.inr h.1))
        refine this.congr (fun u => ?_) (fun u => ?_)
        · constructor
          · intro ⟨hu, hnv, hnw⟩
            exact hu.elim Or.inl (fun h => Or.inr ⟨h, hnv, hnw⟩)
          · intro hu
            rcases hu with h | ⟨h, hnv, hnw⟩
            · refine ⟨Or.inl h, fun e => ?_, fun e => ?_⟩
              · rcases e with e | e
                · exact hdisj u (Or.inl h) (Or.inl (e ▸ hv))
                · exact (hsep u v (Or.inl h) (Or.inl hv)).2 e
              · exact hdisj u (Or.inl h) (Or.inr (e ▸ hw))
            · exact ⟨Or.inr h, hnv, hnw⟩
        · constructor
          · intro ⟨hu, hne, hnw⟩
            exact hu.elim Or.inl (fun h => Or.inr ⟨h, hne, hnw⟩)
          · intro hu
            rcases hu with h | ⟨h, hne, hnw⟩
            · refine ⟨Or.inl h, fun e => hdisj u (Or.inr h) (Or.inl (e ▸ hv)), fun e => ?_⟩
              rcases e with e | e
              · exact hdisj u (Or.inr h) (Or.inr (e ▸ hw))
              · exact (hsep u w (Or.inr h) (Or.inr hw)).2 e
            · exact ⟨Or.inr h, hne, hnw⟩

end Col
