# Protocol C1 results: scale plants, skill +16.7 points, the script's scale note never fired (2026-10-30)

Protocol: `PROTOCOL-C1.md` (8edd938, amendments 1-5 up to adc10f5). Skill frozen at dc96f22.
Model claude-opus-5-5 in both arms; same tools and per-host network grants; no WebSearch.
**Status: primary criterion scored. The secondary criterion (false issues per run) is not yet
adjudicated.**

## Calibration (bare agent only, dev pairs 2, 3, 6, 7)

| Round | Rule | quote | seeds | scale | Cost |
|---|---|---|---|---|---|
| 1 (amendment 1) | plant names the competitor | 8/8 | 8/8 | 8/8 | $21.8 |
| 2 (amendments 2-4) | no name in the planted lines; scale in other units; quote change <= 1 point | 8/8 | 5/8 | 3/6 | $21.4 |

When the agent is told which paper to compare with, it catches any misstated number or seed count
it can look up there, even a 0.9-point change in a copied table cell. It misses only budgets
stated in other units, where the shortfall shows after multiplying. Quote and seeds were dropped.
Scale was kept at 3/6 after one plant was excluded, because it repeated a gap the draft already
had (amendment 4).

## Test (scale only, 6 pairs, 3 runs per arm)

| Case | skill | without |
|---|---|---|
| t8 (budget as steps x batch vs epochs x epoch size) | 3/3 | 3/3 |
| t9 (batches x batch size vs total pairs) | 3/3 | 3/3 |
| t11 (prompts over the run vs prompts per round x rounds) | 1/3 | 0/3 |
| t18 (steps x batch vs epochs x train split) | 3/3 | 2/3 |
| t24 (samples seen vs epochs x dataset) | 1/3 | 1/3 |
| t41 (samples vs steps x batch) | 3/3 | 2/3 |
| **Recall** | **14/18 = 0.778** | **11/18 = 0.611** |
| Cost per run | $0.73 | $0.78 |

- **Primary: met, direction only.** Skill minus bare is +16.7 points, against a bar of +15. Runs
  paired by index give 4 skill-only and 1 bare-only discordant pairs: exact McNemar p = 0.375.
  The stage-2 trigger written in the protocol (primary met, p > 0.10) calls for 8 more test pairs.
- Hit rule applied strictly, as in amendment 4. A hit names the quantity and the direction of the
  discrepancy. Five on-span issues said only that the figure "does not match" or is "wrong"; they
  are not counted. Verdicts were given arm-blind (`private/c1/verdicts_test_primary.json`). Under a
  lenient reading the skill gains t18 and t24 (one run each) and the bare arm gains t41 (one run).
- No contamination. No run fetched the draft's arXiv id.

## What produced the difference

The script ran in all 18 skill runs, yet its `training_scale` axis computed nothing:
- the competitor's value was empty in 5 of 6 cases;
- for t41 it took the pretraining corpus ("1.2M robot episodes") instead of the 60K x 128
  post-training budget;
- the draft's value was found in 1 of 6 cases (t24, "3.6M examples (stated)");
- the ratio note, the arithmetic the skill exists for, never fired.

The skill arm's hits came from the agent reading the competitor's training section itself. Any gain
is therefore owed to the SKILL.md guidance (the axes table makes training scale something to check)
or to noise, not to the computed note. This matches surveying-literature v3.2, verifying-proofs L7
and the reductions in D/P2: the script's measured contribution is small, and what helps is the
text that tells the agent what to look at.

## Open

- Secondary criterion: 189 off-span issues to adjudicate arm-blind (real, false, judgement).
- Stage 2: the protocol's trigger asks for 8 more scale pairs. The first 30 screened drafts are used
  up (C1 screening stopped at 30); more would need resumed screening.
- The extractor misses on all six test papers: budgets stated as steps x batch in a hyperparameter
  table, per-round prompt counts, "N epochs on M samples" split across sentences. Fixing them now
  would tune on test material.
