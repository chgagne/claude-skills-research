import Mathlib

open Real MeasureTheory Set

/-! L2_c30: the space "W^{3,1}_0(0,1)" defined with phi''' ∈ L^3 does not contain every
phi = x_3(·T) produced by an L^1 control. Witness (T = 1):
  phi(t) = t^{5/2} (1-t)^3 = t^{5/2} - 3 t^{7/2} + 3 t^{9/2} - t^{11/2},
  u = phi''' ~ (15/8) t^{-1/2} near 0: u ∈ L^1(0,1), u ∉ L^3(0,1).
The trajectory x1 = phi'', x2 = phi', x3 = phi solves x1' = u, x2' = x1, x3' = x2 on (0,1),
starts at 0 and ends at x1 = x2 = x3 = 0, so it satisfies the hypotheses of Lemma p:no. -/

noncomputable def phi (t : ℝ) : ℝ :=
  t ^ (5/2 : ℝ) - 3 * t ^ (7/2 : ℝ) + 3 * t ^ (9/2 : ℝ) - t ^ (11/2 : ℝ)
noncomputable def d1 (t : ℝ) : ℝ :=
  5/2 * t ^ (3/2 : ℝ) - 21/2 * t ^ (5/2 : ℝ) + 27/2 * t ^ (7/2 : ℝ) - 11/2 * t ^ (9/2 : ℝ)
noncomputable def d2 (t : ℝ) : ℝ :=
  15/4 * t ^ (1/2 : ℝ) - 105/4 * t ^ (3/2 : ℝ) + 189/4 * t ^ (5/2 : ℝ) - 99/4 * t ^ (7/2 : ℝ)
/-- the control u = phi''' -/
noncomputable def u (t : ℝ) : ℝ :=
  15/8 * t ^ (-1/2 : ℝ) - 315/8 * t ^ (1/2 : ℝ) + 945/8 * t ^ (3/2 : ℝ) - 693/8 * t ^ (5/2 : ℝ)

lemma hd (p : ℝ) {t : ℝ} (ht : 0 < t) : HasDerivAt (fun x : ℝ => x ^ p) (p * t ^ (p - 1)) t :=
  hasDerivAt_rpow_const (Or.inl ht.ne')

lemma deriv_phi {t : ℝ} (ht : 0 < t) : HasDerivAt phi (d1 t) t := by
  have h := (((hd (5/2) ht).sub ((hd (7/2) ht).const_mul 3)).add
    ((hd (9/2) ht).const_mul 3)).sub (hd (11/2) ht)
  refine h.congr_deriv ?_
  simp only [d1]; norm_num; ring

lemma deriv_d1 {t : ℝ} (ht : 0 < t) : HasDerivAt d1 (d2 t) t := by
  have h := ((((hd (3/2) ht).const_mul (5/2)).sub ((hd (5/2) ht).const_mul (21/2))).add
    ((hd (7/2) ht).const_mul (27/2))).sub ((hd (9/2) ht).const_mul (11/2))
  refine h.congr_deriv ?_
  simp only [d2]; norm_num; ring

lemma deriv_d2 {t : ℝ} (ht : 0 < t) : HasDerivAt d2 (u t) t := by
  have h := ((((hd (1/2) ht).const_mul (15/4)).sub ((hd (3/2) ht).const_mul (105/4))).add
    ((hd (5/2) ht).const_mul (189/4))).sub ((hd (7/2) ht).const_mul (99/4))
  refine h.congr_deriv ?_
  simp only [u]; norm_num; ring

lemma u_integrable : IntegrableOn u (Ioo 0 1) := by
  have I : ∀ s : ℝ, -1 < s → IntegrableOn (fun x : ℝ => x ^ s) (Ioo 0 1) := fun s hs =>
    (intervalIntegral.integrableOn_Ioo_rpow_iff zero_lt_one).2 hs
  have := ((((I (-1/2) (by norm_num)).const_mul (15/8)).sub
    ((I (1/2) (by norm_num)).const_mul (315/8))).add
    ((I (3/2) (by norm_num)).const_mul (945/8))).sub ((I (5/2) (by norm_num)).const_mul (693/8))
  exact this

lemma u_lower {t : ℝ} (ht : 0 < t) (ht' : t < 1/100) : t ^ (-1/2 : ℝ) ≤ u t := by
  set s := √t with hs
  have spos : 0 < s := Real.sqrt_pos.2 ht
  have hts : t = s ^ 2 := (Real.sq_sqrt ht.le).symm
  have e1 : t ^ (1/2 : ℝ) = s := by rw [hs, Real.sqrt_eq_rpow]
  have em : t ^ (-1/2 : ℝ) = s⁻¹ := by
    rw [show (-1/2 : ℝ) = -(1/2) by norm_num, Real.rpow_neg ht.le, e1]
  have e3 : t ^ (3/2 : ℝ) = t * s := by
    rw [show (3/2 : ℝ) = 1 + 1/2 by norm_num, Real.rpow_add ht, Real.rpow_one, e1]
  have e5 : t ^ (5/2 : ℝ) = t ^ 2 * s := by
    rw [show (5/2 : ℝ) = 2 + 1/2 by norm_num, Real.rpow_add ht, e1]; norm_cast
  simp only [u]; rw [em, e1, e3, e5, hts]
  have hs1 : s < 1/10 := by
    have : s ^ 2 < (1/10) ^ 2 := by rw [← hts]; linarith
    nlinarith
  rw [← sub_nonneg]
  have key : 15/8 * s⁻¹ - 315/8 * s + 945/8 * (s ^ 2 * s) - 693/8 * ((s ^ 2) ^ 2 * s) - s⁻¹
      = (7/8 - 315/8 * s ^ 2 + 945/8 * s ^ 4 - 693/8 * s ^ 6) / s := by
    field_simp; ring
  rw [key]
  apply div_nonneg _ spos.le
  have h2 : s ^ 2 < 1/100 := by nlinarith
  have h6 : s ^ 6 ≤ s ^ 2 := by
    have : s ^ 4 ≤ 1 := by nlinarith [pow_pos spos 4]
    nlinarith [pow_pos spos 2]
  nlinarith [pow_pos spos 4]

lemma u_not_L3 : ¬ IntegrableOn (fun t => |u t| ^ 3) (Ioo 0 1) := by
  intro H
  have H' : IntegrableOn (fun t => |u t| ^ 3) (Ioo 0 (1/100)) :=
    H.mono_set (Ioo_subset_Ioo_right (by norm_num))
  have G : IntegrableOn (fun t : ℝ => t ^ (-3/2 : ℝ)) (Ioo 0 (1/100)) := by
    refine Integrable.mono' H' ?_ ?_
    · exact (ContinuousOn.rpow_const (s := Ioo (0:ℝ) (1/100)) continuousOn_id
        (fun x (hx : x ∈ Ioo (0:ℝ) (1/100)) => Or.inl (ne_of_gt hx.1))).aestronglyMeasurable
        measurableSet_Ioo
    · refine (ae_restrict_iff' measurableSet_Ioo).2 (Filter.Eventually.of_forall ?_)
      intro t ht
      have hl := u_lower ht.1 ht.2
      have p0 : 0 ≤ t ^ (-1/2 : ℝ) := Real.rpow_nonneg ht.1.le _
      have e : t ^ (-3/2 : ℝ) = (t ^ (-1/2 : ℝ)) ^ 3 := by
        rw [← Real.rpow_natCast, ← Real.rpow_mul ht.1.le]; norm_num
      rw [Real.norm_eq_abs, abs_of_nonneg (Real.rpow_nonneg ht.1.le _), e]
      exact pow_le_pow_left₀ p0 (hl.trans (le_abs_self _)) 3
  have := (intervalIntegral.integrableOn_Ioo_rpow_iff (by norm_num : (0:ℝ) < 1/100)).1 G
  norm_num at this

/-- Main certificate: an L^1 control u on (0,1) (T = 1) satisfying the hypotheses of Lemma p:no
(trajectory from 0, ending with x1 = x2 = x3 = 0) whose phi''' = u is NOT in L^3(0,1).
Hence "phi ∈ W^{3,1}_0(0,1)" fails when the space is defined with L^3 as written. -/
theorem flag_witness :
    IntegrableOn u (Ioo 0 1) ∧ ¬ IntegrableOn (fun t => |u t| ^ 3) (Ioo 0 1) ∧
    (∀ t ∈ Ioo (0:ℝ) 1, HasDerivAt d2 (u t) t ∧ HasDerivAt d1 (d2 t) t ∧ HasDerivAt phi (d1 t) t) ∧
    ContinuousOn d2 (Icc 0 1) ∧ ContinuousOn d1 (Icc 0 1) ∧ ContinuousOn phi (Icc 0 1) ∧
    d2 0 = 0 ∧ d1 0 = 0 ∧ phi 0 = 0 ∧ d2 1 = 0 ∧ d1 1 = 0 ∧ phi 1 = 0 := by
  refine ⟨u_integrable, u_not_L3, fun t ht => ⟨deriv_d2 ht.1, deriv_d1 ht.1, deriv_phi ht.1⟩,
    ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩
  · apply Continuous.continuousOn; unfold d2
    have c := fun (q : ℝ) (h : 0 ≤ q) => Real.continuous_rpow_const h
    fun_prop (disch := norm_num)
  · apply Continuous.continuousOn; unfold d1; fun_prop (disch := norm_num)
  · apply Continuous.continuousOn; unfold phi; fun_prop (disch := norm_num)
  all_goals simp [d2, d1, phi, Real.zero_rpow]
  all_goals norm_num

#print axioms flag_witness
