# Reviewing when all you have is the PDF

Referee work usually arrives as a single blind PDF. The rest of this skill
assumes LaTeX sources: `run-bibcheck.py` wants a `.bib`, `run-proofcheck.py`
wants a root `.tex`, `run-survey.py` and `run-compare.py` want a `paper_dir`.
None of that is available, and the two habits that compensate for it are the
ones this file is about.

## Build the pseudo-source first

```sh
python3 assets/run-pdfshim.py paper.pdf --out review-assets/
```

| Output | What it is for |
|---|---|
| `structure.md` | Pages, headings, every caption, where the body ends, how many reference lists exist. **Read it end to end before anything else.** |
| `refs.bib` | Synthetic BibTeX. Feeds `run-bibcheck.py` unmodified. |
| `refs-low-confidence.md` | Entries whose parse looked unreliable. Transcribe these from the page by hand. |
| `body-flow.txt` | De-hyphenated, unwrapped prose. `pdftotext` hard-wraps, which defeats every multi-word search. |
| `body-raw.txt` | Raw layer. Search this too: `flow()` joins a line to the next only when the next starts lowercase, so a doubled word before a capitalised token ("…in in\nEq. 3") survives only in the raw text. |
| `appendix-*.txt` | Same, for the supplement. |

The shim replaces transcription, not judgement. Its reference parsing was
measured against three public papers by diffing extracted titles against each
paper's own `.bbl`/`.bib`:

| Reference style | Printed | Parsed | Flagged low | Precision on unflagged | Title recall |
|---|---|---|---|---|---|
| Numbered `[1]` (arXiv 2203.08679) | 45 | 45 | 5 | 100% | 97.8% |
| Surname + initials (arXiv 2103.00020) | 210 | 203 | 10 | 99.5% | 95.2% |
| Full-name ACL style (arXiv 1907.11692) | 51 | 52 | 24 | 92.9% | 60.8% |

One defect worth knowing about because it was shipped and then caught: the first version
emitted the printed author list verbatim into the `author` field. BibTeX separates authors
with ` and `, so the checker read each list as a single author and reported every co-author as
missing — three fabricated findings in a six-entry sample, indistinguishable in a report from
real ones. If you extend the shim, **run its output through `run-bibcheck.py` and confirm a
clean bibliography comes back clean**; a tool that manufactures findings is worse than no tool.

The same failure recurred once more in use, from a different cause. In a semicolon-separated
list a wrapped line often begins with a co-author ("…Piperno, M.;" / "Ciora, O.-A.; Pachl, E.;
…"), which looked like the start of a new entry; the entry was split mid-list and the truncated
half was reported as an entry missing four co-authors. On one paper that produced two of three
CRITICAL flags, both false. The fix is to require the entry in hand to be complete — to contain
a year — before a line may start a new one, which costs about two points of recall and removes
the fabricated findings. **Whenever the checker reports missing co-authors, read the printed
entry before believing it.**

Read the ACL row as the honest ceiling: for full-name author-year lists the
parser flags nearly half its own output, and what it does not flag is still only
93% right. **Always check the parsed count against the printed list.** A parser
that silently returns 7 of 50 entries looks like a short bibliography, not a
broken parse.

## The absence rule

The single largest source of wrong findings in PDF-only reviewing is writing
*"the paper does not report X"* after a search that missed it. Across four
reviews this produced six false findings, every one of them survivable by
reading rather than grepping. Real examples of what went wrong:

- Searched `leave-one-out`; the paper said `leave-one-dataset-out`.
- Read the second paragraph of a supplementary section and cited it, without
  reading the first paragraph, which contained the seed variance being demanded.
- Used `^(Figure|Table) \d` to inventory captions; in a two-column extraction
  captions share a line with the adjacent column, so two floats went missing and
  a numbering gap was nearly reported.
- Wrote "I would accept this if it were stated in the main text" about something
  stated in the main text, on the page under review.

**Before any sentence of the form "the paper does not report / never states /
omits X":**

1. Read `structure.md`'s heading and caption inventory end to end. Not a grep.
2. Search the concept in three or four wordings, not one.
3. Read the whole subsection you are citing, not the paragraph you landed on.
4. If the claim is that something is *absent from the main text*, confirm the
   main text does not merely point at it.

A promise of credit is a special case: never write "I would accept X if the
paper did Y" without first verifying the paper has not done Y. That sentence
hands the authors a one-line rebuttal.

## Text-layer findings are hypotheses

Anything typographic or presentational that you found in extracted text must be
confirmed against a render of the page it appears on before it enters the
review:

```sh
pdftoppm -r 150 -png -f 7 -l 7 paper.pdf /tmp/pg    # then read the image
```

Two false findings came from skipping this. A stale caption sat in a figure's
text layer but was clipped out of the printed page, so reporting it would have
been a visible-error claim about something no reader can see. A "missing hyphen"
in a product name was `pdftotext` dehyphenating a line break; the hyphen is
there on the page. Figure axis labels and legend fragments also interleave with
prose in the raw layer and generate false doubled-word hits.

## Check baseline provenance

Results tables routinely quote numbers from the cited papers rather than
re-running them, which is fine only if the protocols match. This is cheap to
check and repeatedly produces the finding that sets the rating:

1. Take each baseline's reported values from the submission's table.
2. Pull that baseline's own source: `curl -sL arxiv.org/e-print/<id> | tar -xz`
   gives LaTeX; CVF Open Access and ACL Anthology give camera-ready PDFs.
3. Diff the values. An exact match across every column to two decimals settles
   that they were quoted, not reproduced.
4. Then read that paper's methods section for the protocol it used — loss
   weighting, temperature, epochs, trial count — and compare against the
   submission's. Also compare hyperparameter search budgets.

The same pass answers a second question worth asking every time: **does every
baseline named in a results table have a bibliography entry?** On one paper four
of nine did not.

## Read the appendix's prose, not only its tables

On two separate papers the strongest finding in the review was a sentence in a
supplement conceding something the main text presented favourably: a scaled-up
model performing worse than its own smaller version on an independent benchmark;
a competitor "achieving the best overall performance across most settings".
Neither was concealment, and both were stated plainly where they sat. Both were
absent from the main body a reader actually reads.

So: read the supplement's discussion paragraphs, not just its numbers. The
concession lives in a sentence.

## Ask what turns the contribution off

For any paper proposing a mechanism with a tunable strength, look at the
hyperparameter grid in the appendix **before** the results tables, and ask
whether it contains the value that disables the mechanism. One paper searched
its parameter over four negative values, with no zero and no positive value, so
it never ran itself with its own contribution switched off, and its gains could
not be separated from the tuning around them.

More generally, for a theory paper: are the constants in the guarantee ever
measured on real data? A bound whose parameters are never instantiated cannot be
told apart from a vacuous one.

## Adapting the workflow

- **Phase 1 (ground truth)** becomes: run the shim, then reconcile page count,
  reference-list count and caption inventory against what you can see. There is
  no compile step and no `.bbl` to cross-check the bibliography against, so the
  bibliography audit has only one source of truth instead of two.
- **Phase 4b (mathematics)** cannot use `run-proofcheck.py` without a `.tex`.
  Reconstructing theorem environments from a long PDF is rarely worth it for a
  single paper; do the structural audit by hand instead, and check specifically
  for the things the tool would have: a restatement that drops a hypothesis, an
  induction with no base case, a claim dependency cycle, a division by something
  never shown non-zero. Verify a suspected dropped hypothesis against the
  notation section before reporting it, since standing assumptions declared once
  are easy to mistake for missing ones.
- **Phase 5 (bibliography)** runs normally on `refs.bib`, with two additions:
  hand-transcribe everything in `refs-low-confidence.md` first, and audit *every*
  reference list — a paper can carry a second one in the appendix for dataset or
  resource citations, and `structure.md` says how many exist.
- **Phase 8 (refute)** moves earlier. See below.

## Run the refutation pass before committing the rating

The skill's phase 8 puts the adversarial pass after the review is written. In
PDF-only reviewing that is too late: across four reviews the pass changed the
**rating on three of them**, because the findings it overturned were the ones
carrying the recommendation.

Give the refuter the paper, the review, and this instruction explicitly:

> My most common failure is claiming "the paper does not report X" when it does,
> somewhere I did not look. Before accepting any such claim, search the whole
> document including every appendix page, with several different wordings. If
> the paper does report something the review says it does not, say so loudly.

Then re-verify every challenge yourself against the PDF before acting on it.
These agents over-claim, and on two occasions a challenge's own supporting facts
needed correcting before use. Record what changed: a notes file whose top
section says which of its own earlier claims are superseded is far more useful
than one that silently reads as if it was right all along.
