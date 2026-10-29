# Protocol L5, stage 3: subtle false findings were rejected too; the failure path stays untested (2026-10-28)

Protocol: `PROTOCOL-L5.md`, stage 3 section (9964f99). Material hashed in the journal (45e0950)
before any run. 8 false findings on correct steps, built to be hard to refute (the refutation lives
far from the quoted step, or the counterexample fails on a buried detail), one per P1 paper, drawn
from 16 candidates and each re-checked by Claude. Skill frozen at bf81bdc, prompt names it, no
web: **$2.79 in total**, 55 to 134 s per run. Lean files rebuilt from the traces and recompiled by
Claude; kept in `private/l5/certs3/`.

| Case | Finding (device) | Verdict | Where the run found the refutation | Lean |
|---|---|---|---|---|
| t01 | h12 (far assumption) | does not hold | Assumption 1 (f a diffeomorphism) in the corollary's hypotheses | injective derivative and adjoint, CLEAN (partial, labelled) |
| t02 | h5 (normalisation) | does not hold | the factor 2 inside the lemma's event | constants of the combination, CLEAN |
| t03 | h10 (buried slip) | does not hold | the finding's factorisation | weights sum to 1, CLEAN |
| t04 | h3 (normalisation) | does not hold | the C² quantity's definition (line 349), so k >= 1 | k >= 1 and the radius, CLEAN |
| t05 | h2 (subtle counterexample) | does not hold | no ω₀ and no I*_{i,1}: the grid starts at ω₁ = 1 | - |
| t06 | h7 (buried slip) | does not hold | τ⁻³τ^{5/2} = τ^{-1/2}, not τ^{1/2} | the last step, CLEAN |
| t07 | h16 (far assumption) | does not hold | the subsection's standing assumption 2 < γ (line 1477) | - |
| t08 | h14 (normalisation) | does not hold | the adjoint identity and the sign convention | adjoint identity and density, CLEAN |

## Against the protocol

- **False certification: 0/8**; over all three stages **0/23** (95% one-sided bound about 12%).
- **Verdict errors: 0/8**; every run named the place where the refutation lives, including the
  ones that sit hundreds of lines from the quoted step. The plants still did not reach the path the
  stage targeted (a wrong verdict, then a certificate), so that path remains **untested**.
- Skill loaded 8/8; Lean used to certify the refutation in 6/8, all CLEAN, one partial and labelled.

## Reading

Planted false findings written by a model, even ones designed to need distant context, are
refuted by the same model reading the whole paper in one to two minutes. The writer and the
checker share what they can see; a finding hard enough to fool the checker may need information
outside the paper (a convention of the field, a result from another paper) or a longer paper than
these. L5 closes here: no false certification in 23 tries, and the agents certify whichever side
their reading supports. The open risk is the one this design cannot reach: a wrong verdict on a
real paper, with a certificate built on it.
