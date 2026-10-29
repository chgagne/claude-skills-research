# Protocol L8 results: real findings, the documented 1101 defect missed (2026-10-29)

Protocol: `PROTOCOL-L8.md` (760a00f). Live skill at 4b56e5c, frozen. 2 runs, no web, $1.13 in
total, about 2.5 minutes each (7 and 9 turns). Both runs loaded the skill and used Lean; both
certification passes reported CLEAN. The Lean files were rebuilt from the traces (one heredoc each,
no later edits), recompile on the clean project with no error and no `sorry`, and are in `lean/L8/`.

| Paper | Documented defect | Flags | Real (by content) | Lean | Cost |
|---|---|---|---|---|---|
| 1101.2597 | **missed** (no flag in eq3) | 10 | 10 (2 minor) | 3 theorems, faithful | $0.55 |
| 0907.0453 | not located (descriptive) | 5 | 5 | 3 theorems, 1 substantive, faithful | $0.58 |

## 1101.2597

**Miss under the protocol's rule.** The withdrawal note says "a crucial error in one of equation in
(3)". No flag quotes eq3, and the run took eq3 as correct: its λ₂′ finding starts "From the term
−(1−u₁)L in (3)". One flag comes close by content. It says Theorem 5.1 asserts nonnegativity, but
at S = 0 the S-equation of (3) gives μω(1−εC) + δV < 0 when εC > 1. That is a property of eq3 (and
of eq1), but the flag places the error in the existence proof, not in the equation.

**The findings are real.** eq9 is checked against the paper's own Hamiltonian (5), which copies
eq3's right-hand sides:
- λ₂′, λ₃′ and λ₄′ disagree with −∂M/∂x. Lean shows the derivative of the faithful eq5 fragment
  and the paper's value at one instance. I checked the instances against eq5 and eq9 term by term.
- λ₁′ uses a nonexistent λ₇.
- The proof's own derivation (eq12) contradicts the statement: λ₁ appears where λ₂ belongs.
- The transversality conditions run i = 1..7.
- u₁* is mis-bracketed.
- The admissible set is not closed (a strict inequality).
- Two flags are minor (undefined E(t), and coercivity stated for J rather than the integrand).

**Where the defect sits.** eq9's λ₂′ has [(μ+σ+β₁) + u₁]λ₂ and λ₄′ has u₂ terms. Those are the
adjoints of dynamics with −u₁L and −u₂C, not −(1−u₁)L and −(1−u₂)C. eq9 looks derived from an eq3
without the (1−u) terms. With eq3 as printed, the system also disagrees with eq1 at u = 0 (my
pre-run candidate, journal 2026-10-29). So the certified `lam2_wrong` is true of the paper as
written, but it is a downstream symptom: the run localised the inconsistency in the adjoint and
missed its likely source in the state equation. The λ₃′ (sign of β₂) and λ₄′ (sign of the λ₄
term) errors do not depend on eq3.

**Fidelity.** No certificate states something the paper does not say. The "paper" side of each
theorem is a hand-evaluated numeric expression; all three match eq9.

## 0907.0453

All 5 flags are real.

1. **Theorem 3: P(Ξ,Δ,Γ) factored with P(Δ)P(Γ).** Δ and Γ share the random (x, y). I checked the
   counterexample by hand: S = {ε, a}, D uniform, δ_A(1,a) = 2 gives P(Δ∧Γ) = 1/2 ≠ P(Δ)P(Γ).
   Lean checks only the arithmetic.
2. **Theorem 3: P(Γ | x ≠ y) = 1/n.** False as an equality. Lean enumerates all 4 transition
   functions: a unary alphabet, n = 2, "aa" against "aaa" gives 3/4. That models UDFA (uniform δ,
   q₀ fixed) faithfully. The ≥ 1/n the proof needs is not proved.
3. **Anti-concentration lemma.** The factor 2 assumes X is symmetric. The step is wrong but the
   lemma holds by the run's repair (σ² ≤ t² + P(|X| > t)).
4. **Theorem 2: expected iterations 1/v².** v² = Var ξ is over A and B jointly. With A fixed
   through the iterations, as the proof itself says, the success probability is p(A), and
   E_A[1/p(A)] ≥ 1/E_A[p(A)]. The theorem gets no per-target bound.
5. **Theorem 1(a).** It drops the log(2em/d) factor of eq:vc-bound.

**Bearing on the main claim.** Finding 4 is the step that turns an average over targets into a
guarantee for one target under an arbitrary D. The Angluin, Eisenstat, Kontorovich, Reyzin SQ lower
bound (2009) rules that guarantee out for random DFAs. It is the most plausible candidate for the
documented error, but plausible only: the withdrawal note does not locate it. Findings 1 and 2 are
real but repairable, and do not reach the main claim.

## Reading

- **The wrong-verdict-then-certificate path is still untested.** No run reached a wrong verdict.
  Every certificate states something true of the paper as written.
- **A new failure shape: correct certificates, wrong locus.** On 1101 the run trusted the state
  system and certified its downstream consequences. A certificate proves the inconsistency, not
  which side of it is wrong. The protocol's hit rule caught this; a span scorer counting "Lean
  CLEAN on a real inconsistency" would not.
- **Cheap and fast.** Both papers were read whole in about 2.5 minutes, against $0.29-$3.30 per
  run in L4/L7. Neither paper is long (750 and 1130 lines).
- Two runs, discovery only: no SKILL.md change (protocol).

## What could follow (not decided)

- A reading line "check that a controlled or perturbed system reduces to the base system at zero
  control" would be written from this one paper, the L7 pattern. Three prose lines are already
  measured as read and not applied.
- The structural alternative: when two displayed systems are claimed to be related (one is the
  other plus control terms, or the adjoint of the other), the hygiene script emits the pair and
  the agent must answer whether they agree. This is the same shape as the structural closure check
  set aside on 2026-10-28.
