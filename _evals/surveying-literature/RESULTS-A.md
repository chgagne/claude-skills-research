# Protocol A results: baseline on the test set (2026-10-09)

Protocol: `PROTOCOL-A.md`, pushed at 6f52569 before the first scored run; analysis code
committed at 45d3f61 before any scored data was read. 200 runs (60 per agent arm, 20 script),
`claude-opus-5-5`, about $214 in model cost. Scores: `results/A-primary.json`,
`results/A-sensitivity.json`. Gold labels stay private until protocol B has run on the same
test set, because a run with web search could otherwise find them.

## Primary analysis (contamination rule as written; 9 runs discarded)

| Arm | Runs | Recall@30 key non-memory (primary) | @10 | Recall@30 random non-memory | key memory | Already cited | Cost/run | Time/run |
|---|---|---|---|---|---|---|---|---|
| without | 58 | **0.397** | 0.397 | 0.053 | 0.905 | 0.2% | $0.89 | 90 s |
| skill | 55 | **0.377** | 0.283 | 0.043 | 0.893 | 0.6% | $1.17 | 492 s |
| self | 58 | **0.414** | 0.414 | 0.116 | 0.914 | 0.5% | $1.14 | 600 s |
| script | 20 | **0.050** | 0.050 | 0.061 | 0.175 | 1.2% | $0 | 361 s |

Skill minus without: **-2.0 points** (criterion 1 needs +15: fails). Already-cited share 0.6%
against 0.2% (criterion 2: fails). Exact McNemar on 324 (reference, run) pairs: 3 only-skill,
3 only-without, p = 1.0. Skill minus self: -3.7 points.

**Verdict under the protocol: not a success.**

Sensitivity, no run discarded: without 0.383, skill 0.400, self 0.400, script 0.050; gap +1.7
points, McNemar 4 vs 3, p = 1.0. The conclusion does not depend on the discards.

## What the runs show

- **The bare agent is the strong baseline.** It ran 90 s, made about 4 web searches, and
  recovered 40% of the key prior work that the no-tool probe could not name, plus 90% of the
  memory-reachable ones. Knowing the field and asking a few precise queries does most of the work.
- **The sweep contributes almost nothing on its own.** Run alone, `run-survey.py` puts a removed
  reference in its top 30 for 5% of key prior work and 11% of all removed references, although
  it returns 1,000 to 2,600 candidates per draft. The skill arm spends five times longer than the
  bare agent, mostly in the sweep, for the same recall, and its top-10 recall is lower (0.283
  against 0.397): mixing sweep output into the list pushes good candidates down.
- **Every sweep reported degraded coverage** (about 6 Semantic Scholar and DBLP failures per run).
  Retrieval is fragile, but the script-only figure is too low for failures alone to explain it.
- The self-written skill is no worse than the bare agent and no better than the product skill.
- **Semantic Scholar key state.** During the baseline the circuit never opened and S2 failures
  stayed moderate (median 4 per skill run, 7 per script run, of roughly 200 S2 requests). After
  the baseline the key degraded further: by the dev diagnosis it answered 429 to every request,
  even spaced 5 s apart, while anonymous requests passed. The baseline therefore measured the
  sweep with a partly throttled key; the retry layer now falls back to anonymous requests on a
  keyed 429 (tested on the dev set before protocol B).

## Deviations, all decided before reading the scores

1. **33 runs hit the account's session limit** (an infrastructure error, not an agent failure),
   all in the last four test cases alphabetically. Rule applied: every run of any affected case
   was redone in every arm (36 runs) after the limit reset; the failed runs were dropped, not
   scored as zero.
2. **The contamination check was narrower in the protocol's words than in its first
   implementation.** The rule says a run is discarded when the agent *requests* the source by
   arXiv id or DOI. The first checker flagged any shell command containing the id, which caught
   15 self-arm runs that only wrote "the draft appears on arXiv as <id>" into their reports; no run
   fetched the source by id. The checker now counts an id only inside a network request. The
   60%-of-title-words rule for WebSearch was kept as written, although it flags generic queries on
   one short title (2610.01583, 5 runs across all arms); 4 skill runs genuinely searched the source's
   exact title after the sweep surfaced it.
3. The script arm ran with the live `_shared`, which differs from the frozen one only by the added
   `post_json` (unused by the frozen sweep).

## Next

The improvement loop on the dev set (`PLAN.md`): diagnose whether removed references are in the
sweep's pool at all and at what rank, then test the opt-in variants (`--seedset`, `--rank coupling`,
`--angles`), then protocol B on this same frozen test set.
