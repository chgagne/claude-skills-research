# verifying-bibliography, protocol E2: the given-name change on E's bibliographies

Written 2026-10-26, before any run. Thread 6 of the 2026-10-25 session close, chosen by the
researcher on 2026-10-26.

## Question

After protocol E, `author-name-form` (MINOR) became `author-given-name` (MAJOR, from any record;
5ee826d), because both reduced runs dismissed Daniel Trewartha's wrong given name when the script
printed it as MINOR. Does the change recover that error without adding false positives?

## Arm and material

One arm, **reduced2**: `verifying-bibliography` at 5ee826d (the published skill, reduced SKILL.md plus
the change), frozen into `fresh/private/run/reduced2/`; `_shared` and the scaffold as E (bf62212).
E's six cases, prompt, grants, model, limits, contamination rule unchanged. **2 runs per case, 12
runs**, one case at a time behind the usual gate.

## Scoring

Against E's natural pool (18 confirmed errors, `results/E-2026-10-24.json`) with E's verdicts for
entries E already adjudicated. An entry E never adjudicated that a reduced2 run flags is adjudicated
by E's rules before reduced2's numbers are compared with E's: error (then it joins the pool, and
E's arms are re-scored on the enlarged pool, which can only lower their recall) or false positive.
Every `author-given-name` flag in the reports is listed with its verdict.

## Reading (against E's reduced arm, 61ee681: 30/36, 8 false-positive entries)

- **Change holds:** Trewartha's error flagged in at least 1 of 2 runs, recall at least 0.833 - 0.05,
  false-positive entries at most 12 (1.5 x 8), and no `author-given-name` false positive.
- **Change costs:** any given-name false positive, or false-positive entries above 12: reported with
  the entries; whether to keep MAJOR, narrow it, or revert is decided with the researcher.
- **Change does nothing:** Trewartha still missed in both runs: the traces are read to see whether
  the MAJOR line was printed and dismissed or not printed.

Reported beside it: recall against E's full arm (0.889) and bare arm (0.861), cost per run. Two runs
per case: one hit moves recall by 0.028, so the comparison is a direction, not a test.

## Budget

About $13 (E's reduced arm cost $1.06 per run).
