# Protocol W4: an open defect criterion in place of "no rule, no row"

Written 2026-11-12, before the variant is built and before any W4 run. Direction, material and bars ruled by
the researcher in one interview the same day (journal `2026-11-12.md`).

## Why

W3 (`RESULTS-W3.md`): on fresh unplanted drafts the bare agent covers 0.684 of the judged-real writing
defects and the published skill 0.438. The trace reading (journal 2026-11-12) found the cause upstream of the
gate: the skill agent writes ~54 rows where the bare agent writes ~81, by choice (no size limit reached; the
gate cuts under one row per run), and about two thirds of the real defects only the bare agent found have no
key in `style-defaults.md`: semantic precision, captions vs text, notation, ambiguous reference, claim vs
evidence. "Every style row cites a rule; if you cannot name the rule, do not write the row" plus the rubric's
taxonomy keep the agent inside that set. W4 asks: **with an open criterion in place of the rule whitelist,
does the skill reach the bare agent's coverage without more harmful edits?**

## The variant (branch `proofread-open`, from `main`)

- SKILL.md step 2: the "no rule, no row" sentence is replaced by: write a row for anything a careful copy
  editor at an ML venue would change (errors, unclear or wrong wording, notation, captions vs text, claims
  the evidence does not carry); cite a default when one fits, otherwise `rule` = `clarity: <one line why>`.
  The hard rule "Every `style` row cites a rule. No rule, no row." becomes "Every `style` row says why".
- Rubric: the four levels gain the missing kinds as examples (notation and symbols, ambiguous reference,
  wrong or imprecise word, caption or table vs text, claim the evidence does not carry). Gate question 2
  ("which rule does this rest on? none: taste") becomes "can you say what a reader would stumble on? no:
  taste". The renderer accepts `clarity:` rules (ledger validation already requires only a non-empty rule).
- Unchanged: caps, gate questions 1, 3-5, renderer, deliverable, report.
- **Dev gate:** W3's test drafts 2608.07572 and 2609.02233, 1 run each: the renderer builds, `clarity:`
  rows render, and the run writes more rows than W3's `current` runs on the same draft. Not scored. These
  drafts informed the design and are not used for testing.

## Material

The next 6 eligible drafts of W3's screen (R5's pool, shuffled seed 20261110, from the first position after
W3's eighth eligible), same rules: one flattened `.tex`, compiles locally in under 3 minutes, 4,000-12,000
words, no author in the researcher's group, not used in R5 or W3.

## Arms and runs

| arm | what it is |
|---|---|
| `open` | proofreading-paper-writing at `proofread-open`, frozen when the test cases are built |
| `current` | the published skill, frozen at the same time |
| `without` | same agent, no skill |

W1's prompt verbatim, W1's settings (claude-opus-5-5, Read/Write/Edit/Bash/Glob/Grep/Skill/Agent, no web,
200 turns, 60 min). 6 drafts x 3 arms x 3 runs = **54 runs**, about $115; judges about $10. Gate 0.50/0.80.
W3's launcher, file keeper, case builder and scorer, with the arm names changed.

## Measures

W3's, unchanged: per draft, the located proposals of all 9 runs clustered by character overlap, each
cluster judged REAL/NOT by W3's cluster judge (same prompt); coverage per run = REAL clusters hit / REAL
clusters; W1 pairwise agreement; W1's precision judge on 15 sampled proposals per run. **All judging for
all three arms is done in the same session** (W3 found the precision judge drifting 14 -> 30 of 270 on
identical prompts between 2026-11-06 and 11-12).

## Criteria

1. **Coverage:** `open` >= `without` - 0.05.
2. **Precision guard:** judged-harmful share (bad fix + meaning changed), `open` <= `without`.

Reported: `open` - `current` coverage, agreement, proposals per run by level, REAL share, arm-only REAL
clusters, cost (no bar), math/notation proposals per run.

| Outcome | What follows |
|---|---|
| both met | merge `proofread-open`, measured line in SKILL.md (W3 + W4) |
| coverage met, guard missed | report, decide with the researcher |
| coverage not met | report, no merge; read the traces for what still limits volume |

No W1 planted-draft guard this time (researcher's design: the question is reach on real drafts); W1's
plant types are all within the rule set the variant keeps.

## Frozen material

To be added as amendment 1 before the first test run.

## Amendment 1 (2026-11-12 09:45, after the dev gate, before any test run)

- **Variant frozen at 9aeeff2** (branch `proofread-open`): SKILL.md step 2/3 and hard rule, rubric (notation,
  ambiguous `it`/`this`, imprecise word, caption/table vs text, claim vs evidence; gate question 2), ledger
  schema (`clarity: <why>`). No code change: ledger validation already accepted any non-empty rule. 98 tests
  pass. `current` frozen from `main` (18cfe81 tree).
- **Dev gate passed** (W3's 2608.07572 and 2609.02233, 1 run each): 71 and 59 proposals against 47-58 and
  44-48 for W3's `current` runs on the same drafts; 34 and 30 rows cite `clarity:`; 2 and 1 rows cut; PDF built;
  $2.03 and $1.66.
- Test drafts (W3 screen orders 41-49): 2610.03002, 2609.04292, 2610.01076, 2609.03603, 2610.01373,
  2608.02950. No author in the researcher's group.
- Scorer `score_w4.py` (W3's with arms open/current/without and W4's criteria; sha256 prefix 625444a0a4dc);
  W3's judge prompts and runner unchanged. Material hash over 215 files (`private/w4/FROZEN_W4.txt`):
  `76a39f4da7b4ebe3638b434630b951acd2a4fb61276adab07b5e6e75c530f6a7`.
