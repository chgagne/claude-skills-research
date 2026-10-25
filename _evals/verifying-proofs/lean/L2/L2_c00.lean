import Mathlib

/-- Lower bound on the cloning radius cost: if the clone radius `ρ` must satisfy
the paper's minimal accuracy requirement `4 * sqrt W * ρ ≤ Δ ≤ 1` (Lemma spread,
ℓ ≥ 1, L_φ B ≥ 1/2 dropped as favorable), then `log (1/ρ) ≥ (log W)/2`. -/
lemma log_inv_rho_ge (d : ℕ) (ρ : ℝ) (hρ : 0 < ρ)
    (hreq : 4 * Real.sqrt ((2:ℝ)^d) * ρ ≤ 1) :
    (d:ℝ) * Real.log 2 / 2 ≤ Real.log (1 / ρ) := by
  have hs : 0 < Real.sqrt ((2:ℝ)^d) := Real.sqrt_pos.mpr (by positivity)
  have h1 : Real.sqrt ((2:ℝ)^d) ≤ 1 / ρ := by
    rw [le_div_iff₀ hρ]; nlinarith
  have h2 : Real.log (Real.sqrt ((2:ℝ)^d)) ≤ Real.log (1/ρ) := Real.log_le_log hs h1
  rw [Real.log_sqrt (by positivity), Real.log_pow] at h2
  linarith

/-- The paper's cloning entropy bound, instantiated at teacher width `W = 2^d`
(memorizer), is `(d + W + 1) * log (1/ρ)` per neuron (plus nonnegative terms).
Even with the most favorable admissible `ρ_d`, this is NOT `O(2^d)`. -/
theorem cloning_bound_not_O_two_pow (ρ : ℕ → ℝ) (hρ : ∀ d, 0 < ρ d)
    (hreq : ∀ d, 4 * Real.sqrt ((2:ℝ)^d) * ρ d ≤ 1) :
    ¬ ∃ C : ℝ, ∀ d : ℕ, ((d:ℝ) + 2^d + 1) * Real.log (1 / ρ d) ≤ C * 2^d := by
  rintro ⟨C, hC⟩
  have hl2 : 0 < Real.log 2 := Real.log_pos (by norm_num)
  obtain ⟨d, hd⟩ := exists_nat_gt (2 * C / Real.log 2)
  have hL := log_inv_rho_ge d (ρ d) (hρ d) (hreq d)
  have hdC : C < (d:ℝ) * Real.log 2 / 2 := by
    rw [div_lt_iff₀ hl2] at hd; linarith
  have hp : (0:ℝ) < 2^d := by positivity
  have hd0 : (0:ℝ) ≤ d := by positivity
  have hLnn : 0 ≤ Real.log (1 / ρ (d)) := le_trans (by positivity) hL
  have key := hC d
  have : (2:ℝ)^d * Real.log (1 / ρ d) ≤ ((d:ℝ) + 2^d + 1) * Real.log (1 / ρ d) := by
    apply mul_le_mul_of_nonneg_right _ hLnn; linarith
  nlinarith [mul_lt_mul_of_pos_left hdC hp, mul_le_mul_of_nonneg_left hL hp.le]

#print axioms cloning_bound_not_O_two_pow
