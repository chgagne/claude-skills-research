# Protocol B5: a foundations list the lookup requires

Written 2026-11-13, before the variant is built and before any B5 run. Target, bars and arms ruled by the
researcher in one interview the same day (journal `2026-11-13.md`).

## Question

In B4, v3.3 (the published skill) recovered 0.849 of the key references the agent can name from memory,
against 0.922 for the bare agent; 23 of its 25 misses were never written to `memory.txt`, which the step-2
wording limits to "the closest prior work". Asking in prose for the foundations as well (v3.4) failed on dev.
The proofreading series (W5) and C2 found that a step a script enforces is executed where the same step in
prose is not. **Does a foundations section that the lookup refuses to run without close the memory loss,
without losing hard references, at a similar cost?**

## The variant (branch `surveying-foundations`, from `main`)

- `memory.txt` gets two required sections: `## closest` (the current list, at least 10 titles) and
  `## foundations` (at least 5: the works the closest ones build on, i.e. the origin of the method, the
  datasets and benchmarks, the standard baselines). `lookup-titles.py` refuses to run when either section
  is missing or short, and tags foundation titles `[F]`.
- SKILL.md step 2 describes both sections; step 6 (the answer) keeps every `FOUND`, uncited `[F]` title
  eligible for the 30 like `[M]` ones. Nothing else changes.
- **Before building:** read the v3.4 dev traces (`private/v3dev/out/step0d.jsonl`) for why the prose request
  failed (open since 2026-10-26); the reading goes in the journal and may shape the wording, not the bars.
- **Dev gate:** the 10 dev drafts, 1 run each: the lookup's refusal fires when a section is missing (unit
  test) and every dev run writes both sections; reported, not scored as a decision.

## Arms and material

| arm | what it is |
|---|---|
| `foundations` | surveying-literature at `surveying-foundations`, frozen when the cases are built |
| `without` | the bare agent, **rerun on the same days** |
| v3.3, v3.1 | B4's and B3's stored runs, reported as reference only |

B3's 35 drafts, prompt, grants, model (`claude-opus-5-5`), limits, contamination rule (id), `gold-B3.json`,
`analyze.py`. **2 runs per draft and arm: 140 runs**, about $190. Gate 0.50/0.80, one case at a time.

## Measures and criteria (B4's, unchanged)

1. key/memory Recall@30 of `foundations` >= 0.892 and > 0.831. The 0.892 is B4's bar (B3 bare 0.922 - 0.03),
   kept fixed as ruled; the rerun bare value is reported beside it.
2. key/non-memory Recall@30 >= 0.175.
3. Cost per run <= $1.72.

Reported: all@30, all@10, `[F]` titles listed and returned, foundations among the misses, the same table with
no discard and under the title rule, and rerun bare against B3's bare (drift).

| Outcome | What follows |
|---|---|
| all met | merge `surveying-foundations`, measured line in SKILL.md |
| 1 met, 2 or 3 missed | report, decide with the researcher |
| 1 missed | report, no merge; diagnose the misses as in B4 |

## Frozen material

To be added as amendment 1 before the first test run.

## Amendment 1 (2026-11-13 19:53, after the dev gate, before any test run)

- **Why v3.4 failed (step 0d traces, read before building):** asking in prose for the foundations in the same
  list displaced closest work rather than adding to it. v3.4 listed about as many titles as v3.3 (median 28
  vs 26 `[M]` lookup lines), but only 10 of 21 key memory references reached the lookup as `[M]` (v3.3: 15),
  and 6 were never listed (v3.3: 3); its lists mix close work with distant generic classics. This supports the
  design as written: two sections with separate minimums, so the foundations add to the closest list.
- **Variant frozen at 76e1a30** (branch `surveying-foundations`): `survey/lookup.py` `parse_memory` and an `F`
  tag in `merge`; `lookup-titles.py` refuses without `## closest` (>= 10) and `## foundations` (>= 5); SKILL.md
  steps 2, 5 and 6. 115 tests pass. Frozen into `private/b3/run/b5/`, `_shared` from `main` into `run/b5sh/`.
- **Dev gate passed** (10 dev drafts, 1 run each): both sections written in every run, no refusal, `[F]` lines in
  every lookup, JSON block in every answer, $1.22-1.48 per run. Dev key/memory@30 0.81 (v3.4 0.714, v3.3 0.857,
  bare 0.833 on earlier days; 21 references, reported only).
- Test: `run/launch_b5.sh test`, one `with-without` call per draft (2 runs each arm), gate 0.50/0.80; scoring
  `analyze_b5.sh` (bare rerun named `without_b5`). Material hash over 723 files (`private/b3/FROZEN_B5.txt`):
  `30006ab568cb7afe2fcce6a6c8a065ba331b02351b4ad59dc4c37bd0822d09d4`.
