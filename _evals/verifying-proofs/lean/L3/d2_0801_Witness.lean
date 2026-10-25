import Mathlib

/-- Instance n = 1, k = 1 of Theorem (Section 3): L_1 has moments a0 a1 a2,
B_{L_1} has Gram matrix [[a0,a1],[a1,a2]], B_{L_0} has Gram matrix [a0] (rank ≤ 1).
If B_{L_1} is positive definite, its determinant is nonzero, so rank B_{L_1} = 2 > 1 ≥ rank B_{L_0}:
L_1 is not flat. Hence the hypothesis "flat with positive definite B_{L_k}" is unsatisfiable. -/
theorem posdef_not_flat (a0 a1 a2 : ℝ)
    (hpd : ∀ x y : ℝ, (x ≠ 0 ∨ y ≠ 0) → 0 < a0 * x ^ 2 + 2 * a1 * x * y + a2 * y ^ 2) :
    a0 * a2 - a1 ^ 2 ≠ 0 := by
  have h0 : 0 < a0 := by
    have := hpd 1 0 (Or.inl one_ne_zero); nlinarith
  intro hdet
  have := hpd (-a1) a0 (Or.inr (ne_of_gt h0))
  have : a0 * (-a1) ^ 2 + 2 * a1 * (-a1) * a0 + a2 * a0 ^ 2 = a0 * (a0 * a2 - a1 ^ 2) := by ring
  nlinarith
