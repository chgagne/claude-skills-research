# Results R6: a reduced SKILL.md

2026-11-21. Protocol: `PROTOCOL-R6.md` (+ amendment 1). Variant: branch `review-lean` (0776b10), SKILL.md
369 → 185 lines, cut text moved to `reference/build-and-venue.md` and `reference/recurring-findings.md`.
Reference runs re-judged the same day in fresh judge directories.

## Verdict

**The half-length skill is non-inferior on every criterion and 9% cheaper: all six criteria met,
merged.** On R5's six papers it covered more figures (0.952 vs 0.901) and covered them more
consistently (Jaccard 0.916 vs 0.849), with the same 14-item coverage (0.937 vs 0.944). It cost
$1.73 per run against $1.90. On R1 stage 3's documented defects it found 21/24, against 20/24 for
the old skill and 21/24 for no skill.

## Numbers

Part A (6 post-cutoff papers, 96 floats, 3 runs per arm):

| | lean (185 lines) | live (369 lines, R5b runs) |
|---|---|---|
| figure coverage | **0.952** | 0.901 |
| stability (Jaccard) | **0.916** | 0.849 |
| 14-item coverage | 0.937 | 0.944 |
| figure findings REAL / FALSE per run | 14.2 / 2.06 | 12.2 / 1.39 |
| cost per run, mean (median) | **$1.73** ($1.59) | $1.90 ($1.84) |
| issues per run | 29.7 | 27.4 |
| renders read per run | 8.3 | 7.8 |
| checker run with `--floats` / final review passes | 18/18 / 18/18 | 17/18 / — |

Per paper (figure coverage, lean / live): 2608.03135 0.85/0.82, 2609.03615 0.97/0.93, 2609.01311
1.00/1.00, 2610.01685 0.95/0.82, 2609.02504 1.00/0.95, 2608.01072 0.95/0.88. Lean is at or above
live on all six papers.

Part B (8 papers, 12 documented defects, 2 runs per arm):

| | lean | skill (R3 form, d2329ee) | without |
|---|---|---|---|
| defect-runs found | **21/24** | 20/24 | 21/24 |
| papers with ≥1 found | 7/8 | 7/8 | 7/8 |
| same verdict in both runs | 11/12 | 10/12 | 11/12 |
| cost per run | $1.66 | $1.68 | $1.07 |

Criteria: (1) 0.952 ≥ 0.871 met; (2) 0.916 ≥ 0.819 met; (3) 0.937 ≥ 0.924 met; (4) 21 ≥ 18 met;
(5) $1.73 ≤ $1.90 met; (6) 18/18 met.

## Judge drift

Re-judging the same 18 live reviews gave a figure coverage of 0.901 (R5b: 0.944) and a Jaccard of
0.849 (0.900). Both moved by more than the 0.03 the protocol says to report. The 14-item coverage
held (0.944 vs 0.944). Part B moved by one hit per arm (skill 19 → 20, without 20 → 21). The figure
judge flipped 40 of 576 verdicts between its two passes (6.9%, R5: 6.5%), so the drift is about the
size of the judge's own noise. The comparison is same-day, so drift does not favour either arm.
Against R5b's original 0.944, lean's 0.952 is still higher.

## Reading

Removing half the text changed nothing that this bench measures, except cost. What the skill
measurably adds lives in the form, the checker and the per-float rows, and those were kept word for word.
The cost saving ($0.17 per run) comes from fewer turns, not from skipped work: lean read more
renders and raised more issues. Lean raised more figure findings of both kinds (+2.0 REAL,
+0.7 FALSE per run). R5 showed that the FALSE label is noisy in every arm, so this is reported, not
scored. Part B repeats R1 stage 3: no arm detects more than the bare agent, and all three miss the
same two bare-count slips.

Not measured: whether the lessons moved to `reference/` (build traps, venue rules, rebuttal
benches) still get applied. This bench could not have measured them in place either. They are
still in the skill, one pointer away.

Spend: 34 runs (~$58) plus the judge (~$6).
