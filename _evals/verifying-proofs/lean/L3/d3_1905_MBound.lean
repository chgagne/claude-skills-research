import Mathlib

/-! Lemma `lemma:m_bound` claims E‖μ m_{t,i} + g_{t,i}‖² ≤ G²/(1-μ).
Instance: d = 1, deterministic gradients g_0 = g_1 = 1 (σ = 0, ω = 1, so G² = 1),
μ = 1/2, m_{-1} = 0, m_t = μ m_{t-1} + g_t, t = 1. -/

def μ : ℚ := 1/2
def g : ℕ → ℚ := fun _ => 1
def m : ℕ → ℚ
  | 0 => g 0
  | (n+1) => μ * m n + g (n+1)

theorem m_bound_fails :
    let G2 : ℚ := 1
    (μ * m 1 + g 1)^2 > G2 / (1 - μ) := by
  simp [m, g, μ]; norm_num

-- The bound the proof actually derives, G²/(1-μ)², does hold here.
theorem proof_bound_holds :
    let G2 : ℚ := 1
    (μ * m 1 + g 1)^2 ≤ G2 / (1 - μ)^2 := by
  simp [m, g, μ]; norm_num
