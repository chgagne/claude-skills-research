---
name: proofreading-paper-writing
description: Use when asked to proofread, polish, or critique the writing of an academic paper from its LaTeX sources — grammar and mechanics, sentence clarity and style, paragraph flow, terminology and framing — and deliver the proposals as coloured track changes with margin comments plus a numbered writing report. Triggers on "proofread the writing", "polish the prose", "check the style of my draft", "why does this read oddly", "odd formulations", or as phase 7b of reviewing-paper-sources.
---

# Proofreading Paper Writing

## Overview

A critical reader for the prose of an ML paper. It judges each sentence, paragraph and
framing choice against a **field profile** (what well-written papers at the venue do) and
phrases fixes in the **author profile** (how these authors write when they write well).
Field decides what is a defect; author decides the wording of the fix. Proposals become a
second `changes.sty` author, `LG`, in dark green, next to the blue science author `CL`
that `reviewing-paper-sources` uses, so a reader sees at a glance which marks are about
the science and which about the writing.

Four levels, tiered in the PDF: **mechanics** as bare track changes, **style** as track
changes with a `W<n>` margin tag, **flow** and **framing** as margin comments only. Every
`W<n>` is an entry in `writing-report.md`.

## Inputs and outputs

Input: a paper directory with a compiling `main.tex` (or the pdfshim pseudo-source),
optionally an existing `main-annotated.tex` from the reviewer. Outputs, all in the paper
directory, none committed:

| File | Content |
|---|---|
| `main-annotated.tex` / `.pdf` | existing `CL` markup plus `LG` markup |
| `writing-report.md` / `.pdf` | header, counts, one entry per `W<n>`, cut appendix |
| `writing-ledger.jsonl` | every proposal with its final status |
| `glossary.md` | the paper's terms, first definitions, variants found |

Private state (never in this repo): `$STYLE_PROFILES_DIR` (default `~/Claude/style-profiles`)
with profiles, sources, `preferences.md`, `preferences-pending.md`. See
`reference/building-style-profiles.md`.

## Workflow

**0. Mode and profiles.** Mode A (internal, authors will see the copy) runs everything.
Mode B (external referee) runs only step 1 and writes its top ten findings as prose into
the review's §8; no annotated copy, no calibration, no author profile. Then: does a field
profile exist for this subfield, and an author profile for these authors? If not, propose
corpora and build them (`reference/building-style-profiles.md`); if the user declines or
the fetch fails, run on `reference/style-defaults.md` alone and say so in the report
header. Read `preferences.md` now; every rule in it binds every agent below.

**1. Global reader.** One subagent. Give it: the rendered PDF pages, the tex, the
profiles, `style-defaults.md`, `preferences.md`, `reference/critique-rubric.md`,
`reference/ledger-schema.md`. Ask for three things, in this order:
(a) `glossary.md` — every coined or load-bearing term, where it is first defined, every
variant or synonym found with locations; (b) paper-wide rules — spelling variant, tense
per section type, first-person convention, cross-reference form, how contributions are
enumerated; (c) ledger rows at levels `flow` and `framing` only, anchored at the first
sentence of the paragraph, ids starting at `W1`. It must read the paper end to end before
writing a row, and must not propose sentence-level rewrites.

**2. Calibration probe (Mode A).** Run one section worker (step 3's prompt) on the
abstract and the body section with the densest prose, capped at ten rows stratified about
2 mechanics / 5 style / 2 flow (take these from step 1) / 1 framing. Show them in **one**
AskUserQuestion round as before → after with the one-line reason; options accept / reject
/ rewrite (via Other). Turn the answers into **run rules**, phrased as instructions
("do not flatten hedges in the limitations paragraph", "British spelling is deliberate"),
numbered `run:1…`. Ask once; never re-ask mid-run.

**3. Section workers.** One subagent per top-level `\section` (appendix sections too,
told they are lower priority), in parallel. Each receives: its section's tex with line
numbers, `glossary.md`, the paper-wide rules, the run rules, both profiles,
`style-defaults.md`, `preferences.md`, the rubric and the schema, and the id range it may
use (`W<start>–W<end>`, blocks of 100 per section, so ids never collide). Each emits
`mechanics` and `style` rows only. The prompt must contain these sentences verbatim:

> Copy every anchor from the tex, whole tokens, unique in the section; extend to the full
> sentence if a phrase recurs. Never anchor inside \cite, math, tabular, \resizebox,
> \footnote or existing \ch markup: comment on the paragraph and put the rewrite in the
> rationale. Every style row cites a rule from the profiles, the defaults or the
> preferences; if you cannot name the rule, do not write the row. Keep every number,
> citation and hedge the sentence had. Do not touch text already inside \chreplaced,
> \chadded or \chdeleted.

**4. Noise gate.** One subagent, given all rows, the tex, the profiles and preferences,
and the five questions at the end of `reference/critique-rubric.md`. It sets `status` to
`kept` or `cut` with a `cut_reason` for every row, enforces the caps (style ≤ 2 per
paragraph; flow + framing ≤ 1 per paragraph and ≤ 25 total; mechanics uncapped), cutting
lowest confidence first, and never edits a row's text. Its default is to keep a row it
can tie to a rule and to cut one it cannot.

**5. Render.**

```
python3 assets/render-ledger.py --ledger writing-ledger.jsonl \
  --tex main-annotated.tex --out main-annotated.tex --report writing-report.md \
  --paper main.tex --mode A --field-profile <slug> --author-profile <slug> \
  --run-rule "..." [--forbid-ulem]
```

Use `--tex main.tex` when no annotated copy exists. Pass `--forbid-ulem` when
`grep -n forbidden *.sty *.cls` names `ulem`. The script inserts the `changes` preamble
if missing, adds the `LG` author, frees a paper-defined `\todo`, applies kept rows,
degrades unsafe ones to comments, compiles the markup build and the accept-all build in
`.lg-build/`, and bisects by level if the markup build fails. Exit 2 means a level was
dropped or the accept-all build failed: read the report header and say so to the user.
Then `_shared/md2pdf/md2pdf --review writing-report.md`, and render two or three pages
of the markup PDF and look at them: markup that compiles can still be unreadable.

**6. Preferences.** From the calibration rejections and rewrites, write candidate rules
to `preferences-pending.md` (date, paper slug, rule text). Ask once whether to promote
each to `preferences.md`. Unpromoted candidates stay pending; never promote silently.

**7. Hand back.** Report: counts by level, how many degraded and why, the builds, the
profiles used, the run rules, and the three framing findings you consider most important.
Offer the PDF and the report.

## Hard rules

- Never modify `main.tex`; the renderer refuses that output name.
- Never commit paper artifacts or write anything from the paper into this repository or
  into a profile.
- Every `style` row cites a rule. No rule, no row.
- `LG` never edits inside `CL` markup; overlaps become comments.
- The cut list is always published. Silence about a cut is a defect.
- Never install pandoc or LaTeX. Missing tools are a question for the user.
- A build that did not happen is reported as "not run", never as passed.

## Findings that recur

- The same concept under two names across sections, one of them introduced in a figure
  caption only. Framing row, and the glossary is how you catch it.
- An intensifier standing in for a number that a table already gives.
- Hedges removed by a worker from a limitations paragraph. The gate must catch this;
  the preferences should carry the rule after the first time.
- Anchors copied from the PDF instead of the tex: ligatures and `~` make them unanchored.
- Workers editing a bare macro (`\backto{}`) or a section heading, and quoting `\citet` inside a
  comment: all three broke the build on the first real paper. The renderer now degrades or
  escapes them, and the report lists each as `degraded` with its reason.
- The accept-all `[final]` build failed on a 52-page paper whose markup build passed; treat the
  markup build as the deliverable and report the other honestly.

## Quick reference

`assets/`: `render-ledger.py`, `profile-stats.py`, `fetch-corpus.py`, `changes-author-LG.tex`,
`proofread/` (ledger, anchors, markup, preamble, apply, report, build, stats, corpus).
`reference/`: `ledger-schema.md`, `critique-rubric.md`, `style-defaults.md`,
`writing-report-template.md`, `building-style-profiles.md`.
Preamble source: `reviewing-paper-sources/assets/changes-preamble.tex`; recipe and gotchas:
`reviewing-paper-sources/reference/annotating-with-changes.md`.
Tests: `cd assets && python3 -m unittest discover -s tests`.
