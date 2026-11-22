# The artifact, its build and the venue

Moved from SKILL.md (R6 reduction, 2026-11-21). Read it at phase 1 (ground truth), phase 2
(venue rules), phase 3 (figures), and whenever the paper is an unfinished draft.

## What you were given, and where it is in its lifecycle

**Then establish what you were given.** With LaTeX sources, follow the workflow below as
written. With only a PDF — the usual case for refereeing — the compile step, the `.bbl`
cross-check and the source-based tools are all unavailable, and two failure modes appear that
do not exist otherwise. Build the pseudo-source first and read
`reference/pdf-only-review.md`:

```sh
python3 assets/run-pdfshim.py paper.pdf --out review-assets/
```

Also establish **where in its lifecycle** the paper is, because it changes what the review is for: pre-submission (triage by what fits the deadline), already submitted (target what reviewers will attack, and prepare answers), or post-rejection (framing and structural weaknesses).

## Unfinished drafts: the three-way split

**An unfinished draft is a fourth case, and it needs the findings split three ways: content, not-yet-written, and container.** Content is the only one that bears on the judgement — claims that are written and wrong, framing the paper's own data refutes, work missing from the argument. Container is everything that makes the artifact submittable rather than good, and it belongs in its own late section with the severity tag saying so (*"Blocks submission; not a judgement on the work"*) rather than sitting at the top of the concerns list outranking the science. The temptation runs the other way, because container defects are the easiest to find and the easiest to state with certainty — which is exactly why they crowd out the findings that took real work to establish.

For the not-yet-written third: empty sections, note-form prose and TODO stubs are normal at this stage and the authors already know about them; reporting them as defects wastes the review. What they cannot see is which of the text they *have* written is wrong. So give this third an inventory table — location, current state, and a yes/no column for whether it blocks submission — rather than prose. The yes/no column is the deliverable: on one draft it distinguished an empty Conclusions section and a section heading with nothing under it, both of which had to be written, from an appendix the author was mid-way through rewriting, which could ship as it stood. Read the notes rather than skipping them, too: an author's own `\todo{is this correct?}` against a method description means the method is not settled, which is a finding about the work and not about the prose — promote that one to content.

Two boundary calls worth making the same way each time. A venue-mandated statement that is only a stub is **container**, not not-yet-written, however unwritten it looks: writing it is mechanical and it earns no credit. An absent Limitations section is **content**, because what goes in it is the paper's own account of what its evidence cannot support, and that is a judgement only the authors can make.

One trap specific to this case: an unfinished Discussion often lists contributions in note form that the Results section does not contain, because the experiment was cut or commented out. Cross-check every claimed contribution in the notes against the built paper before assuming it is merely unwritten.

**On an early draft, separate the two gates and let only one of them score.** The disqualifying-floor rule was written for a finished paper, where a desk-reject risk and a soundness failure both stop the same submission. On a draft still being written they are different questions, and merging them produces a verdict about the *container* instead of the work. Anonymisation leaks, an unset template switch, page count, missing bibliography entries and LaTeX errors are all real and none can be skipped — and all of them are a morning's work that the authors were always going to do. State them, in their own section, under their own heading, listed after the content findings; give the §2 line as *two* lines — what gates the science, and what gates the submission — and score only the first. A review that opens with four mechanical items and one substantive one has told the author their paper is bad when what it means is that their build is unfinished. This was learned the hard way: a review on file did exactly that and had to be restructured after the author pointed it out.

## Identify the real artifact before reviewing

The paper is what was *submitted*, and the repository may not contain it. Before writing anything, reconcile:

- **A commented-out `\input` does not mean the content is absent.** Sections get consolidated: check where each heading actually lives (`grep -n '^\\section' sections/*.tex`) before concluding anything is missing. One file routinely holds two top-level sections. A file named `eval_*.tex` that nothing includes is usually a superseded draft, not a lost result.
- **Map the built structure against the submitted PDF** heading by heading, then compare word multisets per page. Differences that are only ligatures (`di`+`erent` for `different`) or missing figure-embedded numerals mean the submitted PDF was re-saved through a viewer (check `pdfinfo` Producer for `Quartz`, etc.) and its *text layer*, not its content, differs.
- **Diff the reference lists.** A name present in the submitted bibliography but absent from yours is either a citation removed post-submission or a phantom entry from a stale `.bbl`. Both are findings.
- If the repository still cannot produce the submitted paper, **ask for the submitted PDF** rather than reviewing a reconstruction. Say what you would otherwise be guessing at.

## Build traps (phase 1)

A stale committed PDF is a finding in itself — it can carry the wrong title, or real author names in a double-blind submission. Also list the directory: unused files whose names identify authors (`figure_JH.pdf`) are an anonymity risk worth reporting.

**A build that stops before BibTeX ships a paper with every citation unresolved.** `latexmk` abandons the run on the first fatal error, so BibTeX never executes and no `.blg` appears — yet a PDF from an earlier pass may still be sitting there, with all `(?)`. If you see errors, re-run with `-f` and compare: the difference between the two builds is what the authors will ship if they do not look. On one draft that difference was 47 citations against 14 genuinely missing entries.

**Grep the rendered text for the authors' own editorial macros, not the source.** In-progress comment macros (`\todo`, `\fixme`, first-initial macros like `\ab{...}`) are usually defined to *print*, in colour, and survive into a double-blind submission carrying their author's name. `pdftotext main.pdf - | grep -c 'Name:'` settles it in one command; the source cannot, because a macro that looks inert may be `\newcommand`-ed to render. Count them and say where the reader-visible ones fall — abstract and first body page are the ones that matter. This is a desk-reject risk at every double-blind venue and it is the most common anonymity leak by a wide margin, ahead of identifying filenames.

**Delete stale `.bbl` before testing a bibliography.** `\bibliography{...}` inputs `./main.bbl`, so a leftover `.bbl` in the source directory silently shadows your test even with `-outdir`. If citations resolve suspiciously well, or no `.blg` appears, that is what happened. This also explains a class of real defect: a submission built past a fatal error against an old `.bbl` ships a bibliography that no longer matches its own citations.

## Venue traps (phase 2)

**Read the template's own comments — they list the commands that block publication.** `grep '^%' <venue>.sty main.tex` typically yields lines like *"`\nocopyright` -- Your paper will not be published if you use this command"*. Collect them, then grep the *comment-stripped* source for live usage. Check `\vspace` too: negative vertical space to win room is the most common silent violation. Verify the page split by extracting text per page rather than trusting the page count — "7 pages of content, 9 total" means the References heading must fall at the top of page 8, and that is a one-command check.

**A venue-mandated statement can be present in the source and absent from the PDF.** Templates gate required blocks on class conditionals — a track option, a camera-ready switch — and an *unset* option commonly falls through to a branch that sets none of them. The statement then sits in `main.tex` looking done while the PDF has no trace of it, which is worse than a visible placeholder because nothing prompts anyone to fix it. Never confirm a mandatory statement from the source: grep the **rendered text**, then read the class to find which flag gates it (`grep -n 'newif\|needs' <venue>.cls`). An unset track option usually also prints its own header banner — *"Unspecified Track"* or similar — which is the visible symptom of the invisible defect.

## Figure text layers (phase 3)

**Extract the text layer of every figure** — `pdftotext Figures/*.pdf -`. Plots are generated by scripts, so their legends contain series the prose may never mention. On one submission this surfaced a fourth series in the headline scalability figure — a CPU build of the authors' own engine — whose name appeared **zero times** in the `.tex`. It was the ablation separating the paper's GPU claim from the effect of reimplementation alone, and no reader could have known it existed. Compare the series names against the text and ask about any that are unexplained.

## Baseline provenance (phase 4a)

On one review the provenance check took fifteen minutes and produced the finding that set the rating. While you are there: does every baseline named in a results table have a bibliography entry? On one paper four of nine did not. `comparing-papers` on one real paper reproduced a critical finding (6.4M vs 60M examples, ~11%) that had taken a manual pass through two appendices.

## Rendering the review (phase 6)

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

## Every artifact, by module

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
| Writing markup | `main-annotated.tex` / `.pdf` (author `LG`, green) | A |
| Writing report | `writing-report.md` / `.pdf`, `writing-ledger.jsonl`, `glossary.md` | A (report only in B) |
| PDF pseudo-source | `review-assets/structure.md`, `refs.bib`, `refs-low-confidence.md`, `body-*.txt` | PDF-only |

Every `.md` in that table gets a `.pdf` from `md2pdf --review`; deliver both.
