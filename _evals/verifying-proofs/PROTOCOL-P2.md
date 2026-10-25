# Protocol P2: the reduced verifying-proofs skill, non-inferiority on P1's cases

Written 2026-10-25, before any run. Decided with the researcher the same day (after P1: no gain over
the bare agent): reduce SKILL.md and check it quickly. Frozen by the commit that adds it.

## Question

Does the reduced SKILL.md (branch `proofs-reduce`, 16a1102, 86 lines: a reading method, the hygiene
pass, reporting rules; the removed text verbatim in `reference/design-notes.md`) do at least as
well as the full skill P1 measured (9924de7)?

## Cases and arms

- **Test:** P1's four test cases (t1, t3, t5, t8; one dropped-hypothesis plant each). Reduced skill,
  2 runs each (8 runs). The full skill's and the bare agent's results are P1's (8 runs each).
- **Dev, reported only:** the two tightened dev hypothesis cases where the bare agent missed
  (d2_hypothesis_t 1/2, d3_hypothesis_t 0/2). Reduced and full skill, 2 runs each (8 runs).

Same model, tools (no web), prompt, scaffold, limits and gate as P1. 16 runs, about $30.

## Criterion (all must hold, on the test cases)

1. Planted recall at least 7/8 (the full skill's 8/8 minus one hit).
2. Other flags per run at most 1.5 x the full skill's (1.25), i.e. at most 1.88.
3. Mean cost per run at most 1.1 x the full skill's ($1.89), i.e. at most $2.08.

Reported beside it: dev recall for reduced, full and bare; script runs; tool calls to
`reference/`.

## Reading

- All met: the reduction is merged to main; publishing (push) is asked separately.
- Any failed: no merge; the traces are compared with the full skill's and the fix is decided with
  the researcher.

Caveat written before the runs: the reduced text was written after reading P1, including the dev
hypothesis plants the bare agent missed (a condition inherited through "Under the above"); its
reading method names "a condition used but never stated" and "a cited result applied outside its
hypotheses". The dev comparison may therefore flatter the reduction; the test criterion does not
depend on it, but the test plants were also seen.
