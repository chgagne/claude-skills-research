# Recurring findings and mistakes, expanded

Moved from SKILL.md (R6 reduction, 2026-11-21). SKILL.md keeps the one-line lists; this file
holds the cases they came from. `claim-audit.md` expands the claim checks themselves.

## Repository evidence the draft has not absorbed

**A rebuttal or response directory is a second body of results, and it outranks the draft.**
After a review round the repository often holds the re-runs the authors promised: a
dashboard, a figure-pair script, a batch job. Read it before auditing the draft's numbers,
because the authors may have refuted their own headline and not yet carried it into the
text. On one paper the bench re-ran the baseline at its published recipe and moved it from
47.8 to 88.8 on the metric the abstract leaned on, above the paper's own method as printed.
That was the review, and it was sitting in the repository unused.

**Then check that the bench and the figures aggregate the same thing.** A response bench and
a figure script are two pipelines over one set of runs, and they differ in ways nothing
announces: one may aggregate native inputs where the other standardises, or use a different
arm, pool or seed stream. "Two of the authors' own pipelines disagree" is a tempting finding
and it was wrong on the paper where it was first written — the dashboard aggregated
`*_native_*` while the figure script read `*_standardized_*`, which the appendix had
specified all along. Read both scripts for the series they actually load before reporting a
reproduction gap, and grep the appendix for the protocol word before believing either.

**Verify an aggregate column from the per-item data, not from its name.** A `Pooled` or
`Union` column that beats every component looks impossible and is usually fine for a
retrieval metric, while a column that is genuinely a fourth dataset can hide under either
name. Count distinct items per group in the released per-item file: on one paper the pooled
column had exactly 129 = 81 + 35 + 13 rows and matched the size-weighted mean of the three
corpora to 0.003, which settled in one command a question two subagents had answered
opposite ways.

**Read the commented-out text** (`grep -n '^\s*%' sections/*.tex`). Authors delete their own
caveats under page pressure, and a caveat they wrote and cut is the strongest recommendation you
can make — you are asking them to restore their own sentence, not accept yours.

## The refutation pass (phase 8), what it needs to be told

Across four PDF-only reviews the pass changed the **rating on three of them**, because the
findings it overturned were the ones carrying the recommendation.

- **Adjudicate against the artifact the review pins, not the working tree.** On the
  one review this was tried against, the tree had moved one commit past the reviewed
  artifact and already conceded five of seven findings. Judging a review by
  revisions made in response to it is circular, and the refuter has to be told so
  or it will report those concessions as refutations.
- **Have it check the review's own arithmetic and labels, not only its
  conclusions.** The value showed up inside sound findings rather than against them:
  0 of 7 findings were overturned, and 3 carried a wrong sub-claim — a confidence
  interval attributed to the wrong method, a "the metric cannot fail by
  construction" assertion contradicted by the paper's own figure, and a parenthetical
  whose numbers could not average to the figure they were said to average to. Each
  would have been corrected by an author, and a review's authority rests on getting
  exactly that kind of thing right.

An objection neither answered nor recorded is the one that comes back in the authors' response.

Nothing else in the workflow re-checks the review's own statistics — phase 4 audits
the paper's arithmetic, not yours.

## Common mistakes, with their cases

- **Reviewing the committed PDF.** It may not correspond to the sources. Compile first.
- **Spot-checking the bibliography.** In practice errors cluster in the references the authors were least likely to re-read — the classic ones. Sampling misses them.
- **Clearing an entry after checking authors only.** Check authors, title, venue, volume/issue, pages, and DOI. A correct DOI beside a wrong title is how fabrication becomes detectable.
- **Softening the central objection.** If the headline claim is unsupported, that belongs in the summary, not in concern #7.
- **Writing "should be improved" without the fix.** In Mode A every concern needs a concrete, costed action.
- **Skipping the figure render.** Illegible figures are invisible in the `.tex`.
- **Writing "the paper does not report X" after one failed search.** The largest source of
  wrong findings in PDF-only reviewing, six times across four reviews. Read the caption and
  heading inventory end to end, search the concept in several wordings, and read the whole
  subsection rather than the paragraph you landed on. Never write "I would accept this if the
  paper did Y" without checking that it has not already done Y.
- **Shipping a typographic finding straight from the text layer.** Extraction artifacts
  masquerade as author errors: a caption clipped out of the printed page, a hyphen removed at
  a line break, axis labels producing doubled words. Render the page and look before reporting.
- **Treating `WEAK`/`UNVERIFIED` as a pass.** They mean no database confirmed the entry — which is what a fabricated reference looks like. Check them by hand.
- **Reporting a rate-limited run as a clean bill.** When the checker's circuit breaker drops a source, most entries fall through to title-search only. Say "nothing wrong was found in a degraded run", not "the bibliography is correct", and re-run when quotas reset.
- **Letting the review PDF drop characters.** md2pdf warns, but you have to read the warning: a missing glyph is deleted silently by the engine, so the sentence reads as though you never wrote it.
- **Delivering only one format.** The `.md` is for editing and diffing, the `.pdf` for circulating. Produce both and say where they are; do not make the user ask.
- **Counting warnings and calling them defects.** LaTeX warns once per *use*, so "12 undefined
  cross-references" can be 12 uses of 10 labels. Say which you counted, and make any
  parenthetical breakdown add up to the headline number — on one review it summed to 8 beside a
  12, which is exactly the arithmetic an author checks first. The same applies to "N of M"
  counts over a file: decide whether a file named only inside a commented-out `\input` counts
  as used, and say so.
- **Taking a refuter's correction without recomputing it.** The pass exists to catch your
  errors, and it makes its own: on one review it proposed a page list and a publisher volume
  number that the sources did not support, alongside four corrections that were right. Recheck
  each objection the same way you checked the finding, and keep your number when it holds.

## The disqualifying line

Across five reviews on file the verdict line once named `M1–M3` while its own prose named a
fourth item carrying desk-reject risk; a reader acting on the bold line would have submitted with
it outstanding.

## Phase text before the R6 reduction

Kept word for word so nothing in the earlier SKILL.md is lost.

### Phase 4a in full

**4a. Check baseline provenance.** Before comparing protocols, establish whether the baseline
rows were re-run or quoted. Take the reported values, pull that paper's own source
(`curl -sL arxiv.org/e-print/<id> | tar -xz`, or CVF/ACL Anthology for camera-readies), and
diff. An exact match across every column to two decimals settles it. Then read the baseline's
methods section and compare protocol and search budget against the submission's. On one review
this took fifteen minutes and produced the finding that set the rating. While you are there:
does every baseline named in a results table have a bibliography entry? On one paper four of
nine did not.

For the baseline-scale and seed-count checks specifically, invoke `comparing-papers`:
`python3 ~/.claude/skills/comparing-papers/assets/run-compare.py . --against "<baseline title>" --out review-assets/`
It fetches the baseline's LaTeX source, extracts `updates x batch` against the baseline's own
published scale, and computes the ratio with both quotes. On one real paper this reproduced a
critical finding (6.4M vs 60M examples, ~11%) that had taken a manual pass through two
appendices.

### Phase 4b in full

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

### Phase 5 in full

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

### Measured lines (R3, R5b) in full

Measured (R2-R3, `_evals/reviewing-paper-sources/RESULTS-R3.md`, 6 drafts x 3 runs): with the form
every review had the same twelve sections and passed the checker (18/18; 0/18 for the advisory
template and for no skill); checklist coverage 0.90 vs 0.86 (old skill) and 0.85 (no skill), at
1.15x the old skill's cost. It does not change which findings a run raises or the verdict, and
real errors were found as often as without the skill (0.96).

Measured (R5-R5b, `_evals/reviewing-paper-sources/RESULTS-R5b.md`, 6 post-cutoff papers with their
figure files, 96 figures and tables, 3 runs): with one §6 row per float enforced by `--floats`,
reviews addressed 0.94 of the floats, vs 0.78 for the form without it and 0.62 for no skill. The
same floats were covered across runs (Jaccard 0.90 vs 0.81). A separate inventory script that also
rendered every figure did no better (0.90) and was dropped. Cost $1.90 per run vs $1.70.

### Phase 7 and 7b in full

**7. Annotate the sources (Mode A only).** Produce `main-annotated.tex` with `changes.sty` markup and a corrected `.bib`. See `reference/annotating-with-changes.md` — check the document class for a forbidden-package list first, and expect the `[final]` accept-all build to be less reliable than the markup build. Render the marked-up pages and look at them; markup that compiles can still be garbage.

**7b. Proofread the writing (Mode A, when selected in phase 0).** Invoke
`proofreading-paper-writing` on `main-annotated.tex` *after* the scientific markup exists,
so its green `LG` author layers on the blue `CL` marks without touching them. It adds
`writing-report.md`/`.pdf`, `writing-ledger.jsonl` and `glossary.md`. Its framing findings
(terms used before definition, contributions the results do not support) belong in this
review's §8 as well, in one sentence each with their `W<n>`; do not re-score anything for
them. In Mode B the skill runs report-only and its top findings go into §8 as prose.
