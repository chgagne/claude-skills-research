# Results R5: a figure inventory the review must answer

2026-11-11. Protocol: `PROTOCOL-R5.md` (+ amendment 1). Candidate: branch `figure-inventory`
(eb039e0, worktree). Current: 9e72981. Material in `private/r5/`.

## Verdict

**Primary not met, so no merge per the protocol, though the effect is real and in the right
direction.** Every review written with the inventory covers more figures and tables than every
current-skill review: 0.897 vs 0.779 (+0.118, bar +0.15). It also covers them more consistently
across runs (Jaccard 0.880 vs 0.813, met). The candidate is at or above current on all 6 papers.
The gain is largest on figure-heavy papers (+0.29, +0.15 and +0.14 on the 14-, 19- and 22-float
papers) and nil where both arms hit the ceiling (6 floats: 1.00 vs 1.00). The false-findings guard
(≤ 1.0 per run) is missed by **every** arm, bare included, so the bar was ill-calibrated. The
other guards are met.

## Numbers

6 post-cutoff arXiv papers with their figure files (96 floats), 3 runs per arm, no web, R3's review
prompt:

| | candidate (inventory + §6 rows) | current (R3 form) | bare |
|---|---|---|---|
| figure coverage (floats addressed / floats) | **0.897** | 0.779 | 0.617 |
| coverage SD within paper | 0.055 | 0.055 | 0.079 |
| stability (Jaccard of addressed floats, run pairs) | **0.880** | 0.813 | 0.744 |
| R3 14-item coverage | 0.940 | 0.952 | 0.849 |
| figure findings per run judged REAL / FALSE | 14.6 / 1.72 | 13.1 / 1.44 | 13.3 / 1.39 |
| cost per run | $1.85 | $1.70 | $1.06 |
| issues per run | 28.9 | 28.6 | 29.8 |
| figure renders read per run | 7.1 | 5.2 | 1.1 |

Criteria: (1) +0.118 < +0.15 **not met**; (2) Jaccard **met**; (3) 14-item coverage 0.940 ≥ 0.932
met, cost 1.09× ≤ 1.3× met, FALSE figure findings 1.72 > 1.0 **not met** (current 1.44, bare 1.39 also
above it). Judge: 56 of 864 float verdicts flipped between the two passes (6.5%), resolved by a
third call.

## What drives the gain

- **The form row, not the script.** The candidate ran the inventory script in 14 of 18 runs. The 4
  runs that skipped it covered as many floats (0.92 vs 0.89), because the §6 template demands one
  row per figure either way. The checker (run with --inventory in most candidate runs) is what
  enforces completeness.
- **Current skill reviews lump figures.** One current review covered six figures with a single
  "Fig. 1, 2, 4, 5, 6, 9: legible at print size", which the coverage rule does not count as
  addressing them, and said nothing about four others.
- **False findings are noisy in every arm.** The FALSE labels mix real reviewer errors (a
  "caption says fur, but it is a butterfly" complaint; a sign "error" that matches Eq. 9),
  subjective legibility calls judged from a 110-dpi render, and judge artifacts (two "findings"
  whose problem is that the review raised none). The candidate raises more figure findings of both
  kinds: +1.5 REAL, +0.3 FALSE per run.

## Reading

Structure moved coverage and stability in the predicted direction, as in C2 and R3. The effect
(+0.12) is real but below the pre-registered +0.15. By the protocol's rule there is no merge. A
lighter variant is suggested by the data, not tested: keep the one-row-per-figure §6 form and the
checker, and drop or demote the script. Whether to merge as is, test that variant, or close is
the researcher's call. Cost: 54 runs, about $83, plus 2 dev runs and the judge. The weekly ceiling
was lifted for this test by the researcher.
