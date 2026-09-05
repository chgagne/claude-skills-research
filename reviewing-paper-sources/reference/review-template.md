# Review document template

Write to `review-<reviewer>-<YYYYMMDD>.md`. Keep GitHub-flavoured markdown: pipe tables, `**bold**`, blockquotes. `_shared/md2pdf/md2pdf --review` renders it.

The metadata block below is a run of consecutive `**Label:** value` lines, and
`--review` breaks the PDF at each label. Keep that shape: a continuation line
that starts with `**Something:**` becomes its own field, and one that does not
flows into the previous field.

Adapt freely — the section list is a checklist of what must be covered, not a form to fill in. Order concerns by severity, never by paper order.

---

```markdown
# Review — *<paper title>*

**Reviewer:** <name/persona>
**Date:** <YYYY-MM-DD>
**Venue targeted:** <venue, track>
**Artifact reviewed:** `main.tex` @ commit `<sha>`, compiled locally with `latexmk -pdf`
(<TeX distribution>). <N> pages; body ends p.X, references p.X–Y.

> **Note on the repository state.** <Only if there is one: stale PDF, anonymity
> leak, unused files with identifying names, uncommitted divergence. This is the
> first thing the author must act on, so it goes above everything else.>

---

## 1. Summary of the submission

Two paragraphs, neutral, no judgement. Demonstrate you understood it — the
authors should recognise their own paper. Second paragraph: what the evaluation
actually did, with numbers.

## 2. Overall assessment

| Criterion | Score (1–5) |
|---|---|
| Relevance to <venue> | |
| Novelty / contribution | |
| Soundness of evaluation | |
| Clarity of presentation | |
| Reproducibility | |
| Scholarly care | |

**Disqualifying findings:** <M-numbers, or "none">

Each one imposes a floor on the recommendation, and the verdict may not sit above
that floor. The scores are a deliverable for the venue's form; this line is the
review's actual logic. Never sum or average the criteria — a total lets a strength
cancel a defect that cannot be cancelled, and a 5 on relevance does not offset a
1.5 on soundness.

**List every finding that gates the outcome, not a subset.** Anything carrying
desk-reject risk, a venue-compliance breach, or an anonymity leak belongs here
whatever severity tag it wears in §4.

**On an early draft, give this as two lines and score only the first.** *Findings that
gate the science* names the content findings that cap the scores and cannot be edited
away. *Findings that gate the submission but not the judgement* names the container
items from §8 — necessary, non-negotiable, and scored nowhere. Merging them produces a
verdict about the build rather than the work, and the author reads it as a verdict about
the work.

**Recommendation: <verdict>.** Two or three sentences: what is real and worth
keeping, what must be fixed, and whether it is fixable in the time available.
Name the same findings the line above names.

For an already-submitted paper the verdict is moot; retitle to *Assessment for
rebuttal purposes* and let the floor say what must be answered first instead of
what must be fixed.

## 3. Strengths

Numbered, specific, and honest — name the single best sentence or idea in the
paper. A review with no credible strengths section will not be believed on its
weaknesses.

## 4. Major concerns

One subsection per concern, **ordered by severity**, each tagged
*(Severity: blocking / critical / major / moderate)* and labelled M1, M2, … so the
rest of the document and the annotated `.tex` can cross-reference them.

`blocking` is for a defect that stops the submission whatever else is true — over
the page limit, an anonymity leak, a missing venue-mandated statement. It was added
because two reviews reached for the word before the template offered it: the tier
above `critical` was needed and improvised. Every `blocking` finding goes in the §2
disqualifying line by definition.

**On an early draft, `blocking` defects do not belong in this section at all.** Every
example in the paragraph above — page limit, anonymity, a missing mandated statement —
is a property of the *container*, and on a draft the authors have not finished, all of
them are a morning's work they were always going to do. Move them to §8, tag them
*(Blocks submission; not a judgement on the work)*, and keep §4 for content: claims that
are wrong, framing the data refutes, work missing from the argument. §4 stays ordered by
severity within content. For a finished or submitted paper, leave them here as written.

Each concern states: what is wrong, the evidence (arithmetic, quotation, or
source), why it matters, and — in Mode A — the concrete fix and its cost.

## 4a. Not written yet — only for an unfinished draft

Omit this section entirely for a finished paper. When the draft *is* unfinished, it is what makes
the review usable: it separates prose that is wrong from prose that does not exist yet, so the
authors are not made to re-read things they already know are missing.

A table, not prose — location, current state, and a column for whether it blocks submission:

| Location | State | Necessary for submission? |
|---|---|---|
| §8 Conclusions | Heading only | **Yes** |
| Appendix C.3 | Author mid-rewrite | No — appendix |

The third column is the deliverable. Close the section by naming any contribution the notes claim
that the built paper does not contain — a cut experiment still advertised in a Discussion bullet
is a finding, not an omission.

## 5. Bibliography audit

See `reference/bibliography-audit.md`. Subsections: material errors, minor,
correct as written, unverifiable, selective citation, action.

## 6. Figures and tables

Per figure: legibility at printed size, redundancy against other figures and the
prose, encoding consistency, and share of the page budget. Two more that recur on
quantitative papers: whether an axis is truncated with no break indicator — which
magnifies a difference the data may not support — and whether error bars are drawn
at all when the paper reports variance somewhere else. A figure plotting bare point
estimates from an appendix table that has standard deviations in every cell is a
presentation choice worth naming.

Per table: whether the columns are commensurable, whether the caption describes what
is actually in it, and whether every row is cited.

## 7. Detailed comments by section

Section by section, including title, abstract, and keywords. Line-level
observations that are not major concerns. Note repetition counts of the headline
result.

## 8. Writing, formatting, and mechanics — the container

Compilation warnings, page-budget compliance, placeholder values, spacing hacks,
voice and register, hyphenation and terminology consistency.

On an early draft this section also absorbs the `blocking` items that would otherwise
head §4 — anonymity leaks, an unset template switch, missing mandated statements,
missing bibliography entries. Open it by saying plainly that none of it is skippable
and none of it influenced a score, so the author can act on it without reading it as a
verdict.

## 9. Action section (Mode A) — title it for the lifecycle stage

Ordered by value ÷ cost, each with a time or compute estimate, and an explicit
statement of which items are necessary versus optional. This is the most
actionable part of the review — do not let it become a restatement of §4.

On an early draft, carry a **Kind** column reading *Content* or *Container*, and put the
content items first even where a container item is cheaper. The column is what stops a
week being spent on the build: it lets the author see at a glance that the half-day of
mechanical work is a half-day, and that everything else is the paper. Where an item is
genuinely both — cutting to a page limit, say — file it by what it costs: moving figures
to an appendix is container, cutting a result is content.

- **Pre-submission** → "Prioritised plan before the <date> deadline". Close with:
  what the framing should become if only the necessary items get done.
- **Already submitted** → "Rebuttal preparation, in priority order". Everything
  must be answerable in a response: cheap experiments, disclosures, and
  re-aggregations of data already in hand. Separate these from "camera-ready
  fixes regardless of outcome". Check whether the venue permits new results.
- **Post-rejection** → "What to change before resubmission". Structural and
  framing items rank above local fixes here.

## 10. Questions for the authors

Numbered, answerable, non-rhetorical. In Mode A retitle to "Questions the
reviewers will likely ask" — the value is anticipating them, and each should
map to an item in §9.
```

---

## Register notes

**Mode A** — write to a colleague with a shared stake. Blunt about severity, generous about what works, specific about cost. "This is the most quietly damaging sentence in the paper" is appropriate. Always give the fix.

**Mode B** — write to the authors and the chair. Neutral. Diagnose without rewriting. Never propose specific replacement prose; that is the authors' job.

**Both** — no hedging on findings you verified. If the headline claim is unsupported, say so in §2, not in §4.
