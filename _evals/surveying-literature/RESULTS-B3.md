# Protocol B3 results: the offline-confirmation method (v3.1) on new drafts (2026-10-15)

Protocol: `PROTOCOL-B3.md`, frozen at 7a99a33, with amendment 1 (7b598fe) pushed before any
agent run. Skills frozen: v3.1 on branch `surveying-v31` at b1594da, v2 at d6d64fa. 175 runs
(70 v3.1, 70 without, 35 v2), one case at a time behind the usage gate, about $290 in model
cost; no run lost to a limit, no format failure, no run discarded under the id rule. Scores:
`results/B3-primary.json`, `results/B3-nodiscard.json`, `results/B3-titlerule.json`,
`results/B3-covariates.json`. Gold labels: `gold-B3.json`; the drafts stay private.

## Material

The 20 drafts of the frozen protocol left **9 non-memory key references** after the memory
probe (83 of 120 removed references named from memory, against 55 in B2): the strict key rule
picks references cited at least twice in the related-work section, and those are the ones the
model knows. Amendment 1 extended the pool before any run (arXiv query, 60 candidates screened in
a drawn order, 28 eligible) and added one batch of 15 drafts (the 3 reserves and 12 new ones).
Final set: **35 drafts, 210 removed references, 140 named from memory, 22 non-memory key
references** (floor 15), 48 non-memory random.

The leak audit, scripted for B3, found defects the B2 pipeline would have let through: the
original abstract kept in 5 drafts (outside the main file or in a custom environment), author
blocks in non-standard forms, reviewer-comment macros named after authors, names glued to other
letters, a letter-by-letter acronym, a sentence repeating the title. All were fixed before the
probes; the batch-1 drafts were rebuilt byte-identical after the fixes.

## Primary analysis (id rule; no run discarded)

| Arm | Runs | Recall@30 key non-memory (primary) | @10 | key memory @30 | random non-memory @30 | all @30 | all @10 | Already cited | Cost/run | Web searches billed/run | Time/run |
|---|---|---|---|---|---|---|---|---|---|---|---|
| without | 70 | 0.159 | 0.136 | **0.922** | **0.167** | **0.588** | **0.486** | 0.6% | $1.27 | 7.4 | 113 s |
| v3.1 (offline confirmation) | 70 | **0.205** | 0.182 | 0.831 | 0.115 | 0.524 | 0.402 | 0.5% | $1.72 | 13.0 | 203 s |
| v2 (search method, live) | 35 | 0.227 | 0.182 | 0.819 | 0.125 | 0.543 | 0.390 | 0.7% | $2.29 | 17.3 | 152 s |

- **Primary**: v3.1 minus without = **+4.6 points** (bar +6: **not met**). Exact McNemar on 44
  (reference, run) pairs: 5 only-v3.1, 3 only-without, p = 0.73.
- **Secondary 1**: v3.1 minus v2 = -2.2 points (bar -3: met). v2 has one run per draft, so this
  is the least precise comparison: 22 pairs, one reference is 4.5 points.
- **Secondary 2**: v3.1 cost 0.75 of v2's (bar 0.70: **not met**).
- Every v3.1 run called `lookup-titles.py`; it made exactly 8 WebSearch calls per run, billed
  as 13 server searches.

## Sensitivities

- No run discarded: identical (the id rule discarded nothing).
- Protocol B's rule (id or 60% of title words): 9 runs discarded (3 v3.1, 4 without, 2 v2);
  v3.1 0.190 vs without 0.179, +1.1 points.

## Reading

- On 22 hard references the gain over the bare agent is +4.6 points, 5 discordant pairs
  against 3: noise-sized, and smaller than B2's +6. v2 does no better (+6.8 over without on one
  run per draft).
- **Both skill versions lose recall the bare agent has.** Without a skill the agent recovers
  92% of the key references it can name from memory and 59% of all removed references; with v3.1
  83% and 52%, with v2 82% and 54%. B2 showed the opposite (skill 0.886 vs 0.829 on memory key
  references). On these drafts, where two thirds of the removed references are memory-reachable,
  the search method displaces references the agent would otherwise list: its 30 slots fill with
  search hits.
- v3.1 is 25% cheaper than v2 per run, not the 30% the bar asked, and 35% dearer than the bare
  agent, which searched more here than in B2 (7.4 billed searches and $1.27 per run, against
  $0.94 per run in B2).
- The strict key rule made the primary measure small (22 references from 35 drafts). It is the
  rule for the next protocol to revisit, not the cost of drafts.

Per the protocol's outcome table: primary missed, v3.1 at or above v2 minus 3 points, so **v3.1
replaces v2 for its cost**, and its "Measured result" paragraph states that the gain was not
replicated. The cost secondary is also missed (0.75 against 0.70) and is stated there too.
