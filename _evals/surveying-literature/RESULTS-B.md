# Protocol B results: the search-method skill on the frozen test set (2026-10-10)

Protocol: `PROTOCOL-B.md`, pushed at cbbdecb before any protocol-B run; skill frozen at d6d64fa;
analysis code unchanged since protocol A. 120 runs (60 skill, 60 without) in one with-without
call, about $183 in model cost. Scores: `results/B-primary.json`, `results/B-sensitivity.json`.
Gold labels are now published in `gold.json`; the drafts stay private (arXiv source licences).

## Primary analysis (contamination rule as written; 12 runs discarded)

| Arm | Runs | Recall@30 key non-memory (primary) | @10 | key memory @30 | all @30 | all @10 | Already cited | Cost/run | Time/run |
|---|---|---|---|---|---|---|---|---|---|
| without | 57 | 0.340 | 0.302 | 0.915 | 0.558 | 0.439 | 0.4% | $0.83 | 161 s |
| skill (search method) | 51 | **0.521** | 0.354 | 0.857 | 0.542 | 0.369 | 0.1% | $2.12 | 285 s |

Skill minus without: **+18.1 points** (criterion 1, +15: met). Already-cited share 0.1% against
0.4% (criterion 2: met). Exact McNemar on 300 (reference, run) pairs: 7 only-skill, 1 only-without,
p = 0.07. **Verdict under the protocol: success.**

## Sensitivity: no run discarded

without 0.400, skill 0.517: **+11.7 points**, below the 15-point bar; McNemar 8 vs 1, p = 0.04.
The protocol's verdict therefore rests partly on the discards. The 60%-of-title-words rule
removed 9 skill runs and 3 without runs; the without runs it removed had searched close to the
source's title and scored high, which lowers the without arm in the primary analysis. Read
together: the search method raises recall on hard references by **12 to 18 points**, and the
lower bound does not clear the bar the protocol set.

## What changed, and what it costs

- **Gain where it matters.** Key prior work the model could not name from memory: 0.52 against
  0.34-0.40. These are the references a user is least likely to know already.
- **Loss on the easy ones.** References the model knows from memory: key 0.857 against 0.915,
  random 0.652 against 0.769. With 30 slots, the skill trades some well-known citations for
  harder ones, so overall Recall@30 is flat (0.542 against 0.558) and Recall@10 lower.
- **Cost.** $2.12 against $0.83 per run, 285 s against 161 s.
- One test draft (2609.39272) timed out at 40 minutes in 3 skill runs and 1 without run; per the
  protocol a run with no list scores zero.
- Compared with protocol A: the without arm is stable (0.397 in A, 0.340-0.400 here); the original
  script-first skill scored 0.377 in A.

## Status

The skill as it now stands (search method, script optional) is the measured improvement. Whether
its gain survives without the contamination rule's help is the open question; a stage with more
drafts, or a narrower title rule written before running, would settle it.
