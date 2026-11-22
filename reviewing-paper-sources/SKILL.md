---
name: reviewing-paper-sources
description: Use when asked to review, critique, or assess an academic paper from its LaTeX sources — including pre-submission critique of a student's or collaborator's draft, or a referee report for a venue. Also when the only artifact is a blind PDF with no sources. Triggers on "review this paper", "assess the paper", "read my student's draft", "referee report", a directory holding main.tex/refs.bib/*.cls, a submission PDF to review, or a request to check a paper's claims, figures, bibliography or math.
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

**Then establish what you were given and where it is.** PDF only (the usual referee case): run
`python3 assets/run-pdfshim.py paper.pdf --out review-assets/` and read `reference/pdf-only-review.md`.
Lifecycle: pre-submission, submitted, post-rejection, or an **unfinished draft**, whose findings
split into content (scored), not-yet-written (an inventory with a "blocks submission" column) and
container (its own late section, not scored). Make sure you have the submitted artifact, not a
reconstruction. Both: `reference/build-and-venue.md`.

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
| Proofread the writing | `proofreading-paper-writing` | one pass: ledger, gate, render; about 10 min; uses style profiles when present |

Offer bibliography verification **pre-selected** (highest finding-rate per minute). Run a gap
sweep with `--seeds-only` first: it shows the queries without spending OpenAlex budget.

**1. Ground truth.** Compile the sources yourself into a scratch dir:
`latexmk -pdf -interaction=nonstopmode -outdir=/tmp/pbuild main.tex`
Compare against any committed PDF (a stale one is a finding). Record page count, LaTeX errors,
undefined citations/references, overfull boxes. If it does not compile, fix it first. Build traps
(BibTeX skipped, printing editorial macros, stale `.bbl`): `reference/build-and-venue.md`.

**2. Venue rules.** Find the CFP and report compliance: page limit (do references count),
anonymity, template, deadline (it sets the triage). Confirm mandatory statements in the
**rendered** text, never the source (`reference/build-and-venue.md`, "Venue traps").

**3. Read the rendered pages, not just the source.** `pdftoppm -r 110 -png main.pdf /tmp/pg`, then
read the images (legibility, encoding, the page share figures take). Compare each figure's text
layer (`pdftotext Figures/*.pdf -`) with the prose. Review §6 has one row per figure and table:
`check-review-form.py --list-floats paper.tex` lists them (ids F1.., T1..), and
`check-review-form.py review.md --floats paper.tex` fails on a missing row.

**4. Audit the claims.** For every headline number: find its sample size, recompute the statistic,
and check whether the comparison is licensed. Read the primary sources for numbers the paper
quotes from others — protocols rarely match. See `reference/claim-audit.md`.

**4a. Check baseline provenance.** Establish whether the baseline rows were re-run or quoted: pull
the baseline's own source (`curl -sL arxiv.org/e-print/<id> | tar -xz`, or CVF/ACL Anthology) and
diff the reported values (an exact match settles it); compare protocol and search budget. For
training scale and seed counts, invoke `comparing-papers`:
`python3 ~/.claude/skills/comparing-papers/assets/run-compare.py . --against "<baseline title>" --out review-assets/`

**4b. Check the mathematics.** For any paper with theorem or proof environments, invoke
`verifying-proofs`:
`python3 ~/.claude/skills/verifying-proofs/assets/run-proofcheck.py main.tex --out review-assets/`
Read its coverage table before the findings, then do the non-mechanical half
(`reference/structural-audit.md` in that skill). A load-bearing derivation you cannot follow goes
to `explaining-derivations`: **a step nobody can make explicit is evidence against it.**

**5. Audit the bibliography — every entry, no exceptions.** Invoke `verifying-bibliography`:
`python3 ~/.claude/skills/verifying-bibliography/assets/run-bibcheck.py refs.bib --bbl main.bbl --out review-assets/`
Then check load-bearing citations against their abstracts (selective citation) and write
`refs-corrected.bib` (`reference/bibliography-audit.md`). `WEAK`/`UNVERIFIED` rows are **not
passes**. The phase most likely to be skipped and most likely to produce a finding.

**6. Write the review** into `review-<reviewer>-<YYYYMMDD>.md` in the **fixed form** of
`reference/review-template.md`: its twelve headings verbatim and in order, none dropped and none
added, and the 14-row coverage checklist (§2a) filled with a status and the evidence for every
row. The form is what makes two reviews from this skill comparable; a section with nothing to
say keeps its heading and says why. Then check it, and fix until it prints `OK`:

```sh
python3 ~/.claude/skills/reviewing-paper-sources/assets/check-review-form.py review-<reviewer>-<date>.md \
    --floats paper.tex
```

Measured (R3, R5b): same twelve sections in 18/18 reviews; figure coverage 0.94 vs 0.62 without the skill.

Then render it and every audit report, and read what md2pdf prints (a dropped character is a
defect in the review):

```sh
MD2PDF=~/.claude/skills/_shared/md2pdf/md2pdf
"$MD2PDF" --review review-<reviewer>-<date>.md
"$MD2PDF" --review review-assets/*.md        # bibcheck, proofcheck, gaps, comparison
```

**7. Annotate the sources (Mode A only).** Produce `main-annotated.tex` with `changes.sty` markup
and a corrected `.bib`. See `reference/annotating-with-changes.md`. Render the marked-up pages and
look at them; markup that compiles can still be garbage.

**7b. Proofread the writing (when selected).** Run `proofreading-paper-writing` on
`main-annotated.tex` after the scientific markup (Mode A) or report-only (Mode B); its framing
findings go in §8, one sentence each with their `W<n>`.

**8. Verify, then offer both formats.** Every artifact compiles; every claim in the review traces
to something you ran or read.

**Refute your own findings before committing the rating.** One subagent gets the finished review
and the sources and tries to refute each critical and major finding (default "refuted" under
uncertainty; judge against the pinned artifact, not a later tree; check the review's own
arithmetic and labels). Resolve every surviving objection visibly — amend, or keep with the
reason — after rechecking it yourself (`reference/recurring-findings.md`).

Close by listing what exists, `.md` and `.pdf` side by side with page counts (a 30-page review is a
finding about the review), and offer to open the PDF.

## Hard rules

- **Never modify the originals.** `main.tex` and `refs.bib` are inputs. Write `main-annotated.tex`, `refs-corrected.bib`. If you must test a corrected bib against the real build, back up, test, restore, and say so.
- **Never install tooling without asking.** Missing pandoc/LaTeX is a question for the user, not a `brew install`.
- **Never commit anything.** Leave the artifacts untracked; integration is the author's call.
- **Every number in the review must be one you computed or read from a source.** No "approximately" derived from memory.
- **Report what you could not verify.** An unverifiable reference or an anonymous artifact is a stated limitation, not a silent pass.
- **A disqualifying finding sets a floor the scores cannot lift.** Never sum or average the §2 criteria; the recommendation follows soundness, and the §2 disqualifying line names *every* finding that gates the outcome.
- **On an early draft, the §2 line is two lines** — what gates the science (scored) and what gates the submission (container, not scored).

## Findings that recur

Run this list against every quantitative paper; each is expanded in `reference/claim-audit.md`:
sample size behind a 0%/100% rate (rule of three) · protocol match to each baseline ·
**baseline training scale vs its published scale** · **seed count** · self-built baselines ·
ablations for the claimed mechanism · metric saturation by construction ·
selection on the reported construct · per-item denominators hidden inside an aggregate ·
unevaluated contributions · cost of the method · selective citation ·
**does the hyperparameter grid contain the value that turns the contribution off** ·
**are the constants in a stated guarantee ever measured on real data** ·
**does the appendix concede something the main text presents favourably** ·
**do the ranking gaps survive the variance the paper's own appendix reports** ·
**does every derived annotation on a figure match the table it came from** ·
**does the paper's own comparison table support the superiority its caption claims** ·
**does a response bench in the repository already answer the draft's weakest number**.

Also: verify an aggregate column from per-item data, and read the commented-out text for cut
caveats (`grep -n '^\s*%' sections/*.tex`). Cases: `reference/recurring-findings.md`.

## Common mistakes

The two that produce the most wrong findings: **"the paper does not report X" after one failed
search** (search several wordings, read the whole subsection), and **a typographic finding taken
from the text layer** (render the page and look). The rest, with cases: `reference/recurring-findings.md`.

## Quick reference

| Artifact | Name | Mode |
|---|---|---|
| Prose review | `review-<reviewer>-<YYYYMMDD>.md` / `.pdf` | A + B |
| Annotated sources, corrected bibliography | `main-annotated.tex` / `.pdf`, `refs-corrected.bib` | A |
| Module reports (bibcheck, proofcheck, gaps, comparison, writing) | `review-assets/*.md` / `.pdf` | A + B |
| PDF pseudo-source | `review-assets/structure.md`, `refs.bib`, `body-*.txt` | PDF-only |

Every `.md` gets a `.pdf` from `md2pdf --review`; deliver both. Full artifact list by module:
`reference/build-and-venue.md`.

`assets/`: `check-review-form.py` (phase 6), `changes-preamble.tex`, `run-pdfshim.py` + `pdfshim/`.
`reference/`: `review-template.md`, `claim-audit.md`, `bibliography-audit.md`,
`annotating-with-changes.md`, `pdf-only-review.md`, `build-and-venue.md`, `recurring-findings.md`.
