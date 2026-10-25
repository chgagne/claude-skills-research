import Mathlib

open MeasureTheory Real

/-- Pointwise: with k_t = g + t (f - g), d/dt e^{-k_t} = -(f-g) e^{-k_t}. -/
theorem pointwise_deriv (f g t : ℝ) :
    HasDerivAt (fun s : ℝ => exp (-(g + s * (f - g))))
      (-(f - g) * exp (-(g + t * (f - g)))) t := by
  have h : HasDerivAt (fun s : ℝ => -(g + s * (f - g))) (-(f - g)) t := by
    have h1 := (((hasDerivAt_id t).mul_const (f - g)).const_add g).neg
    convert h1 using 1
    · funext s; simp only [Pi.neg_apply, id]
    · ring
  have := h.exp
  simpa [mul_comm] using this

/-- Counterexample to the displayed formula: μ = δ₀ on ℝ, f ≡ 1, g ≡ 0.
  Then t ↦ E^μ[e^{-k_t}] = e^{-t}; its derivative at every t is
  -E^μ[(f-g)e^{-k_t}] = -e^{-t}, which differs from the paper's
  E^μ[(f-g)e^{-k_t}] = e^{-t}. -/
theorem paper_display_false (t : ℝ) :
    let μ : Measure ℝ := Measure.dirac 0
    let f : ℝ → ℝ := fun _ => 1
    let g : ℝ → ℝ := fun _ => 0
    let F : ℝ → ℝ := fun s => ∫ x, exp (-(g x + s * (f x - g x))) ∂μ
    HasDerivAt F (-∫ x, (f x - g x) * exp (-(g x + t * (f x - g x))) ∂μ) t ∧
    deriv F t ≠ ∫ x, (f x - g x) * exp (-(g x + t * (f x - g x))) ∂μ := by
  intro μ f g F
  have hF : F = fun s => exp (-(0 + s * (1 - 0))) := by
    funext s; simp [F, μ, f, g]
  have hR : (∫ x, (f x - g x) * exp (-(g x + t * (f x - g x))) ∂μ)
      = (1 - 0) * exp (-(0 + t * (1 - 0))) := by
    simp [μ, f, g]
  have hd := pointwise_deriv 1 0 t
  refine ⟨?_, ?_⟩
  · rw [hF, hR]; simpa [neg_mul] using hd
  · rw [hF, hR, hd.deriv]
    have hpos : 0 < exp (-(0 + t * (1 - 0))) := exp_pos _
    intro h; linarith

#print axioms pointwise_deriv
#print axioms paper_display_false
