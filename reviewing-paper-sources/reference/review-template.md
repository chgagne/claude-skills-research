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

**Recommendation: <verdict>.** Two or three sentences: what is real and worth
keeping, what must be fixed, and whether it is fixable in the time available.

## 3. Strengths

Numbered, specific, and honest — name the single best sentence or idea in the
paper. A review with no credible strengths section will not be believed on its
weaknesses.

## 4. Major concerns

One subsection per concern, **ordered by severity**, each tagged
*(Severity: critical / major / moderate)* and labelled M1, M2, … so the rest of
the document and the annotated `.tex` can cross-reference them.

Each concern states: what is wrong, the evidence (arithmetic, quotation, or
source), why it matters, and — in Mode A — the concrete fix and its cost.

## 5. Bibliography audit

See `reference/bibliography-audit.md`. Subsections: material errors, minor,
correct as written, unverifiable, selective citation, action.

## 6. Figures and tables

Per figure: legibility at printed size, redundancy against other figures and the
prose, encoding consistency, and share of the page budget. Per table: whether
the columns are commensurable, and whether the caption describes what is
actually in it.

## 7. Detailed comments by section

Section by section, including title, abstract, and keywords. Line-level
observations that are not major concerns. Note repetition counts of the headline
result.

## 8. Writing, formatting, and mechanics

Compilation warnings, page-budget compliance, placeholder values, spacing hacks,
voice and register, hyphenation and terminology consistency.

## 9. Action section (Mode A) — title it for the lifecycle stage

Ordered by value ÷ cost, each with a time or compute estimate, and an explicit
statement of which items are necessary versus optional. This is the most
actionable part of the review — do not let it become a restatement of §4.

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
