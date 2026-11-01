# Protocol C2: comparing-papers with a budget extractor that works

Written 2026-10-31, before the extractor change, any C2 plant or any C2 run. The researcher chose
to follow C1 with "C2, fix the extractor" and asked to move forward without a question round; the
defaults below are Claude's and are marked as such for review.

## Why

In C1's test the script ran in every skill run, yet its `training_scale` axis computed nothing:
the competitor's value was empty in 5 of 6 papers, once it took a pretraining corpus for the
budget, and the ratio note never fired. The skill arm's +16.7 points (p = 0.375) cannot be owed to
the arithmetic the skill exists for. The recurring lesson (surveying v3.2, proofs L7) is that
structure the agent must answer helps and prose does not; C2 tests the structural version.

## Change (branch `compare-budgets`)

- `training_scale` becomes a list of **every training-budget statement** in each paper, converted
  to examples seen where the text allows it: steps x batch (also from hyperparameter table rows),
  epochs x dataset or epoch size, rounds x items per round, stated totals ("N samples seen",
  "trained on N examples"). Each entry keeps its quote, section and arithmetic. Tokens stay a
  separate unit.
- The report puts the draft's and the competitor's lists side by side and computes the ratio for
  each pair of entries; it states no verdict (the skill's rule: evidence, not judgement).
- SKILL.md asks the agent to answer, for each draft budget that concerns the competitor (directly,
  or through "baselines", "the base paper", an initialisation or a released checkpoint), whether
  it matches the competitor's own figure.
- Offline tests keep passing; stdlib only.

## Dev (not test material)

C1's 14 scale plants and their papers: round 1 d2, d3, d6, d7; round 2 d3, d6 (both, including the
one amendment 4 excluded), d7; test t8, t9, t11, t18, t24, t41. **Dev gate** before any C2 test
run: on at least 11 of 14 cases the report lists the planted draft budget with the correct count
and the competitor budget it contradicts, with their ratio. The extractor may be tuned on these
papers; they are not used for scoring C2.

## Test material

Fresh pairs from the resumed C1 screen (same pool, same order, drafts after the first 30), same
eligibility, disguise, memory probe and plant procedure as C1. Scale plants only, under C1
amendment 2's rule (no competitor name in the planted lines, budget in other units, shortfall to
at most one third visible only after arithmetic), one per pair. **8 pairs** (Claude's default).
A pair that cannot host a valid plant is skipped in screening order; if fewer than 8 are found
after the screen stops, the shortfall goes to the researcher before any run.

## Arms

| arm | what it is |
|---|---|
| `fixed` | comparing-papers on branch `compare-budgets`, frozen when test cases are built |
| `current` | comparing-papers at dc96f22 (C1's skill) |
| `without` | the same agent, no skill |

C1's prompt, tools, network grants, limits and contamination rule. **3 runs per arm per pair**
(Claude's default): 72 runs, roughly $55.

## Criteria

- **Primary:** recall, fixed minus without, at least +0.15 (24 runs per arm; McNemar on paired
  runs reported).
- **Secondary:** fixed minus current at least 0; false issues per run, fixed at most 1.5 x
  without (C1's adjudication, arm-blind); cost per run, fixed at most 1.3 x without.
- Mechanism (reported): in how many fixed runs the report lists the planted budget and the
  competitor's, and whether the agent's answer uses them.

| Outcome | What follows |
|---|---|
| primary and secondaries met | merge `compare-budgets`; SKILL.md measured line |
| primary met, fixed below current | read the traces before merging |
| primary not met, extractor fired in most runs | the arithmetic does not change what the agent finds: discuss reducing the skill with the researcher |
| primary not met, extractor did not fire | report the extractor's misses; no merge |

Hit rule as in C1 (located on the plant span +-3 lines, then content: names the budget and the
direction), verdicts arm-blind.
