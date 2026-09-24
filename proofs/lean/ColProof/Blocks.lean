import ColProof.Game

/-!
# Blocks, seams and windows

A `Blk` is a position on a `3 × w` strip (columns `0 … w-1`) that the player
to move (Blue) loses. `Blk.cat` places two blocks side by side; it needs the
seam condition that no row is White-legal on both sides of the joint.
`Blk.rep4` repeats a width-4 block. `window_step` is the step used by every
case of the induction: Blue opens inside a window block, White replies, and
the resulting position is dominated by `left · window · right`.
-/

namespace Col

/-- The empty `3 × n` board: every cell legal for both players. -/
def board (n : Nat) : Board := fun u => u.1 < 3 ∧ u.2 < n

structure Blk where
  w : Nat
  A : Board
  B : Board
  supp : ∀ u, A u ∨ B u → u.1 < 3 ∧ u.2 < w
  loses : Loses adj A B

/-- Grid edges that do not cross between columns `x - 1` and `x`. -/
def cutAt (x : Nat) (u v : Cell) : Prop :=
  adj u v ∧ ¬ (u.2 < x ∧ x ≤ v.2) ∧ ¬ (v.2 < x ∧ x ≤ u.2)

def shiftB (d : Nat) (P : Board) : Board := fun u => d ≤ u.2 ∧ P (u.1, u.2 - d)

theorem Loses.shift {X Y : Board} (h : Loses adj X Y) (d : Nat) (H : Cell → Cell → Prop)
    (hH : ∀ u u', d ≤ u.2 → d ≤ u'.2 → (H u u' ↔ adj u u')) :
    Loses H (shiftB d X) (shiftB d Y) := by
  refine h.pull (fun u => (u.1, u.2 - d)) (fun u => (u.1, u.2 + d)) (fun u => d ≤ u.2)
    (fun u => Iff.rfl) (fun u => Iff.rfl) ?_ ?_ ?_
  · intro u _
    exact ⟨Nat.le_add_left d u.2, by simp⟩
  · intro u u' h1 h2 e
    simp only [Prod.mk.injEq] at e
    exact Prod.ext e.1 (by omega)
  · intro u u' h1 h2
    rw [hH u u' h1 h2]
    unfold adj
    omega

def Blk.cat (b1 b2 : Blk) (hseam : ∀ r, b1.B (r, b1.w - 1) → b2.B (r, 0) → False) : Blk where
  w := b1.w + b2.w
  A := fun u => b1.A u ∨ shiftB b1.w b2.A u
  B := fun u => b1.B u ∨ shiftB b1.w b2.B u
  supp := by
    intro u hu
    rcases hu with (h | h) | (h | h)
    · have := b1.supp u (Or.inl h); omega
    · have := b2.supp _ (Or.inl h.2); simp at this; omega
    · have := b1.supp u (Or.inr h); omega
    · have := b2.supp _ (Or.inr h.2); simp at this; omega
  loses := by
    have h1 : Loses (cutAt b1.w) b1.A b1.B := by
      refine b1.loses.pull id id (fun u => u.2 < b1.w) ?_ ?_ ?_ ?_ ?_
      · intro u; exact ⟨fun h => ⟨(b1.supp u (Or.inl h)).2, h⟩, fun h => h.2⟩
      · intro u; exact ⟨fun h => ⟨(b1.supp u (Or.inr h)).2, h⟩, fun h => h.2⟩
      · intro u hu; exact ⟨(b1.supp u hu).2, rfl⟩
      · intro u u' _ _ e; exact e
      · intro u u' (h : u.2 < b1.w) (h' : u'.2 < b1.w)
        simp only [cutAt, id]
        constructor
        · exact fun h => h.1
        · intro ha; exact ⟨ha, by omega, by omega⟩
    have h2 : Loses (cutAt b1.w) (shiftB b1.w b2.A) (shiftB b1.w b2.B) := by
      refine b2.loses.shift b1.w (cutAt b1.w) ?_
      intro u u' h h'
      simp only [cutAt]
      constructor
      · exact fun h => h.1
      · intro ha; exact ⟨ha, by omega, by omega⟩
    have h3 := h1.union h2
      (fun u a b => by
        have := b1.supp u a
        rcases b with b | b <;> (have := b.1; omega))
      (fun u u' a b => by
        have := b1.supp u a
        have hb : b1.w ≤ u'.2 := by rcases b with b | b <;> exact b.1
        simp only [cutAt]
        constructor
        · intro ⟨_, h, _⟩; exact h ⟨this.2, hb⟩
        · intro ⟨_, _, h⟩; exact h ⟨this.2, hb⟩)
    refine h3.compare (fun u v h => h.1) (fun u h => h) (fun u h => h) ?_
    intro u w hadj hnc hu hw
    have hcross : (w.2 < b1.w ∧ b1.w ≤ u.2) ∨ (u.2 < b1.w ∧ b1.w ≤ w.2) :=
      Classical.byContradiction fun hn => hnc ⟨hadj, fun h => hn (Or.inl h), fun h => hn (Or.inr h)⟩
    -- The crossing edge joins (r, b1.w-1) and (r, b1.w); both are virtually White-legal.
    have key : ∀ p q : Cell, adj p q → p.2 < b1.w → b1.w ≤ q.2 →
        (b1.B p ∨ shiftB b1.w b2.B p) → (b1.B q ∨ shiftB b1.w b2.B q) → False := by
      intro p q hpq hp hq bp bq
      have bp' : b1.B p := bp.elim id fun h => absurd h.1 (by omega)
      have bq' : shiftB b1.w b2.B q := bq.elim (fun h => absurd (b1.supp q (Or.inr h)).2 (by omega)) id
      obtain ⟨p1, p2⟩ := p
      obtain ⟨q1, q2⟩ := q
      unfold adj at hpq
      simp only at hp hq hpq
      have e1 : p1 = q1 := by omega
      have e2 : p2 = b1.w - 1 := by omega
      have e3 : q2 - b1.w = 0 := by omega
      subst e1 e2
      exact hseam p1 bp' (by have := bq'.2; simp only at this; rw [e3] at this; exact this)
    rcases hcross with ⟨a, b⟩ | ⟨a, b⟩
    · exact key w u hadj a b hw hu
    · exact key u w (adj_symm hadj) a b hu hw

def Blk.empty : Blk where
  w := 0
  A := fun _ => False
  B := fun _ => False
  supp := fun _ h => h.elim False.elim False.elim
  loses := Loses.of_empty fun _ h => h

/-! ## Repeating a width-4 block -/

theorem rep4_loses (b : Blk) (hw : b.w = 4) (hself : ∀ r, b.B (r, 3) → b.B (r, 0) → False) :
    ∀ m, Loses adj (fun u => u.2 < 4 * m ∧ b.A (u.1, u.2 % 4))
      (fun u => u.2 < 4 * m ∧ b.B (u.1, u.2 % 4)) := by
  intro m
  induction m with
  | zero => exact Loses.of_empty fun u h => by omega
  | succ m ih =>
    let bm : Blk :=
      { w := 4 * m
        A := fun u => u.2 < 4 * m ∧ b.A (u.1, u.2 % 4)
        B := fun u => u.2 < 4 * m ∧ b.B (u.1, u.2 % 4)
        supp := by
          intro u hu
          rcases hu with h | h
          · exact ⟨(b.supp _ (Or.inl h.2)).1, h.1⟩
          · exact ⟨(b.supp _ (Or.inr h.2)).1, h.1⟩
        loses := ih }
    have hseam : ∀ r, b.B (r, b.w - 1) → bm.B (r, 0) → False := by
      intro r h1 h2
      rw [hw] at h1
      exact hself r h1 h2.2
    refine (b.cat bm hseam).loses.congr (fun u => ?_) (fun u => ?_)
    · simp only [Blk.cat, shiftB, bm, hw]
      constructor
      · intro ⟨h1, h2⟩
        by_cases hc : u.2 < 4
        · left
          have : u.2 % 4 = u.2 := by omega
          rw [this] at h2
          exact h2
        · right
          refine ⟨by omega, by omega, ?_⟩
          have : (u.2 - 4) % 4 = u.2 % 4 := by omega
          rw [this]; exact h2
      · intro h
        rcases h with h | ⟨h1, h2, h3⟩
        · have := (b.supp u (Or.inl h)).2
          rw [hw] at this
          have e : u.2 % 4 = u.2 := by omega
          exact ⟨by omega, by rw [e]; exact h⟩
        · have : (u.2 - 4) % 4 = u.2 % 4 := by omega
          rw [this] at h3
          exact ⟨by omega, h3⟩
    · simp only [Blk.cat, shiftB, bm, hw]
      constructor
      · intro ⟨h1, h2⟩
        by_cases hc : u.2 < 4
        · left
          have : u.2 % 4 = u.2 := by omega
          rw [this] at h2
          exact h2
        · right
          refine ⟨by omega, by omega, ?_⟩
          have : (u.2 - 4) % 4 = u.2 % 4 := by omega
          rw [this]; exact h2
      · intro h
        rcases h with h | ⟨h1, h2, h3⟩
        · have := (b.supp u (Or.inr h)).2
          rw [hw] at this
          have e : u.2 % 4 = u.2 := by omega
          exact ⟨by omega, by rw [e]; exact h⟩
        · have : (u.2 - 4) % 4 = u.2 % 4 := by omega
          rw [this] at h3
          exact ⟨by omega, h3⟩

/-- `m` copies of a width-4 block side by side. -/
def Blk.rep4 (b : Blk) (hw : b.w = 4) (hself : ∀ r, b.B (r, 3) → b.B (r, 0) → False) (m : Nat) :
    Blk where
  w := 4 * m
  A := fun u => u.2 < 4 * m ∧ b.A (u.1, u.2 % 4)
  B := fun u => u.2 < 4 * m ∧ b.B (u.1, u.2 % 4)
  supp := by
    intro u hu
    rcases hu with h | h
    · exact ⟨(b.supp _ (Or.inl h.2)).1, h.1⟩
    · exact ⟨(b.supp _ (Or.inr h.2)).1, h.1⟩
  loses := rep4_loses b hw hself m

/-! ## The window step -/

/-- The position after Blue's move `v` and White's reply `w` on the empty
`3 × n` board, with Blue to move, is a loss for Blue provided it is dominated
by `L · W · R`, where the window `W` contains both moves. All hypotheses are
local to the window and its two seams. -/
theorem window_step (L W R : Blk) (v' w' : Cell) (n : Nat) (v w : Cell)
    (hn : L.w + W.w + R.w = n) (hvdef : v = (v'.1, L.w + v'.2)) (hwdef : w = (w'.1, L.w + w'.2))
    (hLfull : ∀ r c, r < 3 → c < L.w → L.A (r, c))
    (hRfull : ∀ r c, r < 3 → c < R.w → R.A (r, c))
    (hWA : ∀ r c, r < 3 → c < W.w → ¬ ((r, c) = v' ∨ adj v' (r, c)) → (r, c) ≠ w' → W.A (r, c))
    (hWB : ∀ u, W.B u → u ≠ v' ∧ ¬ (u = w' ∨ adj w' u))
    (hLseam : ∀ r, L.B (r, L.w - 1) → W.B (r, 0) → False)
    (hRseam : ∀ r, W.B (r, W.w - 1) → R.B (r, 0) → False)
    (hLnb : w'.2 = 0 → ¬ L.B (w'.1, L.w - 1))
    (hRnb : w'.2 + 1 = W.w → ¬ R.B (w'.1, 0))
    (hv' : v'.2 < W.w) (hw' : w'.1 < 3 ∧ w'.2 < W.w) (hvw : w' ≠ v') :
    board n w ∧ w ≠ v ∧ Loses adj (afterX adj (board n) v w) (afterY adj (board n) v w) := by
  obtain ⟨v1, v2⟩ := v'
  obtain ⟨w1, w2⟩ := w'
  subst hvdef hwdef hn
  simp only at *
  have hWpos : 0 < W.w := by omega
  let LW := L.cat W hLseam
  have hseam2 : ∀ r, LW.B (r, LW.w - 1) → R.B (r, 0) → False := by
    intro r h hR
    rcases h with h | h
    · have := (L.supp _ (Or.inr h)).2
      simp only [LW, Blk.cat] at this
      omega
    · have e : L.w + W.w - 1 - L.w = W.w - 1 := by omega
      have h2 := h.2
      simp only [LW, Blk.cat] at h2
      rw [e] at h2
      exact hRseam r h2 hR
  let T := LW.cat R hseam2
  refine ⟨⟨hw'.1, by omega⟩, fun e => hvw ?_, ?_⟩
  · simp only [Prod.mk.injEq] at e ⊢; omega
  refine T.loses.compare (fun _ _ h => h) ?_ ?_ (fun _ _ h h' => absurd h h')
  · -- Blue keeps every move.
    intro ⟨r, x⟩ ⟨⟨hr, hx⟩, hnv, hnw⟩
    simp only [T, LW, Blk.cat, shiftB] at *
    by_cases h1 : x < L.w
    · exact Or.inl (Or.inl (hLfull r x hr h1))
    by_cases h2 : x < L.w + W.w
    · refine Or.inl (Or.inr ⟨by omega, hWA r (x - L.w) hr (by omega) ?_ ?_⟩)
      · intro h
        apply hnv
        simp only [Prod.mk.injEq, adj] at h ⊢
        omega
      · intro h
        apply hnw
        simp only [Prod.mk.injEq] at h ⊢
        omega
    · exact Or.inr ⟨by omega, hRfull r (x - (L.w + W.w)) hr (by omega)⟩
  · -- White gains no move.
    intro ⟨r, x⟩ hu
    simp only [T, LW, Blk.cat, shiftB] at hu
    simp only [afterY, board]
    rcases hu with (hL | ⟨hx, hW⟩) | ⟨hx, hR⟩
    · have hs := L.supp _ (Or.inr hL)
      simp only at hs
      refine ⟨⟨hs.1, by omega⟩, fun e => by simp only [Prod.mk.injEq] at e; omega, fun h => ?_⟩
      have hadj : adj (w1, L.w + w2) (r, x) := by
        rcases h with h | h
        · simp only [Prod.mk.injEq] at h; omega
        · exact h
      unfold adj at hadj
      simp only at hadj
      have e1 : w2 = 0 := by omega
      have e2 : x = L.w - 1 := by omega
      have e3 : r = w1 := by omega
      subst e2 e3
      exact hLnb e1 hL
    · have hs := W.supp _ (Or.inr hW)
      simp only at hs
      have ⟨hne, hnw⟩ := hWB _ hW
      refine ⟨⟨hs.1, by omega⟩, fun e => hne ?_, fun h => hnw ?_⟩
      · simp only [Prod.mk.injEq] at e ⊢; omega
      · rcases h with h | h
        · left; simp only [Prod.mk.injEq] at h ⊢; omega
        · right; unfold adj at h ⊢; simp only at h ⊢; omega
    · have hs := R.supp _ (Or.inr hR)
      simp only at hs
      refine ⟨⟨hs.1, by omega⟩, fun e => by simp only [Prod.mk.injEq] at e; omega, fun h => ?_⟩
      have hadj : adj (w1, L.w + w2) (r, x) := by
        rcases h with h | h
        · simp only [Prod.mk.injEq] at h; omega
        · exact h
      unfold adj at hadj
      simp only at hadj
      have e1 : w2 + 1 = W.w := by omega
      have e2 : x - (L.w + W.w) = 0 := by omega
      have e3 : r = w1 := by omega
      rw [e2, e3] at hR
      exact hRnb e1 hR

end Col
