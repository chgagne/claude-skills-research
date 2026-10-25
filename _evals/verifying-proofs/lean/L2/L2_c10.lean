import Mathlib

open Finset Real

/-! Flag L2/c10: NLE objective, paper line 125.
Finite-space model: prior `p : X → ℝ`, true likelihood `q x y`, model likelihood `qθ θ x y`.
KL between the conditionals at `x` is a sum over `y`, hence a function of `x` only. -/

variable {X Y Θ : Type*} [Fintype X] [Fintype Y]

/-- `KL(q(·|x) ‖ qθ(·|x))`: integrates out `y`; depends on `x` (and `θ`). -/
noncomputable def klx (q : X → Y → ℝ) (qθ : Θ → X → Y → ℝ) (θ : Θ) (x : X) : ℝ :=
  ∑ y, q x y * Real.log (q x y / qθ θ x y)

/-- Expected log-likelihood `E^{(x,y)} log qθ(y|x)` under the joint `p(x) q(y|x)`. -/
noncomputable def ell (p : X → ℝ) (q : X → Y → ℝ) (qθ : Θ → X → Y → ℝ) (θ : Θ) : ℝ :=
  ∑ x, p x * ∑ y, q x y * Real.log (qθ θ x y)

/-- Corrected objective: outer expectation over `x` (prior), `E^x KL`. -/
noncomputable def ekl (p : X → ℝ) (q : X → Y → ℝ) (qθ : Θ → X → Y → ℝ) (θ : Θ) : ℝ :=
  ∑ x, p x * klx q qθ θ x

/-- Decomposition: `E log qθ = -E^x KL + C`, with `C` independent of `θ`. -/
theorem ell_eq (p : X → ℝ) (q : X → Y → ℝ) (qθ : Θ → X → Y → ℝ)
    (hq : ∀ x y, 0 < q x y) (hqθ : ∀ θ x y, 0 < qθ θ x y) (θ : Θ) :
    ell p q qθ θ = - ekl p q qθ θ + ∑ x, p x * ∑ y, q x y * Real.log (q x y) := by
  unfold ell ekl klx
  rw [← sub_eq_neg_add, ← Finset.sum_sub_distrib]
  refine Finset.sum_congr rfl (fun x _ => ?_)
  rw [← mul_sub, ← Finset.sum_sub_distrib]
  congr 1
  refine Finset.sum_congr rfl (fun y _ => ?_)
  rw [Real.log_div (hq x y).ne' (hqθ θ x y).ne']
  ring

/-- Main theorem (corrected statement): argmax of `E^{(x,y)} log qθ(y|x)` equals argmin of
`E^x KL(q(·|x) ‖ qθ(·|x))`, as sets of parameters. -/
theorem argmax_ell_eq_argmin_ekl (p : X → ℝ) (q : X → Y → ℝ) (qθ : Θ → X → Y → ℝ)
    (hq : ∀ x y, 0 < q x y) (hqθ : ∀ θ x y, 0 < qθ θ x y) :
    {θ | ∀ θ', ell p q qθ θ' ≤ ell p q qθ θ} = {θ | ∀ θ', ekl p q qθ θ ≤ ekl p q qθ θ'} := by
  ext θ
  simp only [Set.mem_setOf_eq, ell_eq p q qθ hq hqθ]
  constructor <;> intro h θ' <;> have := h θ' <;> linarith

/-! Witness for the flag: the KL in the written form is a function of `x`, so any reading of
`E^y KL(q(y|x) ‖ qθ(y|x))` that keeps `x` free gives an `x`-dependent minimiser, which cannot
equal the (x-free) argmax of the joint objective. Concrete instance: X = Y = Bool, Θ = Bool,
`qθ true = q` (exact), `qθ false` swaps the two conditionals. -/

noncomputable def q0 : Bool → Bool → ℝ
  | false, false => 1/2 | false, true => 1/2
  | true, false => 1/4 | true, true => 3/4

noncomputable def qθ0 : Bool → Bool → Bool → ℝ
  | true, x, y => q0 x y
  | false, x, y => q0 (!x) y

-- per-x KL of the swapped model is positive at x = false and x = true
lemma kl_false_false : 0 < klx q0 qθ0 false false := by
  simp only [klx, Fintype.univ_bool, Finset.sum_insert, Finset.mem_singleton, Finset.sum_singleton,
    q0, qθ0, Bool.not_false]
  norm_num
  have h1 : Real.log (1/2 / (3/4) : ℝ) = Real.log 2 - Real.log 3 := by
    rw [show (1/2 / (3/4) : ℝ) = 2/3 by norm_num, Real.log_div (by norm_num) (by norm_num)]
  have h2 : Real.log (1/2 / (1/4) : ℝ) = Real.log 2 := by norm_num
  have h3 : Real.log 3 < 2 * Real.log 2 := by
    rw [← Real.log_rpow (by norm_num)]
    exact Real.log_lt_log (by norm_num) (by norm_num)
  nlinarith [h1, h2, h3]

lemma kl_true_zero (x : Bool) : klx q0 qθ0 true x = 0 := by
  cases x <;> simp [klx, qθ0, q0, Fintype.univ_bool]

/-- The written form, read literally with `x` free: at `x = false` the unique minimiser over Θ
is `true`; the objective genuinely depends on `x` (it is not a single number), so the written
`E^y` is not the expectation that makes the identity hold. -/
theorem written_form_depends_on_x :
    klx q0 qθ0 true false < klx q0 qθ0 false false ∧
    (fun x => klx q0 qθ0 false x) false ≠ (fun x => klx q0 qθ0 true x) false := by
  refine ⟨?_, ?_⟩
  · rw [kl_true_zero]; exact kl_false_false
  · simp only; rw [kl_true_zero]; exact (kl_false_false).ne'

#print axioms argmax_ell_eq_argmin_ekl
#print axioms written_form_depends_on_x
