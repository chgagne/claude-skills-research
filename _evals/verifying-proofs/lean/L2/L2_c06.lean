import Mathlib

open Finset

/-- First-layer field `ζ = W·x + b`. -/
noncomputable def field {d : ℕ} (W : Fin d → ℝ) (b : ℝ) (x : Fin d → ℝ) : ℝ :=
  (∑ i, W i * x i) + b

/-- Defect: on the per-coordinate cylinder (each of the `d` first-layer entries and the bias
within `ρ` of target), the field deviation on the cube `{±1}^d` can exceed `ρ(√d+1)`
for every `d ≥ 2` and every `ρ > 0`; it reaches `ρ(d+1)`. -/
theorem base_bound_fails (d : ℕ) (hd : 2 ≤ d) (ρ : ℝ) (hρ : 0 < ρ) :
    ∃ (W Ws : Fin d → ℝ) (b bs : ℝ) (x : Fin d → ℝ),
      (∀ i, x i = 1 ∨ x i = -1) ∧ (∀ i, |W i - Ws i| ≤ ρ) ∧ |b - bs| ≤ ρ ∧
      |field W b x - field Ws bs x| = ρ * (d + 1) ∧
      ρ * (Real.sqrt d + 1) < |field W b x - field Ws bs x| := by
  have key : |field (fun _ : Fin d => ρ) ρ (fun _ => 1) - field (fun _ : Fin d => (0:ℝ)) 0 (fun _ => 1)|
      = ρ * (d + 1) := by
    simp only [field, mul_one, mul_zero, sum_const, card_univ, Fintype.card_fin,
      nsmul_eq_mul, add_zero, sub_zero]
    rw [abs_of_pos (by positivity)]; ring
  refine ⟨fun _ => ρ, fun _ => 0, ρ, 0, fun _ => 1, fun _ => Or.inl rfl, ?_, ?_, key, ?_⟩
  · intro i; simp [abs_of_pos hρ]
  · simp [abs_of_pos hρ]
  · rw [key]
    have hd' : (2:ℝ) ≤ d := by exact_mod_cast hd
    have hs : Real.sqrt d < d := by
      rw [Real.sqrt_lt' (by linarith)]; nlinarith
    nlinarith

/-- The corrected bound `ρ(d+1)` does hold on the per-coordinate cylinder over the cube. -/
theorem base_bound_corrected (d : ℕ) (ρ : ℝ) (W Ws : Fin d → ℝ) (b bs : ℝ) (x : Fin d → ℝ)
    (hx : ∀ i, x i = 1 ∨ x i = -1) (hW : ∀ i, |W i - Ws i| ≤ ρ) (hb : |b - bs| ≤ ρ) :
    |field W b x - field Ws bs x| ≤ ρ * (d + 1) := by
  have h1 : field W b x - field Ws bs x = (∑ i, (W i - Ws i) * x i) + (b - bs) := by
    simp only [field, sub_mul, sum_sub_distrib]; ring
  rw [h1]
  have hxi : ∀ i, |x i| = 1 := fun i => by rcases hx i with h | h <;> simp [h]
  have hs : |∑ i, (W i - Ws i) * x i| ≤ ∑ _i : Fin d, ρ := by
    refine (abs_sum_le_sum_abs _ _).trans (sum_le_sum fun i _ => ?_)
    rw [abs_mul, hxi i, mul_one]; exact hW i
  simp only [sum_const, card_univ, Fintype.card_fin, nsmul_eq_mul] at hs
  calc |(∑ i, (W i - Ws i) * x i) + (b - bs)|
      ≤ |∑ i, (W i - Ws i) * x i| + |b - bs| := abs_add_le _ _
    _ ≤ d * ρ + ρ := add_le_add hs hb
    _ = ρ * (d + 1) := by ring

#print axioms base_bound_fails
#print axioms base_bound_corrected
