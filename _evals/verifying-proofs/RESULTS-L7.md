# Protocol L7 results: the closure check was read and not applied (2026-10-28)

Protocol: `PROTOCOL-L7.md` (9c7791b). Skill at 565e20c (branch `proofs-closure`: step 4 of the
reading method, check closure of anything the paper calls a subspace, ideal, group, cone or convex
set). 4 runs, no web, $2.73 in total. Every run loaded the skill; the step-4 text is in every trace.

| Paper | Runs | Documented defect (by content) | Other flags | Cost/run | L4 for comparison |
|---|---|---|---|---|---|
| 0801.4243 (target) | 2 | **0/2** | 5, 6 | $0.29, $0.46 | 0/1, 6 flags, $0.41 |
| 2505.02888 | 1 | found (`thm:diverge`, `lem:gamma_min`) | 20 | $0.86 | found, 18, $0.66 |
| 1905.10936 | 1 | found (constant step size) | 7 | $1.12 | found, 4, $1.44 |

## Against the protocol

- **Target missed.** Neither 0801.4243 run mentions closure, in the report or in its reasoning.
  One run found a different, real defect in the same definition: as written U is not contained in
  K[X]_{2k} (polynomials of degree above 2k satisfy the condition vacuously). The documented one,
  U not closed under addition (certified in `lean/L6/`), stays at 0 of 10 runs.
- **Regression:** documented defects still found on both papers; 1905.10936 has 7 flags against 4
  (bar 6), the three extra are real slips earlier runs also reported (an `=` for `\le`, `m` for
  `M`, an unstated unbiasedness); 2505.02888 cost $0.86 against $0.66, 1.30 times (bar 1.3).

## Reading

The instruction is in context and is not executed: the agents read the definition of U, accept the
paper's word "subspace", and check the steps that use it. A fourth checklist item does not change
what the reading attends to; the earlier finding that prose instructions are followed less than
structure (surveying-literature v3.2, the optional Lean step in L2) holds here too. Branch
`proofs-closure` stays unmerged. A structural route (the hygiene script listing every "subspace",
"ideal", "group", "convex" claimed of a defined set, so the agent has to answer each) is the
candidate if this is pursued; it would need its own measurement on papers other than this one.
