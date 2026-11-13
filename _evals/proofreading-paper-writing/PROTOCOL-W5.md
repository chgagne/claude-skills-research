# Protocol W5: a second pass for defects not yet in the ledger

Written 2026-11-12, before the variant is built and before any W5 run. The researcher chose option 2 after
W4 ("push on what the bare agent still finds") and, after the W4 data rejected my first sketch, chose the
second-pass variant in one interview the same day (journal `2026-11-12.md`). Design otherwise as W4.

## Why

After W4 the published skill (open criterion, merged 78e4580) covers 0.547 of the judged-real defects on
fresh drafts against 0.653 for the bare agent. The gap (111 REAL clusters bare hits and `open` misses) is
broad: 42 mechanics (only 9 deviations from the paper's own conventions), 45 framing, 18 style, 6 flow;
only 11 notation items; 9 rows degraded to comments in 18 runs. 49 of the 111 were found by one bare run of
three, so the bare agent's edge looks like breadth of scanning, partly random. W5 asks: **does a second,
section-by-section pass for defects not yet in the ledger bring the skill to the bare agent's coverage
without more harmful edits?**

## The variant (branch `proofread-pass2`, from `main` 78e4580)

- SKILL.md gains step **2b. Second pass**: after the ledger is written, re-read the paper section by
  section; for each section, append rows for defects not already in the ledger (any level); do not revisit
  existing rows; then gate (step 3) as usual. Nothing else changes.
- **Dev gate:** W4's test drafts 2610.03002 and 2609.04292, 1 run each: the renderer builds, the trace shows
  a second pass over every section, and the run writes more rows than W4's `open` runs on the same draft.
  Not scored; these drafts informed the design.

## Material

The next 6 eligible drafts of W3's screen, same rules (one flattened `.tex`, compiles locally in under 3
minutes, 4,000-12,000 words, no author in the researcher's group, not used in R5, W3 or W4).

## Arms, runs, measures

| arm | what it is |
|---|---|
| `pass2` | proofreading-paper-writing at `proofread-pass2`, frozen when the test cases are built |
| `current` | the published skill (78e4580, open criterion), frozen at the same time |
| `without` | same agent, no skill |

W1's prompt and settings; 6 drafts x 3 arms x 3 runs = **54 runs**, about $140; judges about $10. Gate
0.50/0.80. W4's harness, scorer (arm `open` renamed `pass2`), cluster judge and precision judge (with the
last-complete-answer parser), all arms judged in one session.

## Criteria (W4's)

1. **Coverage:** `pass2` >= `without` - 0.05.
2. **Precision guard:** judged-harmful share, `pass2` <= `without`.

Reported: `pass2` - `current`, agreement, proposals per run by level, rows appended by the second pass,
arm-only REAL clusters, cost (no bar).

| Outcome | What follows |
|---|---|
| both met | merge `proofread-pass2`, measured line in SKILL.md |
| coverage met, guard missed | report, decide with the researcher |
| coverage not met | report, no merge |

## Frozen material

To be added as amendment 1 before the first test run.
