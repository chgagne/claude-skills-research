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

## Stage 2 design (2026-10-25, confirmed with the researcher before any case was built)

**Papers:** the three proof defects among the five that survived the memory probe:

| Paper | Documented defect | Hit spans (source lines, each widened by 3) |
|---|---|---|
| 2505.02888v1 | withdrawn: error in Theorem 2 (Unbounded Growth) and Lemma 2 (compression-gain lower bound) | `lem:gamma_min` 228-236; `thm:diverge` 646-655; its proof, Appendix B, 1213-1234 |
| 0801.4243v1 | withdrawn: "U in Lemma 2 is not a subspace" | `lemma gr` and its proof 237-273 |
| 1905.10936 | Lemma 2 error bound wrong for decreasing learning rates (correction 2003.04706) | `lemma:wm_error_bound` 524-527; `lemma:error_bound` and its proof 1831-1890 |

**Arms:** the reduced skill on main (`verifying-proofs` at the commit that adds this section)
against the same skill plus the Lean step (branch `lean-step`, 2e4f829). Both arms get the same
scaffold: a copy-on-write clone of the Lean toolchain and of a clean Mathlib project at
`~/.lean-project` in the run's HOME (the sandbox cannot read outside it), so only the skill text
differs. Prompt, tools (no web), limits and scoring as P1. 2 runs per paper per arm: 12 runs.

**Hit:** a flag whose quote locates inside a hit span. **Reported:** hits per arm (out of 6), other
flags per run, Lean certificates produced (count, `lean-certify.py` status), cost and time per run.
Stage 2 is reported beside the stage-1 rule, not inside it.
