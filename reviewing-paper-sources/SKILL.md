---
name: reviewing-paper-sources
description: Use when asked to review, critique, or assess an academic paper from its LaTeX sources — including pre-submission critique of a student's or collaborator's draft, or a referee report for a venue. Triggers on "review this paper", "assess the paper", "read my student's draft", a directory holding main.tex/refs.bib/*.cls, or a request to check a paper's claims, figures, or bibliography.
---

# Reviewing Paper Sources

## Overview

A paper review is an **evidence-gathering exercise, not a reading exercise**. The findings that change a paper come from things you compute or verify, not from things you notice while reading: recomputing the headline statistic, checking every reference against its publisher record, compiling the sources yourself, rendering the figures at print size.

**Core principle: never trust an artifact you did not produce.** The committed PDF is stale until proven current. A reference is wrong until checked against a primary source. A reported rate means nothing until you have its sample size.

## Mode: establish this first

| | Mode A — internal | Mode B — external |
|---|---|---|
| Situation | Advisor/self-review of your own group's draft | Referee report for a venue |
| Register | Blunt, shared stake in the outcome | Neutral, addressed to authors + chair |
| Proposes fixes | Yes, including edits to the sources | No — diagnose only, never rewrite the authors' text |
| Artifacts | Review `.md` + `.pdf`, `*-annotated.tex`, `refs-corrected.bib` | Review `.md` + `.pdf` only |
| Scores/verdict | Yes (both modes) | Yes |

If it is ambiguous, ask. "My student's paper" ⇒ Mode A. "I'm reviewing for X" ⇒ Mode B.

Also establish **where in its lifecycle** the paper is, because it changes what the review is for: pre-submission (triage by what fits the deadline), already submitted (target what reviewers will attack, and prepare answers), or post-rejection (framing and structural weaknesses).

## Identify the real artifact before reviewing

The paper is what was *submitted*, and the repository may not contain it. Before writing anything, reconcile:

- **A commented-out `\input` does not mean the content is absent.** Sections get consolidated: check where each heading actually lives (`grep -n '^\\section' sections/*.tex`) before concluding anything is missing. One file routinely holds two top-level sections. A file named `eval_*.tex` that nothing includes is usually a superseded draft, not a lost result.
- **Map the built structure against the submitted PDF** heading by heading, then compare word multisets per page. Differences that are only ligatures (`di`+`erent` for `different`) or missing figure-embedded numerals mean the submitted PDF was re-saved through a viewer (check `pdfinfo` Producer for `Quartz`, etc.) and its *text layer*, not its content, differs.
- **Diff the reference lists.** A name present in the submitted bibliography but absent from yours is either a citation removed post-submission or a phantom entry from a stale `.bbl`. Both are findings.
- If the repository still cannot produce the submitted paper, **ask for the submitted PDF** rather than reviewing a reconstruction. Say what you would otherwise be guessing at.

## Workflow

Create a todo per phase. Do not skip phases 1–4 to get to the writing.

**0. Scope the review.** Before any work, present the optional modules with their costs and
ask which to run. Record the answer in the review header so the artifact states its own
coverage. Ask once; do not re-ask mid-review.

| Module | Skill | Cost |
|---|---|---|
| Core review | (this skill) | always |
| Verify bibliography | `verifying-bibliography` | minutes for a 57-entry file, seconds once cached |
| Find missed related work | `surveying-literature` (gap sweep) | ~1.5 min for an 18-entry bibliography, ~90 API calls |
| Map the field | `surveying-literature` (`--field-map TOPIC`) | similar |
| Deep paper comparison | `comparing-papers` | ~1 min per paper, fetches LaTeX source |
| Check the mathematics | `verifying-proofs` | seconds for a 46-proof corpus; no dependencies in its default mode |
| Expand a derivation | `explaining-derivations` | one subagent and one PDF per theorem; minutes each |

Before running a gap sweep, run it with `--seeds-only` first: it makes no requests and shows
exactly which queries will be used. Wrong angles mean wrong results, and OpenAlex bills each
search against a small daily budget.

Offer bibliography verification **pre-selected**: measured against two bibliographies with
known ground truth, it has the highest finding-rate per minute of any phase, and it found a
defect a careful manual pass had missed.

**1. Ground truth.** Compile the sources yourself into a scratch dir:
`latexmk -pdf -interaction=nonstopmode -outdir=/tmp/pbuild main.tex`
Then compare against any committed PDF. A stale committed PDF is a finding in itself — it can carry the wrong title, or real author names in a double-blind submission. Record page count, LaTeX errors, undefined citations/references, and overfull boxes. Also list the directory: unused files whose names identify authors (`figure_JH.pdf`) are an anonymity risk worth reporting.

If it does not compile, **fix it before reviewing** — a review of a document you could not build is worth little. Then ask which artifact is authoritative before writing anything (see *Identify the real artifact*).

**Delete stale `.bbl` before testing a bibliography.** `\bibliography{...}` inputs `./main.bbl`, so a leftover `.bbl` in the source directory silently shadows your test even with `-outdir`. If citations resolve suspiciously well, or no `.blg` appears, that is what happened. This also explains a class of real defect: a submission built past a fatal error against an old `.bbl` ships a bibliography that no longer matches its own citations.

**2. Venue rules.** Find the CFP (WebSearch/WebFetch) and check: page limit and whether references count, anonymity requirements, format/template, deadline. The deadline determines how you triage. Report compliance explicitly.

**Read the template's own comments — they list the commands that block publication.** `grep '^%' <venue>.sty main.tex` typically yields lines like *"`\nocopyright` -- Your paper will not be published if you use this command"*. Collect them, then grep the *comment-stripped* source for live usage. Check `\vspace` too: negative vertical space to win room is the most common silent violation. Verify the page split by extracting text per page rather than trusting the page count — "7 pages of content, 9 total" means the References heading must fall at the top of page 8, and that is a one-command check.

**3. Read the rendered pages, not just the source.** `pdftoppm -r 110 -png main.pdf /tmp/pg`, then read the images. This is the only way to catch illegible figures, encoding inconsistencies, and space allocation. Estimate what fraction of the page budget the figures consume.

**Extract the text layer of every figure** — `pdftotext Figures/*.pdf -`. Plots are generated by scripts, so their legends contain series the prose may never mention. On one submission this surfaced a fourth series in the headline scalability figure — a CPU build of the authors' own engine — whose name appeared **zero times** in the `.tex`. It was the ablation separating the paper's GPU claim from the effect of reimplementation alone, and no reader could have known it existed. Compare the series names against the text and ask about any that are unexplained.

**4. Audit the claims.** For every headline number: find its sample size, recompute the statistic, and check whether the comparison is licensed. Read the primary sources for numbers the paper quotes from others — protocols rarely match. See `reference/claim-audit.md`.

For the baseline-scale and seed-count checks specifically, invoke `comparing-papers`:
`python3 ~/.claude/skills/comparing-papers/assets/run-compare.py . --against "<baseline title>" --out review-assets/`
It fetches the baseline's LaTeX source, extracts `updates x batch` against the baseline's own
published scale, and computes the ratio with both quotes. On one real paper this reproduced a
critical finding (6.4M vs 60M examples, ~11%) that had taken a manual pass through two
appendices.

**4b. Check the mathematics.** For any paper with theorem or proof environments,
invoke `verifying-proofs`:
`python3 ~/.claude/skills/verifying-proofs/assets/run-proofcheck.py main.tex --out review-assets/`
Its default mode needs no external tooling and reports what the structure of the
argument gives up: an induction with no base case, a claim dependency cycle, a
restatement that drops a hypothesis, a division by something nobody proved
non-zero. Read the coverage table **before** the findings — "54 of 138 inference
steps were mechanically checkable" is usually the more important number, and a
dense cluster of `UNVERIFIED` inside one proof is a finding in itself.

Then do what the tool cannot: `reference/structural-audit.md` in that skill is the
non-mechanical half — whether the hypothesis is *used*, whether quantifier order
survives, whether the induction covers its claim.

When a specific derivation is load-bearing and you cannot follow it, invoke
`explaining-derivations`. **A step nobody can make explicit is evidence against
the derivation**, and its gap ledger converts that into review findings with
severities.

**5. Audit the bibliography — every entry, no exceptions.** Invoke `verifying-bibliography`:
`python3 ~/.claude/skills/verifying-bibliography/assets/run-bibcheck.py refs.bib --bbl main.bbl --out review-assets/`
Consume `bibcheck-report.md`, then do what the tool cannot: read each load-bearing citation's
abstract and check the submission's characterisation against it (selective citation), and
write `refs-corrected.bib`. See `reference/bibliography-audit.md` for the audit-table format
and the corrected-bib rules.

`WEAK` and `UNVERIFIED` rows are **not passes** — they are the entries a human must check,
and a fabricated reference is exactly the one no database can find. Run the checker over the
whole file, not only the cited subset: uncited entries are also unaudited.

This is the phase most likely to be skipped and most likely to produce a finding.

**6. Write the review** into `review-<reviewer>-<YYYYMMDD>.md` using `reference/review-template.md`, then render it and every audit report:

```sh
MD2PDF=~/.claude/skills/_shared/md2pdf/md2pdf
"$MD2PDF" --review review-<reviewer>-<date>.md
"$MD2PDF" --review review-assets/*.md        # bibcheck, proofcheck, gaps, comparison
```

`--review` breaks the metadata block per label, turns the repository-state
blockquote into a callout box, and tightens the audit tables. It is one
self-contained script, so copying just that file into `review-assets/` keeps the
build reproducible after the skill is gone.

**Read what it prints.** A character no font can render is dropped *silently* by
the engine — the sentence then reads as though you never wrote it. md2pdf reports
every dropped character; treat that warning as a defect in the review, not noise.
It also says when it had to degrade something (a quoted macro typeset literally,
math typeset as source text).

Do not hand-tune the LaTeX for wide tables. Wide tables already step down a font
size and long DOIs already get break opportunities inserted; a table still
running off the page means the content needs splitting, not the preamble.

**7. Annotate the sources (Mode A only).** Produce `main-annotated.tex` with `changes.sty` markup and a corrected `.bib`. See `reference/annotating-with-changes.md` — check the document class for a forbidden-package list first, and expect the `[final]` accept-all build to be less reliable than the markup build. Render the marked-up pages and look at them; markup that compiles can still be garbage.

**8. Verify, then offer both formats.** Every artifact compiles; every claim in the
review traces to something you ran or read.

Close by listing what exists, `.md` and `.pdf` side by side, so the user can read
it either way without asking — the `.md` is what they will edit and diff, the
`.pdf` is what they will circulate or annotate:

```
review-claude-20260815.md   review-claude-20260815.pdf   (8 pp)
review-assets/bibcheck-report.md   .../bibcheck-report.pdf   (2 pp)
```

Offer to open the PDF. Report page counts: a review that ran to 30 pages is a
finding about the review, not about the paper.

## Hard rules

- **Never modify the originals.** `main.tex` and `refs.bib` are inputs. Write `main-annotated.tex`, `refs-corrected.bib`. If you must test a corrected bib against the real build, back up, test, restore, and say so.
- **Never install tooling without asking.** Missing pandoc/LaTeX is a question for the user, not a `brew install`.
- **Never commit anything.** Leave the artifacts untracked; integration is the author's call.
- **Every number in the review must be one you computed or read from a source.** No "approximately" derived from memory.
- **Report what you could not verify.** An unverifiable reference or an anonymous artifact is a stated limitation, not a silent pass.

## Findings that recur

Run this list against every quantitative paper; each is expanded in `reference/claim-audit.md`:
sample size behind a 0%/100% rate (rule of three) · protocol match to each baseline ·
**baseline training scale vs its published scale** · **seed count** · self-built baselines ·
ablations for the claimed mechanism · metric saturation by construction ·
selection on the reported construct · per-item denominators hidden inside an aggregate ·
unevaluated contributions · cost of the method · selective citation.

**Read the commented-out text** (`grep -n '^\s*%' sections/*.tex`). Authors delete their own
caveats under page pressure, and a caveat they wrote and cut is the strongest recommendation you
can make — you are asking them to restore their own sentence, not accept yours.

## Common mistakes

- **Reviewing the committed PDF.** It may not correspond to the sources. Compile first.
- **Spot-checking the bibliography.** In practice errors cluster in the references the authors were least likely to re-read — the classic ones. Sampling misses them.
- **Clearing an entry after checking authors only.** Check authors, title, venue, volume/issue, pages, and DOI. A correct DOI beside a wrong title is how fabrication becomes detectable.
- **Softening the central objection.** If the headline claim is unsupported, that belongs in the summary, not in concern #7.
- **Writing "should be improved" without the fix.** In Mode A every concern needs a concrete, costed action.
- **Skipping the figure render.** Illegible figures are invisible in the `.tex`.
- **Treating `WEAK`/`UNVERIFIED` as a pass.** They mean no database confirmed the entry — which is what a fabricated reference looks like. Check them by hand.
- **Reporting a rate-limited run as a clean bill.** When the checker's circuit breaker drops a source, most entries fall through to title-search only. Say "nothing wrong was found in a degraded run", not "the bibliography is correct", and re-run when quotas reset.
- **Letting the review PDF drop characters.** md2pdf warns, but you have to read the warning: a missing glyph is deleted silently by the engine, so the sentence reads as though you never wrote it.
- **Delivering only one format.** The `.md` is for editing and diffing, the `.pdf` for circulating. Produce both and say where they are; do not make the user ask.

## Quick reference

| Artifact | Name | Mode |
|---|---|---|
| Prose review | `review-<reviewer>-<YYYYMMDD>.md` / `.pdf` | A + B |
| Annotated sources | `main-annotated.tex` / `.pdf` | A |
| Corrected bibliography | `refs-corrected.bib` | A |
| Bibliography report | `review-assets/bibcheck-report.md` / `.pdf`, `bibdiff.csv` | A + B |
| Related-work gaps | `related-work-gaps-<date>.md` / `.pdf`, `review-assets/candidates.json` | A + B |
| Field map | `lit-review-<date>.md` / `.pdf` | A + B |
| Head-to-head comparison | `paper-comparison-<date>.md` / `.pdf`, `review-assets/comparison.json` | A + B |
| Proof check | `review-assets/proofcheck-report.md` / `.pdf`, `proof-ledger.json`, `checks/*.py` | A + B |
| Expanded derivations | `derivations/<label>.tex` / `.pdf`, `derivations/gaps.json` | A + B |
| Build helper | `md2pdf` copied into `review-assets/` (one file, self-contained) | A + B |

Every `.md` in that table gets a `.pdf` from `md2pdf --review`; deliver both.

`assets/`: `changes-preamble.tex`
`reference/`: `bibliography-audit.md`, `claim-audit.md`, `annotating-with-changes.md`, `review-template.md`
PDF rendering: `_shared/md2pdf/md2pdf --review` (see its `README.md`)
Sibling skills: `verifying-bibliography` (phase 5), `surveying-literature` (phase 0),
`comparing-papers` (phases 0 and 4), `verifying-proofs` and
`explaining-derivations` (phases 0 and 4b).
Shared layers: `_shared/scholarly` (retrieval), `_shared/latexmath` (proof parsing).
