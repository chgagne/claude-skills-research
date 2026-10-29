import Mathlib

/-! Finding A: P(Γ | x ≠ y) = 1/n is false.
Unary alphabet, n = 2, start state 0. A transition function is f : Fin 2 → Fin 2,
drawn uniformly (4 choices). x = "aa", y = "aaa". -/
def qx (f : Fin 2 → Fin 2) : Fin 2 := f (f 0)
def qy (f : Fin 2 → Fin 2) : Fin 2 := f (f (f 0))

theorem gamma_not_one_over_n :
    (Finset.univ.filter (fun f : Fin 2 → Fin 2 => qx f = qy f)).card = 3 ∧
    (Fintype.card (Fin 2 → Fin 2)) = 4 := by decide
-- so P(Γ | x="aa", y="aaa") = 3/4 ≠ 1/2 = 1/n

/-! Finding B: Δ and Γ are not independent.
S = {ε, a}, D uniform, A with δ_A(1,a) = 2 (so Δ ↔ x = y), B uniform on n states.
P(Δ) = 1/2, P(Γ) = 1/2 + 1/(2n), P(Δ ∧ Γ) = P(x = y) = 1/2. -/
theorem delta_gamma_dependent (n : ℚ) (hn : 2 ≤ n) :
    (1/2 : ℚ) ≠ (1/2) * (1/2 + 1/(2*n)) := by
  have : 0 < n := by linarith
  intro h
  field_simp at h
  nlinarith

/-! Finding C: E X² = 2(∫₀ᵗ x² dP + ∫ₜ¹ x² dP) needs symmetry.
X = -1/2 w.p. 2/3, X = 1 w.p. 1/3: mean 0, |X| ≤ 1. -/
theorem lemma_factor_two :
    (2/3 : ℚ) * (-1/2) + (1/3) * 1 = 0 ∧
    ((2/3 : ℚ) * (1/4) + (1/3) * 1 = 1/2) ∧
    (2 * ((1/3 : ℚ) * 1) = 2/3) ∧ ((1/2 : ℚ) ≠ 2/3) := by norm_num
