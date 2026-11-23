# Results C3: an axis answer table to widen comparing-papers reviews

2026-11-22. Protocol: `PROTOCOL-C3.md` (+ amendment 1). Arms frozen: wide = branch `compare-axes`
6874764, live = main 5107b1b (C2's merged skill), without = no skill; all three run the same day on
C2's 8 scale pairs, 3 runs each (72 runs, no contamination). Every issue adjudicated arm-blind
with C2's prompt (3 subagent batches); Claude content-checked the 68 on-span issues for hits, and
checked every "false" and the contested verdicts against the sources (5 corrections, below).

## Verdict

**Primary not met: the answer table did not widen the reviews at all. No merge.** Wide raised 0.38
other real issues per run, live 0.29, the bare agent 0.88 (bar: wide ≥ 0.78). Counting only real
issues that are *not about the planted budget*, the gap is total: **wide 0, live 0, bare 11 (0.46
per run)**. Budget recall held: wide 22/24, live 23/24, bare 12/24 (wide vs bare McNemar 10 vs 0,
p = 0.002), so C2's gain replicates on a second day.

## Numbers

| per run | wide (answer table) | live (C2 skill) | without |
|---|---|---|---|
| plant recall | **22/24** | 23/24 | 12/24 |
| other real issues (scorer) | 0.38 | 0.29 | 0.88 |
| of which not about the plant | **0.00** | **0.00** | 0.46 |
| false issues | 0.04 | 0.04 | 0.08 |
| judgement calls | 0.71 | 0.75 | 1.08 |
| issues | 2.0 | 2.0 | 2.5 |
| cost | $0.59 | $0.53 | $0.53 |
| checker run to OK | 21/24 | — | — |

Criteria: (1) breadth 0.38 vs bar 0.78 **not met**; (2) recall 22 ≥ 21 and +0.42 over bare, met;
(3) false 0.04 ≤ 0.12, met; (4) cost 1.11x ≤ 1.3x, met; (5) checker 21/24 vs 22, **not met** (three
runs never ran it; the four sandbox resolution failures were retried and are not the cause).

Replication of C2 (2026-11-01, same pairs): recall fixed 21/24, bare 13/24; other real issues fixed
0.25, bare 0.58. C3's same-day numbers point the same way, on both measures.

## Why it did not work

The wide runs filled the table honestly: on the three papers where the bare agent found other real
issues, most rows read "not stated" or "not checkable", and the few "differs" rows were the planted
budget. The bare agent's 11 non-plant findings are not on any of the table's seven axes:

- c116 (3 runs): the draft's "paired comparison" of a fine-tuned model and its base changes both the
  weights and the control inputs, so the attribution to fine-tuning is confounded.
- c135 (4): the draft groups the competitor with "single-benchmark fine-tuning", but it trains on
  five pooled sources; the draft's own table contradicts its transfer claim.
- c140 (4): the competitor's input column omits its mask, text prompt and retrieval base; a column
  winner is left unbolded; the draft calls its method "local integration" when it is global.

These are claims the draft makes *about* the competitor, in sentences that cite it. The same lesson as
proofreading W3 (a category form did not move coverage) and the opposite of R5 (one row per float
did): **a form listing generic categories is filled and changes nothing; a form listing the paper's
own objects is what moves coverage.** The object here would be every draft sentence that cites or
describes the competitor.

## Adjudication notes

- 102 non-hit issues in 3 batches: 37 real, 4 false, 61 judgement after corrections (batches as
  returned: 40 / 5 / 57).
- Corrections (in `private/c3/adj/verdicts9_claude_corrections.json`): one "real" was false (the
  competitor does report EPDMS, `tab:main_epdms`; another batch had judged the twin issue false), and
  four c148 zero-shot-label issues set to judgement (eight near-identical issues had come back false,
  real and judgement across batches; the competitor keeps overlapping datasets but excludes evaluation
  images, so the label is a choice the texts cannot settle). Every remaining "false" was checked
  against the sources and upheld.
- Hits (Claude, arm-blind, C1 rule): 57 of 68 on-span issues; "matches neither reading" without a
  direction is not a hit, as in C2.
- Most of the "real" non-hit issues in every arm are about the plant (consequences of the
  under-trained baseline, or near-misses without a direction). That inflates the bare arm's
  pre-registered breadth number, because the bare agent misses the plant more often; the
  plant-excluded count above removes it.

Spend: 72 runs ~$40, 4 dev runs ~$2, adjudication ~$5 in subagent usage.
