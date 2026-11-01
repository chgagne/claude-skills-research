# Protocol C2 results: the budget extractor, +33 points over the bare agent (2026-11-01)

Protocol: `PROTOCOL-C2.md`. Arms frozen: fixed = branch `compare-budgets` 14ffa09, current =
dc96f22 (C1's skill), without = no skill; `_shared` 14ffa09 in every arm. Model claude-opus-5-5,
C1's prompt, tools and network grants. 8 fresh scale pairs x 3 runs x 3 arms = 72 runs, $39.5, no
contamination, no format failure.

## Material

The resumed C1 screen (1,825 more drafts, 50 with a candidate pair, 136 pairs) gave 18 scale
candidates in screening order, one per draft, benchmark and dataset competitors skipped. Plants
under C1 amendment 2's rule (no competitor name in the planted lines, budget in other units,
shortfall to at most one third visible only after arithmetic), each checked by Claude against both
sources. 8 valid in order: 108, 115, 116, 135, 140, 148, 156, 161. No plant or rejected: 54, 93,
109, 133, 134, 144, 152, 153 (`private/c2/plants/decisions.json`). Memory probe 36/36 "don't know".

## Dev gate (before any test run)

13/14 on C1's scale cases (`private/c2/dev_check.py`). The miss states its cap as "we set this
number at 200".

## Primary

| Case | fixed | current | without |
|---|---|---|---|
| c108 (50K clips vs 160K) | 3/3 | 3/3 | 3/3 |
| c115 (800 scenes vs 180 steps x 16) | 0/3 | 0/3 | 0/3 |
| c116 (9K clip samples vs 9,420 x 3 epochs) | 3/3 | 2/3 | 2/3 |
| c135 (250 steps x 128 vs 5 epochs x 27K) | 3/3 | 3/3 | 3/3 |
| c140 (8K iterations x 32 vs 300 epochs x 4,040) | 3/3 | 2/3 | 0/3 |
| c148 (0.5B tokens/rank vs 50K steps x 32K) | 3/3 | 3/3 | 2/3 |
| c156 (6.4M samples vs 200K steps x 128) | 3/3 | 0/3 | 0/3 |
| c161 (0.25 epochs vs 2 x 10K iterations x 8) | 3/3 | 3/3 | 3/3 |
| **Recall** | **21/24 = 0.875** | 16/24 = 0.667 | 13/24 = 0.542 |

**Primary met: fixed minus without = +33.3** (bar +15). Runs paired by index: 8 fixed-only, 0
without-only discordant pairs, exact McNemar p = 0.008. Hit rule as in C1: located on the plant
span, then named budget and direction (the competitor's larger figure counts as direction); five
on-span issues with no direction ("cannot be derived", "matches nothing") are not counted.
Verdicts arm-blind (`private/c2/verdicts_test_primary.json`).

## Secondary

| per run | fixed | current | without |
|---|---|---|---|
| false issues | 0.04 | 0.12 | 0.12 |
| real issues besides the hit | 0.25 | 0.83 | 0.58 |
| judgement calls | 0.75 | 1.17 | 1.54 |
| cost | $0.51 | $0.59 | $0.55 |

- fixed minus current: +20.8 (bar >= 0): met.
- false issues: fixed 0.04 vs without 0.12 (bar 1.5x): met. 130 non-hit issues adjudicated
  arm-blind by subagents; Claude checked every "false" (7) against the sources and upheld them.
- cost: fixed 0.93 x without (bar 1.3x): met.

## Sensitivity and what it costs

- **By content** (counting 20 issues that name the plant with its error but quote a neighbouring
  line): fixed 21/24, current 20/24, without 14/24. The gain over the bare agent holds (+29); the
  gain over C1's skill is mostly that the fixed arm quotes the planted line itself.
- **Narrower reviews.** The fixed arm raises fewer issues of every other kind (0.25 real per run
  against 0.58 bare and 0.83 for the current skill). The "answer each budget" step focuses the
  review on budgets. The protocol does not measure breadth; it is a cost of the change.

## Mechanism

The extractor listed the planted budget in 5 of 8 drafts (108, 116, 135, 140, 161). It missed "800
scenes" (the item word), "0.5B packed tokens per rank" (tokens are a separate unit) and "the fourth
row is trained for 6.4M samples" (c148, c156, c115). The fixed arm still found c148 and c156 in
every run (c156: 3/3 against 0/3 in both other arms): the competitor's budget list and the SKILL.md
instruction to answer each budget carry part of the gain. c115 was missed by every run of every
arm.

## Outcome

Primary and secondaries met: `compare-budgets` merged, SKILL.md measured line updated. This is the
first structural change in the eval series that measurably beats the bare agent on fresh material,
and the lesson repeats: a list the agent must answer, not a prose reminder.
