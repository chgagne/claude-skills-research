# Protocol R5: a figure inventory the review must answer

Written 2026-11-09, before any material, script or run. Design settled with the researcher in an
interview the same day (journal `2026-11-07.md`, "Decision record: R5"), after the cross-protocol
finding that skills add structure, not detection.

## Question

With R3's fixed form, the review covers figures least of the 14 checklist items (0.33 with the
form, 0.17 current, 0.28 bare). The current skill already tells the reviewer, in prose, to render
figures and check each one, and runs mostly skip it. C2 showed that a list the agent must answer
item by item is executed. R5 asks: **does a figure inventory that the review must answer row by
row make every run cover every figure, and cover the same ones in the same way?** It measures
coverage and stability, not recall.

## The candidate (branch `figure-inventory`, built on dev papers only)

`assets/figure-inventory.py paper-dir/` lists every `figure`/`table` float (including `*` and
`wrap` variants): label, caption (first sentence), image files used and their paths, each
sentence that `\ref`s it (or "never referenced"), and a rendered PNG per image file (PDF via
`mutool`/`pdftoppm`, raster copied) under `review-assets/figures/`. Review form §6 gets **one row per
inventory item**: what it shows (read from the render, or "no image" for a table), whether it
supports the sentence that cites it (yes / partly / no / not cited), and the problem if any.
`check-review-form.py --inventory` fails a review missing a row. SKILL.md gets one line naming the
script in step 3. Nothing else changes.

## Material

The pool is post-cutoff arXiv papers (v1 submitted 2026-08-01 to 2026-10-31), primary cs.LG,
cs.CV or cs.CL, listed by the API and screened in a shuffled order (seed 20261110). Eligible: the
source flattens to one `.tex`; it has **at least 4 figure floats whose image files are in the
source** (pdf/png/jpg); the main text has 6 to 15 pages of content (proxy: 4,000 to 12,000 words);
and no author is in the researcher's group. The first 8 eligible papers are used, 2 dev and 6 test
in screening order. The download keeps image files (unlike C1/C2). No disguise: runs have no web
tools. A one-call memory check per title (bare, no tools) is logged, and a paper the model knows
is replaced by the next eligible one.

## Arms

| arm | what it is |
|---|---|
| `candidate` | the skill at `figure-inventory` (frozen when test cases are built) |
| `current` | the skill as published (R3 form), frozen at the same time |
| `without` | the same agent, no skill |

R3's prompt verbatim; tools Read, Write, Edit, Bash, Glob, Grep, Skill; no web. 150 turns, 40 min.
**6 test papers × 3 arms × 3 runs = 54 runs.** Dev: 2 papers × candidate × 1 run as a build gate
(the inventory script runs; checker OK; every row answered); dev runs are not scored. Gate
`--five 0.50 --seven 0.80`; deliverables (review.md, rendered figures) kept by the scaffold watcher.

## Measures (Sonnet judge, no tools; prompts hashed before the first test run)

- **Figure coverage (primary):** for each float in the paper (the inventory computed by the frozen
  script, the same list for every arm), the judge reads the review and marks it ADDRESSED if the
  review says something specific about that float (what it shows, a problem, or that it supports
  or fails to support a named claim), otherwise NOT_ADDRESSED. A bare mention ("see Fig. 3") is
  NOT_ADDRESSED. Coverage per run = addressed / floats. Judged twice, tie-break on disagreement.
- **Stability:** per paper and arm, the mean pairwise Jaccard similarity across the 3 runs of the
  set of addressed floats. Also the SD of coverage across the 3 runs.
- **Figure findings:** each figure-level problem the review raises is labelled by the judge
  REAL / FALSE against the paper and its rendered figure (the judge gets the figure image when
  it is a raster or rendered PDF). This is reported, and it serves as the noise guard.
- **Guards:** R3's 14-item coverage (same judge prompt as R3), cost per run, issues per run.

## Criteria

1. **Primary:** figure coverage, candidate − current ≥ **+0.15** (mean over 18 runs per arm).
2. **Stability:** mean Jaccard, candidate ≥ current.
3. **Guards:** 14-item coverage ≥ current − 0.02; FALSE figure findings per run ≤ 1.0; cost ≤ 1.3 ×
   current.

All met: merge `figure-inventory` with a measured line. Primary met, something else missed:
report, decide with the researcher. Primary not met: report, no merge.

## Cost

Test 54 runs × ~$1.5-2.5 = ~$80-130 (rendering adds turns). Dev gate ~$5. Judge ~$10.
