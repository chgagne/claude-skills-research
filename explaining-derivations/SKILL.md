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

## `Licensed by` is a closed set of five

| Kind | Meaning |
|---|---|
| `equation` | a labelled equation in this paper |
| `citation` | a cited result, with its bib key |
| `named-result` | an entry from the move vocabulary |
| `local-result` | another theorem of this paper, by its `\ref` label |
| `not-established` | **nothing in the paper licenses this move** |

Free text is refused by `fragment.py`. **If one guard in this skill survives, it
should be this one.** `local-result` was added after a real expansion had nowhere
to put the licence it was actually using — a lemma of the same paper — and
smuggled the label into the `move` field instead. A closed set that leaves out a
common referent does not prevent free text; it displaces it somewhere worse. The `expert-shorthand` register otherwise invites a
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

## What the first real run cost

The dispatch loop was closed once, on a 22-step lemma in a real draft: one
subagent, one `explain-fragment/1`, 22 rows and 6 gaps, assembled into an
11-page PDF. **Every component was already unit-tested and the run still produced
six defects**, and only two of them could have been caught without compiling the
document and reading the pages:

| Where | What |
|---|---|
| `--verdicts` | a `proof-ledger.json` loaded as an empty mapping, so every *Checked* cell read *not run* — indistinguishable from a paper no engine could reach |
| `_shared` ledger | stripping `\label{...}` left a blank line inside `align`, and the extracted statement would not compile |
| step blocks | steps were numbered by row position while gaps were named by ledger id, so the ledger pointed at numbers appearing nowhere |
| *Checked* cell | a verdict with no engine rendered as `UNVERIFIED by ?` |
| inline gaps | `SUBSTANTIVE` gaps were rendered in the `BLOCKING` red, under *could not be made explicit*, directly beneath the step that had just been made explicit |
| gap ledger | four narrow columns; any gap carrying inline mathematics overran the right margin by up to 179pt and was **clipped mid-word, with a PDF produced** |

The last one is the reason this file says to render the pages and look at them.
`build.py` scrapes the log for overfull boxes precisely because the failure ships
a document that looks finished.

The expander also needed three moves the vocabulary did not have —
`apply-product-rule`, `drop-lower-order-term`, `mean-field-closure` — which is
the off-vocabulary warning working as designed. They have been added.

## The second run, on a public paper

Dispatched on Bubeck's gradient-mapping lemma (arXiv:1405.4980) — public on
purpose, so the returned fragment could ship as
`assets/tests/test_expansion_replay.py` rather than staying local. 7 rows,
4 gaps, 6 pages. **Five more defects, four of them in the contract rather than
the code:**

| Where | What |
|---|---|
| `licensed_by` | had no kind for *another theorem of this paper*. The load-bearing licence was a lemma — not an equation, not a bib key, not a move — so the expander smuggled the label into the `move` field. A closed set missing a common referent displaces free text rather than preventing it. |
| `assemble.py` | `tex_fragment` was validated for forbidden tokens, stored, and **never rendered**. |
| `assemble.py` | `expanded_into` appeared **nowhere in the code**, while `registers.md` instructs the expander that "a step that takes three moves to justify gets three sub-steps". Roughly a page of this expansion was validated and thrown away. |
| `_shared` segmentation | a licence stated *after* its display — `\[ … \] which follows from Lemma 3` — landed in a narration step of its own, so the display carried no reference and the expander recovered it only by opening the source. |

## The third run, which was a test of the second's complaints

Two complaints had arrived twice by then, from independent expanders on different
papers — no referenced *equations* in the request, and a symbol glossary passed
whole. Both were fixed and the same lemma dispatched again to find out whether
the complaints stopped.

**`context.referenced_equations` was, in the third expander's words, the single
most useful field in the request, and it changed the output.** Having the cited
equation verbatim showed that its *left* half is the convexity inequality, so the
step that uses it is two applications of one displayed result rather than one
application plus an uncited appeal to convexity. **Without it the expander would
have written a gap that was wrong.** A supplied citation is not a courtesy; it is
the difference between a finding and a false one.

The narrowing was half-done and the third run said so: `symbols` went from 81 to
6, `macros` was still the paper's whole 70-entry `\newcommand` list — 15% of the
request's bytes for a proof that invokes none of them. Narrowed the same way it
now yields **zero**, which is the right answer: everything the expander receives
is already macro-expanded, so the table was pure weight. The request is **20 KB,
down from 34**, carrying strictly more.

**And a coordinate bug, the same shape as one found the round before.** The
request advertised `claim.source.offset` as a position in a named file. It is a
position in the macro-*expanded* concatenation, and on this paper it pointed
18,000 characters past the end of the file it named. Subtracting the file's start
looks like the fix and lands somewhere else entirely, because the file map is of
the raw source and expansion shifts every position after it. The field now names
its own coordinate system instead of inviting the wrong reading.

**Still not measured:** whether a *fresh* expander finds the same *gaps* twice.
All three fixtures pin assembly, not expansion.

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

On the one claim from that draft taken all the way through, the expansion
returned **22 rows and 6 gaps — 2 `BLOCKING`, 3 `SUBSTANTIVE`, 1 `NOTATIONAL`**.
Both `BLOCKING` gaps are the thesis in operation: one is a modelling replacement
announced in prose with nothing bounding what it discards, the other an
approximation whose stated justification runs the opposite way to the paper's own
parameter values. Neither is algebra, and neither was flagged by any mechanical
checker — every one of the proof's 22 steps came back `UNVERIFIED`. **That is the
case for this skill existing**: on a proof where `verifying-proofs` reaches
nothing, an expansion that could not be completed still located the two steps
that carry the argument.

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
