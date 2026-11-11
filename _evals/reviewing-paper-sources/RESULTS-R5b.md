# Results R5b: the figure form without the inventory script

2026-11-11. Protocol: `PROTOCOL-R5b.md` (+ amendment 1). Variant: branch `figure-form` (be1fe8a,
worktree). Compared with R5's candidate and current runs on the same 6 papers, same judges.

## Verdict

**The script-free variant covers more figures than the inventory candidate, and is as stable, but
it misses the cost criterion by $0.05 per run.** Under the protocol that is a decision for the
researcher, not an automatic merge. Coverage: 0.944 vs 0.897 (candidate) and 0.779 (current).
Stability: 0.900 vs 0.880. The variant is at or above the candidate on 5 of 6 papers, with the
largest gain on the 22-float paper (0.82 vs 0.64). Cost: $1.90 vs $1.85 mean, but the variant's
median run ($1.84) is below the candidate's mean, and its runs range from $1.26 to $2.62.

## Numbers

| | variant (form + checker) | candidate (inventory script + form) | current |
|---|---|---|---|
| figure coverage | **0.944** | 0.897 | 0.779 |
| stability (Jaccard) | **0.900** | 0.880 | 0.813 |
| 14-item coverage | 0.944 | 0.940 | 0.952 |
| figure findings REAL / FALSE per run | 14.3 / 1.50 | 14.6 / 1.72 | 13.1 / 1.44 |
| cost per run (mean) | $1.90 | $1.85 | $1.70 |
| issues per run | 27.4 | 28.9 | 28.6 |
| renders read per run | 7.8 | 7.1 | 5.2 |

Per paper (figure coverage, variant / candidate / current): 2608.03135 0.82/0.64/0.50,
2609.03615 1.00/0.93/0.90, 2609.01311 1.00/1.00/1.00, 2610.01685 0.95/0.96/0.81,
2609.02504 0.95/0.93/0.64, 2608.01072 0.95/0.92/0.83.

Criteria: (1) coverage ≥ candidate − 0.03, **met**; (2) Jaccard ≥ candidate − 0.03, **met**;
(3) 14-item coverage ≥ current − 0.02 (0.944 ≥ 0.932) met, cost ≤ candidate ($1.90 vs $1.85)
**not met**. The variant ran the checker with --floats in 17 of 18 runs.

## Reading

R5's hint holds: the gain comes from the one-row-per-figure form and the checker that enforces it,
not from the inventory script. Without the script, coverage is higher still. The variant also
raises fewer false figure findings than the candidate (1.50 vs 1.72, close to current's 1.44). The
only miss, cost, is a 2.7% difference in means with a spread of $1.26 to $2.62 per run. Against
current, the variant gains +0.165 coverage, above R5's original +0.15 bar. That comparison spans
two days of runs and was not the pre-registered one.

Spend: 18 runs (~$34) plus the judge.
