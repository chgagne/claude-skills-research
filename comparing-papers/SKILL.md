---
name: comparing-papers
description: Use when comparing a draft against specific prior work head to head — checking whether a baseline was trained at the same scale, whether protocols match, how many seeds each ran, or what a competitor actually reports. Triggers on "compare this paper to X", "how does our method differ from Y", "is the baseline comparison fair", "did they train at the same scale", or a shortlist of papers from a gap sweep.
---

# Comparing Papers

## Overview

Puts a draft and its closest prior work side by side on the axes reviewers attack, with
every cell traceable to a quoted sentence and the section it came from.

**The tool gathers evidence; you draw the conclusion.** It computes a note on exactly two
axes — a training-scale ratio and a seed count — because those are arithmetic. On every
other axis it shows two passages and stops. "These protocols differ" reads like a finding
but is a judgement, and a tool that makes it will eventually make it wrongly in a document
you sign your name to.

This automates the check `reviewing-paper-sources/reference/claim-audit.md` calls
*"baseline training scale vs its published scale"*, which otherwise means reading two
appendices and doing a multiplication.

## Run it

```sh
python3 ~/.claude/skills/comparing-papers/assets/run-compare.py . \
    --against "SNIP: Bridging Mathematical Symbolic and Numeric Realms" \
    --out review-assets/

# take the shortlist straight from a gap sweep
python3 ~/.claude/skills/comparing-papers/assets/run-compare.py . \
    --from-candidates review-assets/candidates.json --grade THREAT
```

Run by absolute path from the paper directory. Stdlib only. `--against` accepts a title, a
DOI or an arXiv id and repeats; `--limit` caps how many papers are fetched (default 5).

Writes `paper-comparison-<date>.md` and `comparison.json`. Exit code `2` means some paper
was reachable only as an abstract.

## The acquisition ladder

```
1. arXiv e-print source  LaTeX, read with stdlib tarfile/gzip
2. arXiv PDF             via pdftotext, only if that binary is installed
3. open-access PDF       via OpenAlex oa_url, same caveat
4. abstract              degraded
```

**LaTeX source leads for a reason.** Training scale, seed counts and compute budgets live in
appendices, and appendices are what PDF extraction mangles. Rung 1 needs no PDF parsing at
all and keeps section headings exact. On the SNIP paper it yields 66 sections including
*"Pre-training Data Details"*; the number the whole comparison turns on is in there.

A document that falls to rung 4 is marked **degraded** and the report says so, because
"not found in the abstract" is not evidence of absence.

**Numbers hide inside LaTeX math.** SNIP writes its scale as `$60$ million`, the draft writes
`$10^5$ updates`, and `1{,}000` is a thousands separator. Delimiters are stripped before any
extraction — without that step every numeric pattern silently matches nothing.

## Axes

| Axis | Why a reviewer cares |
|---|---|
| `problem` | what the paper claims to solve |
| `data` | datasets and corpora |
| `training_scale` | **a baseline retrained at a fraction of its published scale can manufacture the headline result** |
| `checkpoint` | if an official checkpoint exists and was not evaluated, that is the first question asked |
| `seeds` | one seed means confidence intervals describe evaluation noise, not training variance |
| `metrics` | whether the comparison is like-for-like |
| `results` | the headline numbers |
| `compute` | the cost the method actually buys its quality with |

`training_scale` prefers a stated total ("pre-trained on approximately 60 million examples")
and otherwise multiplies updates by batch size, showing the arithmetic so you can check it.

## Measured result

Benchmarked against a prior human review of the same draft, which found the scale gap
by hand and graded it **critical**. The tool reproduces it from source text:

| Axis | Draft | SNIP |
|---|---|---|
| `training_scale` | 6.4M examples (100K updates × 64 batch), *Optimization* | 60M examples (stated), *Pre-training* |
| `seeds` | "All variants are trained from scratch with training seed 0", *Hyperparameter selection* | — |

with the computed note **"6.4M vs 60M — about 11% of the other paper's scale"**, matching the
review's 10.7%. 10 acceptance criteria, 68 offline tests.

## Limits

- **The descriptive axes are weaker than the numeric ones.** `problem`, `data` and `metrics`
  find *a* relevant sentence, not necessarily the best one. Treat them as pointers into the
  text; treat `training_scale`, `seeds` and `compute` as findings.
- **`—` means no sentence matched, not that the paper omits it.** Check the source before
  reporting an absence.
- **Release information is often not in the manuscript.** SNIP's `SNIP-10dmax` checkpoint is
  public, but the string never appears in the paper — the checkpoint axis reports *not found*
  for it, correctly and unhelpfully. Look at the repository.
- **Only what the paper wrote.** If a protocol difference is never stated, no extractor finds
  it.
- Slowest of the three review skills: arXiv is throttled at 3s and e-print tarballs are large.

## See also

- `reference/axes.md` — what each axis exposes and what to do with it
- `reviewing-paper-sources` — phase 4 (claim audit) and phase 0 offer this skill
- `surveying-literature` — produces the `candidates.json` shortlist this consumes
