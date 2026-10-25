# Probe L1 results: Lean settled both statements, in minutes (2026-10-25)

Design: `PROBE-L1.md` (4870be1). Lean 4.36.0-rc1, Mathlib (cache), one opus agent per statement,
the full planted paper, not told the lemma was edited, no web. Both Lean files recompiled by Claude;
`#print axioms` shows only `propext`, `Classical.choice`, `Quot.sound`; no `sorry`.

| | d2 `lem: rn^q` (2607.06252) | d3 `lem:D` (2607.25785) |
|---|---|---|
| Bare agent in P1 (2 runs) | 1/2 found | 0/2 found |
| Agent's verdict | **fails** | holds under thm:tuned's hypotheses; the preamble's list omits `G_s <= overline G_sigma`, which step 3 needs |
| Lean | refutation proved: for every q > 1 an admissible f makes the expectation infinite | the lemma proved **with** `G_s <= overline G_sigma` (the original statement) |
| Fidelity (checked by Claude) | specialised instance (H = R, Gaussian prior, F = {g0}); class assumption and joint law built as in the text; constants left abstract, covered by "every q > 1" | Lambda >= 1 taken as a hypothesis (the paper's Lambda satisfies it); substitutions by hand as in eq:threesubs; probabilistic content (eq:master) outside the lemma |
| Time, compiles | ~15 min, 4 | ~25 min, 7 (55 s per compile) |

**Success criterion met** (a certified, faithful refutation of at least one statement): d2.

**d3 was a flawed plant.** The edited sentence still points to thm:tuned's hypotheses, which keep the
condition; the agent read it that way, found the gap informally, and certified the original lemma.
Correction notice in `RESULTS-P1.md`. In effect, d3 gave a stage-2 data point for free: Lean
confirmed a true research-level lemma (an explicit constant-propagation bound) in 25 minutes.

## What this shows and does not

- Lean + Mathlib is usable on this material: a measure-theoretic counterexample (Gaussian moments,
  product measures with densities) and an explicit constant-propagation bound, each in under half an hour.
- Both agents also reasoned correctly in prose; the Lean file added certainty, not discovery. Two
  statements, no comparison with the bare agent on the same budget (`PROBE-L1.md`).
