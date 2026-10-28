# Protocol B4 results: v3.3 narrows the memory loss by a fifth; criterion 1 missed (2026-10-28)

Protocol: `PROTOCOL-B4.md` (0f840a2). v3.3 frozen at 5fb46ed, 70 runs on B3's 35 drafts,
2026-10-27 to 2026-10-28 (paused overnight at the 7-day gate, resumed after the reset). No run
lost, no format failure, none discarded under the id rule. Compared with B3's existing runs.
Scores: `results/B4-primary.json`, `results/B4-nodiscard.json`, `results/B4-titlerule.json`.

| Arm | Runs | key/memory@30 | key/non-memory@30 | all@30 | all@10 | Cost/run | Time/run |
|---|---|---|---|---|---|---|---|
| without (B3) | 70 | **0.922** | 0.159 | **0.588** | **0.486** | $1.27 | 113 s |
| v3.1 (B3, published) | 70 | 0.831 | **0.205** | 0.524 | 0.402 | $1.72 | 203 s |
| v2 (B3) | 35 | 0.819 | 0.227 | 0.543 | 0.390 | $2.29 | 152 s |
| **v3.3** | 70 | 0.849 | 0.182 | 0.538 | 0.407 | **$1.31** | 200 s |

## Criterion

1. key/memory@30 >= 0.892 and > 0.831: **0.849, missed** (above v3.1 by 1.8 points, a fifth of the
   9.1-point gap to the bare agent).
2. key/non-memory@30 >= 0.175: 0.182, met (v3.1 0.205: one hit fewer in 44 pairs).
3. Cost <= $1.72: $1.31, met (24% cheaper than v3.1).

Same reading with no discard; under the title rule (13 runs discarded) v3.3 0.848, without 0.925.
Per the protocol, v3.3 is **not merged**.

## Where the remembered references were lost

`private/b3/diagnose_b4.py`. memory.txt was written and read by the lookup in all 70 runs, with 27
titles at the median (19 to 44). Of v3.3's 25 misses on key memory references, **23 were never in
memory.txt**; 2 were in it, printed `[M] FOUND`, and ranked out of the 30. The bare agent beats
v3.3 on 10 references, v3.3 beats it on 3. The ten are mostly foundational works the draft builds
on rather than its closest competitors: particle swarm optimisation (1995), Adam, cooperative
coevolution (1994), clearing (1996), nucleus sampling, AI Feynman. Step 2 asks for "the closest
prior work you can name"; asked to list what the paper should cite, the bare agent includes the
classics, the skill's memory list does not.

## Reading

The mechanism works (the list is always written and always survives into the lookup), and v3.3 is
the cheapest skill version measured. What it lists is the remaining problem: the memory list is
scoped to close competitors, so the foundational references the bare agent remembers never enter
it. This is a wording question about step 2, not a mechanism question; any rewording would need
its own measurement.
