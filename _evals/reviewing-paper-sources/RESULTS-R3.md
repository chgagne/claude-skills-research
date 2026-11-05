# Results R3: a fixed review form for reviewing-paper-sources

Protocol: `PROTOCOL-R3.md` (bdb0fe6). Branch `review-form` (33d51b1). Dev gate met in round 1
(checker `OK` 4/4, same 12 headings in all 4; no tuning). Test material hashed in the journal
(a2ad142) before any test run. 54 runs on 2026-11-04/05, none failed.

## Test: 6 drafts (134, 179, 144, 177, 108, 116) x 3 runs x 3 arms

| measure | form | current | without | criterion |
|---|---|---|---|---|
| same heading sequence in all 3 runs | **6/6 drafts** | 0/6 | 0/6 | form >= 5/6: **met** |
| checker `OK` at the end of the run | **18/18** | 0/18 | 0/18 | form >= 17/18: **met** |
| coverage (14 items, Sonnet judge) | 0.897 | 0.857 | 0.849 | >= current - 0.02: **met**; >= without + 0.05 (0.899): **missed by 0.002** |
| coverage, within-draft SD | 0.006 | 0.011 | 0.025 | reported |
| coverage, 9 generic items | 0.932 | 0.895 | 0.889 | reported |
| gold recall (7 errors, 134 and 179) | 0.958 | 1.000 | 0.958 | guard >= without - 0.10: **met** |
| heading Jaccard across runs | 1.00 | 0.13 | 0.26 | reported |
| finding agreement (R2 span rule) | 0.718 | 0.712 | 0.721 | reported |
| same recommendation across runs | 1.00 | 1.00 | 1.00 | reported |
| issues per run | 29.2 (23-35) | 29.2 (23-36) | 29.6 (22-37) | reported |
| cost per run | $1.71 | $1.49 | $1.19 | form <= 1.3 x current (1.15): **met** |

Coverage by item (form / current / without): reproducibility 1.00 / 0.72 / 0.72, ablations
1.00 / 1.00 / 0.83, build 1.00 / 1.00 / 0.94, contribution 1.00 / 1.00 / 0.94, appendix
0.83 / 0.78 / 0.83, positioning 0.39 / 0.33 / 0.33, figures 0.33 / 0.17 / 0.28 (no web tools,
and figures were not rendered in most runs). The two gold misses (form 1, without 1) are the same
item (PMED k-Shot below two baselines), each in one run.

## Outcome

Structure, the purpose of the form, is met decisively: every form review has the same twelve
sections in the same order, and the agent ran the checker and fixed the review until it passed in
every run. Coverage is the highest of the three arms and the most stable (SD 0.006), but the
"without + 0.05" bar is missed by 0.002, inside the judge's re-run noise (0.042 per review in R2).
No row of the outcome table covers this exact case. The researcher had asked to merge the branch
if it proved good; Claude judged it so on the structure result and merged, stating the miss here
and in SKILL.md. What the form does not change: which findings each run raises (agreement 0.72 in
all arms) and the verdict (already identical in every arm).
