# Protocol R2: does reviewing-paper-sources make reviews consistent?

Written 2026-11-04, before any R2 case or run. The researcher reframed the question after R1
(`../SYNTHESIS-2026-11.md`): the skill should be judged as a way to produce a standard, complete,
repeatable review, not as a way to find one more planted defect. The design and thresholds below
are Claude's defaults; the researcher asked to plan and execute without a question round.

## Question

Across repeated runs on the same draft, do reviews written with the skill cover the same ground,
reach the same findings and the same verdict more often than reviews written without it, without
finding fewer real errors?

## Material

Six disguised, memory-probed drafts from the C2 pool, **without plants**: 54, 93, 134, 179 (R1
dev; their original text) and 109, 152 (never used in a run). Sources unchanged from
`_evals/comparing-papers/private/c2/drafts/`.

## Arms and runs

| arm | what it is |
|---|---|
| `skill` | reviewing-paper-sources as frozen for R1 (cc5bb1d, unchanged since), `_shared` installed |
| `without` | same agent, no skill |

claude-opus-5-5, tools Read, Write, Edit, Bash, Glob, Grep, Skill, **no web tools**, 40 min, 150
turns. **4 runs per arm per draft: 48 runs** (about $75). Prompt identical in both arms: R1's
prompt, with the JSON block extended to

```json
{"recommendation": "ready|minor revision|major revision|not ready",
 "top_concerns": ["draft_quote of the most important issue", "second", "third"],
 "issues": [{"draft_quote": "...", "problem": "...", "severity": "critical|major|minor"}]}
```

## Measures (all within a draft, across its 4 runs, then averaged over drafts)

1. **Finding stability (primary).** Two issues from different runs match when their located
   `draft_quote` spans are within 3 lines (`_harness/consistency.py` rule). Pairwise agreement =
   matched issues / all issues over the 6 run pairs. Also reported: the core share (findings,
   clustered by span, present in at least 3 of 4 runs, over all distinct findings).
2. **Coverage (primary).** A fixed checklist of 14 review items, written below before any run,
   judged per review (`review.md` plus the final message) by a separate Sonnet 5.5 call that sees
   no arm label, with skill-specific vocabulary masked (skill names, "Mode A/B", `review-assets`).
   Coverage = items addressed / 14. Reported: mean and the within-draft standard deviation.
3. **Verdict stability.** Share of run pairs with the same `recommendation`; overlap of
   `top_concerns` (span rule).
4. **Guard: real errors found.** A gold list of real natural errors in drafts 54, 93, 134, 179,
   built and checked against the sources **before reading any R2 output**, from the R1 plant
   subagents' natural-inconsistency notes and the R1 calibration findings
   (`private/r2/gold_natural.json`). Recall per run, judged by content, arm-blind.
5. Reported: issues per run (mean, range), cost and time per run.

Checklist (items 1-9 are generic referee-form items; 10-14 come from the skill's own
"Findings that recur" list and therefore favour it; reported separately as well as pooled):

1. states the paper's contribution in its own words
2. assesses whether the main claims are supported by the results
3. assesses the experimental protocol (baselines, datasets, splits)
4. addresses statistical uncertainty (seeds, variance, significance)
5. addresses reproducibility (code, data, hyperparameters, compute)
6. addresses positioning against prior work
7. addresses clarity and presentation
8. addresses limitations or threats to validity
9. gives an overall recommendation and prioritised actions
10. checks a headline number against its table or recomputes a derived number
11. checks the appendix against claims in the main text
12. checks for ablations of the claimed mechanism
13. checks figures (legibility, unexplained series, figure vs table)
14. checks the build (compiles, unresolved references, leftover notes)

## Criteria

- **Primary:** pairwise finding agreement, skill minus without, **at least +0.10**; and coverage
  within-draft SD, skill **at most** without.
- **Guard:** gold recall, skill at least without minus 0.10.
- Secondary (reported): verdict agreement, core share, generic-only coverage, cost.

| Outcome | What follows |
|---|---|
| primary and guard met | measured consistency line in SKILL.md |
| primary not met | R3: a structured version (every checklist item answered present / absent / n.a. with evidence, in a fixed order), dev on these drafts, test on fresh ones |
| guard missed | read the traces before anything else |

## Analysis notes

Paired by draft (6 drafts): per-draft differences reported, sign test on the 6 (direction only;
n is small). Span matching can merge two different issues at one location or split one issue
quoted at two places; both arms carry the same bias.
