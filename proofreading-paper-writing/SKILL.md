---
name: proofreading-paper-writing
description: Use when asked to proofread, polish, or critique the writing of an academic paper from its LaTeX sources — grammar and mechanics, sentence clarity and style, paragraph flow, terminology and framing — and deliver the proposals as coloured track changes with margin comments plus a numbered writing report. Triggers on "proofread the writing", "polish the prose", "check the style of my draft", "why does this read oddly", "odd formulations", or as phase 7b of reviewing-paper-sources.
---

# Proofreading Paper Writing

## Overview

A critical reader for the prose of an ML paper. Each sentence, paragraph and framing choice is
judged against a rubric of defects (`reference/critique-rubric.md`) and the conventions in
`reference/style-defaults.md`, or a field and author profile when the user has them. Proposals
become a second `changes.sty` author, `LG`, in dark green, next to the blue science author `CL`
that `reviewing-paper-sources` uses, so a reader sees at a glance which marks are about the
science and which about the writing.

Four levels, tiered in the PDF: **mechanics** as bare track changes, **style** as track changes
with a `W<n>` margin tag, **flow** and **framing** as margin comments only. Every `W<n>` is an
entry in `writing-report.md`.

**Measured (headless, style defaults, no calibration; 6 drafts, 29 planted defects, 3 runs).**
Against the bare agent the skill gains only on intensifiers standing in for a table number (0.94 vs
0.39); recall 0.94 vs 0.85 overall, no gain in run-to-run consistency, fewer proposals and fewer
judged-harmful edits (W1). This single-pass workflow matched the earlier multi-agent text on the
same cases (W2: recall 0.93 vs 0.94, consistency 0.84 vs 0.82, same cost). On fresh unplanted
drafts that version covered fewer judged-real defects than the bare agent (0.44 vs 0.68, W3): it wrote
fewer rows because "no rule, no row" kept it inside the style defaults. The open criterion below raised
coverage to 0.55 against 0.44 at the same judged-harm rate (0.081 vs 0.078); the bare agent still covers
more (0.65), mostly mechanics and notation (W4). The calibrated, profile-based mode is not measured.

## Inputs and outputs

Input: a paper directory with a compiling `main.tex` (or another main file, or the pdfshim
pseudo-source), optionally an existing `main-annotated.tex` from the reviewer. Outputs, all in the
paper directory, none committed:

| File | Content |
|---|---|
| `main-annotated.tex` / `.pdf` | existing `CL` markup plus `LG` markup |
| `writing-report.md` | header, counts, one entry per `W<n>`, cut list |
| `writing-ledger.jsonl` | every proposal with its final status |

## Workflow

**0. Mode.** Mode A (internal, authors will see the copy) runs everything below. Mode B (external
referee) runs steps 1-2 only and writes its top ten findings as prose into the review's §8; no
annotated copy. If a user is present, see "When a user is present" before step 1.

**1. Read.** Read `reference/critique-rubric.md`, `reference/style-defaults.md` and
`reference/ledger-schema.md`, then the paper end to end before writing any row. Note the paper-wide
conventions it already follows (spelling variant, tense per section, first person,
cross-reference form) and every coined term with where it is first defined and every variant
found: the most useful framing rows come from two names for one concept and terms used before
they are defined.

**2. Write the ledger.** One row per defect in `writing-ledger.jsonl`, ids `W1`, `W2`, ... The
four levels and what belongs in each are in the rubric. Flow and framing rows are anchored at the
first sentence of the paragraph. Rules for every row:

> Copy every anchor from the tex, whole tokens, unique in the file; extend to the full sentence if
> a phrase recurs. Never anchor inside \cite, math, tabular, \resizebox, \footnote or existing \ch
> markup: comment on the paragraph and put the rewrite in the rationale. Write a row for anything
> a careful copy editor at an ML venue would change: errors, unclear or wrong wording, notation and
> symbols, captions or tables that disagree with the text, claims the evidence does not carry. Cite
> a default, profile or preference when one fits; otherwise set `rule` to `clarity: <one line on
> what a reader would stumble on>`. Keep every number, citation and hedge the sentence had. Do not
> touch text already inside \chreplaced, \chadded or \chdeleted.

**3. Gate.** Go through every row with the five questions at the end of the rubric and set
`status` to `kept` or `cut` with a `cut_reason`. Enforce the caps (style <= 2 per paragraph; flow +
framing <= 1 per paragraph and <= 25 total; mechanics uncapped), cutting lowest confidence first.
Keep a row when you can say what a reader would stumble on; cut one that is only taste. Never edit
a row's text at this step.

**4. Render.**

```
python3 assets/render-ledger.py --ledger writing-ledger.jsonl \
  --tex main-annotated.tex --out main-annotated.tex --report writing-report.md \
  --paper main.tex --mode A [--field-profile <slug> --author-profile <slug>] \
  [--run-rule "..."] [--forbid-ulem]
```

Use `--tex main.tex` when no annotated copy exists. The input must never already carry `LG`
markup: the renderer refuses it, because a second pass onto its own output degrades every row as
inside markup and doubles the comments. Keep a science-only copy and render from that. Pass
`--forbid-ulem` when `grep -n forbidden *.sty *.cls` names `ulem`. The script inserts the
`changes` preamble if missing, adds the `LG` author, frees a paper-defined `\todo`, applies kept
rows, degrades unsafe ones to comments, compiles the markup build and the accept-all build in
`.lg-build/`, and bisects by level if the markup build fails. Exit 2 means a level was dropped or
the accept-all build failed: read the report header and say so to the user.

**Run it from the paper directory, and check the output rather than the exit line.** The build
resolves the class, the figures and the `.bib` relative to the output file, so an `--out` under
`review-assets/` fails with `aaai2027.sty not found` before any row is tried. The printed counts
come from the row statuses, which the renderer writes back into the ledger: they say what the rows
claim, not what this run did. `grep -c 'id=LG' <out>.tex` is the check that cannot lie to you.
Then render two or three pages of the markup PDF and look at them: markup that compiles can still
be unreadable.

**When the bisect drops a level, find the one bad row instead of accepting the loss.** Re-render
with `--no-build`, compile that tex yourself, and read the first error. On one paper a stray `^` in
one margin comment dropped 21 of 167 rows, and the error named neither the row nor the level: a
margin note is typeset inside todonotes' tikzpicture, so an out-of-math superscript surfaces as
`\begin{tikzpicture} ended by \end{document}` a thousand lines later.

**5. Hand back.** Counts by level, how many degraded and why, the builds, the conventions or
profiles used, and the three framing findings you consider most important. Offer the PDF and the
report.

## When a user is present

- **Profiles.** If `$STYLE_PROFILES_DIR` (default `~/Claude/style-profiles`) has a field profile
  for this subfield or an author profile for these authors, use them: field decides what is a
  defect, author decides the wording of the fix. If not, offer to build them
  (`reference/building-style-profiles.md`); if declined, run on the defaults and say so in the
  report header. Read `preferences.md` there; every rule in it binds every row.
- **Calibration (Mode A).** After step 2, show about ten rows (2 mechanics / 5 style / 2 flow / 1
  framing, from the abstract and the densest body section) in **one** AskUserQuestion round as
  before -> after with the reason; options accept / reject / rewrite. Turn the answers into run
  rules (`run:1...`), apply them in step 3 and pass them to the renderer. Ask once. Whenever a
  consistent draft disagrees with a stored preference (spelling especially), ask in this round: a
  co-authored paper usually keeps its own.
- **Preferences.** After the hand-back, write candidate rules from rejections and rewrites to
  `preferences-pending.md` (date, paper slug, rule) and ask once whether to promote each. Never
  promote silently.
- **Antidote (Mode A).** If `/Applications/Antidote` exists, offer the pass in the first question
  round: `reference/antidote-pass.md`. The corrected copy is only ever diffed, never rendered.

## Hard rules

- Never modify `main.tex`; the renderer refuses that output name.
- Never commit paper artifacts or write anything from the paper into this repository or into a
  profile.
- Every `style` row says why: a default, profile or preference key, or `clarity: <why>`.
- `LG` never edits inside `CL` markup; overlaps become comments.
- The cut list is always published. Silence about a cut is a defect.
- Never install pandoc or LaTeX. Missing tools are a question for the user.
- A build that did not happen is reported as "not run", never as passed.

## Findings that recur

- The same concept under two names across sections, one of them introduced in a figure caption
  only. Framing row; the term list from step 1 is how you catch it.
- An intensifier standing in for a number that a table already gives.
- Hedges removed from a limitations paragraph. The gate must catch this.
- Anchors copied from the PDF instead of the tex: ligatures and `~` make them unanchored.
- Editing a bare macro (`\backto{}`) or a section heading, and quoting `\citet` inside a comment:
  the renderer degrades or escapes them, and the report lists each as `degraded` with its reason.
- The accept-all `[final]` build can fail where the markup build passes; treat the markup build as
  the deliverable and report the other honestly.
- A run rule is about one property of a row: before cutting a row under it, ask whether the row
  survives with that property changed.
- Paper-defined macros in a replacement (`\ourmodel{}`) degrade the row to a comment. Expect a
  handful per paper and say so in the hand-back.

## Quick reference

`assets/`: `render-ledger.py`, `antidote-rows.py`, `profile-stats.py`, `fetch-corpus.py`,
`changes-author-LG.tex`, `proofread/`. `reference/`: `critique-rubric.md`, `style-defaults.md`,
`ledger-schema.md`, `writing-report-template.md`, `building-style-profiles.md`,
`antidote-pass.md`, `design-notes.md` (the removed multi-agent workflow and why). Preamble source:
`reviewing-paper-sources/assets/changes-preamble.tex`; recipe and gotchas:
`reviewing-paper-sources/reference/annotating-with-changes.md`.
Tests: `cd assets && python3 -m unittest discover -s tests`.
