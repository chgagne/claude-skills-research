import Mathlib

/-!
Counterexample to Lemma `lem: rn^q` (paper.tex, line 881), specialised to
H = ℝ, m = 1, prior μ = N(0,1), class 𝓕 = {g} with g(x,y) = y².
For every q > 1 we exhibit a measurable f with 0 < Z_f(y) < ∞ for all y such that
E^{λ_g} (dμ_f^y / dμ_g^y)^q = ∞.
Convention: potentials are written `f x y`; points of H × ℝ^m are stored as `p = (y, x)`.
-/

open MeasureTheory ProbabilityTheory Real
open scoped ENNReal NNReal

noncomputable section
namespace LemRnQ

/-- Prior μ on H = ℝ: the standard Gaussian. -/
abbrev μ : Measure ℝ := gaussianReal 0 1

/-- Z_f(y) := ∫_H exp(-f(x;y)) μ(dx). -/
def Z (f : ℝ → ℝ → ℝ) (y : ℝ) : ℝ := ∫ x, exp (-f x y) ∂μ

/-- dμ_f^y/dμ (x) = exp(-f(x;y)) / Z_f(y). -/
def post (f : ℝ → ℝ → ℝ) (x y : ℝ) : ℝ := exp (-f x y) / Z f y

/-- dμ_f^y/dμ_g^y (x), as the quotient of the two densities w.r.t. μ. -/
def ratio (f g : ℝ → ℝ → ℝ) (x y : ℝ) : ℝ := post f x y / post g x y

/-- π_g(y) := Z_g(y) / ∫ Z_g(y') dy' (Lebesgue density). -/
def piDens (g : ℝ → ℝ → ℝ) (y : ℝ) : ℝ := Z g y / ∫ y', Z g y'

/-- λ_g(dx,dy) = π_g(dy) (e^{-g(x,y)}/Z_g(y)) μ(dx), on pairs p = (y, x). -/
def lam (g : ℝ → ℝ → ℝ) : Measure (ℝ × ℝ) :=
  (volume.prod μ).withDensity (fun p => ENNReal.ofReal (piDens g p.1 * post g p.2 p.1))

/-- The fixed g ∈ 𝓕. -/
def g₀ : ℝ → ℝ → ℝ := fun _ y => y ^ 2

/-- The bad measurable potential, depending on q. -/
def fq (q : ℝ) : ℝ → ℝ → ℝ := fun x _ => -(x ^ 2 / (2 * q))

lemma integrable_exp_mul_sq {a : ℝ} (ha : a < 1 / 2) :
    Integrable (fun x : ℝ => exp (a * x ^ 2)) μ := by
  rw [μ, gaussianReal_of_var_ne_zero _ one_ne_zero,
    integrable_withDensity_iff_integrable_smul' (measurable_gaussianPDF _ _)
      (ae_of_all _ fun _ => gaussianPDF_lt_top)]
  have : (fun x : ℝ => (gaussianPDF 0 1 x).toReal • exp (a * x ^ 2))
      = fun x => (√(2 * π))⁻¹ * exp (-(1 / 2 - a) * x ^ 2) := by
    funext x
    rw [gaussianPDF, ENNReal.toReal_ofReal (gaussianPDFReal_nonneg _ _ _), gaussianPDFReal,
      smul_eq_mul, mul_assoc, ← exp_add]
    congr 2
    · simp
    · push_cast; ring
  rw [this]
  exact (integrable_exp_neg_mul_sq (by linarith)).const_mul _

/-- Assumption (eq: sub gaussian prior) holds for μ with C₁ = 1/4. -/
theorem prior_subgaussian : Integrable (fun x : ℝ => exp ((1 / 4) * x ^ 2)) μ :=
  integrable_exp_mul_sq (by norm_num)

/-- g₀ is non-negative and satisfies (eq: bounds on f) with C₂⁻ = C₂⁺ = 1, δ(ε) = 1;
so 𝓕 = {g₀} (trivially convex and closed) satisfies Assumption `ass: assumption`. -/
theorem g₀_in_class :
    (∀ x y, 0 ≤ g₀ x y) ∧
    ∀ ε > (0 : ℝ), ∃ δ > (0 : ℝ), ∀ x y : ℝ,
      -1 - ε * x ^ 2 + δ * y ^ 2 ≤ g₀ x y ∧ g₀ x y ≤ 1 * (1 + x ^ 2 + y ^ 2) := by
  refine ⟨fun x y => sq_nonneg y, fun ε hε => ⟨1, one_pos, fun x y => ⟨?_, ?_⟩⟩⟩
  · simp only [g₀]; nlinarith [sq_nonneg x]
  · simp only [g₀]; nlinarith [sq_nonneg x]

lemma Z_g₀ (y : ℝ) : Z g₀ y = exp (-y ^ 2) := by
  simp [Z, g₀, μ]

lemma post_g₀ (x y : ℝ) : post g₀ x y = 1 := by
  rw [post, Z_g₀]; simp [g₀, (exp_pos _).ne']

lemma int_Z_g₀ : ∫ y, Z g₀ y = √π := by
  simp_rw [Z_g₀]
  have := integral_gaussian 1
  simp only [neg_mul, one_mul, div_one] at this
  exact this

lemma fq_integrable {q : ℝ} (hq : 1 < q) (y : ℝ) :
    Integrable (fun x => exp (-fq q x y)) μ := by
  have : (fun x => exp (-fq q x y)) = fun x : ℝ => exp ((1 / (2 * q)) * x ^ 2) := by
    funext x; simp only [fq, neg_neg]; ring_nf
  rw [this]
  apply integrable_exp_mul_sq
  rw [div_lt_div_iff₀ (by linarith) (by norm_num)]; linarith

lemma Z_fq_pos {q : ℝ} (hq : 1 < q) (y : ℝ) : 0 < Z (fq q) y := by
  rw [Z, integral_pos_iff_support_of_nonneg (fun x => (exp_pos _).le) (fq_integrable hq y)]
  have : Function.support (fun x => exp (-fq q x y)) = Set.univ :=
    Set.eq_univ_of_forall fun x => (exp_pos _).ne'
  rw [this, measure_univ]; exact one_pos

lemma fq_measurable (q : ℝ) : Measurable (Function.uncurry (fq q)) := by
  unfold fq; fun_prop

lemma ratio_pow {q : ℝ} (hq : 1 < q) (x y : ℝ) :
    ratio (fq q) g₀ x y ^ q = exp (x ^ 2 / 2) / Z (fq q) 0 ^ q := by
  have hZ : Z (fq q) y = Z (fq q) 0 := rfl
  rw [ratio, post_g₀, div_one, post, hZ,
    div_rpow (exp_pos _).le (Z_fq_pos hq 0).le, ← exp_mul]
  congr 2
  simp only [fq, neg_neg]
  field_simp

lemma lintegral_bad {c : ℝ} (hc : 0 < c) :
    ∫⁻ x, ENNReal.ofReal (exp (x ^ 2 / 2) / c) ∂μ = ∞ := by
  rw [μ, gaussianReal_of_var_ne_zero _ one_ne_zero,
    lintegral_withDensity_eq_lintegral_mul _ (measurable_gaussianPDF _ _) (by fun_prop)]
  have : ∀ x : ℝ, (gaussianPDF 0 1 * fun x => ENNReal.ofReal (exp (x ^ 2 / 2) / c)) x
      = ENNReal.ofReal ((√(2 * π))⁻¹ / c) := by
    intro x
    rw [Pi.mul_apply, gaussianPDF, ← ENNReal.ofReal_mul (gaussianPDFReal_nonneg _ _ _),
      gaussianPDFReal]
    congr 1
    have h0 : -(x - 0) ^ 2 / (2 * ((1 : ℝ≥0) : ℝ)) + x ^ 2 / 2 = 0 := by push_cast; ring
    rw [mul_assoc, ← mul_div_assoc, ← exp_add, h0, exp_zero]
    push_cast; ring_nf
  simp_rw [this, lintegral_const, Real.volume_univ]
  apply ENNReal.mul_top
  rw [ne_eq, ENNReal.ofReal_eq_zero, not_le]
  positivity

/-- **Refutation of `lem: rn^q`** in the instance above: for every q > 1 there is a
measurable f with 0 < Z_f(y) < ∞ (Z_f(y) integrable) for all y, such that
E^{λ_g}[(dμ_f^y/dμ_g^y)^q] = ∞, so no finite constant C(q) exists. -/
theorem lem_rn_q_fails (q : ℝ) (hq : 1 < q) :
    ∃ f : ℝ → ℝ → ℝ, Measurable (Function.uncurry f) ∧
      (∀ y, Integrable (fun x => exp (-f x y)) μ ∧ 0 < Z f y) ∧
      ∫⁻ p, ENNReal.ofReal (ratio f g₀ p.2 p.1 ^ q) ∂(lam g₀) = ∞ := by
  refine ⟨fq q, fq_measurable q, fun y => ⟨fq_integrable hq y, Z_fq_pos hq y⟩, ?_⟩
  have hd : (fun p : ℝ × ℝ => ENNReal.ofReal (piDens g₀ p.1 * post g₀ p.2 p.1))
      = fun p => ENNReal.ofReal (exp (-p.1 ^ 2) / √π) := by
    funext p; rw [post_g₀, mul_one, piDens, Z_g₀, int_Z_g₀]
  have hi : (fun p : ℝ × ℝ => ENNReal.ofReal (ratio (fq q) g₀ p.2 p.1 ^ q))
      = fun p => ENNReal.ofReal (exp (p.2 ^ 2 / 2) / Z (fq q) 0 ^ q) := by
    funext p; rw [ratio_pow hq]
  rw [lam, hd, hi, lintegral_withDensity_eq_lintegral_mul _ (by fun_prop) (by fun_prop)]
  simp only [Pi.mul_apply]
  rw [lintegral_prod_mul (f := fun y : ℝ => ENNReal.ofReal (exp (-y ^ 2) / √π))
      (g := fun x : ℝ => ENNReal.ofReal (exp (x ^ 2 / 2) / Z (fq q) 0 ^ q))
      (by fun_prop) (by fun_prop),
    lintegral_bad (rpow_pos_of_pos (Z_fq_pos hq 0) q)]
  apply ENNReal.mul_top
  rw [← ofReal_integral_eq_lintegral_ofReal]
  · rw [integral_div]
    have := integral_gaussian 1
    simp only [neg_mul, one_mul, div_one] at this
    rw [this, div_self (by positivity)]; simp
  · have := (integrable_exp_neg_mul_sq (b := 1) one_pos).div_const √π
    simpa using this
  · exact ae_of_all _ fun y => by positivity

/-- Corollary in the lemma's own form: no finite C(q) bounds the expectation. -/
theorem no_constant (q : ℝ) (hq : 1 < q) :
    ∃ f : ℝ → ℝ → ℝ, Measurable (Function.uncurry f) ∧
      (∀ y, Integrable (fun x => exp (-f x y)) μ ∧ 0 < Z f y) ∧
      ∀ C : ℝ, ¬ (∫⁻ p, ENNReal.ofReal (ratio f g₀ p.2 p.1 ^ q) ∂(lam g₀) < ENNReal.ofReal C) := by
  obtain ⟨f, h1, h2, h3⟩ := lem_rn_q_fails q hq
  exact ⟨f, h1, h2, fun C => by rw [h3]; exact not_top_lt⟩

end LemRnQ
