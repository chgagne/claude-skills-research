---
name: explaining-derivations
description: Use when a proof or derivation needs to be made explicit step by step — expanding a paper's algebra for a reader without formal mathematical training, producing a worked companion document, or establishing whether a derivation can be justified at all. Triggers on "explain this derivation", "walk me through this proof", "expand the algebra", "I can't follow this step", "make this readable for a non-mathematician", or a referee needing to show why a step does not follow.
---

# Explaining Derivations

## Overview

**An expansion that cannot be completed is evidence against the derivation.**

That is the thesis, and it is what separates this skill from pedagogy. Making a
proof explicit is useful in itself — but the moment a step resists being made
explicit, you have learned something about the proof rather than about the reader.
A step nobody can justify leaves this skill as a gap-ledger row with a severity,
and that ledger feeds back into the review as findings.

So the deliverable is two things at once: a standalone LaTeX document per theorem,
readable by an undergraduate engineer or an ML graduate student without formal
maths training, **and** a ledger of every step that could not be written down.

**Core principle: never manufacture a justification.** The register that reads
best is also the one that most invites a plausible-sounding reason for a step
nobody checked. Every guard below exists for that.

## Run it

```sh
python3 ~/.claude/skills/explaining-derivations/assets/run-explain.py main.tex \
    --out derivations/ --level grad-ml --plan-only
```

Run it by absolute path from the paper directory. Stdlib only — no install, no
venv. `latexmk` is used if present, never installed; absent, the `.tex` is still
written and the run exits `2`.

- `--plan-only` **first, always.** A dozen theorems is a dozen subagents. It
  prints the plan and dispatches nothing.
- `--level undergrad | grad-ml | expert-shorthand` — see `reference/registers.md`
- `--verdicts review-assets/proofsteps.csv` — verdicts from `verifying-proofs`.
  Without them **every *Checked* cell reads *not run***, and the expander is
  forbidden to write one it did not receive
- `--claims thm:main` · `--only-flagged` · `--all-gaps` · `--no-pdf`

Outputs into `--out`: `<label>.tex` and `.pdf` per theorem, `index.md`,
`gaps.json`, `requests/*.json`, and `preamble.tex` copied in so the artifact still
builds after this skill is gone.

## The workflow is three phases, not one command

**1. Plan.** `--plan-only` ranks claims by *load-bearingness* — a lemma the main
theorem leans on before an isolated corollary — and costs each in inference steps
rather than sentences. Choose what to expand.

**2. Dispatch one subagent per theorem.** The tool writes one
`explain-request/1` object per claim into `requests/`. Each carries the claim, the
proof's steps verbatim, the **frozen notation**, the definitions and results the
proof references, and any mechanical verdicts. The subagent returns one
`explain-fragment/1` object and **writes no files** — the dispatcher owns all I/O,
which is what makes assembly deterministic and notation collisions detectable.
See `reference/subagent-contract.md`.

**3. Assemble.** Rerun with `--fragments`. Fragments are validated, notation
collisions become gap rows, documents are built, and the gap ledger rolls up.

## The step block

Each step renders as two bands: the mathematics on top with the move as a tag,
the small print below.

```
Step 4                                    apply-named-inequality:jensen
  FROM   E[ sum_i f(x_i) ]
  TO     sum_i E[ f(x_i) ]
  ----------------------------------------------------------------
  Licensed by  Jensen's inequality
  Breaks if    the sum is infinite -> needs dominated convergence
  Checked      MAJOR by sideconds (checks/proof-thm-elbo-s04.py)
  In words     averaging a total is the same as totalling the
               averages, as long as there are finitely many terms
```

Not a seven-column table: wide tables run off the right margin and the text is
clipped silently. **Render the pages and look at them** after any layout change —
`build.py` scrapes the log for overfull boxes and missing glyphs, because both
produce a PDF anyway.

## `Licensed by` is a closed set of four

| Kind | Meaning |
|---|---|
| `equation` | a labelled equation in this paper |
| `citation` | a cited result, with its bib key |
| `named-result` | an entry from the move vocabulary |
| `not-established` | **nothing in the paper licenses this move** |

Free text is refused by `fragment.py`. **If one guard in this skill survives, it
should be this one.** The `expert-shorthand` register otherwise invites a
confident-sounding reason for a step nobody checked, and a fabricated
justification is worse than an admitted gap. `not-established` is a first-class
answer, not a failure.

## The gap ledger

| Severity | Meaning |
|---|---|
| `BLOCKING` | The step could not be justified at all. The derivation has a hole here until someone supplies what `what_would_close_it` names. |
| `SUBSTANTIVE` | Justifiable only under an assumption the paper never states. |
| `NOTATIONAL` | A symbol collision, an undefined symbol, notation that shifts meaning mid-proof. |
| `COSMETIC` | An index slip that does not threaten the argument. |

Default view is `SUBSTANTIVE` and above; `--all-gaps` shows everything. A
`BLOCKING` gap is rendered **inline, where the step would have been**, as well as
in the ledger — a gap relegated to an appendix reads as an afterthought.

**"No gaps" is stated explicitly, never implied by an empty section**, and it says
what it means: the expansion was completed, not that the theorem is true.

## Failure is a result

A subagent that cannot finish returns `BLOCKING` gaps plus whatever rows it has.
After one retry, the document gets a section titled *"This derivation could not be
expanded"* carrying the partial ledger. That is the thesis in operation, not an
error path — and it is why the skill never silently produces a shorter document.

## Keeping independent fragments coherent

Four guards, because fragments are written by subagents that never see each
other's output:

1. **Frozen preamble**, computed before dispatch and passed read-only. A fragment
   containing `\usepackage`, `\newcommand` or `\documentclass` is refused — a
   fragment is a body, not a document. `macros_requested` is the sanctioned
   channel, and a granted macro is regenerated into *every* document.
2. **Symbol-collision detection** after all fragments return. Two expansions
   introducing the same symbol with different meanings produce a `NOTATIONAL` gap
   and a rename, never a silent overwrite.
3. **A controlled move vocabulary** — ~32 names, each with a canonical *Breaks
   if*. An off-vocabulary move is flagged, **not dropped**: losing the row would
   lose the explanation.
4. **Content-hash binding.** Every row carries the ledger step's hash, and a row
   whose hash no longer matches is refused rather than attached to a step that has
   since changed.

## When latexmk is absent

A question for the user, never an install. The `.tex` is written, the run exits
`2`, and `index.md` shows the document with **not built** in place of a PDF.
Losing the expansion — the expensive part — to preserve the build would be the
wrong trade.

## Limits

- **It explains; it does not verify.** A step rendered with a licence is a step
  someone could justify, not a step proved correct. Where a mechanical verdict
  exists it is shown; where none was supplied the cell reads *not run*.
- **A derivation with no gaps has been made explicit, nothing more.** It is not a
  proof that the theorem holds.
- **One PDF per theorem at `undergrad` register is a lot of paper.** A 40-step
  proof produces something nobody reads end to end. `--only-flagged` narrows to
  steps a checker flagged or the author hedged; the gap ledger stays complete
  either way, and it is the part that carries the finding.
- **It never rewrites the paper's proof.** The document is a companion, and the
  orchestrator's Mode B rule — never rewrite the authors' text — applies.
- **A proof written as running prose rather than `\begin{proof}` is invisible**,
  because the ledger cannot find it.

## Status: experimental

**The dispatch loop has never run end to end.** Triage, the frozen notation, the
fragment contract, assembly and the PDF build are each unit-tested in isolation,
and the templates have been compiled and looked at — but no subagent has yet
returned a fragment that was validated against a real ledger and assembled into a
document. Until that has happened once, treat a clean run as untested rather than
as evidence.

Everything upstream of dispatch *is* exercised on real papers: the step ledger,
triage ordering and request generation all run against live drafts.

## Measured results

On arXiv:1810.02054, `--plan-only` produced 10 expandable claims and **96
inference steps**, ordered load-bearing first: four lemmas the main results depend
on ahead of a 35-step theorem nothing depends on. Step counts distinguish
inferences from narration, so a proof that is thirty sentences of scene-setting
and two inferences is correctly costed as a short job.

On a second draft it planned 12 claims and 540 inference steps — but only after a
fix: triage had been skipping every claim marked `duplicate_of`, which on a paper
that states theorems in the body and proves them in an appendix meant **all five
main results were silently dropped from the plan**.

## See also

- `reference/subagent-contract.md` — the exact request and response, versioned
- `reference/registers.md` — what each of the three registers says and omits
- `reference/move-vocabulary.md` — the controlled move list and its canonical
  *Breaks if* clauses
- `reference/gap-ledger.md` — severities, and why an uncompletable expansion is
  evidence
- `verifying-proofs` — produces the verdicts this skill renders, and the step
  ledger both read
- `reviewing-paper-sources` — phase 0 offers this skill; phase 4b invokes it
- Shared parsing layer: `_shared/latexmath`
