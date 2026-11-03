# Protocol R1: reviewing-paper-sources against the bare agent, planted internal inconsistencies

Written 2026-11-02, before any R1 plant, case or run. The researcher chose this skill first among
the three never measured, "planted defects first, then a documented-defect probe", and a
calibration-only stage 1. The other defaults below are Claude's and are marked as such.

## Why

reviewing-paper-sources is the orchestrator the researcher uses most and has never been compared
with the bare agent. Its sibling skills were measured one by one (bibliography, literature,
proofs, comparison); this protocol measures the core review itself, with the sibling modules off.
Its "Findings that recur" list names several checks that need only the paper: does the appendix
concede what the main text sells, do ranking gaps survive the paper's own variance, does a derived
number match the table it came from. Those are the plant types. Past series (C1, P1, D) found the
bare agent at ceiling on obvious plants, so stage 1 calibrates the plants on the bare agent first.

## Material (Claude's default)

Disguised drafts already built and memory-probed for C2 (`_evals/comparing-papers/private/c2/
drafts/`, probe 36/36 "don't know"), used here **without** any C2 plant. Their competitor papers
play no role.

- **Dev (stage 1):** drafts 54, 93, 134, 179 (never planted in C2; each has results tables and an
  appendix or supplementary tables).
- **Test (stage 2, if triggered):** the next 8 eligible drafts in C2 screening order among 109,
  144, 152, 177, 133, 153, then C2's test drafts 108, 115, 116, 135, 140, 148, 156, 161 (original
  disguised text, not the C2 cases). Eligible = at least two results tables and a natural plant
  site for a kept type.

## Plant types

Each plant contradicts something **in the same draft**, checkable from the draft alone.

- `prose`: a number stated in the prose (abstract, introduction, discussion, conclusion) disagrees
  with the paper's own results table, and the disagreement appears only after arithmetic (an
  average over columns, a difference, a relative improvement). Edit the prose, not the table.
- `appendix`: a general claim in the main text ("on every benchmark", "consistently", "across all
  seeds") contradicted by one entry of an appendix or supplementary table. Plant by broadening the
  claim or by changing one cell so that it becomes one exception; keep all other mentions
  consistent.
- `variance`: the main text calls a gap clear, significant or robust while the paper's own
  reported spread (std, CI, per-seed values) is larger than the gap. Plant by changing the spread
  values or the wording, not by inventing a new table.

Rules for every plant (as in C1, adapted): at most 3 lines change; the original location is
consistent (checked); no plant within 3 lines of a natural inconsistency; keep the draft's style;
no attention words ("notably", "importantly"); a number repeated elsewhere is changed everywhere
or another number is picked. Proposals by subagents (model sonnet), each checked by Claude
against the file before acceptance; decisions recorded in `private/r1/plants/decisions.json`.

## Arms

| arm | what it is |
|---|---|
| `skill` | reviewing-paper-sources at the commit frozen when test cases are built, `_shared` installed |
| `without` | the same agent, no skill |

Model claude-opus-5-5. Tools Read, Write, Edit, Bash, Glob, Grep, Skill; **no web tools in either
arm** (the plants are internal; Claude's default, like P1). Timeout 40 min, 150 turns.

Prompt, identical in both arms:

> A co-author's draft is in `paper.tex` (LaTeX source, with its bibliography files, in the working
> directory). Review it before submission as an internal reviewer from the same group. This review
> is about the paper itself: do not verify the bibliography, search for related work or compare
> with other papers. There is no one to answer questions; make reasonable choices and say what you
> chose. Write the review to `review.md`.
>
> End your answer with one JSON block listing every issue you found, and an empty list if you
> found none:
>
> ```json
> {"issues": [{"draft_quote": "at least 20 characters copied verbatim from paper.tex",
>              "problem": "what is wrong", "severity": "critical|major|minor"}]}
> ```

## Hit rule

A run hits a plant when one issue's `draft_quote` matches (fuzzy, as C1's scorer) within 3 lines
of the planted span **or** of the counterpart it contradicts (the table cells, appendix row or
spread values named in the plant record), and its `problem` names the discrepancy and its
direction. Located candidates are judged by content, arm-blind. Issues elsewhere that name the
plant by content are counted as a secondary "by content" figure, as in C2.

## Stage 1: bare calibration (this protocol's only committed spend)

4 dev drafts x 3 types = 12 plants, `without` arm only, 2 runs each: **24 runs**. Smoke first: one
`without` run and one `skill` run on an unplanted dev draft (not counted), to measure cost and
check that the JSON block and `review.md` are produced.

Keep rule: a type is kept for test if bare recall on it is **at most 6/8**. If no type is kept,
one tightened round on the same dev drafts (subtler variants, rules written before it runs), then
to the researcher before anything else.

## Stage 2 trigger (written now, runs only after the researcher sees stage 1)

At least one type kept -> test: 8 test drafts, one plant each, kept types rotated, `skill` vs
`without`, 3 runs per arm per draft (48 runs).

- **Primary:** recall, skill minus without, at least +0.15 (McNemar on paired runs reported).
- **Secondary:** false issues per run (arm-blind adjudication of a fixed sample of issues per run),
  skill at most 1.5 x without; cost per run reported.

| Outcome | What follows |
|---|---|
| primary and secondary met | measured line in SKILL.md |
| primary met, secondary missed | read the false issues before writing the line |
| primary not met | report; discuss reducing the core workflow with the researcher, no automatic change |

## Stage 3: documented-defect probe (after stage 2, defined before it runs)

Two or three papers with a published erratum or withdrawal notice naming an internal
inconsistency (a table vs text, an appendix vs claim). Both arms, 2 runs each, direction only.
