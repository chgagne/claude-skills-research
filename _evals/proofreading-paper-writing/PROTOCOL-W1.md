# Protocol W1: proofreading-paper-writing, with and without the skill

Written 2026-11-05, before any scored case or run. Two 1+1 smokes on draft 54 (outside the test
set) checked feasibility only; their output is not scored. Design choices ruled by the researcher
in one AskUserQuestion round (journal 2026-11-05): deliverable prompt, plants + stability as the
two primaries, 6 drafts x 3 runs.

**Smoke 1 (findings-only prompt) and why the prompt asks for the deliverable.** Asked only for a
JSON list of proposals, the skill arm loaded the skill, read it, and declined its workflow ("You
asked for findings"): no subagents, glossary, noise gate or annotated copy; one pass like the bare
agent ($1.03 vs $1.08, 32 vs 41 proposals). Measuring that would measure the skill's description,
not its method. Both arms are therefore asked for the skill's documented deliverable (annotated
copy with tracked changes and a numbered writing report) plus the JSON block.

## Question

When an agent proofreads the writing of a real ML draft, does the skill make its proposals (a)
find more of a fixed set of known writing defects, (b) more consistent across repeated runs, and
(c) no more harmful to meaning, than the same agent without the skill?

The skill has never been measured. Following the consistency reframing
(`../SYNTHESIS-2026-11.md`), stability is measured alongside recall rather than recall alone.

## Configuration measured

Headless, no user. The skill's interactive steps cannot run: no calibration round (step 2), no
preference promotion (step 6), no Antidote pass (3b), no style profiles (the fresh HOME has none;
the prompt says none exists, so the skill runs on `reference/style-defaults.md`, its documented
fallback). This is the skill's floor configuration; a Mode A run with profiles and calibration
is not what W1 measures, and RESULTS will say so.

## Material

Six disguised, memory-probed drafts from the C2 pool, used unplanted in R3: 134, 179, 144, 177,
108, 116 (`private/w1/drafts/`). Writing is not what the probes were about, but the drafts are
real, compile, and have known structure.

**Plants.** Five writing defects per draft, written into a copy before any run, one of
each type, placed away from each other and from the abstract's first sentence:

| type | level | example of the rule |
|---|---|---|
| `agreement` | mechanics | subject-verb or article error in a body sentence ("the results shows") |
| `duplicate` | mechanics | duplicated function word across a line break ("the the") |
| `term` | framing | a defined term renamed once in a later section ("feature bank" -> "memory pool"), nowhere defined |
| `intensifier` | style | a sentence quoting a number in the results is rewritten to a vague intensifier ("by 1.2 points" -> "substantially"), the number still in the table |
| `undefined` | framing | an acronym introduced without expansion at its first use, expansion moved to a later section |

Plants were built by a Sonnet subagent with the rule text and checked by Claude by content (one
valid, unambiguous defect; no other change; each original and new string unique). **29 plants**:
draft 116's `undefined` plant was dropped because 116 already uses its only expanded acronyms
(ISR, LRA) before their definition, so the plant would not be the only defect of its kind and
the draft has no clean alternative (`private/w1/plants/116_undefined_dropped.json`). Where the
draft has no mid-sentence line break the `duplicate` plant is in-line (116). In 179 and 177 the
acronym had two expansions; the first was removed rather than moved. A plant is "found" when a proposal's located span is within 2
lines of the plant and its content addresses that defect (arm-blind, by content).

## Arms and runs

| arm | what it is |
|---|---|
| `skill` | proofreading-paper-writing frozen at 21831f0 (`private/w1/run/skill/`), `_shared` installed |
| `without` | same agent, no skill |

claude-opus-5-5; tools Read, Write, Edit, Bash, Glob, Grep, Skill, Agent; no web tools; 60 min,
200 turns. **3 runs per arm per draft: 36 runs**; smoke 2: skill $2.64 / 8 min, bare $1.85 / 5 min,
projected ~$81 (Claude returns to the researcher if the projected total exceeds $150). In smoke 2
the skill arm ran its whole workflow in one agent (no subagent) and rendered with
`render-ledger.py`; that is the configuration measured. Prompt identical in both arms
(`private/w1/make_cases_deliver.py`): the deliverable request, then a JSON block of proposals
`{draft_quote, level, proposed, reason}`. Scoring uses the JSON block in both arms.

## Measures

1. **Plant recall.** Found plants / 30 per run, averaged per arm; by type.
2. **Stability.** Within a draft, across its 3 runs: two proposals from different runs match when
   their located `draft_quote` spans overlap or lie within 1 line. Pairwise agreement = matched
   proposals / all proposals over the 3 run pairs, averaged over drafts. Also the core share
   (proposals present in all 3 runs, over distinct proposals). Plants excluded.
3. **Harm (scripted; may be uninformative: 0 of 21 and 0 of 31 replacements flagged in smoke 2).** Among proposals with a non-empty `proposed`: share that drop a number, a
   `\cite`/`\ref` command, or a hedge word (fixed lexicon: may, might, could, suggest(s), likely,
   possibly, approximately, roughly, appear(s), seem(s)) present in `draft_quote`. Sentence-level
   rewrites that move the number elsewhere count as a drop only if the number is absent from
   `proposed`.
4. **Precision (judged, reported).** 15 proposals sampled per run, judged by Sonnet 5.5 with no
   arm label and skill vocabulary masked (W-ids, `LG`, level names kept since both arms use them):
   real defect and improving fix / real defect, bad fix / not a defect / meaning changed.
5. Reported: proposals per run (by level), cost and time, whether the skill loaded, whether an
   annotated PDF was built (skill arm only).

## Criteria

- **Primary:** plant recall, skill minus without, **at least +0.15** (pooled, 90 plant-runs per
  arm).
- **Primary (consistency):** pairwise agreement, skill minus without, **at least +0.10**.
- **Guard:** scripted harm share, skill **at most** without + 0.02.
- Secondary: precision (judged), cost (skill at most 3x without, reported).

| Outcome | What follows |
|---|---|
| both primaries and guard met | measured line in SKILL.md |
| recall met, consistency not | measured line; a W2 on structure (fixed pass order the agent must answer) |
| neither primary met, guard met | reduce the skill to what the trace shows the agent actually used (as P2, D4), validate non-inferiority |
| guard missed | read the traces before anything else |

## Analysis notes

Paired by draft (6 drafts); per-draft differences reported, sign test (direction only). McNemar
on plant-runs paired by (plant, run index). Span matching can merge two proposals in one
sentence; both arms carry the same bias, and the skill's per-paragraph caps make it propose fewer
rows, which lowers its chance agreement: proposals per run are reported beside agreement.

## Frozen material

Scorer `private/w1/score_w1.py` (selftest passes; refuses to score before 36 runs and a verdict for
every on-span proposal), plant applier `apply_plants.py`, prompt `make_cases_deliver.py`, launcher
`launch_test.sh` (usage gate 0.40 / 0.75). SHA-256 over the sorted per-file hashes of
`cases/w1_*`, `cases_meta/`, `plants/`, the three scripts, the launcher and the frozen skill copy:
`415a24f6ff3876fc211c1d143d631bbfe9d1410c889b1ecbb6eb8e3bb767c5b8`. The locator found every quote
of both smoke-2 arms (34/34, 38/38). Run directories are sealed after a run, so deliverables are
not kept; scoring uses the JSON block in both arms.
