import Mathlib

open Submodule

/-- The paper's restated Theorem 1.11 at m = 0 (L^∞): π = 1 + ⌈(2j-2)/1⌉ = 2j-1 for j ≥ 1. -/
theorem pi_at_m0 (j : ℕ) (hj : 1 ≤ j) : 1 + (2*j - 2) / (0 + 1) = 2*j - 1 := by omega

/-- Abstract form: the 2j-1 (sharp, Thm 1.11 at m=0) condition implies the 2j+1
(Kawski-as-quoted) condition, so the quoted sentence is a true, weaker necessary condition. -/
theorem kawski_quoted_follows {B V : Type*} [AddCommGroup V] [Module ℝ V]
    (n1 : B → ℕ) (f : B → V) (W : B) (j : ℕ) (hW : n1 W = 2*j)
    (h : f W ∈ span ℝ (f '' {b | 1 ≤ n1 b ∧ n1 b ≤ 2*j - 1 ∧ n1 b ≠ 2})) :
    f W ∈ span ℝ (f '' {b | b ≠ W ∧ n1 b ≤ 2*j + 1}) := by
  refine span_mono (Set.image_mono ?_) h
  intro b ⟨h1, h2, _⟩
  refine ⟨?_, by omega⟩
  rintro rfl; omega

/-- The converse fails: the 2j+1 condition is strictly weaker (j = 1, a bracket b with n1 b = 3). -/
theorem kawski_quoted_strictly_weaker :
    ∃ (n1 : Fin 2 → ℕ) (f : Fin 2 → ℝ),
      n1 0 = 2*1 ∧
      f 0 ∈ span ℝ (f '' {b | b ≠ 0 ∧ n1 b ≤ 2*1 + 1}) ∧
      f 0 ∉ span ℝ (f '' {b | 1 ≤ n1 b ∧ n1 b ≤ 2*1 - 1 ∧ n1 b ≠ 2}) := by
  refine ⟨![2, 3], ![1, 1], rfl, ?_, ?_⟩
  · apply subset_span
    refine ⟨1, ⟨by decide, by decide⟩, rfl⟩
  · have : {b : Fin 2 | 1 ≤ (![2, 3] : Fin 2 → ℕ) b ∧ (![2, 3] : Fin 2 → ℕ) b ≤ 2*1 - 1 ∧
        (![2, 3] : Fin 2 → ℕ) b ≠ 2} = ∅ := by
      ext b; fin_cases b <;> simp
    rw [this]; simp

#print axioms pi_at_m0
#print axioms kawski_quoted_follows
#print axioms kawski_quoted_strictly_weaker
