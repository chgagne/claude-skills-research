# Protocol P1 results: no measurable gain (2026-10-24)

Protocol: `PROTOCOL-P1.md` (9924de7, amended c924acb, 8a497a9, c799b51, b1aef91), each amendment
committed before the runs it governs. Model claude-opus-5-5, tools Read, Write, Edit, Bash, Glob,
Grep, Skill in both arms, no web tools. Skill frozen at 9924de7 (copy verified identical to the
live skill at launch). Scores: `results/P1-2026-10-24.json`.

## Calibration (dev, bare agent only)

| Plant type | First round (dev, 4 papers) | Tightened round (amendment 2) | Kept? |
|---|---|---|---|
| inequality | 8/8 | 8/8 | dropped |
| algebra | 8/8 | 6/8 | dropped |
| dropped hypothesis | 5/8 | 3/6 (3 plants; none valid in one paper) | kept, at the bar |

46 bare runs, $1.5 per run, none contaminated. The tightened rule put the broken step in the middle
of a displayed chain of at least three relations with the final bound unchanged; the bare agent
still found every inequality slip.

## Test

One tightened dropped-hypothesis plant per test paper (amendment 4). Four of the eight test papers
yielded a valid plant; the others had no displayed chain whose middle step uses an unrestated
statement hypothesis, or (one paper) only a candidate that contradicted the sentence introducing
its lemma.

| Case | Paper | Plant |
|---|---|---|
| t1 | 2609.01415 | `gamma > 0` weakened to `gamma != 0` (sequence boundedness lemma) |
| t3 | 2610.12288 | boundary separation of the base point dropped (Newton existence theorem) |
| t5 | 2609.33154 | `alpha^2 <= 1/4` on the active set weakened to `< 1` (occupation estimate) |
| t8 | 2607.05735 | `beta > 0` weakened to `beta != 0` (Gibbs multiplier lemma) |

| | Skill (9924de7) | Without |
|---|---|---|
| Planted recall | **8/8** | **8/8** |
| Other flags per run | 1.25 | 1.63 |
| Mean cost per run | $1.89 | $1.76 |
| Script ran | 2 of 8 | - |

**Verdict: criterion 1 not met** (skill minus bare = 0, bar +0.15). Criterion 2 met (1.25 against a
bar of 2.44). No run discarded: the only tool calls that matched the contamination filter were the
skill's own script at its frozen install path.

## Other flags

All 23 other flags came from t8. The 20 drawn (seed 20261023) were adjudicated arm-blind against the
paper: **20 of 20 are real defects of the original paper**, none caused by the plant, none false
alarms. They are 8 distinct slips (a cover-argument constant giving 3Delta/8 for Delta/4, a
per-coordinate tube bounded as if Euclidean, a within-group error term dropped from a spread
recursion, `Theta <= Delta` not giving `(sqrt(eps_-) + Theta)^2 <= eps_- + Delta`, an introduction
claiming O(2^d) where the theorem gives poly(2^d), a theorem applied at one width where it needs all
large widths, a product of two bounded factors bounded by one factor, a Lipschitz constant that
depends on the width). Among the 20 drawn, skill runs raised 7 of the 8, bare runs 7 of the 8.

## Reading

Per the protocol: the skill does not beat the bare agent on this task, and SKILL.md now says so.
What to change, or whether to reduce the skill as was done for verifying-bibliography, is for the
researcher. Two observations for that decision:

- The bare agent is strong at this task: planted single-step errors of all three types, and real
  slips in an unplanted paper, which both arms found at the same rate.
- Bare recall on tightened hypothesis plants was 3/6 on dev and 8/8 on test. The test plants may be
  easier (three of the four are sign conditions, `> 0` weakened), or dev was unlucky; with 6 and 8
  runs the two cannot be told apart.

## Limits

Four test cases, 8 runs per arm: one hit moves recall by 0.125. Hits are scored by location only.
Other flags were adjudicated only where they occurred, which was one paper.
