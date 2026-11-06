# Protocol W2: a reduced proofreading-paper-writing, non-inferiority on W1's cases

Written 2026-11-05, before any change to the skill and before any W2 run. Scope and bars ruled by
the researcher (AskUserQuestion, journal 2026-11-05): single-pass core plus a short user branch;
P2-style non-inferiority bars.

## Why

W1 (`RESULTS-W1.md`): the skill met neither primary; its only measured gain is the intensifier
rule. Its traces (18 skill runs) show what the agent uses: the critique rubric (17/18), ledger
schema, style defaults, the `LG` author and preamble, `render-ledger.py`, the `id=LG` count and a
page render (18/18). Rarely or never: the glossary (4/18), the report template (4/18), the subagent
pipeline (1/18, appendix only), profile building, Antidote and `md2pdf` (0/18). Calibration cannot
run headless. Outcome row "neither primary met, guard met" calls for a reduction to what is used,
validated for non-inferiority (as P2, D4).

## The reduced skill (branch `proofread-reduce`, written after this protocol is committed)

- The default workflow is the single pass the traces show: read the rubric, defaults and schema;
  read the paper end to end; write ledger rows at all four levels; gate them with the rubric's five
  questions and the caps; render with `render-ledger.py`; check with `grep -c 'id=LG'` and a page
  render; hand back.
- A short "when a user is present" section keeps calibration, style profiles, preferences and the
  Antidote offer, pointing to their reference files.
- The subagent fan-out (global reader, section workers, noise gate as separate agents) is removed;
  its text moves to `reference/design-notes.md`. Hard rules and "Findings that recur" are kept.
- Scripts, rubric, schema and defaults unchanged.

## Material and runs

W1's six planted cases (`private/w1/cases/w1_*`, 29 plants), W1's prompt and settings
(claude-opus-5-5, tools incl. Agent, 60 min, 200 turns), **reduced arm only, 3 runs per draft: 18
runs** (~$47). Compared with W1's skill arm (full skill, 21831f0). Same scorer
(`score_w1.py`, with a `--arm-dir` option that reads W2 runs), same verdict procedure (content,
arm-blind, the prefilter plus a search of every missed plant-run), same Sonnet precision judge
(15 sampled proposals per run, seeded as in W1).

## Criteria (all must hold)

| measure | bar (W1 full skill value) |
|---|---|
| plant recall | >= 0.893 (0.943 - 0.05) |
| intensifier recall | >= 15/18 (W1 17/18) |
| pairwise agreement across runs | >= 0.767 (0.817 - 0.05) |
| judged harmful (bad fix + meaning changed) | <= 15 of 270 (1.5 x 10) |
| cost per run | <= $2.86 (1.1 x $2.60) |

Reported: proposals per run, levels, judged precision, skill invoked, the annotated PDF built.

| Outcome | What follows |
|---|---|
| all bars met | merge the reduction; measured line in SKILL.md |
| a bar missed | read the traces for the cause, report to the researcher; no automatic revert or retuning |

## Caveat

Same cases as W1, which motivated the reduction: W2 shows the reduction loses nothing measured on
these drafts, not that it generalises. W1's arm ran on an earlier date; run-to-run noise between
days is not separated from the change.
