# Results R1: reviewing-paper-sources, planted internal inconsistencies (stages 1-2 closed)

Protocol: `PROTOCOL-R1.md` (cc5bb1d), amendments 1 (e1d8566) and 2 (5b5f066). Closed 2026-11-04 by
the researcher's choice after round 2 could not be built. No skill-vs-bare test was run.

## Calibration (round 1)

4 disguised, memory-probed drafts (C2 pool: 54, 93, 134, 179), 12 plants, agent without the skill,
no web tools, 2 runs each: 24 runs, $29.45 ($1.23 per run), 0 failures. Score:
`results/R1-calibration-2026-11-03.json`.

| type | located hits | by content |
|---|---|---|
| prose (a prose number off from its table after arithmetic) | 7/8 | 7/8 |
| appendix (a general claim vs one far table entry) | 6/8 | 8/8 |
| variance ("clear"/"significant" gap inside the paper's own spread) | 6/8 | 6-7/8 |

Both appendix "misses" (draft 134) named the planted exception exactly (61.89 < 62.44) but quoted
another of the draft's three sentences making the same claim. By content the agent without the
skill found about 22 of 24 plants. It also found the drafts' natural errors unprompted (A×L
products that do not equal LUTs × latency, a baseline above the value bolded as best, a misreported
best prior result).

## Round 2 (tightened rules, amendment 2): not buildable

Four plant subagents, two candidates per type, checked against the rules written before they ran.
Valid: 3 prose plants (two-step arithmetic, inputs far away). Appendix: none (no general claim made
exactly once and contradicted only by an appendix cell; two drafts' appendices hold only
hyperparameters or coding rules stated several times). Variance: none (only two drafts report a
spread; where it exists, every method-vs-baseline gap is already inside it, or the only site was
excluded by the distance rule). Rejections in `private/r1/plants/proposals2/` and this file.

## Conclusion

On defects checkable from the draft alone, the agent without the skill reviews at ceiling: it
recomputes derived numbers and cross-checks claims against tables without being told to. Plants
subtle enough to discriminate require structures real drafts rarely contain, so planted internal
inconsistencies cannot measure this skill's gain on this material. **Not established:** whether
the skill helps; the skill smoke run (unplanted draft 54) did follow its workflow (compiled,
rendered pages, recomputed statistics) at the same cost as the bare run ($1.91 vs $1.80), 24 vs
21 issues. Same pattern as C1 calibration, P1 and D: single planted defects sit at the bare
agent's ceiling unless the skill adds structure the agent must answer (C2).

Next: stage 3, documented defects in real papers (defined in its own protocol before any run).
