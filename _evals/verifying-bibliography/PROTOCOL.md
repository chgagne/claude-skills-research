# verifying-bibliography: with/without evaluation, stage 1

Written 2026-10-08, before any scored run. Nothing below changes once the first scored
run starts; a change means a new stage with its own protocol.

## Question

Does `verifying-bibliography` let an agent find substantive errors in a BibTeX file better
than the same agent without it, and better than a skill the agent writes for itself?

## Material

Four bibliographies (`cases/case1..4.bib`), 38 entries, all real ML/EC works whose
metadata was read from Crossref (DOI) or the arXiv API on 2026-10-08. 24 entries are
correct, 14 carry one planted defect each: title under the right DOI (2), invented
co-author (2), DOI of another work (2), wrong volume/pages/year (3), arXiv preprint of a
published paper (3), nonexistent work (2). Labels are in `gold.json`, outside every arm's
plugin directory. One correct entry (`chen2016xgboost`) keeps its real subtitle, which
Crossref omits; it is correct and labelled `ok`.

## Arms

Same prompt, same tools (Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch, Skill),
same model (`--model claude-opus-5-5`), fresh HOME per run (`claude plugin eval` sandbox).

- **without**: no skill loaded (the baseline arm of the `skill` arm's `claude plugin eval`
  call; the `self` call runs with `--ablation none`).
- **skill**: `verifying-bibliography` frozen at repository commit 2091ec8.
- **self**: `self-verifying-bibliography`, written once by Claude in a session with skills,
  settings and MCP disabled and only the Write tool, from a generic task description,
  without feedback (17 min, 4 turns). Copied verbatim to `self-skill/` and frozen by its
  sha256 in `self-skill.sha256`.

## Scale

4 cases x 3 runs per arm: 12 runs each for without, skill and self (36 runs).

## Scoring (`score.py`)

Per run, the last fenced `json` block of the final message gives the flagged keys.
- recall = flagged defective entries / defective entries
- false-positive rate = flagged correct entries / correct entries
- label accuracy = caught defects with the right label / caught defects (secondary)
- a run with no parseable block scores recall 0 and FP 0, and is counted as a format failure
Arm figures pool all runs; per-case figures are reported beside them.

## Success criterion

The skill arm succeeds if **both** hold:
1. its pooled recall exceeds the without arm's and the self arm's by at least 20 points;
2. its pooled false-positive rate is not higher than either other arm's.

Token cost and wall time are reported, not scored.

## Stage-2 trigger

Run stage 2 (8 cases x 5 runs, new cases) only if stage 1 is ambiguous: a recall gap
between 10 and 30 points against either arm, or criterion 2 failing by one entry or less.
A clear pass or a clear failure stops here.

## Known before running

- DBLP's API answered with an anti-bot page on 2026-10-08. The skill uses DBLP to find the
  published version of a preprint, so its preprint detection may fail in every arm that
  relies on DBLP. This is recorded now so it cannot be used afterwards to excuse a result.
- Contamination check: every trace is searched for `gold.json` and `_evals`; a run that
  touched either is discarded and reported.

- A harness smoke run (case1, skill arm, 1 run, not scored) checked that traces and final
  messages can be recovered. It found all 3 defects and no false positive; it is not part
  of the results.
