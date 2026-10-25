import Mathlib

open Filter Real

/-- Reduced entropy at width `N` from prior mass `p N` of the accurate set:
`s_N = -(1/N) log p_N` (paper eq. redent). -/
noncomputable def sN (p : ℕ → ℝ) (N : ℕ) : ℝ := -(1 / (N : ℝ)) * Real.log (p N)

/-- Prior masses that are large (= 1) at a single width `N0` and `exp(-N^2)` elsewhere. -/
noncomputable def pBad (N0 : ℕ) (N : ℕ) : ℝ := if N = N0 then 1 else Real.exp (-((N : ℝ) ^ 2))

lemma sN_pBad_ne (N0 N : ℕ) (h : N ≠ N0) (hN : 0 < N) : sN (pBad N0) N = N := by
  unfold sN pBad
  rw [if_neg h, Real.log_exp]
  have : (N : ℝ) ≠ 0 := by exact_mod_cast hN.ne'
  field_simp

/-- The defect: a bound on `s_N` at one width `N0` (all that (ii) controls) does not bound
`s_∞ = limsup_N s_N`. Here every `p N ∈ (0,1]`, `s_{N0} = 0`, yet `s_N` is unbounded above
along `N → ∞`, so the limsup is `+∞` and no polynomial bound on `s_∞` follows. -/
theorem single_width_does_not_bound_limsup (N0 : ℕ) :
    (∀ N, 0 < pBad N0 N ∧ pBad N0 N ≤ 1) ∧
    sN (pBad N0) N0 = 0 ∧
    ¬ IsBoundedUnder (· ≤ ·) atTop (sN (pBad N0)) := by
  refine ⟨fun N => ?_, ?_, ?_⟩
  · unfold pBad
    split_ifs
    · norm_num
    · exact ⟨Real.exp_pos _, Real.exp_le_one_iff.mpr (by nlinarith [sq_nonneg (N:ℝ)])⟩
  · simp [sN, pBad]
  · rintro ⟨C, hC⟩
    rw [eventually_map, eventually_atTop] at hC
    obtain ⟨M, hM⟩ := hC
    obtain ⟨k, hk⟩ := exists_nat_gt C
    set N := max (max M (N0 + 1)) (k + 1) with hNdef
    have h1 : N ≠ N0 := by omega
    have h2 : 0 < N := by omega
    have := hM N (by omega)
    rw [sN_pBad_ne N0 N h1 h2] at this
    have : (k : ℝ) + 1 ≤ N := by exact_mod_cast (le_max_right _ _)
    linarith

/-- What Theorem thm:conv actually needs: a bound for all sufficiently large N gives the
limsup bound. -/
theorem eventual_bound_gives_limsup (s : ℕ → ℝ) (C : ℝ) (h : ∀ᶠ N in atTop, s N ≤ C)
    (hb : IsBoundedUnder (· ≥ ·) atTop s) :
    limsup s atTop ≤ C :=
  limsup_le_of_le hb.isCoboundedUnder_flip h

#print axioms single_width_does_not_bound_limsup
#print axioms eventual_bound_gives_limsup
