# Protocol L7: a closure check in the reading method

Written 2026-10-28, before any run. The researcher chose to add the line (journal 2026-10-26/28).

## Why, and the caveat

0801.4243 was withdrawn because "U in Lemma 2 is not a subspace". No run found it in 8 tries (L2
stage 2, L3, L4); the defect holds under the lemma's hypothesis (Lean, `lean/L6/`). The paper
writes "Consider the linear subspace U := ..." and every run checked the steps after it, never the
closure. Branch `proofs-closure` (565e20c) adds step 4 to the reading method: every object the
paper calls a subspace, ideal, group, cone or convex set, check closure with two elements; a
condition whose quantifier range depends on the element is where it fails.

**The line is written from this one paper**, down to the hint about element-dependent quantifier
ranges. Finding the defect here shows the line is read and acted on, not that it generalises.

## Runs

The skill at 565e20c, frozen; L4's scaffold, prompt, tools (no web), limits (100 turns, 40 min,
$20 cap). 0801.4243 twice; 2505.02888 and 1905.10936 once each (regression). 4 runs.

## Measures and reading

- **Target:** the 0801.4243 documented defect found, read by content (a flag saying U is not
  closed under addition, or not a subspace, or an argument that needs U to be one fails), in at
  least 1 of 2 runs. Baseline 0/8.
- **Regression:** on 2505.02888 and 1905.10936 the documented defect still found (L4 found both),
  other flags per run at most 1.5 x L4's on the same paper, cost per run at most 1.3 x L4's.
- Reported: closure checks the runs did and what they concluded, Lean use.

Target and regression met: merge, with the caveat in SKILL.md's measured section. Target missed:
the traces are read before any rewording, branch unmerged. Regression missed: discuss with the
researcher.

## Budget

About $4.
