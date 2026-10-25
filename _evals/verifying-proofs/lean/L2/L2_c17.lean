import Mathlib

open Real MeasureTheory

/-! Instance: H = ℝ, m = 1, μ = δ₀, f(x,y) = y²/2 (independent of x).
Assumptions (2.x): C₁ arbitrary, C₂⁻ = 1/10, C₂⁺ = 1/2, δ(ε) = 1/2.
Then Z_f(y) = exp(-y²/2), π_f = Z_f / ∫Z_f, and with μ = δ₀ the factor
e^{2κ‖x‖²} = 1, so the paper's three quantities become:
  * true value E^{λ_f}[e^{2κ‖x‖²}] = ∫ π_f(y) dy = 1,
  * the claimed equal expression E^{π_f⊗μ}[e^{-f}/∫Z_f] = ∫ Z_f(y)² dy / (∫Z_f)²,
  * the claimed bound e^{C₂⁻}/(C⁻ ∫ e^{-C₂⁺ y²} dy) · E^μ[e^{2.5κ‖x‖²}], C⁻ = e^{-C₂⁺}E^μ[e^{-C₂⁺‖x‖²}] = e^{-1/2}. -/

noncomputable def Zf (y : ℝ) : ℝ := exp (-(1/2) * y ^ 2)

theorem instance_satisfies_assumptions :
    (∀ y : ℝ, -(1/10 : ℝ) + (1/2) * y ^ 2 ≤ (1/2) * y ^ 2 ∧ (1/2) * y ^ 2 ≤ (1/2) * (1 + y ^ 2)) ∧
    (∀ y : ℝ, exp (-(1/2 : ℝ)) * exp (-(1/2) * y ^ 2) ≤ Zf y) := by
  refine ⟨fun y => ⟨by linarith, by nlinarith⟩, fun y => ?_⟩
  unfold Zf
  have : exp (-(1/2 : ℝ)) ≤ 1 := by rw [exp_le_one_iff]; norm_num
  have h0 : 0 < exp (-(1/2) * y ^ 2) := exp_pos _
  nlinarith

theorem c17_defect :
    -- true value of E^{λ_f}[e^{2κ‖x‖²}]
    (∫ y, Zf y / ∫ y', Zf y') = 1 ∧
    -- the paper's "equal" expression has a different value
    (∫ y, Zf y ^ 2) / (∫ y, Zf y) ^ 2 = 1 / (2 * sqrt π) ∧
    (∫ y, Zf y ^ 2) / (∫ y, Zf y) ^ 2 ≠ 1 ∧
    -- the paper's final upper bound is violated
    exp (1/10) / (exp (-(1/2)) * ∫ y, exp (-(1/2) * y ^ 2)) < 1 := by
  have hZ : (∫ y, Zf y) = sqrt (π / (1/2)) := by
    unfold Zf; simpa using integral_gaussian (1/2 : ℝ)
  have hZ2 : (∫ y, Zf y ^ 2) = sqrt (π / 1) := by
    have : (fun y => Zf y ^ 2) = fun y : ℝ => exp (-1 * y ^ 2) := by
      funext y; unfold Zf; rw [← exp_nat_mul]; congr 1; push_cast; ring
    rw [this, integral_gaussian]
  have hpos : 0 < sqrt (π / (1/2)) := sqrt_pos.mpr (by positivity)
  have hsq : sqrt (π / (1/2)) ^ 2 = 2 * π := by
    rw [sq_sqrt (by positivity)]; ring
  have hspi : 0 < sqrt π := sqrt_pos.mpr pi_pos
  refine ⟨?_, ?_, ?_, ?_⟩
  · rw [integral_div, hZ]; exact div_self hpos.ne'
  · rw [hZ, hZ2, hsq, div_one]
    field_simp
    rw [sq_sqrt pi_pos.le]
  · rw [hZ, hZ2, hsq, div_one]
    intro h
    rw [div_eq_one_iff_eq (by positivity)] at h
    have h2 : sqrt π ^ 2 = π := sq_sqrt pi_pos.le
    nlinarith [pi_gt_three]
  · rw [show (∫ y : ℝ, exp (-(1/2) * y ^ 2)) = sqrt (π / (1/2)) by
      simpa using integral_gaussian (1/2 : ℝ)]
    rw [div_lt_one (by positivity)]
    have h2 : (2:ℝ) < sqrt (π / (1/2)) := by
      rw [show (2:ℝ) = sqrt 4 by rw [show (4:ℝ) = 2^2 by norm_num, sqrt_sq (by norm_num)]]
      apply sqrt_lt_sqrt (by norm_num)
      have := pi_gt_three; linarith [show π / (1/2) = 2 * π by ring]
    have h3 : exp (1/10 : ℝ) < 2 * exp (-(1/2)) := by
      rw [show (1/10 : ℝ) = (3/5) + (-(1/2)) by norm_num, exp_add]
      have : exp (3/5 : ℝ) < 2 := by
        rw [← exp_log (show (0:ℝ) < 2 by norm_num)]
        exact exp_lt_exp.mpr (by linarith [log_two_gt_d9])
      nlinarith [exp_pos (-(1/2 : ℝ))]
    nlinarith [exp_pos (-(1/2 : ℝ))]

#print axioms instance_satisfies_assumptions
#print axioms c17_defect
