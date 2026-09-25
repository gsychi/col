import ColProof.Game

/-!
# Certificates for small positions

A position on a `3 × w` board is encoded by one natural number `key`: bit
`r * w + c` says that White may play at `(r, c)`, and bit `3 * w + r * w + c`
says that Blue may. A certificate is a sorted array `S` of keys. It is
*accepted* when, for every key in `S` and every Blue move, some White reply
leads to a key that is again in `S`. `Loses.of_certificate` proves that Blue,
moving first, loses every accepted key. The checker performs no search, and
its correctness does not depend on how the certificate was produced.
-/

namespace Col

def idx (w r c : Nat) : Nat := r * w + c
def bitA (w r c : Nat) : Nat := 2 ^ (3 * w + idx w r c)
def bitB (w r c : Nat) : Nat := 2 ^ (idx w r c)

/-- The closed neighbourhood of `(r, c)` inside the `3 × w` board, as a mask. -/
def nbhd (f : Nat → Nat → Nat) (w r c : Nat) : Nat :=
  f r c ||| (if 0 < c then f r (c - 1) else 0) ||| (if c + 1 < w then f r (c + 1) else 0)
    ||| (if 0 < r then f (r - 1) c else 0) ||| (if r + 1 < 3 then f (r + 1) c else 0)

def clr (key m : Nat) : Nat := key ^^^ (key &&& m)

/-- Blue plays at `(r, c)`: she loses its neighbourhood, White loses the cell. -/
def blueMove (w key r c : Nat) : Nat := clr key (nbhd (bitA w) w r c ||| bitB w r c)
/-- White plays at `(r, c)`: Blue loses the cell, White loses its neighbourhood. -/
def whiteMove (w key r c : Nat) : Nat := clr key (bitA w r c ||| nbhd (bitB w) w r c)

/-- Blue-legal cells of an encoded position. -/
def gA (w key : Nat) : Board := fun u => u.1 < 3 ∧ u.2 < w ∧ key.testBit (3 * w + idx w u.1 u.2) = true
/-- White-legal cells of an encoded position. -/
def gB (w key : Nat) : Board := fun u => u.1 < 3 ∧ u.2 < w ∧ key.testBit (idx w u.1 u.2) = true

theorem testBit_clr (key m i : Nat) : (clr key m).testBit i = (key.testBit i && !m.testBit i) := by
  simp only [clr, Nat.testBit_xor, Nat.testBit_and]
  cases key.testBit i <;> cases m.testBit i <;> rfl

theorem ite_testBit (p : Prop) [Decidable p] (x i : Nat) :
    (if p then x else 0).testBit i = (decide p && x.testBit i) := by
  by_cases h : p <;> simp [h, Nat.zero_testBit]

theorem rows3 {r : Nat} (h : r < 3) : r = 0 ∨ r = 1 ∨ r = 2 := by omega

/-- Evaluate a bit of a neighbourhood mask as a statement about cells. -/
theorem nbhd_testBit (w r c r' c' off : Nat) (hr : r < 3) (hr' : r' < 3) (hc : c < w) (hc' : c' < w) :
    (nbhd (fun r c => 2 ^ (off + idx w r c)) w r c).testBit (off + idx w r' c') = true ↔
      ((r', c') = (r, c) ∨ adj (r, c) (r', c')) := by
  simp only [nbhd, Nat.testBit_or, ite_testBit, Nat.testBit_two_pow, Bool.or_eq_true,
    Bool.and_eq_true, decide_eq_true_eq, idx, adj, Prod.mk.injEq]
  rcases rows3 hr with rfl | rfl | rfl <;> rcases rows3 hr' with rfl | rfl | rfl <;> omega

theorem bit_testBit (w r c r' c' off : Nat) (hr : r < 3) (hr' : r' < 3) (hc : c < w) (hc' : c' < w) :
    (2 ^ (off + idx w r c)).testBit (off + idx w r' c') = true ↔ (r', c') = (r, c) := by
  simp only [Nat.testBit_two_pow, decide_eq_true_eq, idx, Prod.mk.injEq]
  rcases rows3 hr with rfl | rfl | rfl <;> rcases rows3 hr' with rfl | rfl | rfl <;> omega

theorem idx_lt (w r c : Nat) (hr : r < 3) (hc : c < w) : idx w r c < 3 * w := by
  unfold idx; rcases rows3 hr with rfl | rfl | rfl <;> omega

theorem nbhdB_testBit_A (w r c r' c' : Nat) (hr : r < 3) (hr' : r' < 3) (hc : c < w) (hc' : c' < w) :
    (nbhd (bitB w) w r c).testBit (3 * w + idx w r' c') = false := by
  simp only [nbhd, bitB, Nat.testBit_or, ite_testBit, Nat.testBit_two_pow, Bool.or_eq_false_iff,
    Bool.and_eq_false_iff, decide_eq_false_iff_not, idx]
  rcases rows3 hr with rfl | rfl | rfl <;> rcases rows3 hr' with rfl | rfl | rfl <;> omega

theorem nbhdA_testBit_B (w r c r' c' : Nat) (hr : r < 3) (hr' : r' < 3) (hc : c < w) (hc' : c' < w) :
    (nbhd (bitA w) w r c).testBit (idx w r' c') = false := by
  simp only [nbhd, bitA, Nat.testBit_or, ite_testBit, Nat.testBit_two_pow, Bool.or_eq_false_iff,
    Bool.and_eq_false_iff, decide_eq_false_iff_not, idx]
  rcases rows3 hr with rfl | rfl | rfl <;> rcases rows3 hr' with rfl | rfl | rfl <;> omega

theorem bitA_testBit_B (w r c r' c' : Nat) (hr : r < 3) (hr' : r' < 3) (hc : c < w) (hc' : c' < w) :
    (bitA w r c).testBit (idx w r' c') = false := by
  simp only [bitA, Nat.testBit_two_pow, decide_eq_false_iff_not, idx]
  rcases rows3 hr with rfl | rfl | rfl <;> rcases rows3 hr' with rfl | rfl | rfl <;> omega

theorem bitB_testBit_A (w r c r' c' : Nat) (hr : r < 3) (hr' : r' < 3) (hc : c < w) (hc' : c' < w) :
    (bitB w r c).testBit (3 * w + idx w r' c') = false := by
  simp only [bitB, Nat.testBit_two_pow, decide_eq_false_iff_not, idx]
  rcases rows3 hr with rfl | rfl | rfl <;> rcases rows3 hr' with rfl | rfl | rfl <;> omega

theorem nbhdA_testBit (w r c r' c' : Nat) (hr : r < 3) (hr' : r' < 3) (hc : c < w) (hc' : c' < w) :
    (nbhd (bitA w) w r c).testBit (3 * w + idx w r' c') = true ↔
      ((r', c') = (r, c) ∨ adj (r, c) (r', c')) :=
  nbhd_testBit w r c r' c' (3 * w) hr hr' hc hc'

theorem nbhdB_testBit (w r c r' c' : Nat) (hr : r < 3) (hr' : r' < 3) (hc : c < w) (hc' : c' < w) :
    (nbhd (bitB w) w r c).testBit (idx w r' c') = true ↔ ((r', c') = (r, c) ∨ adj (r, c) (r', c')) := by
  have := nbhd_testBit w r c r' c' 0 hr hr' hc hc'
  simp only [Nat.zero_add] at this
  exact this

theorem gA_blueMove {w key r c : Nat} (hr : r < 3) (hc : c < w) (u : Cell) :
    gA w (blueMove w key r c) u ↔ gA w key u ∧ ¬ (u = (r, c) ∨ adj (r, c) u) := by
  obtain ⟨r', c'⟩ := u
  simp only [gA, blueMove, testBit_clr, Nat.testBit_or, Bool.and_eq_true, Bool.not_eq_true',
    Bool.or_eq_false_iff]
  constructor
  · intro ⟨h1, h2, h3, h4, _⟩
    refine ⟨⟨h1, h2, h3⟩, fun h => ?_⟩
    have := (nbhdA_testBit w r c r' c' hr h1 hc h2).2 h
    simp_all
  · intro ⟨⟨h1, h2, h3⟩, h4⟩
    refine ⟨h1, h2, h3, ?_, bitB_testBit_A w r c r' c' hr h1 hc h2⟩
    cases e : (nbhd (bitA w) w r c).testBit (3 * w + idx w r' c')
    · rfl
    · exact absurd ((nbhdA_testBit w r c r' c' hr h1 hc h2).1 e) h4

theorem gB_blueMove {w key r c : Nat} (hr : r < 3) (hc : c < w) (u : Cell) :
    gB w (blueMove w key r c) u ↔ gB w key u ∧ u ≠ (r, c) := by
  obtain ⟨r', c'⟩ := u
  simp only [gB, blueMove, testBit_clr, Nat.testBit_or, Bool.and_eq_true, Bool.not_eq_true',
    Bool.or_eq_false_iff, nbhdA_testBit_B w r c r' c' hr _ hc _]
  constructor
  · intro ⟨h1, h2, h3, h4, h5⟩
    refine ⟨⟨h1, h2, h3⟩, fun e => ?_⟩
    have := (bit_testBit w r c r' c' 0 hr h1 hc h2).2 e
    simp only [Nat.zero_add] at this
    simp_all [bitB]
  · intro ⟨⟨h1, h2, h3⟩, h4⟩
    refine ⟨h1, h2, h3, nbhdA_testBit_B w r c r' c' hr h1 hc h2, ?_⟩
    cases e : (bitB w r c).testBit (idx w r' c')
    · rfl
    · have := (bit_testBit w r c r' c' 0 hr h1 hc h2).1 (by simpa [bitB] using e)
      exact absurd this h4

theorem gA_whiteMove {w key r c : Nat} (hr : r < 3) (hc : c < w) (u : Cell) :
    gA w (whiteMove w key r c) u ↔ gA w key u ∧ u ≠ (r, c) := by
  obtain ⟨r', c'⟩ := u
  simp only [gA, whiteMove, testBit_clr, Nat.testBit_or, Bool.and_eq_true, Bool.not_eq_true',
    Bool.or_eq_false_iff]
  constructor
  · intro ⟨h1, h2, h3, h4, h5⟩
    refine ⟨⟨h1, h2, h3⟩, fun e => ?_⟩
    have := (bit_testBit w r c r' c' (3 * w) hr h1 hc h2).2 e
    simp_all [bitA]
  · intro ⟨⟨h1, h2, h3⟩, h4⟩
    refine ⟨h1, h2, h3, ?_, nbhdB_testBit_A w r c r' c' hr h1 hc h2⟩
    cases e : (bitA w r c).testBit (3 * w + idx w r' c')
    · rfl
    · exact absurd ((bit_testBit w r c r' c' (3 * w) hr h1 hc h2).1 (by simpa [bitA] using e)) h4

theorem gB_whiteMove {w key r c : Nat} (hr : r < 3) (hc : c < w) (u : Cell) :
    gB w (whiteMove w key r c) u ↔ gB w key u ∧ ¬ (u = (r, c) ∨ adj (r, c) u) := by
  obtain ⟨r', c'⟩ := u
  simp only [gB, whiteMove, testBit_clr, Nat.testBit_or, Bool.and_eq_true, Bool.not_eq_true',
    Bool.or_eq_false_iff]
  constructor
  · intro ⟨h1, h2, h3, h4, h5⟩
    refine ⟨⟨h1, h2, h3⟩, fun h => ?_⟩
    have := (nbhdB_testBit w r c r' c' hr h1 hc h2).2 h
    simp_all
  · intro ⟨⟨h1, h2, h3⟩, h4⟩
    refine ⟨h1, h2, h3, bitA_testBit_B w r c r' c' hr h1 hc h2, ?_⟩
    cases e : (nbhd (bitB w) w r c).testBit (idx w r' c')
    · rfl
    · exact absurd ((nbhdB_testBit w r c r' c' hr h1 hc h2).1 e) h4

/-! ## The checker -/

def cells (w : Nat) : List Cell :=
  (List.range 3).flatMap fun r => (List.range w).map fun c => (r, c)

theorem mem_cells {w : Nat} {u : Cell} : u ∈ cells w ↔ u.1 < 3 ∧ u.2 < w := by
  obtain ⟨r, c⟩ := u
  simp [cells, List.mem_flatMap, List.mem_map, List.mem_range]

/-- Binary search; only its positive answers are used, and they are re-checked. -/
def bsearch (S : Array Nat) (k : Nat) : Nat → Nat → Nat → Option Nat
  | 0, _, _ => none
  | fuel + 1, lo, hi =>
    if lo < hi then
      let mid := (lo + hi) / 2
      let x := S[mid]!
      if x = k then some mid
      else if x < k then bsearch S k fuel (mid + 1) hi
      else bsearch S k fuel lo mid
    else none

def memArr (S : Array Nat) (k : Nat) : Bool :=
  match bsearch S k 64 0 S.size with
  | some i => S[i]? == some k
  | none => false

theorem memArr_sound {S : Array Nat} {k : Nat} (h : memArr S k = true) : k ∈ S := by
  unfold memArr at h
  split at h
  · exact Array.mem_of_getElem? (by simpa using h)
  · exact absurd h (by simp)

/-- Every Blue move has a White reply that stays inside the certificate. -/
def okKey (w : Nat) (mem : Nat → Bool) (key : Nat) : Bool :=
  (cells w).all fun v => !key.testBit (3 * w + idx w v.1 v.2) ||
    (cells w).any fun u => (blueMove w key v.1 v.2).testBit (idx w u.1 u.2) &&
      mem (whiteMove w (blueMove w key v.1 v.2) u.1 u.2)

def Accepted (w : Nat) (S : Array Nat) : Prop := S.all (okKey w (memArr S)) = true

instance (w : Nat) (S : Array Nat) : Decidable (Accepted w S) := by
  unfold Accepted; infer_instance

theorem Loses.of_certificate {w : Nat} {S : Array Nat} (hS : Accepted w S) {key : Nat}
    (hk : memArr S key = true) : Loses adj (gA w key) (gB w key) := by
  suffices H : ∀ m (l : List Cell) key, l.length ≤ m → memArr S key = true →
      (∀ u, gA w key u → u ∈ l) → Loses adj (gA w key) (gB w key) from
    H _ (cells w) key (Nat.le_refl _) hk (fun u hu => mem_cells.2 ⟨hu.1, hu.2.1⟩)
  intro m
  induction m with
  | zero =>
    intro l key hl _ hsupp
    refine Loses.of_empty fun u hu => ?_
    have := hsupp u hu
    cases l with
    | nil => exact absurd this (List.not_mem_nil)
    | cons _ _ => simp at hl
  | succ m ih =>
    intro l key hl hk hsupp
    have hmem := memArr_sound hk
    have hok : okKey w (memArr S) key = true := by
      obtain ⟨i, hi, rfl⟩ := Array.mem_iff_getElem.1 hmem
      exact Array.all_eq_true.1 hS i hi
    refine Loses.mk' fun v hv => ?_
    obtain ⟨r, c⟩ := v
    obtain ⟨hr, hc, hbit⟩ := hv
    have h1 := List.all_eq_true.1 hok (r, c) (mem_cells.2 ⟨hr, hc⟩)
    simp only [hbit, Bool.not_true, Bool.false_or, List.any_eq_true, Bool.and_eq_true] at h1
    obtain ⟨⟨r', c'⟩, hu, hbB, hin⟩ := h1
    obtain ⟨hr', hc'⟩ := mem_cells.1 hu
    have hB' : gB w (blueMove w key r c) (r', c') := ⟨hr', hc', hbB⟩
    obtain ⟨hBu, hne⟩ := (gB_blueMove hr hc _).1 hB'
    refine ⟨(r', c'), hBu, hne, ?_⟩
    have hnext := ih ((l.erase (r, c))) _ ?_ hin ?_
    · refine hnext.congr (fun u => ?_) (fun u => ?_)
      · rw [gA_whiteMove hr' hc', gA_blueMove hr hc]
        simp only [afterX]
        exact Iff.intro (fun h => ⟨⟨h.1, h.2.1⟩, h.2.2⟩) (fun h => ⟨h.1.1, h.1.2, h.2⟩)
      · rw [gB_whiteMove hr' hc', gB_blueMove hr hc]
        simp only [afterY]
        exact Iff.intro (fun h => ⟨⟨h.1, h.2.1⟩, h.2.2⟩) (fun h => ⟨h.1.1, h.1.2, h.2⟩)
    · have := List.length_erase_of_mem (hsupp (r, c) ⟨hr, hc, hbit⟩)
      omega
    · intro u hu
      rw [gA_whiteMove hr' hc', gA_blueMove hr hc] at hu
      obtain ⟨⟨hu, hnv⟩, _⟩ := hu
      exact (List.mem_erase_of_ne fun e => hnv (Or.inl e)).2 (hsupp u hu)

/-! ## Reading certificate data -/

def hexVal (c : Char) : Nat := if c.isDigit then c.toNat - 48 else c.toNat - 87

/-- Parse space-separated lowercase hexadecimal keys. -/
def parseKeys (s : String) : Array Nat :=
  (s.splitOn " ").foldl
    (fun acc t => if t.isEmpty then acc else acc.push (t.foldl (fun n ch => 16 * n + hexVal ch) 0)) #[]

end Col
