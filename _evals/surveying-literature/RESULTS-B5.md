# Protocol B5 results: the foundations section narrows the memory loss further; criteria 1 and 2 missed (2026-11-21)

Protocol: `PROTOCOL-B5.md` (amendment 1, frozen material hash `30006ab5`). Variant `foundations`
frozen at 76e1a30 (branch `surveying-foundations`), 70 runs on B3's 35 drafts, each draft run in one
with-without call with the bare agent (`without_b5`, 70 runs) the same day. Scores:
`private/b3/runs/B5-primary.json`, `B5-nodiscard.json`, `B5-titlerule.json`; recount and miss reading
`private/b3/diagnose_b5.py`.

**The campaign was run twice for 19 drafts.** The first attempt (2026-11-13/14, 76 runs) was paused at the
7-day gate; macOS purged its traces from `/private/tmp` on 2026-11-18, before extraction, so those runs
could not be scored and were rerun on 2026-11-21 (researcher's decision; results of the lost attempt
moved to `run/out/b5/lost-2026-11-14/`, never scored). Final runs: 16 drafts on 2026-11-20/21, 19 drafts
on 2026-11-21. Guard added: `_harness/persist_traces.py` after every draft, `extract.py` refuses a
missing trace. Total spend about $220 (of which $79 lost).

| Arm | Runs | key/memory@30 | key/non-memory@30 | all@30 | all@10 | Cost/run | Time/run |
|---|---|---|---|---|---|---|---|
| without_b5 (same day) | 70 | **0.928** | 0.136 | **0.576** | **0.476** | $1.19 | 147 s |
| without (B3) | 70 | 0.922 | 0.159 | 0.588 | 0.486 | $1.27 | 113 s |
| v3.1 (B3) | 70 | 0.831 | **0.205** | 0.524 | 0.402 | $1.72 | 203 s |
| v3.3 (B4) | 70 | 0.849 | 0.182 | 0.538 | 0.407 | $1.31 | 200 s |
| **foundations** | 70 | 0.873 | 0.159 | 0.529 | 0.376 | $1.34 | 372 s |

key/memory counts: foundations 145/166, same-day bare 154/166, v3.3 141/166 (recounted from the raw runs
by `diagnose_b5.py`, identical to `analyze.py`). key/non-memory: 7/44, 6/44, 8/44.

## Criteria

1. key/memory@30 >= 0.892 and > 0.831: **0.873, missed** (above v3.3 by 2.4 points; still 5.5 points
   below the same-day bare agent, paired 4 vs 13, exact McNemar p = 0.049).
2. key/non-memory@30 >= 0.175: **0.159, missed** (one hit fewer than v3.3 in 44 pairs; 7 vs 6 for bare).
3. Cost <= $1.72: $1.34, met. Time per run nearly doubles (372 s vs 200 s for v3.3).

Same reading with no discard (none discarded under the id rule); under the title rule (20 runs
discarded across arms) foundations 0.875, same-day bare 0.925. Bare drift between B3 and B5: 0.922 ->
0.928 on key memory, 0.159 -> 0.136 on non-memory (one hit): stable. Per the outcome table (criterion 1
missed), **not merged**.

**One timeout.** Run 1 of 2610.06993 (foundations) hit the 40-minute limit and scores zero, as the frozen
setup and the scorer have done for every arm since B3. Crossref and arXiv were slow at that hour (the bare
runs on the same draft took 945 s and 1257 s against a 147 s mean); the lookup script buffers its output,
the agent piped it through `tail`, the 10-minute Bash limit killed it with nothing saved, and the rerun was
still silent at the deadline. Excluding that run (sensitivity only, not the verdict): key/memory 145/164 =
0.884, still below 0.892; non-memory 7/43 = 0.163, still below 0.175. The outcome does not depend on it.

## Where the remembered references were lost

memory.txt was written with both sections in all 70 runs (closest median 17 titles, 11 to 31; foundations
median 11, 5 to 23) and `[F]` lines reached the lookup in all 70. Of foundations' 21 misses on key memory
references, **16 were never in memory.txt** (v3.3: 23 of 25), 2 were in the foundations section and 2 in
closest but not found by the lookup, 1 was found by the lookup and left out of the final list. The same-day bare agent beats
foundations on 11 references, foundations beats it on 3.

Read by eye, the never-listed misses are of two kinds. Close work left out of a 17-title closest list
(reinforcement symbolic regression, AI Feynman, latent-preference adaptive decoding, an auto-steering
diffusion method). And domain classics outside machine learning: Gillespie's exact stochastic simulation
(1977), Holmes et al. on turbulence and coherent structures (1996), cooperative coevolution (1994),
Facebook's Dynamo power manager (2016), self-learning kinetic Monte Carlo (2005). The foundations sections
that missed them were often filled with generic machine-learning staples (PPO, "Attention is all you
need", LSTM, DPO) rather than what the draft's own field builds on.

## Reading

The structural fix did what it was built to do: the second section is always written, always reaches the
lookup, and cuts the never-listed misses from 23 to 16. The recall gain is smaller than the listing gain
(4 references) and does not reach the bar; the bare agent, asked plainly what the paper should cite,
still names the domain classics more often. What the foundations list contains is now the limit: the agent
fills it with whatever is foundational to ML in general. Separately, the lookup's buffered output turns a
slow API into a lost run; that is an engineering defect in a shared script, independent of B5's verdict.
