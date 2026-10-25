import Mathlib

/-- Pointwise content of the equality case at paper line 365-367:
`exp(-f) = exp(-g) * c(y)` with `c > 0` iff `f - g` depends only on `y`
(i.e. `f ~ g`, the relation defining the class space `F_Φ`). -/
theorem L2_c11_equality_case {X Y : Type*} (f g : X → Y → ℝ) :
    (∃ c : Y → ℝ, (∀ y, 0 < c y) ∧ ∀ x y, Real.exp (-f x y) = Real.exp (-g x y) * c y) ↔
    (∃ h : Y → ℝ, ∀ x y, f x y = g x y + h y) := by
  constructor
  · rintro ⟨c, hc, h⟩
    refine ⟨fun y => -Real.log (c y), fun x y => ?_⟩
    have := congrArg Real.log (h x y)
    rw [Real.log_exp, Real.log_mul (Real.exp_pos _).ne' (hc y).ne', Real.log_exp] at this
    linarith
  · rintro ⟨h, hfg⟩
    refine ⟨fun y => Real.exp (-h y), fun y => Real.exp_pos _, fun x y => ?_⟩
    rw [hfg, ← Real.exp_add]; ring_nf

#print axioms L2_c11_equality_case
