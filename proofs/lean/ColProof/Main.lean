import ColProof.Blocks
import ColProof.Data

/-!
# Every empty `3 × n` Col board is a second-player win

`Loses adj (board n) (board n)`: the player to move on the empty `3 × n`
board loses. The two players have the same legal cells on the empty board, so
this holds whichever colour moves first; in game-theoretic terms the board has
value `0`.
-/

namespace Col

instance (w key : Nat) (u : Cell) : Decidable (gA w key u) := by unfold gA; infer_instance
instance (w key : Nat) (u : Cell) : Decidable (gB w key u) := by unfold gB; infer_instance

def gadBlk (w key : Nat) (h : Loses adj (gA w key) (gB w key)) : Blk where
  w := w
  A := gA w key
  B := gB w key
  supp := fun u hu => hu.elim (fun h => ⟨h.1, h.2.1⟩) (fun h => ⟨h.1, h.2.1⟩)
  loses := h

/-! ## The repeated bricks `E4` and `Ebar` -/

def E4g : Blk := gadBlk 4 E4_root E4_loses
def Ebarg : Blk := gadBlk 4 Ebar_root Ebar_loses

theorem E4_self : ∀ r, E4g.B (r, 3) → E4g.B (r, 0) → False := by
  have h : ∀ r, r < 3 → E4_root.testBit (idx 4 r 3) = true → E4_root.testBit (idx 4 r 0) = true → False := by
    decide
  exact fun r h1 h2 => h r h1.1 h1.2.2 h2.2.2

theorem Ebar_self : ∀ r, Ebarg.B (r, 3) → Ebarg.B (r, 0) → False := by
  have h : ∀ r, r < 3 → Ebar_root.testBit (idx 4 r 3) = true → Ebar_root.testBit (idx 4 r 0) = true →
      False := by
    decide
  exact fun r h1 h2 => h r h1.1 h1.2.2 h2.2.2

def E4rep (a : Nat) : Blk := E4g.rep4 rfl E4_self a
def Ebarrep (b : Nat) : Blk := Ebarg.rep4 rfl Ebar_self b

theorem E4_full : ∀ r, r < 3 → ∀ c, c < 4 → E4_root.testBit (3 * 4 + idx 4 r c) = true := by decide
theorem Ebar_full : ∀ r, r < 3 → ∀ c, c < 4 → Ebar_root.testBit (3 * 4 + idx 4 r c) = true := by decide

theorem E4rep_full (a : Nat) : ∀ r c, r < 3 → c < (E4rep a).w → (E4rep a).A (r, c) :=
  fun r c hr hc => ⟨hc, hr, Nat.mod_lt _ (by decide), E4_full r hr _ (Nat.mod_lt _ (by decide))⟩

theorem Ebarrep_full (b : Nat) : ∀ r c, r < 3 → c < (Ebarrep b).w → (Ebarrep b).A (r, c) :=
  fun r c hr hc => ⟨hc, hr, Nat.mod_lt _ (by decide), Ebar_full r hr _ (Nat.mod_lt _ (by decide))⟩

/-- The last column of `E4^a` is White-legal at most where `E4`'s is. -/
theorem E4rep_right {a r : Nat} (h : (E4rep a).B (r, (E4rep a).w - 1)) :
    E4_root.testBit (idx 4 r 3) = true := by
  obtain ⟨h1, _, _, h2⟩ := h
  simp only [E4rep, Blk.rep4] at h1 h2
  have e : (4 * a - 1) % 4 = 3 := by omega
  rw [e] at h2
  exact h2

theorem Ebarrep_left {b r : Nat} (h : (Ebarrep b).B (r, 0)) : Ebar_root.testBit (idx 4 r 0) = true :=
  h.2.2.2

/-! ## Windows -/

/-- The window conditions that do not depend on the left neighbour:
domination of the local position, the right seam against `Ebar`, and the
neighbour of White's reply across it. -/
def WinOK (w key : Nat) (v' w' : Cell) : Prop :=
  (∀ r, r < 3 → ∀ c, c < w → ¬ ((r, c) = v' ∨ adj v' (r, c)) → (r, c) ≠ w' →
      key.testBit (3 * w + idx w r c) = true) ∧
  (∀ r, r < 3 → ∀ c, c < w → key.testBit (idx w r c) = true →
      (r, c) ≠ v' ∧ ¬ ((r, c) = w' ∨ adj w' (r, c))) ∧
  (∀ r, r < 3 → key.testBit (idx w r (w - 1)) = true → Ebar_root.testBit (idx 4 r 0) = false) ∧
  (w'.2 + 1 = w → Ebar_root.testBit (idx 4 w'.1 0) = false) ∧
  v'.1 < 3 ∧ v'.2 < w ∧ w'.1 < 3 ∧ w'.2 < w ∧ w' ≠ v'

/-- Seam conditions against `E4^a` on the left. -/
def LeftE4OK (w key : Nat) (w' : Cell) : Prop :=
  (∀ r, r < 3 → E4_root.testBit (idx 4 r 3) = true → key.testBit (idx w r 0) = false) ∧
  (w'.2 = 0 → E4_root.testBit (idx 4 w'.1 3) = false)

/-- Seam conditions against an empty board on the left (whose last column is
White-legal in every row). -/
def LeftHOK (w key : Nat) (w' : Cell) : Prop :=
  (∀ r, r < 3 → key.testBit (idx w r 0) = false) ∧ w'.2 ≠ 0

/-- An opening has a good reply: afterwards the mover (Blue) loses. -/
def Good (n : Nat) (v : Cell) : Prop :=
  ∃ w, board n w ∧ w ≠ v ∧ Loses adj (afterX adj (board n) v w) (afterY adj (board n) v w)

theorem window_good (L W : Blk) (b key : Nat) (v' w' : Cell)
    (hWA : ∀ u, W.A u ↔ gA W.w key u) (hWB : ∀ u, W.B u ↔ gB W.w key u)
    (hok : WinOK W.w key v' w')
    (hLfull : ∀ r c, r < 3 → c < L.w → L.A (r, c))
    (hLseam : ∀ r, L.B (r, L.w - 1) → key.testBit (idx W.w r 0) = true → False)
    (hLnb : w'.2 = 0 → ¬ L.B (w'.1, L.w - 1))
    (n : Nat) (hn : L.w + W.w + 4 * b = n) :
    Good n (v'.1, L.w + v'.2) := by
  obtain ⟨hA, hB, hrs, hrn, _, hv2, hw1, hw2, hvw⟩ := hok
  refine ⟨_, window_step L W (Ebarrep b) v' w' n _ _ hn rfl rfl hLfull (Ebarrep_full b) ?_ ?_ ?_ ?_ hLnb ?_
    hv2 ⟨hw1, hw2⟩ hvw⟩
  · intro r c hr hc h1 h2
    exact (hWA _).2 ⟨hr, hc, hA r hr c hc h1 h2⟩
  · intro ⟨r, c⟩ hu
    obtain ⟨hr, hc, hbit⟩ := (hWB _).1 hu
    exact hB r hr c hc hbit
  · intro r hL hW
    exact hLseam r hL ((hWB _).1 hW).2.2
  · intro r hW hR
    obtain ⟨hr, _, hbit⟩ := (hWB _).1 hW
    have h1 := Ebarrep_left hR
    rw [hrs r hr hbit] at h1
    exact absurd h1 (by decide)
  · intro h0 hR
    have h1 := Ebarrep_left hR
    rw [hrn h0] at h1
    exact absurd h1 (by decide)

/-- Window step with `E4^a` on the left. -/
theorem good_E4 (a b w key : Nat) (hloses : Loses adj (gA w key) (gB w key)) (v' w' : Cell)
    (hok : WinOK w key v' w') (hleft : LeftE4OK w key w') (n : Nat) (hn : 4 * a + w + 4 * b = n) :
    Good n (v'.1, 4 * a + v'.2) :=
  window_good (E4rep a) (gadBlk w key hloses) b key v' w' (fun _ => Iff.rfl) (fun _ => Iff.rfl)
    hok (E4rep_full a)
    (fun r hL hbit => by
      have h := hleft.1 r hL.2.1 (E4rep_right hL)
      simp only [gadBlk] at hbit
      rw [h] at hbit
      exact absurd hbit (by decide))
    (fun h0 hL => by
      have h := E4rep_right hL
      rw [hleft.2 h0] at h
      exact absurd h (by decide))
    n hn

/-- Window step with nothing on the left (the window touches the board edge). -/
theorem good_edge (b w key : Nat) (hloses : Loses adj (gA w key) (gB w key)) (v' w' : Cell)
    (hok : WinOK w key v' w') (n : Nat) (hn : w + 4 * b = n) : Good n v' := by
  have := window_good Blk.empty (gadBlk w key hloses) b key v' w' (fun _ => Iff.rfl) (fun _ => Iff.rfl)
    hok (fun _ _ _ h => absurd h (Nat.not_lt_zero _)) (fun _ h _ => h) (fun _ h => h) n
    (by simp only [Blk.empty, gadBlk]; omega)
  simpa [Blk.empty] using this

/-- Window step with the empty board `H_c` on the left (Case 6). -/
theorem good_H (c b w key : Nat) (hloses : Loses adj (gA w key) (gB w key))
    (hH : Loses adj (board c) (board c)) (v' w' : Cell)
    (hok : WinOK w key v' w') (hleft : LeftHOK w key w') (n : Nat) (hn : c + w + 4 * b = n) :
    Good n (v'.1, c + v'.2) :=
  let H : Blk := ⟨c, board c, board c, fun _ hu => hu.elim id id, hH⟩
  window_good H (gadBlk w key hloses) b key v' w' (fun _ => Iff.rfl) (fun _ => Iff.rfl)
    hok (fun _ _ hr hc => ⟨hr, hc⟩)
    (fun r hL hbit => by
      simp only [gadBlk] at hbit
      rw [hleft.1 r hL.1] at hbit
      exact absurd hbit (by decide))
    (fun h0 _ => hleft.2 h0) n hn

theorem ok_case1_0_1 : WinOK 7 W_case1_0_1_root (0, 1) (1, 4) := by
  unfold WinOK; refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩ <;> decide
theorem left_case1_0_1 : LeftE4OK 7 W_case1_0_1_root (1, 4) := by
  unfold LeftE4OK; refine ⟨?_, ?_⟩ <;> decide
theorem ok_case1_0_3 : WinOK 7 W_case1_0_3_root (0, 3) (1, 4) := by
  unfold WinOK; refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩ <;> decide
theorem left_case1_0_3 : LeftE4OK 7 W_case1_0_3_root (1, 4) := by
  unfold LeftE4OK; refine ⟨?_, ?_⟩ <;> decide
theorem ok_case1_1_0 : WinOK 7 W_case1_1_0_root (1, 0) (1, 4) := by
  unfold WinOK; refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩ <;> decide
theorem left_case1_1_0 : LeftE4OK 7 W_case1_1_0_root (1, 4) := by
  unfold LeftE4OK; refine ⟨?_, ?_⟩ <;> decide
theorem ok_case1_1_2 : WinOK 7 W_case1_1_2_root (1, 2) (1, 4) := by
  unfold WinOK; refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩ <;> decide
theorem left_case1_1_2 : LeftE4OK 7 W_case1_1_2_root (1, 4) := by
  unfold LeftE4OK; refine ⟨?_, ?_⟩ <;> decide
theorem ok_case2 : WinOK 3 W_case2_root (0, 0) (2, 2) := by
  unfold WinOK; refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩ <;> decide
theorem ok_case3 : WinOK 7 W_case3_root (0, 2) (2, 0) := by
  unfold WinOK; refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩ <;> decide
theorem left_case3 : LeftE4OK 7 W_case3_root (2, 0) := by
  unfold LeftE4OK; refine ⟨?_, ?_⟩ <;> decide
theorem ok_case4 : WinOK 7 W_case4_root (0, 4) (2, 6) := by
  unfold WinOK; refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩ <;> decide
theorem left_case4 : LeftE4OK 7 W_case4_root (2, 6) := by
  unfold LeftE4OK; refine ⟨?_, ?_⟩ <;> decide
theorem ok_case5 : WinOK 7 W_case5_root (1, 1) (0, 0) := by
  unfold WinOK; refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩ <;> decide
theorem left_case5 : LeftE4OK 7 W_case5_root (0, 0) := by
  unfold LeftE4OK; refine ⟨?_, ?_⟩ <;> decide
theorem ok_case6 : WinOK 8 W_case6_root (1, 0) (0, 1) := by
  unfold WinOK; refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩ <;> decide
theorem left_case6 : LeftHOK 8 W_case6_root (0, 1) := by
  unfold LeftHOK; refine ⟨?_, ?_⟩ <;> decide

/-! ## Symmetry: only a quarter of the openings need an answer -/

theorem good_of_symm (n : Nat) (σ : Cell → Cell) (hb : ∀ u, board n u → board n (σ u))
    (hinv : ∀ u, board n u → σ (σ u) = u)
    (hadj : ∀ u u', board n u → board n u' → (adj (σ u) (σ u') ↔ adj u u'))
    (v : Cell) (hv : board n v) (h : Good n (σ v)) : Good n v := by
  obtain ⟨w, hw, hne, hL⟩ := h
  have hinj : ∀ u u', board n u → board n u' → σ u = σ u' → u = u' := fun u u' h1 h2 e => by
    rw [← hinv u h1, ← hinv u' h2, e]
  refine ⟨σ w, hb w hw, fun e => hne (by rw [← e, hinv w hw]), ?_⟩
  refine hL.pull σ σ (board n) (fun u => ?_) (fun u => ?_) ?_ hinj (fun u u' h1 h2 => (hadj u u' h1 h2).symm)
  · simp only [afterX]
    constructor
    · intro ⟨hu, hnv, hnw⟩
      refine ⟨hu, hb u hu, fun h => hnv ?_, fun e => hnw ?_⟩
      · rcases h with h | h
        · exact Or.inl (hinj u v hu hv h)
        · exact Or.inr ((hadj v u hv hu).1 h)
      · rw [← e, hinv u hu]
    · intro ⟨hu, _, hnv, hnw⟩
      refine ⟨hu, fun h => hnv ?_, fun e => hnw ?_⟩
      · rcases h with h | h
        · exact Or.inl (by rw [h])
        · exact Or.inr ((hadj v u hv hu).2 h)
      · rw [e, hinv w hw]
  · simp only [afterY]
    constructor
    · intro ⟨hu, hne', hnw⟩
      refine ⟨hu, hb u hu, fun e => hne' (hinj u v hu hv e), fun h => hnw ?_⟩
      rcases h with h | h
      · exact Or.inl (by rw [← h, hinv u hu])
      · have := (hadj (σ w) u (hb w hw) hu).1
        rw [hinv w hw] at this
        exact Or.inr (this h)
    · intro ⟨hu, _, hne', hnw⟩
      refine ⟨hu, fun e => hne' (by rw [e]), fun h => hnw ?_⟩
      rcases h with h | h
      · exact Or.inl (by rw [h, hinv w hw])
      · have := (hadj (σ w) u (hb w hw) hu).2 h
        rw [hinv w hw] at this
        exact Or.inr this
  · intro u hu
    have : board n u := by
      rcases hu with h | h
      · exact h.1
      · exact h.1
    exact ⟨hb u this, hinv u this⟩

def flipH (n : Nat) (u : Cell) : Cell := (u.1, n - 1 - u.2)
def flipV (u : Cell) : Cell := (2 - u.1, u.2)

theorem good_flipH (n : Nat) (v : Cell) (hv : board n v) (h : Good n (flipH n v)) : Good n v := by
  refine good_of_symm n (flipH n) ?_ ?_ ?_ v hv h
  · intro u hu; simp only [board, flipH] at *; omega
  · intro u hu; simp only [board, flipH] at *; exact Prod.ext rfl (by simp; omega)
  · intro u u' hu hu'; simp only [board, flipH, adj] at *; omega

theorem good_flipV (n : Nat) (v : Cell) (hv : board n v) (h : Good n (flipV v)) : Good n v := by
  refine good_of_symm n flipV ?_ ?_ ?_ v hv h
  · intro u hu; simp only [board, flipV] at *; omega
  · intro u hu; simp only [board, flipV] at *; exact Prod.ext (by simp; omega) rfl
  · intro u u' hu hu'; simp only [board, flipV, adj] at *; omega

/-! ## Even widths: the half-turn mirror strategy -/

def rot (n : Nat) (u : Cell) : Cell := (2 - u.1, n - 1 - u.2)

theorem mirror (n : Nat) (hn : n % 2 = 0) :
    ∀ (l : List Cell) (X : Board), (∀ u, X u → board n u) → (∀ u, X u → u ∈ l) →
      Loses adj X (fun u => board n u ∧ X (rot n u)) := by
  intro l
  induction l with
  | nil => intro X _ hl; exact Loses.of_empty fun u hu => absurd (hl u hu) List.not_mem_nil
  | cons x l ih =>
    intro X hX hl
    have hrb : ∀ u, board n u → board n (rot n u) := by
      intro u hu; simp only [board, rot] at *; omega
    have hinv : ∀ u, board n u → rot n (rot n u) = u := by
      intro u hu; simp only [board, rot] at *; exact Prod.ext (by simp; omega) (by simp; omega)
    have hadj : ∀ u u', board n u → board n u' → (adj (rot n u) (rot n u') ↔ adj u u') := by
      intro u u' hu hu'; simp only [board, rot, adj] at *; omega
    refine Loses.mk' fun v hv => ?_
    have hvb := hX v hv
    refine ⟨rot n v, ⟨hrb v hvb, by rw [hinv v hvb]; exact hv⟩, ?_, ?_⟩
    · intro e
      simp only [rot, board, Prod.ext_iff] at e hvb
      omega
    · -- Remove `v` from the candidate list and recurse.
      let X' := afterX adj X v (rot n v)
      have hX' : ∀ u, X' u → board n u := fun u hu => hX u hu.1
      have hmem : ∀ u, X' u → u ∈ (x :: l).erase v := fun u hu =>
        (List.mem_erase_of_ne fun e => hu.2.1 (Or.inl e)).2 (hl u hu.1)
      have hlen := List.length_erase_of_mem (hl v hv)
      simp only [List.length_cons, Nat.add_sub_cancel] at hlen
      -- Induct on the shorter list (strong form via length).
      have key : ∀ (m : Nat) (l' : List Cell) (Z : Board), l'.length ≤ m → (∀ u, Z u → board n u) →
          (∀ u, Z u → u ∈ l') → Loses adj Z (fun u => board n u ∧ Z (rot n u)) := by
        intro m
        induction m with
        | zero =>
          intro l' Z hlen _ hZ
          refine Loses.of_empty fun u hu => ?_
          have := hZ u hu
          cases l' with
          | nil => exact List.not_mem_nil this
          | cons _ _ => simp at hlen
        | succ m ihm =>
          intro l' Z hlen hZb hZ
          refine Loses.mk' fun u hu => ?_
          have hub := hZb u hu
          refine ⟨rot n u, ⟨hrb u hub, by rw [hinv u hub]; exact hu⟩, ?_, ?_⟩
          · intro e
            simp only [rot, board, Prod.ext_iff] at e hub
            omega
          · have h1 := ihm (l'.erase u) (afterX adj Z u (rot n u))
              (by have := List.length_erase_of_mem (hZ u hu); omega)
              (fun y hy => hZb y hy.1)
              (fun y hy => (List.mem_erase_of_ne fun e => hy.2.1 (Or.inl e)).2 (hZ y hy.1))
            refine h1.congr (fun y => Iff.rfl) (fun y => ?_)
            simp only [afterX, afterY]
            constructor
            · intro ⟨⟨hy, hZy⟩, hne, hnw⟩
              refine ⟨hy, hZy, fun h => hnw ?_, fun e => hne ?_⟩
              · rcases h with h | h
                · exact Or.inl (by rw [← h, hinv y hy])
                · have := (hadj u (rot n y) hub (hrb y hy)).2 h
                  rw [hinv y hy] at this
                  exact Or.inr this
              · rw [← hinv y hy, e, hinv u hub]
            · intro ⟨hy, hZy, hnv, hnw⟩
              refine ⟨⟨hy, hZy⟩, fun e => hnw (by rw [e]), fun h => hnv ?_⟩
              rcases h with h | h
              · exact Or.inl (by rw [h, hinv u hub])
              · have := (hadj u (rot n y) hub (hrb y hy)).1
                rw [hinv y hy] at this
                exact Or.inr (this h)
      exact key (x :: l).length _ _ (by simp at hlen ⊢; omega) hX' hmem |>.congr (fun _ => Iff.rfl)
        (fun y => by
          simp only [afterX, afterY]
          constructor
          · intro ⟨⟨hy, hXy⟩, hne, hnw⟩
            refine ⟨hy, hXy, fun h => hnw ?_, fun e => hne ?_⟩
            · rcases h with h | h
              · exact Or.inl (by rw [← h, hinv y hy])
              · have := (hadj v (rot n y) hvb (hrb y hy)).2 h
                rw [hinv y hy] at this
                exact Or.inr this
            · rw [← hinv y hy, e, hinv v hvb]
          · intro ⟨hy, hXy, hnv, hnw⟩
            refine ⟨⟨hy, hXy⟩, fun e => hnw (by rw [e]), fun h => hnv ?_⟩
            rcases h with h | h
            · exact Or.inl (by rw [h, hinv v hvb])
            · have := (hadj v (rot n y) hvb (hrb y hy)).1
              rw [hinv y hy] at this
              exact Or.inr (this h))

theorem even_width (n : Nat) (hn : n % 2 = 0) : Loses adj (board n) (board n) := by
  have hrb : ∀ u, board n u → board n (rot n u) := by
    intro u hu; simp only [board, rot] at *; omega
  refine (mirror n hn ((List.range 3).flatMap fun r => (List.range n).map fun c => (r, c)) (board n)
    (fun _ h => h) (fun u hu => ?_)).congr (fun _ => Iff.rfl) (fun u => ?_)
  · exact (List.mem_flatMap.2 ⟨u.1, List.mem_range.2 hu.1, List.mem_map.2 ⟨u.2, List.mem_range.2 hu.2, rfl⟩⟩ :
      u ∈ (List.range 3).flatMap fun r => (List.range n).map fun c => (r, c))
  · exact ⟨fun h => ⟨h, hrb u h⟩, fun h => h.1⟩

/-! ## Widths `4k + 1`: the tiling `E4^k F1` -/

def F1g : Blk := gadBlk 1 F1_root F1_loses

theorem width_4k1 (k : Nat) : Loses adj (board (4 * k + 1)) (board (4 * k + 1)) := by
  have hseam : ∀ r, (E4rep k).B (r, (E4rep k).w - 1) → F1g.B (r, 0) → False := by
    intro r h1 h2
    have hr := E4rep_right h1
    have : ∀ r, r < 3 → E4_root.testBit (idx 4 r 3) = true → F1_root.testBit (idx 1 r 0) = true → False := by
      decide
    exact this r h2.1 hr h2.2.2
  have hF : ∀ r, r < 3 → F1_root.testBit (3 * 1 + idx 1 r 0) = true := by decide
  let T := (E4rep k).cat F1g hseam
  refine T.loses.compare (fun _ _ h => h) ?_ ?_ (fun _ _ h h' => absurd h h')
  · intro ⟨r, c⟩ ⟨hr, hc⟩
    simp only [T, Blk.cat, shiftB, E4rep, Blk.rep4, F1g, gadBlk, E4g, gA]
    by_cases h : c < 4 * k
    · exact Or.inl ⟨h, hr, Nat.mod_lt _ (by decide), E4_full r hr _ (Nat.mod_lt _ (by decide))⟩
    · refine Or.inr ⟨by omega, hr, by omega, ?_⟩
      have : c - 4 * k = 0 := by omega
      rw [this]; exact hF r hr
  · intro u hu
    have := T.supp u (Or.inr hu)
    exact ⟨this.1, by simpa [T, Blk.cat, E4rep, Blk.rep4, F1g, gadBlk] using this.2⟩

/-! ## Widths `4k + 3` -/

theorem board_of_cert {w key : Nat} (h : Loses adj (gA w key) (gB w key))
    (hfull : ∀ r, r < 3 → ∀ c, c < w → key.testBit (3 * w + idx w r c) = true ∧ key.testBit (idx w r c) = true) :
    Loses adj (board w) (board w) :=
  h.congr (fun u => ⟨fun h => ⟨h.1, h.2, (hfull _ h.1 _ h.2).1⟩, fun h => ⟨h.1, h.2.1⟩⟩)
    (fun u => ⟨fun h => ⟨h.1, h.2, (hfull _ h.1 _ h.2).2⟩, fun h => ⟨h.1, h.2.1⟩⟩)

theorem width_3 : Loses adj (board 3) (board 3) := board_of_cert H3_loses (by decide)
theorem width_7 : Loses adj (board 7) (board 7) := board_of_cert H7_loses (by decide)

/-- The inductive step for `n = 4k + 3 ≥ 11`, for a normalised opening. -/
theorem step_normalised (k : Nat) (hk : 2 ≤ k)
    (ih : ∀ c, c < 4 * k + 3 → c % 4 = 3 → Loses adj (board c) (board c))
    (r c : Nat) (hr : r ≤ 1) (hc : c ≤ 2 * k + 1) : Good (4 * k + 3) (r, c) := by
  have e : ∀ (a : Nat) (v : Cell), v.1 = r → 4 * a + v.2 = c → (v.1, 4 * a + v.2) = (r, c) :=
    fun a v h1 h2 => by rw [h1, h2]
  by_cases hodd : (r + c) % 2 = 1
  · -- Case 1: odd parity, reply inside a seven-column window.
    have hj : c / 4 ≤ k - 1 := by omega
    rcases (by omega : r = 0 ∨ r = 1) with rfl | rfl
    · rcases (by omega : c % 4 = 1 ∨ c % 4 = 3) with hl | hl
      · have := good_E4 (c / 4) (k - 1 - c / 4) 7 _ W_case1_0_1_loses (0, 1) (1, 4)
          ok_case1_0_1 left_case1_0_1 (4 * k + 3) (by omega)
        rwa [e _ _ rfl (by simp; omega)] at this
      · have := good_E4 (c / 4) (k - 1 - c / 4) 7 _ W_case1_0_3_loses (0, 3) (1, 4)
          ok_case1_0_3 left_case1_0_3 (4 * k + 3) (by omega)
        rwa [e _ _ rfl (by simp; omega)] at this
    · rcases (by omega : c % 4 = 0 ∨ c % 4 = 2) with hl | hl
      · have := good_E4 (c / 4) (k - 1 - c / 4) 7 _ W_case1_1_0_loses (1, 0) (1, 4)
          ok_case1_1_0 left_case1_1_0 (4 * k + 3) (by omega)
        rwa [e _ _ rfl (by simp; omega)] at this
      · have := good_E4 (c / 4) (k - 1 - c / 4) 7 _ W_case1_1_2_loses (1, 2) (1, 4)
          ok_case1_1_2 left_case1_1_2 (4 * k + 3) (by omega)
        rwa [e _ _ rfl (by simp; omega)] at this
  rcases (by omega : r = 0 ∨ r = 1) with rfl | rfl
  · rcases (by omega : c = 0 ∨ c % 4 = 2 ∨ (c % 4 = 0 ∧ 4 ≤ c)) with hc0 | hc2 | ⟨hc0, hc4⟩
    · -- Case 2: the corner.
      subst hc0
      exact good_edge k 3 _ W_case2_loses (0, 0) (2, 2) ok_case2 (4 * k + 3) (by omega)
    · -- Case 3: outer row, column 2 mod 4.
      have := good_E4 (c / 4) (k - 1 - c / 4) 7 _ W_case3_loses (0, 2) (2, 0) ok_case3 left_case3
        (4 * k + 3) (by omega)
      rwa [e _ _ rfl (by simp; omega)] at this
    · -- Case 4: outer row, column 0 mod 4, not the corner.
      have := good_E4 (c / 4 - 1) (k - c / 4) 7 _ W_case4_loses (0, 4) (2, 6) ok_case4 left_case4
        (4 * k + 3) (by omega)
      rwa [e _ _ rfl (by simp; omega)] at this
  · rcases (by omega : c % 4 = 1 ∨ c % 4 = 3) with hl | hl
    · -- Case 5: middle row, column 1 mod 4.
      have := good_E4 (c / 4) (k - 1 - c / 4) 7 _ W_case5_loses (1, 1) (0, 0) ok_case5 left_case5
        (4 * k + 3) (by omega)
      rwa [e _ _ rfl (by simp; omega)] at this
    · -- Case 6: middle row, column 3 mod 4: a dead column and a narrower empty board.
      have hH := ih c (by omega) hl
      have := good_H c ((4 * k + 3 - c - 8) / 4) 8 _ W_case6_loses hH (1, 0) (0, 1) ok_case6 left_case6
        (4 * k + 3) (by omega)
      simpa using this

theorem step (k : Nat) (hk : 2 ≤ k)
    (ih : ∀ c, c < 4 * k + 3 → c % 4 = 3 → Loses adj (board c) (board c)) :
    Loses adj (board (4 * k + 3)) (board (4 * k + 3)) := by
  refine Loses.mk' fun ⟨r, c⟩ hv => ?_
  have hv' := hv
  obtain ⟨hr, hc⟩ := hv
  -- Reflect the opening into rows 0–1 and columns 0 … 2k+1.
  have hnorm : ∀ c', c' < 4 * k + 3 → ∀ r', r' < 3 → Good (4 * k + 3) (r', c') := by
    intro c' hc' r' hr'
    by_cases hcol : c' ≤ 2 * k + 1
    · by_cases hrow : r' ≤ 1
      · exact step_normalised k hk ih r' c' hrow hcol
      · refine good_flipV _ _ ⟨hr', hc'⟩ ?_
        exact step_normalised k hk ih _ _ (by simp [flipV]; omega) (by simpa [flipV] using hcol)
    · refine good_flipH _ _ ⟨hr', hc'⟩ ?_
      simp only [flipH]
      by_cases hrow : r' ≤ 1
      · exact step_normalised k hk ih _ _ hrow (by omega)
      · refine good_flipV _ _ ⟨hr', by omega⟩ ?_
        exact step_normalised k hk ih _ _ (by simp [flipV]; omega) (by simp [flipV]; omega)
  exact hnorm c hc r hr

/-- **Theorem.** For every `n`, the player to move on the empty `3 × n` Col
board loses. Both players have the same legal cells on the empty board, so
this holds whichever colour starts: the second player wins. -/
theorem three_by_n (n : Nat) : Loses adj (board n) (board n) := by
  induction n using Nat.strongRecOn with
  | _ n ih =>
    by_cases he : n % 2 = 0
    · exact even_width n he
    by_cases h1 : n % 4 = 1
    · have := width_4k1 (n / 4)
      rwa [show 4 * (n / 4) + 1 = n by omega] at this
    have h3 : n % 4 = 3 := by omega
    by_cases hn3 : n = 3
    · subst hn3; exact width_3
    by_cases hn7 : n = 7
    · subst hn7; exact width_7
    have := step (n / 4) (by omega) (fun c hc _ => ih c (by omega))
    rwa [show 4 * (n / 4) + 3 = n by omega] at this

end Col
