# Protocol P2 results: the reduction passes (2026-10-25)

Protocol: `PROTOCOL-P2.md` (aa0a261). 16 runs, 14:03 to 14:33, every run loaded the skill, none
discarded or contaminated. Reduced skill frozen at 16a1102 (86 lines), full skill at 9924de7.

| # | Criterion (test, 4 cases x 2 runs) | Reduced | Bar | Full (P1) | Bare (P1) |
|---|---|---|---|---|---|
| 1 | Planted recall | 8/8 | at least 7/8 | 8/8 | 8/8 |
| 2 | Other flags per run | 1.12 | at most 1.88 | 1.25 | 1.63 |
| 3 | Mean cost per run | $1.68 | at most $2.08 | $1.89 | $1.76 |

**Verdict: all three met; the reduction is merged.** Script ran in 2 of 8 reduced test runs (2 of 8
for the full skill in P1); no run opened `reference/design-notes.md`.

Dev, reported only (d2 and d3 tightened hypothesis plants, 2 runs each): reduced 1/4, full 1/4, bare
1/4 (P1). d3 is a flawed plant (see the correction in `RESULTS-P1.md`); on d2 each arm found it once.

Limits: the reduced text was written after reading P1's plants (caveat in the protocol); 8 test
runs; no arm beats the bare agent, so this shows the shorter text loses nothing, not that it adds
anything.
