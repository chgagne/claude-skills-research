# Protocol B4: does v3.3 close the memory loss on B3's drafts?

Written 2026-10-27, before any B4 run. Design chosen by the researcher (journal 2026-10-26/27):
a structural fix for the memory loss B3 measured, checked on dev (IMPROVEMENT-PLAN.md, step 0c),
step 6 reworded after 0c, then measured here.

## Question

In B3 both skill versions recovered fewer of the key references the agent can name from memory
than the bare agent (v3.1 0.831 against 0.922 at 30). v3.3 makes the lookup script require the
step-2 memory list and tag remembered titles `[M]`. Does it close that gap without losing what
v3.1 gains on hard references, at no higher cost?

## Arm and material

**v3.3**: `surveying-literature` at 5fb46ed (branch `surveying-v33`), frozen into
`private/b3/run/v33/`; its scaffold installs the v3.3 assets. B3's 35 drafts, prompt, grants,
model (`claude-opus-5-5`), limits and contamination rule (id), `gold-B3.json`. **2 runs per
draft, 70 runs**, one case at a time behind the usage gate (5h <= 0.40, 7d <= 0.75); the run may
pause across a 7-day reset.

Compared with B3's existing runs, not re-run: without (70) and v3.1 (70). Caveat recorded now: those
runs are twelve days older, so web-search results may have drifted; the bare arm's memory recall
does not depend on search, the v3.1 comparison partly does.

## Measures (analyze.py, id rule)

- **Primary:** key/memory Recall@30, v3.3 against without.
- **Secondary 1:** key/non-memory Recall@30 (B3's primary), v3.3 against v3.1.
- **Secondary 2:** mean cost per run, v3.3 against v3.1 ($1.72).
- Reported: all@30, all@10, random strata, `[M]` titles in the answer, lookup calls with
  `--memory`, web searches billed per run; the same table without any discard and under the title
  rule.

## Criterion

1. key/memory@30 of v3.3 at least without's minus 0.03 (0.892), and above v3.1's 0.831.
2. key/non-memory@30 of v3.3 at least v3.1's minus 0.03 (0.175).
3. Cost per run at most v3.1's ($1.72).

## Reading (no automatic merge)

- All met: merge v3.3 into main; SKILL.md's measured section reports B4.
- 1 met, 2 or 3 missed: the memory fix works but costs elsewhere; decided with the researcher.
- 1 missed: v3.3 is not merged; the traces are read for where remembered titles were lost (not
  listed, not found by the lookup, or ranked out) before any further change.

## Budget

About $95 (step 0c: $1.33 per run).
