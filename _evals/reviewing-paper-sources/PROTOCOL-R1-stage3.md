# Protocol R1, stage 3: documented internal defects (arXiv v1 fixed in v2)

Written 2026-11-08, before any screening or run. Design settled with the researcher in an interview
the same day (journal `2026-11-07.md`, "Decision record: R1 stage 3"). It replaces the
two-sentence sketch in PROTOCOL-R1 ("2-3 papers with a published erratum, both arms, 2 runs,
direction only"). The material source changed (arXiv revisions instead of published errata,
because the latter predate the model's cutoff); the probe character is kept.

## Question

Do reviews (skill vs bare) find **real, author-confirmed** internal inconsistencies? Every earlier
reviewing measurement used planted defects, and the bare agent was at ceiling on them (R1:
about 22/24). A defect that survived the authors' own reading and was fixed only in a revision is a
different test of the same ability. Direction only: no pass bar.

## Material

**Pool.** arXiv papers in cs.LG, cs.CL, cs.CV, cs.AI or stat.ML, v1 submitted from 2026-07-01
(after the model's training cutoff), with at least a v2 whose comment field mentions a correction
(arXiv API query on `co:` with the words corrected, correct, fixed, fix, typo, error, erratum,
mistake, inconsistency). Listed in submission order and screened in a shuffled order (seed
20261108). v1 and v2 LaTeX sources are downloaded and flattened (P1/C2 tools).

**Eligible defect.** A difference between v1 and v2 that **corrects an internal inconsistency of
v1, checkable from v1 alone**: two places in v1 disagree (a prose number vs its table or figure
caption, an abstract claim vs the results, an arithmetic result vs its inputs, a main-text claim vs
an appendix, a definition vs its use), and v2 makes them agree. It must be checkable by reading
v1: no code, no web, no new experiment. Excluded: wording and spelling, references, author or
affiliation changes, added experiments or sections, numbers changed in only one place with no
counterpart in v1 (a re-run, not an inconsistency), and proof errors (verifying-proofs ground).

**Screening.** One subagent per candidate paper reads the comment and the flattened v1-to-v2 diff
and proposes eligible defects, each with: the v1 span (verbatim), the v1 counterpart span it
contradicts (verbatim, unchanged or changed in v2), the v2 correction, and one line on why v1 is
inconsistent. Claude checks every proposal against the two sources and records the check. A
paper is eligible with at least one checked defect. The first **8 eligible papers** in screening
order are used. If the pool is exhausted first, the probe runs on what exists and the pool is
widened only with the researcher.

**No disguise.** The papers are post-cutoff and no web tools are given. A memory probe is not
needed for post-cutoff material without web, but a 1-run probe per paper (bare, no tools: "what is
known about the paper titled X") is logged as a check.

## Arms

| arm | what it is |
|---|---|
| `skill` | reviewing-paper-sources as published at the commit recorded when cases are built (includes R3's fixed review form and checker) |
| `without` | the same agent with no skill |

R3's prompt, verbatim (internal review, no bibliography or related-work checks, `review.md` plus
a JSON issue list). Tools: Read, Write, Edit, Bash, Glob, Grep, Skill. **No web tools** (v2 is
online). Model claude-opus-5-5, 150 turns, 40 min. **2 runs per paper per arm: 32 runs.** Gated by
`usage_gate.py --five 0.50 --seven 0.80`. Deliverables kept by the scaffold watcher
(`explaining-derivations/private/run/keep_files.sh` pattern).

## Scoring

**Sonnet judge, no tools, run twice, tie-break on disagreement.** It sees: the defect (v1 span,
counterpart, v2 correction, why) and the review (review.md + the JSON issues). It classifies each
documented defect per run:

- **FOUND**: the review names this inconsistency, meaning the two disagreeing places or the wrong
  value together with what it should agree with. A vague concern about the same section is not
  enough.
- **NOT_FOUND**.

Claude reads every FOUND evidence quote against the review before the result is written.

**Reported (direction only; no criterion):** documented-defect recall per arm (defects found /
defects × runs), papers with ≥1 defect found, run-to-run agreement on the documented defects
(same verdict in both runs), issues per run, cost, and the judge flip rate. The arms are said to
differ only if recall differs by at least 2 defects-runs *and* the difference has the same sign
on at least 5 of 8 papers. Otherwise the probe reads "no difference visible at this size".

## Reading

- Both arms high: real fixed-in-v2 inconsistencies are within the bare agent's reach as well.
  Stage 3 closes the R1 thread.
- Both arms low: these defects are hard for either arm. Report which kinds were missed; any
  follow-up (a structured check the agent must answer, per the C2 lesson) is the researcher's
  call.
- The arms differ: report it, and propose a scaled test (12 papers x 3 runs, pre-registered bar)
  to the researcher. Nothing is merged or changed on a probe.

## Cost

Screening: API calls and source downloads (free), plus ~10-15 subagent diff reads. Runs: 32 x
~$1.70 = ~$55. Judge under $5.

## Amendment 1 (2026-11-08, during screening, before any run)

Pool: 230 API hits, 202 with v1 ≥ 2026-07-01 and a v2+ (`private/r1s3/pool.json`). Screening
steps added for efficiency. They decide nothing about eligibility, which stays with the diff read:
(1) a **comment pre-filter** drops entries whose comment is metadata-only (author, link,
affiliation… with no content word), declares no content change, or announces a withdrawal or
misupload (`screen.py prefilter`); (2) diffs with **0 changed lines** are not read; diffs with
**more than half the lines changed** (substantial rewrites, where an isolated fix cannot be
attributed) are not read; (3) diffs of **≤ 10 changed lines** are read directly by Claude rather
than by a subagent (first batch: 4 read, none eligible: title change, author removed, added
related work, a deleted sentence fragment). Subagent screeners run on Sonnet with
`private/r1s3/screen_prompt.md`. Downloads use a generic User-Agent.

## Amendment 2 (2026-11-08, material fixed, before any run)

Screened in order: 28 diffs read (8 directly by Claude, 20 by subagents); every proposal was
checked against the v1 source by Claude (`private/r1s3/decisions.json`). Eligible papers in
screening order: 2607.06254, 2608.11985, 2610.16067, 2607.06542, 2608.15428, 2609.31713,
2609.10739, 2607.02802. These are the **first 8, selected**. 2607.24016 (6 defects) is the
reserve: it is eligible but ninth. **Gold: 12 documented defects.** Kinds: arithmetic (F1 from a
stated split), counts (thirteen vs twelve; seven depths with six values; nine vs eleven models;
eleven vs thirteen), table-vs-text (a "variants" column summing to 57 vs "21 variants"; a stated
range vs the table; "0.0% for all" vs a 4.17 cell), a reversed direction stated twice, and a
figure-vs-table taxonomy. **Grouping rule:** when one figure or table contradicts another in many
entries of the same kind (2609.31713: 11 methods placed differently in Fig. 2 and the method
table), the cluster counts as **one** defect, found if the review names at least one instance.
Separate places stay separate defects (2607.06542: two sentences, two defects). Rejected
proposals (needed an unstated assumption, ambiguous ordering, rhetoric within noise, or v1 not
demonstrably inconsistent) are listed with reasons. Memory check (bare, no tools, title): the
model knows none of the 8 papers (`private/r1s3/probe/`). Skill frozen at d2329ee
(`run/FROZEN`, includes R3's form). Scoring material hash **eea73b907719**; cases **56f192bb554b**.
