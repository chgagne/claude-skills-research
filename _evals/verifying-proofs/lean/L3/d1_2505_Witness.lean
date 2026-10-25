import Mathlib

/-! Lemma eps_collapse: with ε* = 1 - δΓ/(2 S), ε > ε* does NOT give δ(1-ε)S < δΓ/2.
    Witness δ=4, Γ=1, S=sup Ω=1, ε=0 (so ε* = -1 < ε). -/
theorem eps_collapse_step_false :
    let δ : ℝ := 4; let Γ : ℝ := 1; let S : ℝ := 1; let ε : ℝ := 0
    ε > 1 - δ*Γ/(2*S) ∧ 0 ≤ ε ∧ ε < 1 ∧ ¬ (δ*(1-ε)*S < δ*Γ/2) := by
  norm_num

/-! Lemma omega_fisher: ‖a+b‖² ≥ ‖a‖²+‖b‖² fails (1-dim scores a=1, b=-1). -/
theorem fisher_superadd_false : ¬ ((1:ℝ) + (-1))^2 ≥ (1:ℝ)^2 + (-1)^2 := by norm_num

/-! Thm multi_beta: pairwise β-complementarity (k=2, taken with equality)
    does not give Ω(m1‖m2) ≥ (1+β) k Ω(m_i) for i=1. Ω1=10, Ω2=1, β=1/10. -/
theorem multi_beta_step_false :
    let β : ℝ := 1/10; let O1 : ℝ := 10; let O2 : ℝ := 1
    let O12 : ℝ := (1+β)*(O1+O2)
    O12 ≥ (1+β)*(O1+O2) ∧ ¬ (O12 ≥ (1+β)*2*O1) := by
  norm_num

/-! Thm bounded: ‖C(t)‖ ≤ Γ and Ω ≤ Γ do not give ‖C‖ + δΩ ≤ Γ. -/
theorem bounded_step_false :
    ∃ c Ω Γ δ : ℝ, 0 < δ ∧ 0 < Γ ∧ c ≤ Γ ∧ 0 ≤ Ω ∧ Ω ≤ Γ ∧ ¬ (c + δ*Ω ≤ Γ) :=
  ⟨1, 1, 1, 1, by norm_num⟩

/-! Thm async_hetero: D = [[0,4],[1,0]] (λ=1, β12=3, β21=0) has eigenvector (2,1)
    with eigenvalue 2 (ρ(D)=2 > 1, eigenvalues ±2 by hand), yet for Δ0=(1,0)
    ‖DΔ0‖² = 1 < ρ²‖Δ0‖² = 4. -/
theorem async_hetero_bound_false :
    let D : Matrix (Fin 2) (Fin 2) ℝ := !![0, 4; 1, 0]
    D.mulVec ![2, 1] = (2:ℝ) • ![2, 1] ∧
    (D.mulVec ![1, 0] 0)^2 + (D.mulVec ![1, 0] 1)^2 < (2:ℝ)^2 * ((1:ℝ)^2 + 0^2) := by
  refine ⟨?_, ?_⟩
  · ext i; fin_cases i <;> simp [Matrix.mulVec, dotProduct, Fin.sum_univ_two] <;> norm_num
  · simp [Matrix.mulVec, dotProduct, Fin.sum_univ_two]
