# Protocol L2: what Lean 4 + Mathlib is worth to verifying-proofs

Written 2026-10-25, before any flag was sampled or any run. Design settled with the researcher the
same day (journal, "Decision record: L2"). Frozen by the commit that adds it.

## Question

Should the skill develop Lean capacities? Two values are measured, staged:

- **(P) Reliable certification.** Given a finding an agent raised on a real paper, can a Lean agent
  certify it when it is real, without ever certifying one that is false?
- **(D) Discovery** (stage 2, conditional). Does an agent with Lean find documented proof defects
  that the bare agent misses?

## Stage 1

**(P) material.** The 161 unplanted flags raised in P1 and P2 runs (`private/runs_*.jsonl.gz`),
deduplicated into distinct claims (same paper, overlapping located lines, same defect; done by a
script, then merged by hand where two quotes name the same step). 12 distinct claims drawn with
seed 20261025, at most 5 from one paper.

**Ground truth first.** Each drawn claim is adjudicated by Claude against the paper before any Lean
run: `real` (the step as written is false or its licence is missing, with a witness), `false` (the
step holds; the flag is wrong), or `unclear` (cannot be settled in about 20 minutes). Verdicts and
reasons are committed (by hash in the journal) before stage 1's Lean runs.

**Lean runs.** One opus agent per claim, in the Lean project, with the paper and the flag (quote,
claim, problem) but not the verdict: certify the flag (prove the step false, or the needed
condition necessary) or certify that the step holds, or report that it could not; 30-minute cap.
Claude reviews every certificate for fidelity (statement against the LaTeX, axioms, no `sorry`).
A certificate on an unfaithful statement counts as **not certified** and is listed.

**(D) memory probe.** For the six documented-defect papers in the local acceptance corpus, the
model without tools is asked whether the paper has a known error and where. A paper whose defect
location it names is excluded from (D).

## Decision rule (researcher's choice, "any reliable use")

**Develop Lean capacities** if, on the `real` claims of stage 1, Lean certifies at least 50% within
the cap **and** certifies none of the `false` claims. Otherwise: do not develop; delete branch
`lean-step` and record why. `unclear` claims are reported, not counted. If no `false` claim is
drawn, the second condition is untested and is reported as such; the rule is then read on the first
condition alone, with that caveat.

Stage 2 (D) runs only if at least 2 documented-defect papers survive the memory probe and budget
remains; its design (bare vs bare + Lean on those papers) is confirmed with the researcher first.
Its result is reported beside the rule, not inside it.

## Budget

About $150 in total; stage 1 about $60. Usage gate as usual (5h <= 0.40, 7d <= 0.75).
