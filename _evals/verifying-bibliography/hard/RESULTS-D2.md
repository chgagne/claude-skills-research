# Protocol D2 results: the reduced skill (2026-10-23)

Protocol: `PROTOCOL-D2.md` (0f4381c), committed before the first run. 12 runs of the reduced skill
(36a8cd8) on D's six cases, 10:01 to 10:58, $15.2 in model cost, usage at most 27% of the 5-hour
window. No run failed, none timed out.

| # | Criterion | Reduced skill (D2) | Bar | Full skill (D) | |
|---|---|---|---|---|---|
| 1 | Planted recall | 22/26 | at least 25/26 | 26/26 | **fail** |
| 2 | False positives after adjudication | 17 | at most 22 | 15 | pass |
| 3 | Natural-error recall | 130/144 = 0.90 | at least 0.80 | 121/144 = 0.84 | pass |
| 4 | Script ran | 12 of 12 | at least 11 | 12 of 12 | pass |
| 5 | Mean cost per run | $1.27 | at most $1.40 | $1.05 | pass |

Natural recall uses the pool of 72 errors (D's 70 plus two that only D2 found: `Ma2025`, an
early-access DOI now in vol. 30(2) pp. 667-687, and `krizhevsky2009learning`, whose report lists
Krizhevsky alone). The D figures are recomputed on the same pool, so they differ from
`RESULTS-D.md` (0.86 there on 70). The bare agent's is 0.75.

**Verdict: the reduction is not published.** Criterion 1 fails.

## Why it failed

The four missed defects fall in two runs: long1 run 0 (`he2024darts`, `li2024zero`) and long3
run 1 (`Niu2008`, `Yin2023`). All four entries lack a DOI, so the script reaches them only by DBLP
title search and reports them as `WEAK`, with no record fields in `bibdiff.csv`. The script, by
design, never compares pages against a title-search record. Finding a shifted page range there
depends on the agent looking each `WEAK` entry up itself.

The full-skill runs did that: in D's long3 run 1, the agent listed the `WEAK` keys from
`bibdiff.csv` and queried each one. The two failing D2 runs did not. The full SKILL.md said so
explicitly in "What is compared against what" (pages, volume and year are compared only against a
record reached by a stable identifier). The reduced text kept only "`WEAK`: not verified, check
each by hand", which reads as doubt about identity rather than "these fields were never checked".

Two failing runs in 12 against none in 12 is weak evidence on its own (Fisher p about 0.5), but
the protocol's rule is the same either way: put the removed instruction back and measure again.

## Scoring notes

- The reduced SKILL.md cites the eval folder in its "Measured" section, so every D2 trace
  mentions `_evals` once through the loaded skill text. No tool call touched `_evals` or
  `gold.json` (checked); `private/scored/prep.py` masks that literal line, as it masks the install
  paths.
- The reduced skill also found more natural errors than the full one (0.90 against 0.84): the
  shorter text did not weaken the scripted pass, only the follow-up on `WEAK` entries.
