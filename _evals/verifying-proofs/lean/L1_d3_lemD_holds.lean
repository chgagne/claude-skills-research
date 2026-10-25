import Mathlib

/-!
# Lemma `lem:D` (Rate coefficient at the tuned parameters)

Formalisation of the coefficient chain `eq:chain` (with the substitutions
`eq:threesubs`: σ² ↦ σ_M², L² ↦ L_M² = 2ΛL² inside B̈ only, s̄ ↦ a parameter)
and the rate coefficient `R(ρ,β) = 2 Y₀ max(β^{1/3}, ϑ², σ² β^{-2/3}) / (ρ ϑ)`.
-/

open Real

noncomputable section

/-- The rate coefficient `R(ρ,β)` of `eq:master`, built from the chain `eq:chain`,
with `sbar` the s̄ constant, `LMsq` the (inflated) `L²` used inside `B̈`,
and `σsq` the (substituted) variance. -/
def Rcoef (D A Fbar sbar LMsq σsq T ρ β : ℝ) : ℝ :=
  let dbar := 8 * (A + sbar + ρ * D)
  let κ := Real.sqrt (2 + 2 * dbar ^ 2 / ρ)
  let Bdot := 18 * (1 + β + dbar ^ 2)
  let Bddot := 40 * LMsq * κ ^ 2 / ρ * Real.log (1 + dbar ^ 2 * T)
  let Y1 := 12 * D ^ 2 * ρ ^ 2 + 144 * Fbar ^ 2 * ρ ^ 2
  let Y2 := 96 * (Bdot + Bddot)
  let Y0 := max (2 * Y1) Y2
  let θ := β ^ (1 / 6 : ℝ) / (1 + β ^ (1 / 6 : ℝ))
  2 * Y0 * max (max (β ^ (1 / 3 : ℝ)) (θ ^ 2)) (σsq * β ^ (-2 / 3 : ℝ)) / (ρ * θ)

lemma pow6_rpow (x : ℝ) (hx : 0 ≤ x) (k : ℕ) (r : ℝ) (hr : (6 : ℝ) * r = k) :
    (x ^ (6 : ℕ)) ^ r = x ^ k := by
  rw [← rpow_natCast x 6, ← rpow_mul hx, show ((6 : ℕ) : ℝ) * r = (k : ℝ) by
    push_cast; linarith, rpow_natCast]

lemma pow3_rpow (x : ℝ) (hx : 0 ≤ x) (k : ℕ) (r : ℝ) (hr : (3 : ℝ) * r = k) :
    (x ^ (3 : ℕ)) ^ r = x ^ k := by
  rw [← rpow_natCast x 3, ← rpow_mul hx, show ((3 : ℕ) : ℝ) * r = (k : ℝ) by
    push_cast; linarith, rpow_natCast]

lemma sq3 (a c d : ℝ) : (8 * (a + c + d)) ^ 2 ≤ 192 * (a ^ 2 + c ^ 2 + d ^ 2) := by
  nlinarith [sq_nonneg (a - c), sq_nonneg (a - d), sq_nonneg (c - d)]

set_option maxHeartbeats 2000000 in
/-- Lemma `lem:D`.  `s1 = 2 Ĝ` is the s̄₁ of the appendix; `sbar` is the s̄ actually
fed to the chain, allowed to be anything in `[0, √Λ s₁]` (this covers both the true
value `s̄ = 2Ĝ` and the conservative value `√Λ s̄₁` giving `d̄ = d̄_M`). -/
theorem lemD (L D A Fbar s1 Gbar Gs Λ T sbar : ℝ)
    (hΛ : 1 ≤ Λ) (hGs : 0 < Gs) (hGsle : Gs ≤ Gbar) (hT : 0 ≤ T)
    (hA : 0 ≤ A) (hD : 0 ≤ D) (hs : 0 ≤ sbar) (hs' : sbar ≤ Real.sqrt Λ * s1) :
    Rcoef D A Fbar sbar (2 * Λ * L ^ 2) (2 * Λ * Gs ^ 2) T (Real.sqrt Λ) (2 * Λ * Gs ^ 2)
      ≤ (2 * (2 : ℝ) ^ (1 / 3 : ℝ) *
          (24 * D ^ 2 + 288 * Fbar ^ 2
            + 1728 * (1 + 2 * Gbar ^ 2 + 192 * (A ^ 2 + s1 ^ 2 + D ^ 2))
            + 7680 * (2 + 384 * (A ^ 2 + s1 ^ 2 + D ^ 2)) * L ^ 2))
        * max 1 (Real.log (1 + (8 * (A + Real.sqrt Λ * s1 + Real.sqrt Λ * D)) ^ 2 * T))
        * (Gs ^ (1 / 3 : ℝ) * Λ ^ (2 / 3 : ℝ) + Gs ^ (2 / 3 : ℝ) * Λ ^ (5 / 6 : ℝ)) := by
  -- change variables: Λ = u⁶, Gs = v³, 2 = w⁶
  obtain ⟨u, hu0, rfl⟩ : ∃ u : ℝ, 0 < u ∧ Λ = u ^ 6 :=
    ⟨Λ ^ (1 / 6 : ℝ), by positivity, by
      rw [← rpow_natCast, ← rpow_mul (by linarith)]; norm_num⟩
  obtain ⟨v, hv0, rfl⟩ : ∃ v : ℝ, 0 < v ∧ Gs = v ^ 3 :=
    ⟨Gs ^ (1 / 3 : ℝ), by positivity, by
      rw [← rpow_natCast, ← rpow_mul hGs.le]; norm_num⟩
  obtain ⟨w, hw0, h2⟩ : ∃ w : ℝ, 0 < w ∧ w ^ 6 = 2 :=
    ⟨(2 : ℝ) ^ (1 / 6 : ℝ), by positivity, by
      rw [← rpow_natCast, ← rpow_mul (by norm_num)]; norm_num⟩
  have hsq : Real.sqrt (u ^ 6) = u ^ 3 := by
    rw [show u ^ 6 = (u ^ 3) ^ 2 by ring]; exact Real.sqrt_sq (by positivity)
  have hu1 : 1 ≤ u ^ 3 := by
    have : 1 ≤ (u ^ 3) ^ 2 := by nlinarith
    nlinarith [pow_pos hu0 3]
  have hu6 : 1 ≤ u ^ 6 := by nlinarith
  have hw1 : 1 ≤ w := by
    by_contra h; push Not at h
    have : w ^ 6 < 1 := pow_lt_one₀ hw0.le h (by norm_num)
    linarith
  -- rewrite all real powers
  have e1 : (v ^ 3) ^ (1 / 3 : ℝ) = v := by
    rw [pow3_rpow v hv0.le 1 _ (by norm_num), pow_one]
  have e2 : (v ^ 3) ^ (2 / 3 : ℝ) = v ^ 2 := pow3_rpow v hv0.le 2 _ (by norm_num)
  have e3 : (u ^ 6) ^ (2 / 3 : ℝ) = u ^ 4 := pow6_rpow u hu0.le 4 _ (by norm_num)
  have e4 : (u ^ 6) ^ (5 / 6 : ℝ) = u ^ 5 := pow6_rpow u hu0.le 5 _ (by norm_num)
  have e5 : (2 : ℝ) ^ (1 / 3 : ℝ) = w ^ 2 := by
    rw [← h2]; exact pow6_rpow w hw0.le 2 _ (by norm_num)
  set b := w * u * v with hb
  have hb0 : 0 < b := by positivity
  have hβ : 2 * u ^ 6 * (v ^ 3) ^ 2 = b ^ 6 := by rw [hb, mul_pow, mul_pow, h2]; ring
  have f1 : (b ^ 6) ^ (1 / 6 : ℝ) = b := by
    rw [pow6_rpow b hb0.le 1 _ (by norm_num), pow_one]
  have f2 : (b ^ 6) ^ (1 / 3 : ℝ) = b ^ 2 := pow6_rpow b hb0.le 2 _ (by norm_num)
  have f3 : b ^ 6 * (b ^ 6) ^ (-2 / 3 : ℝ) = b ^ 2 := by
    rw [show (-2 / 3 : ℝ) = -(2 / 3) by ring, rpow_neg (by positivity),
      pow6_rpow b hb0.le 4 _ (by norm_num)]
    field_simp
  rw [hsq, e1, e2, e3, e4, e5]
  unfold Rcoef
  simp only []
  rw [hβ, f1, f2, f3]
  -- abbreviations
  set K := A ^ 2 + s1 ^ 2 + D ^ 2 with hK
  set dbar := 8 * (A + sbar + u ^ 3 * D) with hdbar
  set dbarM := 8 * (A + u ^ 3 * s1 + u ^ 3 * D) with hdbarM
  set Lc := max 1 (Real.log (1 + dbarM ^ 2 * T)) with hLc
  set c1 := 1 + 2 * Gbar ^ 2 + 192 * K with hc1
  set c2 := 2 + 384 * K with hc2
  have hs1 : 0 ≤ s1 := by
    by_contra h; push Not at h; nlinarith [pow_pos hu0 3]
  -- Step 1
  have hd0 : 0 ≤ dbar := by positivity
  have hdd : dbar ≤ dbarM := by rw [hdbar, hdbarM]; nlinarith [pow_pos hu0 3]
  have hdM : dbarM ^ 2 ≤ 192 * K * u ^ 6 := by
    have h3 : dbarM ^ 2 ≤ 192 * (A ^ 2 + u ^ 6 * s1 ^ 2 + u ^ 6 * D ^ 2) := by
      have := sq3 A (u ^ 3 * s1) (u ^ 3 * D)
      rw [hdbarM]; convert this using 2; ring
    have : A ^ 2 ≤ u ^ 6 * A ^ 2 := le_mul_of_one_le_left (sq_nonneg A) hu6
    have e : 192 * K * u ^ 6 = 192 * (u ^ 6 * A ^ 2 + u ^ 6 * s1 ^ 2 + u ^ 6 * D ^ 2) := by
      rw [hK]; ring
    rw [e]; linarith
  have hd2 : dbar ^ 2 ≤ dbarM ^ 2 := pow_le_pow_left₀ hd0 hdd 2
  have hd1 : dbar ^ 2 ≤ 192 * K * u ^ 6 := le_trans hd2 hdM
  -- Step 2
  have hκ0 : 0 ≤ 2 + 2 * dbar ^ 2 / u ^ 3 := by positivity
  have hκ : Real.sqrt (2 + 2 * dbar ^ 2 / u ^ 3) ^ 2 ≤ c2 * u ^ 3 := by
    rw [Real.sq_sqrt hκ0]
    have : 2 * dbar ^ 2 / u ^ 3 ≤ 384 * K * u ^ 3 := by
      rw [div_le_iff₀ (by positivity)]
      have e : 384 * K * u ^ 3 * u ^ 3 = 2 * (192 * K * u ^ 6) := by ring
      rw [e]; linarith
    have e : c2 * u ^ 3 = 2 * u ^ 3 + 384 * K * u ^ 3 := by rw [hc2]; ring
    rw [e]; linarith
  -- Step 3
  have hGb : (v ^ 3) ^ 2 ≤ Gbar ^ 2 := pow_le_pow_left₀ (by positivity) hGsle 2
  have hBdot : 18 * (1 + b ^ 6 + dbar ^ 2) ≤ 18 * c1 * u ^ 6 := by
    have h1 : 2 * u ^ 6 * (v ^ 3) ^ 2 ≤ 2 * u ^ 6 * Gbar ^ 2 :=
      mul_le_mul_of_nonneg_left hGb (by positivity)
    have e : 18 * c1 * u ^ 6 = 18 * (u ^ 6 + 2 * u ^ 6 * Gbar ^ 2 + 192 * K * u ^ 6) := by
      rw [hc1]; ring
    rw [← hβ, e]; linarith
  -- Step 4
  have hlog0 : 0 ≤ Real.log (1 + dbar ^ 2 * T) :=
    Real.log_nonneg (by nlinarith [sq_nonneg dbar])
  have hlog : Real.log (1 + dbar ^ 2 * T) ≤ Lc := by
    refine le_trans ?_ (le_max_right _ _)
    apply Real.log_le_log (by nlinarith [sq_nonneg dbar])
    nlinarith
  have hLc1 : 1 ≤ Lc := le_max_left _ _
  have hBddot : 40 * (2 * u ^ 6 * L ^ 2) * Real.sqrt (2 + 2 * dbar ^ 2 / u ^ 3) ^ 2 / u ^ 3
        * Real.log (1 + dbar ^ 2 * T) ≤ 80 * c2 * L ^ 2 * Lc * u ^ 6 := by
    have e : 40 * (2 * u ^ 6 * L ^ 2) * Real.sqrt (2 + 2 * dbar ^ 2 / u ^ 3) ^ 2 / u ^ 3
        * Real.log (1 + dbar ^ 2 * T) = 80 * L ^ 2 * u ^ 3 *
          (Real.sqrt (2 + 2 * dbar ^ 2 / u ^ 3) ^ 2 * Real.log (1 + dbar ^ 2 * T)) := by
      field_simp; ring
    rw [e]
    have hc20 : 0 ≤ c2 * u ^ 3 := by positivity
    have : Real.sqrt (2 + 2 * dbar ^ 2 / u ^ 3) ^ 2 * Real.log (1 + dbar ^ 2 * T)
        ≤ c2 * u ^ 3 * Lc := mul_le_mul hκ hlog hlog0 hc20
    have hL0 : 0 ≤ 80 * L ^ 2 * u ^ 3 := by positivity
    calc 80 * L ^ 2 * u ^ 3 * (Real.sqrt (2 + 2 * dbar ^ 2 / u ^ 3) ^ 2
          * Real.log (1 + dbar ^ 2 * T)) ≤ 80 * L ^ 2 * u ^ 3 * (c2 * u ^ 3 * Lc) :=
          mul_le_mul_of_nonneg_left this hL0
      _ = 80 * c2 * L ^ 2 * Lc * u ^ 6 := by ring
  -- Step 6: Y0 bound
  set CY := 24 * D ^ 2 + 288 * Fbar ^ 2 + 1728 * c1 + 7680 * c2 * L ^ 2 with hCY
  set Y0 := max (2 * (12 * D ^ 2 * (u ^ 3) ^ 2 + 144 * Fbar ^ 2 * (u ^ 3) ^ 2))
      (96 * (18 * (1 + b ^ 6 + dbar ^ 2) +
        40 * (2 * u ^ 6 * L ^ 2) * Real.sqrt (2 + 2 * dbar ^ 2 / u ^ 3) ^ 2 / u ^ 3
          * Real.log (1 + dbar ^ 2 * T))) with hY0
  have hc10 : 0 ≤ c1 := by positivity
  have hY0 : Y0 ≤ CY * Lc * u ^ 6 := by
    have hY1 : 2 * (12 * D ^ 2 * (u ^ 3) ^ 2 + 144 * Fbar ^ 2 * (u ^ 3) ^ 2)
        = (24 * D ^ 2 + 288 * Fbar ^ 2) * u ^ 6 := by ring
    have hBdd0 : 0 ≤ 40 * (2 * u ^ 6 * L ^ 2) * Real.sqrt (2 + 2 * dbar ^ 2 / u ^ 3) ^ 2
        / u ^ 3 * Real.log (1 + dbar ^ 2 * T) := by positivity
    have hA1 : 0 ≤ (24 * D ^ 2 + 288 * Fbar ^ 2) * u ^ 6 := by positivity
    have hm : Y0 ≤ (24 * D ^ 2 + 288 * Fbar ^ 2) * u ^ 6 +
        96 * (18 * c1 * u ^ 6 + 80 * c2 * L ^ 2 * Lc * u ^ 6) := by
      rw [hY0, hY1]
      apply max_le
      · have : 0 ≤ 96 * (18 * c1 * u ^ 6 + 80 * c2 * L ^ 2 * Lc * u ^ 6) := by
          have : 0 ≤ Lc := by linarith
          positivity
        linarith
      · linarith
    have hP : 0 ≤ (24 * D ^ 2 + 288 * Fbar ^ 2 + 1728 * c1) * u ^ 6 := by positivity
    have : (24 * D ^ 2 + 288 * Fbar ^ 2 + 1728 * c1) * u ^ 6
        ≤ (24 * D ^ 2 + 288 * Fbar ^ 2 + 1728 * c1) * u ^ 6 * Lc := le_mul_of_one_le_right hP hLc1
    have e : CY * Lc * u ^ 6 = (24 * D ^ 2 + 288 * Fbar ^ 2 + 1728 * c1) * u ^ 6 * Lc
        + 7680 * c2 * L ^ 2 * Lc * u ^ 6 := by rw [hCY]; ring
    rw [e]; linarith
  -- Steps 7-8
  have hθle : b / (1 + b) ≤ b := by
    rw [div_le_iff₀ (by positivity), mul_add, mul_one]
    linarith [mul_nonneg hb0.le hb0.le]
  have hθ0 : 0 < b / (1 + b) := by positivity
  have hmax : max (max (b ^ 2) ((b / (1 + b)) ^ 2)) (b ^ 2) = b ^ 2 := by
    have : (b / (1 + b)) ^ 2 ≤ b ^ 2 := pow_le_pow_left₀ hθ0.le hθle 2
    simp [this]
  rw [hmax]
  have hR : 2 * Y0 * b ^ 2 / (u ^ 3 * (b / (1 + b))) = 2 * Y0 * (b + b ^ 2) / u ^ 3 := by
    field_simp
  rw [hR, div_le_iff₀ (by positivity)]
  have hY00 : 0 ≤ Y0 := le_trans (by positivity) (le_max_left _ _)
  have hbb : 0 ≤ b + b ^ 2 := by positivity
  have step : 2 * Y0 * (b + b ^ 2) ≤ 2 * (CY * Lc * u ^ 6) * (b + b ^ 2) := by
    have := mul_le_mul_of_nonneg_right hY0 hbb; linarith
  refine le_trans step ?_
  have hCY0 : 0 ≤ CY := by positivity
  have hX : 0 ≤ CY * Lc := by positivity
  have hw2 : w ≤ w ^ 2 := by nlinarith
  have hvu : 0 ≤ CY * Lc * v * u ^ 4 * u ^ 3 * u ^ 6 := by positivity
  rw [hb]
  have key : 2 * (CY * Lc * u ^ 6) * (w * u * v + (w * u * v) ^ 2)
      = 2 * CY * Lc * u ^ 3 * (w * (v * u ^ 4) + w ^ 2 * (v ^ 2 * u ^ 5)) := by ring
  have key2 : 2 * w ^ 2 * CY * Lc * (v * u ^ 4 + v ^ 2 * u ^ 5) * u ^ 3
      = 2 * CY * Lc * u ^ 3 * (w ^ 2 * (v * u ^ 4) + w ^ 2 * (v ^ 2 * u ^ 5)) := by ring
  rw [key, key2]
  apply mul_le_mul_of_nonneg_left _ (by positivity)
  have : w * (v * u ^ 4) ≤ w ^ 2 * (v * u ^ 4) :=
    mul_le_mul_of_nonneg_right hw2 (by positivity)
  linarith

end

#print axioms lemD
