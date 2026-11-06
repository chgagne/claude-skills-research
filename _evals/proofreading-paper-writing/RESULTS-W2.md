# Results W2: reduced proofreading-paper-writing, non-inferiority on W1's cases

Protocol: `PROTOCOL-W2.md` (d2e970e; frozen material 06f3809, hash prefix 526d9f1d65eb9f6c).
Reduced skill: branch `proofread-reduce` 8fe35d1, merged 686f6e4 with a measured line (a424ae4).
18 runs on 2026-11-05/06; skill invoked 18/18, no subagent in any run.

## Verdict

**All five bars met; the reduction is merged.** Two bars are met at the edge: intensifier recall
15/18 (bar 15) and judged-harmful edits 14/270 (bar 15). The single-pass text finds as many
planted defects as the multi-agent text did, is as consistent across runs, and costs the same.

## Arms

| arm | what it is |
|---|---|
| reduced | SKILL.md 152 lines: one-agent workflow (read, ledger, gate, render, check), "when a user is present" branch; multi-agent text in `reference/design-notes.md` |
| full | W1's skill arm: SKILL.md 184 lines at 21831f0 (global reader, section workers and gate as subagents; ran as one agent in 16/18 runs) |

## Results (6 drafts x 3 runs, 29 plants, same prompt and scorer as W1)

| measure | reduced | full | bar |
|---|---|---|---|
| plant recall | 0.931 | 0.943 | >= 0.893: **met** (McNemar 1 vs 2) |
| intensifier recall | 15/18 | 17/18 | >= 15/18: **met** (at the bar) |
| pairwise agreement across runs | 0.842 | 0.817 | >= 0.767: **met** (higher in 4/6 drafts) |
| judged harmful (bad fix + meaning changed), of 270 | 14 (11 + 3) | 10 (5 + 5) | <= 15: **met** (one under) |
| cost per run | $2.62 | $2.60 | <= $2.86: **met** |
| recall by type (agreement / duplicate / term / intensifier / undefined) | 1.00 / 1.00 / 0.83 / 0.83 / 1.00 | 1.00 / 0.94 / 0.83 / 0.94 / 1.00 | reported |
| judged good share | 0.641 | 0.585 | reported (bare 0.622) |
| core share | 0.56 | 0.52 | reported |
| proposals per run | 67.3 | 69.9 | reported |
| time per run | 8.5 min | 8.0 min | reported |

The reduced arm's three intensifier misses are all draft 144 ("much higher generative score"),
which the full arm caught in 2 of 3 runs and the bare agent in 0 of 3.

## Notes

- **Unobserved run.** w1_177 run 0 ended with "API Error: Can't reach the API server (ENOTFOUND)"
  after 15 min with no proposals. Under the harness rule for unobserved runs, all three runs of that
  case were redone (00:18-00:30); the failed result is kept in `private/w1/out/w2_failed/`, and its
  cost ($1.76) is not in the cost row. The case was moved aside before any W2 score was computed.
- Verdicts were written by content with the W1 procedure (prefilter now reading the reason too,
  then a search of every missed plant-run); the only misses left are 134 term (3/3, named inside a
  paragraph-level naming finding, as in W1's full arm) and 144 intensifier (3/3).
- Same cases as W1, which motivated the reduction: no evidence that the reduction generalises
  beyond these drafts. The calibrated, profile-based mode was neither measured nor changed beyond
  being shortened into the "when a user is present" section.
