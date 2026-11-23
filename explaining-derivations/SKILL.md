---
name: explaining-derivations
description: Use when a proof or derivation needs to be made explicit step by step — expanding a paper's algebra for a reader without formal mathematical training, producing a worked companion document, or establishing whether a derivation can be justified at all. Triggers on "explain this derivation", "walk me through this proof", "expand the algebra", "I can't follow this step", "make this readable for a non-mathematician", or a referee needing to show why a step does not follow.
---

# Explaining Derivations

## Overview

**An expansion that cannot be completed is evidence against the derivation.**

That is what separates this skill from pedagogy: a step that resists being made explicit
tells you about the proof, not the reader. It leaves as a gap-ledger row with a severity,
and the ledger feeds back into the review as findings.

So the deliverable is two things at once: a standalone LaTeX document per theorem,
readable by an undergraduate engineer or an ML graduate student without formal
maths training, **and** a ledger of every step that could not be written down.

**Core principle: never manufacture a justification.** The most readable register invites a
plausible reason for a step nobody checked; every guard below exists for that.

## Run it

```sh
python3 ~/.claude/skills/explaining-derivations/assets/run-explain.py main.tex \
    --out derivations/ --level grad-ml --plan-only
```

Run it by absolute path from the paper directory. Stdlib only; `latexmk` is used if
present, never installed (absent: the `.tex` is written and the run exits `2`).

- `--plan-only` **first, always**: it prints the plan and dispatches nothing.
- `--level undergrad | grad-ml | expert-shorthand` — see `reference/registers.md`
- `--verdicts review-assets/proofsteps.csv` — verdicts from `verifying-proofs`.
  Without them **every *Checked* cell reads *not run***, and the expander is
  forbidden to write one it did not receive
- `--claims thm:main` · `--only-flagged` · `--all-gaps` · `--no-pdf`

Outputs into `--out`: `<label>.tex`/`.pdf` per theorem, `index.md`, `gaps.json`,
`requests/*.json`, and `preamble.tex` (so the artifact builds without this skill).

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

**Render the pages and look at them** after any layout change: wide content is clipped
silently and still produces a PDF (`build.py` scrapes the log for overfull boxes).

## `Licensed by` is a closed set of five

| Kind | Meaning |
|---|---|
| `equation` | a labelled equation in this paper |
| `citation` | a cited result, with its bib key |
| `named-result` | an entry from the move vocabulary |
| `local-result` | another theorem of this paper, by its `\ref` label |
| `not-established` | **nothing in the paper licenses this move** |

Free text is refused by `fragment.py`. **If one guard in this skill survives, it
should be this one:** a fabricated justification is worse than an admitted gap, and
`not-established` is a first-class answer, not a failure.

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

## Limits

- **It explains; it does not verify.** A step rendered with a licence is a step
  someone could justify, not a step proved correct. Where a mechanical verdict
  exists it is shown; where none was supplied the cell reads *not run*.
- **`kind` on a gap is free text and two expanders will not agree on it.** Read
  the gap, not its label.
- **A derivation with no gaps has been made explicit, nothing more.** It is not a
  proof that the theorem holds.
- **One PDF per theorem at `undergrad` register is a lot of paper.** `--only-flagged`
  narrows to steps a checker flagged or the author hedged; the gap ledger stays complete.
- **It never rewrites the paper's proof.** The document is a companion (Mode B rule).
- **A proof written as running prose rather than `\begin{proof}` is invisible**,
  because the ledger cannot find it.

## Measured results

- **Against the bare agent (X1, X2):** asked only to explain a proof, the bare agent flagged a planted
  false step or absorbed slip at the step in 38 of 40 runs, so what this skill adds on proofs of that
  length is unmeasured.
- **On a real draft**, one 22-step claim gave 6 gaps (2 `BLOCKING`) at steps no mechanical checker
  reached. That is the case for the skill.
- **Two expanders on one lemma** found the same substantive gaps (4/4), on different steps and `kind`s.

Every dispatch run so far found defects only the compiled pages showed:
`reference/development-history.md`.

## See also

- `reference/subagent-contract.md` — the exact request and response, versioned
- `reference/registers.md` — what each of the three registers says and omits
- `reference/move-vocabulary.md` — the controlled move list and its canonical
  *Breaks if* clauses
- `reference/gap-ledger.md` — severities, and why an uncompletable expansion is
  evidence
- `reference/development-history.md` — the dispatch runs, their defects, expander agreement
- `verifying-proofs` — produces the verdicts this skill renders, and the step
  ledger both read
- `reviewing-paper-sources` — phase 0 offers this skill; phase 4b invokes it
- Shared parsing layer: `_shared/latexmath`
