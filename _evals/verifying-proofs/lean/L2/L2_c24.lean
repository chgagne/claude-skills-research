import Mathlib

open Finset

/-- Without the trivial cap, using only the mixing bound of Lemma perlevel
(V_j ≤ 144 H² τ / 2^j, valid at every level since Lemma segment holds for all m ≥ 1),
the level sum is at most 144 H² τ · jmax, i.e. O(τ log T). -/
theorem uncapped_level_sum (H τ : ℝ) (V : ℕ → ℝ) (jmax : ℕ)
    (hV : ∀ j, 1 ≤ j → j ≤ jmax → V j ≤ 144 * H ^ 2 * τ / 2 ^ j) :
    ∑ j ∈ Icc 1 jmax, (2 : ℝ) ^ j * V j ≤ 144 * H ^ 2 * τ * jmax := by
  calc ∑ j ∈ Icc 1 jmax, (2 : ℝ) ^ j * V j
      ≤ ∑ j ∈ Icc 1 jmax, 144 * H ^ 2 * τ := by
        apply sum_le_sum
        intro j hj
        rw [mem_Icc] at hj
        have h2 : (0 : ℝ) < 2 ^ j := by positivity
        have := hV j hj.1 hj.2
        rw [le_div_iff₀ h2] at this
        linarith
    _ = 144 * H ^ 2 * τ * jmax := by
        rw [sum_const, Nat.card_Icc]; simp; ring

/-- The low levels (2^j ≤ τ, i.e. j ≤ log₂ τ) contribute at most 144 H² τ log₂ τ
without the cap. -/
theorem uncapped_low_levels (H : ℝ) (τ : ℕ) (V : ℕ → ℝ)
    (hV : ∀ j, V j ≤ 144 * H ^ 2 * (τ : ℝ) / 2 ^ j) :
    ∑ j ∈ Icc 1 (Nat.log 2 τ), (2 : ℝ) ^ j * V j
      ≤ 144 * H ^ 2 * (τ : ℝ) * (Nat.log 2 τ) :=
  uncapped_level_sum H τ V _ (fun j _ _ => hV j)

/-- The uncapped low-level bound 144 τ log₂ τ is NOT Ω(τ²): for every c > 0 there is
a τ with 144 τ log₂ τ < c τ². Hence "Θ(τ²)" is false. -/
theorem not_theta_tau_sq (c : ℝ) (hc : 0 < c) :
    ∃ τ : ℕ, 1 ≤ τ ∧ 144 * (τ : ℝ) * (Nat.log 2 τ) < c * (τ : ℝ) ^ 2 := by
  obtain ⟨m, hm⟩ := exists_nat_gt (288 / c)
  refine ⟨2 ^ (2 * m), Nat.one_le_two_pow, ?_⟩
  rw [Nat.log_pow (by norm_num)]
  have hm2 : (m : ℝ) < 2 ^ m := by exact_mod_cast Nat.lt_two_pow_self
  have hpos : (0 : ℝ) < 2 ^ m := by positivity
  have hc' : 288 < c * m := by rw [div_lt_iff₀ hc] at hm; linarith
  push_cast
  have e : (2 : ℝ) ^ (2 * m) = 2 ^ m * 2 ^ m := by rw [two_mul, pow_add]
  rw [e]
  -- goal: 144 * (A*A) * (2m) < c * (A*A)^2, A = 2^m
  have key : 288 * (m : ℝ) < c * (2 ^ m * 2 ^ m) := by
    have h1 : 288 * (m:ℝ) < c * m * 2 ^ m := by
      have hm0 : (0:ℝ) < m := by
        rcases Nat.eq_zero_or_pos m with h | h
        · subst h; simp at hc'; linarith
        · exact_mod_cast h
      nlinarith [hpos, hm0, hc']
    have h2 : c * m * 2 ^ m ≤ c * (2 ^ m * 2 ^ m) := by
      have : c * m * 2 ^ m = c * 2 ^ m * m := by ring
      rw [this, mul_assoc]
      apply mul_le_mul_of_nonneg_left _ hc.le
      nlinarith [hm2.le, hpos]
    linarith
  have hA : (0:ℝ) < 2 ^ m * 2 ^ m := by positivity
  nlinarith [key, hA]

#print axioms uncapped_level_sum
#print axioms uncapped_low_levels
#print axioms not_theta_tau_sq
