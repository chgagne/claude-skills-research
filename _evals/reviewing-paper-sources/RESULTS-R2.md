# Results R2: consistency of reviewing-paper-sources across repeated runs

Protocol: `PROTOCOL-R2.md` (41c7d0b), amendment 1 (f1bf3b1); scoring material hashed in the
journal (d0af86d) before any output was read. Runs 2026-11-04.

## Runs

6 unplanted drafts x 4 runs x {skill, without} = 48 runs, all parsed, every review rebuilt from
its trace. Draft 134's first batch was lost to a network outage (2 API errors, 6 timeouts, kept in
`private/r2/out/failed/`) and re-run in full; no other run was repeated. Cost per run: skill $1.35,
without $1.10 (x1.22). The skill loaded and its template and claim-audit reference were read in
24 of 24 skill runs.

## Pre-registered measures

| measure | skill | without | criterion |
|---|---|---|---|
| finding agreement (pairwise, span rule) | 0.658 | 0.664 | skill - without >= +0.10: **not met** (-0.005; 2 of 6 drafts favour the skill) |
| coverage, within-draft SD | 0.049 | 0.047 | skill <= without: **not met** (equal; see judge noise below) |
| gold recall (7 verified errors, drafts 134 and 179) | 1.00 | 1.00 | guard >= without - 0.10: **met** |
| core share (findings in >= 3 of 4 runs) | 0.43 | 0.45 | reported |
| same recommendation across runs | 1.00 | 1.00 | reported (all 48: "major revision") |
| top-3 concern agreement | 0.49 | 0.39 | reported |
| coverage mean, 14 items | 0.89 | 0.81 | reported |
| coverage mean, 9 generic items | 0.94 | 0.88 | reported |
| issues per run | 26.4 (20-34) | 28.5 (20-42) | reported |

Coverage by item (skill / without): contribution 1.00 / 0.88, reproducibility 0.92 / 0.75,
positioning 0.62 / 0.38, figures 0.46 / 0.33, build check 1.00 / 0.67, appendix vs main text
0.75 / 0.67; all other items within 0.05.

**Outcome row:** primary not met, guard met -> R3 (structured version).

## Post-hoc checks (not pre-registered)

- **Judge noise.** Re-judging 12 reviews: 7 of 168 item verdicts flipped; mean coverage change
  0.042, the size of the within-draft SD in both arms. The coverage-spread criterion cannot
  separate the arms at this level; the coverage means (difference 0.08 over 24 runs each) can.
- **By severity.** Agreement on critical+major issues: 0.56 in both arms (12 per run); on minor
  issues 0.46 skill vs 0.51 without.
- **Section structure of review.md** (level-2 headings): pairwise heading Jaccard 0.21 skill vs
  0.31 without; 7.4 sections per run (5-11) vs 4.1 (3-5); no draft got the same section sequence
  twice in either arm. The skill's template says "Adapt freely — the section list is a checklist
  of what must be covered, not a form to fill in", and runs did.

## Reading

1. Without the skill, the review is already consistent where it matters most: every run found
   every verified real error, and all runs reached the same recommendation.
2. Run-to-run variation lives in the long tail (which secondary concerns are raised, and where
   they are quoted) and in the shape of the document. The skill does not reduce the first and
   increases the second.
3. The skill's measurable effect is coverage: it reliably adds a build check, reproducibility,
   positioning and figure checks that the bare agent covers in half to two thirds of its runs,
   at 1.22x the cost.

For a skill meant to give a standard review, the gap is the form: the template is advisory. R3
tests a fixed form (fixed sections in a fixed order, every checklist item answered with evidence
or "n.a.").
