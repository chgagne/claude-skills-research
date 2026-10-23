# verifying-bibliography, protocol D2: validating the reduced skill

Written 2026-10-23, before any D2 run. Frozen by the commit that adds it.

## Question

Protocol D's outcome table reduced `verifying-bibliography` to "run the script, read the
report" (branch `bib-reduce-d`, 36a8cd8: SKILL.md from 201 to 71 lines, the rest moved
verbatim to `reference/design-notes.md`; script and `_shared` unchanged since bf62212). Does
the reduced skill do at least as well as the full skill did in protocol D? This is a
non-inferiority check before publishing the reduction, not a new comparison with the bare agent.

## Design

- **Arm**: the reduced skill at 36a8cd8, installed as in D (`_shared` at bf62212, same
  scaffold, grants, model `claude-opus-5-5`, 100 turns, 40-minute timeout).
- **Cases**: D's six cases (`private/run/cases`), unchanged; 2 runs each, 12 runs, one case at
  a time behind `_harness/usage_gate.py --five 0.40 --seven 0.75`.
- **Comparator**: D's full-skill arm (12 runs, `RESULTS-D.md`), not re-run.
- **Scoring**: as D: `score.py` after `private/scored/prep.py` (install-path mask and the
  source-paper rule). Natural errors: D's 70 adjudicated entries plus any entry newly flagged
  in D2, adjudicated by the same rules (`private/adj/`); new confirmed errors are added to
  the pool for both the D2 arm and the D full-skill arm.

## Criterion (all must hold to publish the reduction)

1. Planted recall at least 25 of 26 (D full skill: 26 of 26).
2. False positives after adjudication at most 22 over the 12 runs (D full skill: 15).
3. Natural-error recall at least 0.80 (D full skill 0.86, D without 0.77).
4. The script ran in at least 11 of 12 runs (D: 12 of 12).
5. Mean cost per run at most $1.40 (D full skill: $1.05).

If any fails, the reduction is not published; the failing criterion is compared against the
D traces to find which removed instruction mattered, and that text goes back into SKILL.md
before a new protocol. A discarded run (contamination, usage-limit failure) is re-run once.
