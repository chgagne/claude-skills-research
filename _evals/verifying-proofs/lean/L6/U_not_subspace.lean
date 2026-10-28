import Mathlib

/-! 0801.4243, Lemma `gr`: the set
  U := {p ∈ K[X]_{2k} | L(pq) = 0 for all q with pq ∈ K[X]_{2k}}
is called a linear subspace; it is not closed under addition, even for a flat L.
Instance: K = ℚ, n = 1, k = 2, L(p) = p(0) + p(1) (two atoms; B_{L_2} and B_{L_1} both have
rank 2, so L_2 is flat). -/

open Polynomial

noncomputable def L (p : ℚ[X]) : ℚ := p.eval 0 + p.eval 1

/-- Membership in U for k = 2 (degrees at most 4). -/
def InU (p : ℚ[X]) : Prop :=
  p.natDegree ≤ 4 ∧ ∀ q : ℚ[X], (p * q).natDegree ≤ 4 → L (p * q) = 0

noncomputable def p1 : ℚ[X] := X ^ 4 - X ^ 3
noncomputable def p2 : ℚ[X] := -X ^ 4 + X ^ 3 + X - C (1 / 2)

lemma natDegree_p1 : p1.natDegree = 4 := by
  unfold p1; compute_degree!

lemma natDegree_p2 : p2.natDegree = 4 := by
  unfold p2; compute_degree!

/-- A degree-4 polynomial times q stays of degree ≤ 4 only if q is a constant. -/
lemma const_of_deg (p q : ℚ[X]) (hp : p.natDegree = 4) (hp0 : p ≠ 0)
    (h : (p * q).natDegree ≤ 4) : q = C (q.coeff 0) := by
  by_cases hq : q = 0
  · simp [hq]
  · rw [natDegree_mul hp0 hq, hp] at h
    exact eq_C_of_natDegree_eq_zero (by omega)

lemma p1_ne : p1 ≠ 0 := by
  intro h; have := natDegree_p1; rw [h] at this; simp at this

lemma p2_ne : p2 ≠ 0 := by
  intro h; have := natDegree_p2; rw [h] at this; simp at this

theorem p1_in_U : InU p1 := by
  refine ⟨natDegree_p1.le, fun q hq => ?_⟩
  rw [const_of_deg p1 q natDegree_p1 p1_ne hq]
  simp [L, p1]

theorem p2_in_U : InU p2 := by
  refine ⟨natDegree_p2.le, fun q hq => ?_⟩
  rw [const_of_deg p2 q natDegree_p2 p2_ne hq]
  simp [L, p2]; ring

theorem sum_not_in_U : ¬ InU (p1 + p2) := by
  rintro ⟨_, h⟩
  have hs : p1 + p2 = X - C (1 / 2) := by unfold p1 p2; ring
  have := h X (by rw [hs]; compute_degree!)
  rw [hs] at this
  simp [L] at this
  norm_num at this

/-- Flatness of this L at k = 2: the moment matrices of L_1 and L_2 have equal rank.
Moments m_j = L(X^j) = 0^j + 1 = (2, 1, 1, 1, 1); B_{L_1} = [[2,1],[1,1]] (det 1),
B_{L_2} = [[2,1,1],[1,1,1],[1,1,1]] (det 0, a nonzero 2x2 minor): both rank 2. -/
theorem flat_witness :
    Matrix.det !![(2:ℚ), 1; 1, 1] ≠ 0 ∧ Matrix.det !![(2:ℚ), 1, 1; 1, 1, 1; 1, 1, 1] = 0 := by
  constructor <;> simp [Matrix.det_fin_two, Matrix.det_fin_three] <;> norm_num
