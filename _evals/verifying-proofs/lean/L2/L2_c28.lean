import Mathlib

/-! Flag L2 c28: Theorem thm:qjk-drift-smooth, last line of proof: "(eq:def-drift) holds with β = 1/4".
Definition def:drift requires β > 1. -/

/-- The paper's β = 1/4 violates the definition's requirement β > 1. -/
theorem beta_quarter_not_admissible : ¬ ((1:ℝ) < 1/4) := by norm_num

/-- The derived estimate gives (eq:def-drift) with β = 5/4 (> 1).
  Abstracted: Px = P x(T;u), ξ = ξ_q(T,u) ≥ 0, X = |x(T;u)|, U = ‖u‖_{W^{m,∞}}. -/
theorem drift_with_beta_five_quarters
    (C ε Px ξ X U : ℝ) (hC : 0 < C) (hξ : 0 ≤ ξ) (hU : U ≤ ε / C)
    (hest : |Px - ξ| ≤ C * U * ξ + C * X ^ ((1:ℝ) + 1/4)) :
    (1:ℝ) < 5/4 ∧ Px ≥ (1 - ε) * ξ - C * X ^ ((5:ℝ)/4) := by
  refine ⟨by norm_num, ?_⟩
  have h1 : (1:ℝ) + 1/4 = 5/4 := by norm_num
  rw [h1] at hest
  have hCU : C * U ≤ ε := by
    have := mul_le_mul_of_nonneg_left hU hC.le
    rwa [mul_div_cancel₀ _ hC.ne'] at this
  have h2 : C * U * ξ ≤ ε * ξ := mul_le_mul_of_nonneg_right hCU hξ
  have h3 := (abs_le.mp hest).1
  nlinarith

/-- With β = 1/4 the inequality (eq:def-drift) carries no obstruction: for every C > 0 and every
  small a > 0, the "target" P x = -a, ξ = 0, |x| = a satisfies it (so it cannot deny STLC). -/
theorem beta_quarter_vacuous (C ε : ℝ) (hC : 0 < C) :
    ∃ δ > 0, ∀ a : ℝ, 0 < a → a < δ →
      (-a : ℝ) ≥ (1 - ε) * 0 - C * a ^ ((1:ℝ)/4) := by
  refine ⟨min 1 (C ^ (4/3 : ℝ)), by positivity, ?_⟩
  intro a ha haδ
  have ha1 : a < 1 := lt_of_lt_of_le haδ (min_le_left _ _)
  have haC : a < C ^ (4/3:ℝ) := lt_of_lt_of_le haδ (min_le_right _ _)
  -- a = a^(1/4) * a^(3/4) and a^(3/4) < C
  have hsplit : a = a ^ ((1:ℝ)/4) * a ^ ((3:ℝ)/4) := by
    rw [← Real.rpow_add ha]; norm_num
  have h34 : a ^ ((3:ℝ)/4) < C := by
    have := Real.rpow_lt_rpow ha.le haC (by norm_num : (0:ℝ) < 3/4)
    rwa [← Real.rpow_mul hC.le, show (4/3:ℝ) * (3/4) = 1 by norm_num, Real.rpow_one] at this
  have hq : 0 < a ^ ((1:ℝ)/4) := Real.rpow_pos_of_pos ha _
  have : a ≤ C * a ^ ((1:ℝ)/4) := by
    have := mul_lt_mul_of_pos_left h34 hq
    linarith [hsplit, mul_comm (a ^ ((1:ℝ)/4)) C]
  linarith

#print axioms beta_quarter_not_admissible
#print axioms drift_with_beta_five_quarters
#print axioms beta_quarter_vacuous
