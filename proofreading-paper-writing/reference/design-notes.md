# Design notes: the removed multi-agent workflow

Until the W2 reduction (2026-11), steps 1 to 4 of the workflow ran as separate agents: one global reader (glossary, paper-wide rules, flow and framing rows), one section worker per top-level \section with id blocks of 100, a calibration probe, and a separate noise-gate agent. Measured headless (W1, 18 runs), the agent ran that workflow as a single pass in 16 of 18 runs and used subagents only for appendix sections in the other 2. The single-pass workflow now in SKILL.md is that observed behaviour. The original text follows for reference.

## Workflow

**0. Mode and profiles.** Mode A (internal, authors will see the copy) runs everything.
Mode B (external referee) runs only step 1 and writes its top ten findings as prose into
the review's §8; no annotated copy, no calibration, no author profile. Then: does a field
profile exist for this subfield, and an author profile for these authors? If not, propose
corpora and build them (`reference/building-style-profiles.md`); if the user declines or
the fetch fails, run on `reference/style-defaults.md` alone and say so in the report
header. In Mode A, if `/Applications/Antidote` exists, ask in the same round whether to add
the Antidote pass (step 3b). Read `preferences.md` now; every rule in it binds every agent below.

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

**3b. Antidote pass (optional, Mode A).** Offered in step 0. If accepted, copy the tex to `antidote.tex`, open the copy in Antidote as
the section workers start, and let the user correct it. After the workers finish, run
`assets/antidote-rows.py` to append its safe fixes as `mechanics` rows and list the rest
in `antidote-review.md`. Antidote silently damages LaTeX (an unescaped `\%` drops the rest
of a line from the PDF with no build error), so the corrected copy is only ever diffed,
never rendered or pasted back. Steps and refusal reasons: `reference/antidote-pass.md`.

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

Use `--tex main.tex` when no annotated copy exists. The input must never already carry `LG` markup: the renderer refuses it, because a second pass onto its own output degrades every row as inside markup and doubles the comments. Keep a science-only copy and render from that. Pass `--forbid-ulem` when
`grep -n forbidden *.sty *.cls` names `ulem`. The script inserts the `changes` preamble
if missing, adds the `LG` author, frees a paper-defined `\todo`, applies kept rows,
degrades unsafe ones to comments, compiles the markup build and the accept-all build in
`.lg-build/`, and bisects by level if the markup build fails. Exit 2 means a level was
dropped or the accept-all build failed: read the report header and say so to the user.
Then `_shared/md2pdf/md2pdf --review writing-report.md`, and render two or three pages
of the markup PDF and look at them: markup that compiles can still be unreadable.

**Run it from the paper directory, and check the output rather than the exit line.**
The build resolves the class, the figures and the `.bib` relative to the output file, so
an `--out` under `review-assets/` fails with `aaai2027.sty not found` before any row is
tried. And the printed counts come from the row statuses, which the renderer writes back
into the ledger: they say what the rows claim, not what this run did.
`grep -c 'id=LG' <out>.tex` is the check that cannot lie to you.

**When the bisect drops a level, find the one bad row instead of accepting the loss.**
The bisect drops whole levels, so a single unbuildable row costs every style, flow and
framing proposal in the paper. Re-render with `--no-build`, compile that tex yourself,
and read the first error. On one paper a stray `^` in one margin comment dropped 21 of
167 rows, and the error named neither the row nor the level: a margin note is typeset
inside todonotes' tikzpicture, so an out-of-math superscript surfaces as
`\begin{tikzpicture} ended by \end{document}` a thousand lines later.

**6. Preferences.** From the calibration rejections and rewrites, write candidate rules
to `preferences-pending.md` (date, paper slug, rule text). Ask once whether to promote
each to `preferences.md`. Unpromoted candidates stay pending; never promote silently.

**7. Hand back.** Report: counts by level, how many degraded and why, the builds, the
profiles used, the run rules, the Antidote pass if run (rows appended, changes refused, `%`
escapes the copy lost), and the three framing findings you consider most important.
Offer the PDF and the report.

