# Protocol R5b: the figure form without the inventory script (non-inferiority)

Written 2026-11-11, before the variant is built. The researcher chose this follow-up to R5
("script-free variant, same papers, non-inferiority to the candidate").

## Question

In R5 the inventory candidate raised figure coverage to 0.897 (current 0.779). Its 4 runs that
skipped the script covered as much as the 14 that ran it, so the gain looked like it came from the
§6 one-row-per-figure form and its checker. Is a variant without `figure-inventory.py` and without
its rendering step non-inferior to the R5 candidate?

## The variant (branch `figure-form`, from `figure-inventory` eb039e0)

- `assets/figure-inventory.py` and its test are removed. SKILL.md step 3 goes back to the current
  skill's wording plus one sentence saying that review §6 has one row per figure and table and the
  checker enforces it.
- `check-review-form.py --floats paper.tex` derives the float list itself (figure/table floats in
  source order, ids F1.. T1.., with label and the first caption words) and fails on a missing or
  unanswered §6 row. `--list-floats paper.tex` prints that list. The inventory script's parsing of
  floats is moved into the checker; citing sentences and rendering are dropped.
- Template §6: the same row table, with the instruction to run the checker's list instead of the
  script.

## Material, arms, measures

R5's 6 test papers, cases, prompt, tools, limits, file capture and reference inventories, unchanged.
**Variant only, 3 runs per paper = 18 runs**, compared with R5's 18 candidate runs (and current, for the
guard). Judged with R5's exact judge prompts and scripts (`score_r5.py` with the variant arm added).
No new bare or current runs.

## Criteria (non-inferiority to the R5 candidate)

1. Figure coverage: variant ≥ candidate − 0.03 (candidate 0.897).
2. Stability (Jaccard): variant ≥ candidate − 0.03 (candidate 0.880).
3. Guards: R3 14-item coverage ≥ current − 0.02 (current 0.952); cost per run ≤ candidate ($1.85).

All met: merge `figure-form` with a measured line (R5 + R5b). Otherwise: report and decide with the
researcher. The R5 false-findings bar is not reused (it was missed by every arm); the variant's
REAL/FALSE figure findings are reported beside the candidate's.

## Cost

18 runs at about $1.7 = about $30, plus the judge.
