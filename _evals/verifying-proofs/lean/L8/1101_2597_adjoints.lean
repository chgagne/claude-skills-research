import Mathlib

/-! Hamiltonian (5) restricted to its C-, I-, L-, S-dependent terms, at fixed other states.
Each part is affine in the variable, so -∂M/∂x is its slope. -/

-- C-dependent part of M
noncomputable def MC (A4 l1 l2 l4 l5 l6 mu om eps be al S I g1 q g2 mu1 mu0 u2 : ℝ) (C : ℝ) : ℝ :=
  A4*C + l1*(mu*om*(1-eps*C) - be*(I+al*C)*S) + l2*(be*(I+al*C)*S + eps*mu*om*C)
  + l4*(g1*q*I - (g2+mu1+mu0)*C - (1-u2)*C) + l5*(g2*C) + l6*((1-u2)*C)

-- Instance: A4=0, l4=1, others 0, mu=mu1=1, u2=0. Correct λ4' = -∂M/∂C = 2; paper's (9) gives -1.
theorem lam4_wrong :
    HasDerivAt (MC 0 0 0 1 0 0 1 0 0 0 0 0 0 0 0 0 1 0 0) (-2) 5 ∧
    let paper := -(0:ℝ) + 0*(0-0)*0*0 - 1*((0+1+0)+0) - 0*0 + 0*0 - 0*(0*1*0)
    paper ≠ -(-2) := by
  refine ⟨?_, by norm_num⟩
  have h : MC 0 0 0 1 0 0 1 0 0 0 0 0 0 0 0 0 1 0 0 = fun C => -2*C := by
    funext C; simp [MC]; ring
  rw [h]; simpa using (hasDerivAt_id (5:ℝ)).const_mul (-2)

-- I-dependent part of M
noncomputable def MI (A3 l1 l2 l3 l4 l5 l6 be al S C sg Lv g1 mu1 b2 q u2 : ℝ) (I : ℝ) : ℝ :=
  A3*I + l1*(-be*(I+al*C)*S) + l2*(be*(I+al*C)*S) + l3*(sg*Lv - (g1+mu1+b2)*I - u2*I)
  + l4*(g1*q*I) + l5*((1-q)*g1*I + b2*I) + l6*(u2*I)

-- Instance: l5=1, b2=1, everything else 0. Correct λ3' = -∂M/∂I = -1; paper's -λ5[(1-q)γ1-β2] = +1.
theorem lam3_wrong :
    HasDerivAt (MI 0 0 0 0 0 1 0 0 0 0 0 0 0 0 0 1 0 0) 1 5 ∧
    let paper := -(0:ℝ) + (0-0)*0*0 + 0*((0+1+0)+0) - 0*0*0 - 1*((1-0)*0 - 1) - 0*0
    paper ≠ -(1:ℝ) := by
  refine ⟨?_, by norm_num⟩
  have h : MI 0 0 0 0 0 1 0 0 0 0 0 0 0 0 0 1 0 0 = fun I => 1*I := by
    funext I; simp [MI]
  rw [h]; simpa using (hasDerivAt_id (5:ℝ)).const_mul (1:ℝ)

-- L-dependent part of M
noncomputable def ML (A2 l2 l3 l5 sg mu1 b1 u1 : ℝ) (L : ℝ) : ℝ :=
  A2*L + l2*(-(sg+mu1+b1)*L - (1-u1)*L) + l3*(sg*L) + l5*((1-u1)*L)

-- Instance: l2=1, all else 0 (u1=0). Correct λ2' = 1; paper's [(μ+σ+β1)+u1]λ2 = 0.
theorem lam2_wrong :
    HasDerivAt (ML 0 1 0 0 0 0 0 0) (-1) 5 ∧
    let paper := -(0:ℝ) + ((0+0+0)+0)*1 - 0*0 + 0*0
    paper ≠ -(-1:ℝ) := by
  refine ⟨?_, by norm_num⟩
  have h : ML 0 1 0 0 0 0 0 0 = fun L => -1*L := by
    funext L; simp [ML]
  rw [h]; simpa using (hasDerivAt_id (5:ℝ)).const_mul (-1:ℝ)
