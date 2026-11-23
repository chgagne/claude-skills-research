# Results S2: rewritten descriptions for the process skills

2026-11-23. Protocol: `PROTOCOL-S2.md` (+ amendment 1). New = branch `process-triggers` fed1737 (only the
description lines of collaborating-on-research and using-drac-clusters change), old = S1's text, without = no
skill, all run the same day on S1's 16 scenarios × 3, plus the 5 drac scenarios with real cluster names (174 runs,
no contamination). Same judge as S1 (5 flips in 174).

## Verdict

**The pre-registered rule is met, merged.** The rewritten descriptions make the skills load in 34 of 48 runs,
against 22 for the old text (collaborating-on-research 14/15 vs 8/15, using-drac-clusters 9/15 vs 2/15), and
passes rise to 39/48 against 35/48. The case the change was aimed at flips: **r5, a fix that changes what the
arms can be compared on, 3/3 with the new description (it asks before syncing) against 0/3 for the old one and
0/3 without a skill.** The real cluster names confirm S1's bench artifact: with "Narval" the old drac
description loads in 12 of 15 runs, against 2 of 15 with "clusterX".

## Numbers

| | new | old | without |
|---|---|---|---|
| skill loaded | **34/48** | 22/48 | — |
| pass, all 16 | **39/48** | 35/48 | 38/48 |
| pass, real incidents | **23/24** | 18/24 | 17/24 |
| pass, skill-blind | 16/24 | 17/24 | **21/24** |
| collaborating-on-research (load; pass) | 14/15; 12/15 | 8/15; 9/15 | —; 12/15 |
| running-cluster-experiments (load; pass) | 11/18; 17/18 | 12/18; 16/18 | —; 16/18 |
| using-drac-clusters (load; pass) | 9/15; 10/15 | 2/15; 10/15 | —; 10/15 |

Named drac copies (new / old): load 15/15 vs 12/15, pass 11/15 vs 11/15.

Rule: (1) load new > old pooled and for both changed skills, met; (2) pass new 39 ≥ old 35 − 2, met.

## Where the skills still lose to the bare agent

- **b8 (end-of-session record): new 0/3, old 0/3, without 3/3.** The skill-blind rubric expects STATUS.md to say
  a job is "still running" and to record the PI's decision there. With the skill loaded, agents mark the job
  "UNVERIFIED" (the skill's rule: verify tracked state, do not assert it from a note), and put the PI's decision
  in CLAUDE.md or the journal (the skill's rule for standing decisions). Mostly a clash between conventions, not
  worse judgement. One run invented a timing inconsistency, which is a real error.
- **b4 (heavy job on a busy login node): new 1/3, old 2/3, without 3/3.** Every arm submits the job properly;
  the skill runs lose points arguing about a scratch file quota. Small, and partly a judge call.
- So the skill-blind half favours the bare agent (21 vs 16/24). Part of that is the bench: those rubrics were
  written without the skills' conventions.

## Replication of S1

- **r3 (24 h timeouts): not replicated at S1's size.** S1: skill 3/3, bare 0/3. S2: old 1/3, new 2/3, bare 1/3.
  Pooled, skill 6/9 vs bare 1/6. Same direction, much noisier. RESULTS-S1 is corrected in place.
- r5 failed in every arm of S1 and in old/without here. It passes only with the new description.
- The ceiling scenarios stay at ceiling in every arm.

## Reading

A description that names the situations, not only the domain, decides whether these skills are used, and on
r5 it decides the outcome. Where the bare agent already knows the right move, loading the skill adds nothing,
and the collaboration skill's own conventions (UNVERIFIED, decisions filed in CLAUDE.md) can cost points on a
rubric written without them.

Spend: 174 runs ~$24, judge ~$5.
