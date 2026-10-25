import Mathlib

/-!
Flag L2/c22: in the proof of Theorem 3.5 (uniform convergence of Φ_N), Lemma 2.4 and
Theorem 3.2 (stated for f ∈ F) are applied to bracket endpoints l_k, u_k ∉ F.

Abstraction: points z : α (= (x,y)); `lo` is the pointwise envelope of all lower
constraints on F (the lower bounds of (eq: bounds on f) for every ε, and 0), `up` the
upper bound C₂⁺(1+‖x‖²+‖y‖²).  G lo up = {f | lo ≤ f ≤ up}.  The auxiliary lemmas'
proofs only use membership in G (plus convexity, for k_t).
-/

/-- The class of functions satisfying the pointwise constraints. -/
def G {α : Type*} (lo up : α → ℝ) : Set (α → ℝ) := {f | ∀ z, lo z ≤ f z ∧ f z ≤ up z}

/-- (a) G is convex, so the segment argument k_t = g + t(f-g) of Lemma 2.4 stays in G. -/
theorem G_convex {α : Type*} (lo up : α → ℝ) : Convex ℝ (G lo up) := by
  intro f hf g hg a b ha hb hab
  intro z
  have h1 := hf z
  have h2 := hg z
  simp only [Pi.add_apply, Pi.smul_apply, smul_eq_mul]
  constructor
  · have e : lo z = a * lo z + b * lo z := by rw [← add_mul, hab, one_mul]
    nlinarith [mul_le_mul_of_nonneg_left h1.1 ha, mul_le_mul_of_nonneg_left h2.1 hb]
  · have e : up z = a * up z + b * up z := by rw [← add_mul, hab, one_mul]
    nlinarith [mul_le_mul_of_nonneg_left h1.2 ha, mul_le_mul_of_nonneg_left h2.2 hb]

/-- (b) The "without loss of generality" clipping is valid: if F ⊆ G and f ∈ F lies in
[l,u], then the clipped bracket [max l lo, min u up] still contains f, its endpoints lie
in G, and its width is pointwise no larger. -/
theorem clip_bracket {α : Type*} (lo up : α → ℝ) (F : Set (α → ℝ)) (hF : F ⊆ G lo up)
    (l u f : α → ℝ) (hf : f ∈ F) (hl : ∀ z, l z ≤ f z) (hu : ∀ z, f z ≤ u z) :
    (∀ z, max (l z) (lo z) ≤ f z ∧ f z ≤ min (u z) (up z)) ∧
    (fun z => max (l z) (lo z)) ∈ G lo up ∧
    (fun z => min (u z) (up z)) ∈ G lo up ∧
    (∀ z, 0 ≤ min (u z) (up z) - max (l z) (lo z) ∧
          min (u z) (up z) - max (l z) (lo z) ≤ u z - l z) := by
  have hG := hF hf
  refine ⟨fun z => ?_, fun z => ?_, fun z => ?_, fun z => ?_⟩
  · have := hG z; have := hl z; have := hu z
    exact ⟨max_le (by linarith) (by linarith), le_min (by linarith) (by linarith)⟩
  · have := hG z; have := hl z
    exact ⟨le_max_right _ _, max_le (by linarith) (by linarith)⟩
  · have := hG z; have := hu z
    exact ⟨le_min (by linarith) (by linarith), min_le_right _ _⟩
  · have := hG z; have := hl z; have := hu z
    constructor
    · have : max (l z) (lo z) ≤ min (u z) (up z) :=
        max_le (le_min (by linarith) (by linarith)) (le_min (by linarith) (by linarith))
      linarith
    · have := le_max_left (l z) (lo z); have := min_le_left (u z) (up z); linarith

/-- (c) The flag's literal point: clipped endpoints satisfy all the pointwise bounds yet
need not lie in F, even for F convex and closed (here F = {const 1}, G = [0,2]). -/
theorem endpoints_not_in_F :
    ∃ (F : Set (Unit → ℝ)) (l u : Unit → ℝ),
      Convex ℝ F ∧ IsClosed F ∧ F ⊆ G (fun _ => 0) (fun _ => 2) ∧
      (∀ f ∈ F, ∀ z, l z ≤ f z ∧ f z ≤ u z) ∧
      l ∈ G (fun _ => 0) (fun _ => 2) ∧ u ∈ G (fun _ => 0) (fun _ => 2) ∧
      l ∉ F ∧ u ∉ F := by
  refine ⟨{fun _ => 1}, fun _ => 1/2, fun _ => 3/2, convex_singleton _, isClosed_singleton,
    ?_, ?_, ?_, ?_, ?_, ?_⟩
  · intro f hf z; rw [Set.mem_singleton_iff] at hf; subst hf; norm_num
  · intro f hf z; rw [Set.mem_singleton_iff] at hf; subst hf; norm_num
  · intro z; norm_num
  · intro z; norm_num
  · intro h; rw [Set.mem_singleton_iff] at h; have := congrFun h (); norm_num at this
  · intro h; rw [Set.mem_singleton_iff] at h; have := congrFun h (); norm_num at this

#print axioms G_convex
#print axioms clip_bracket
#print axioms endpoints_not_in_F
