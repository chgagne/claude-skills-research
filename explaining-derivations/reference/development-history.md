# Development history and measured results

Moved from SKILL.md (X3 reduction, 2026-11-22), word for word. SKILL.md keeps one line per
result; this file keeps the runs that produced them.

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

## Do two expanders find the same gaps?

This was open for three rounds, and it is the question the thesis rests on: if an
expansion that cannot be completed is evidence about the derivation, evidence
that depends on which subagent you asked is not evidence.

Runs two and three expanded **the same lemma** against materially different
requests — the first with no referenced equations, an 81-symbol glossary and a
70-entry macro table, the second with the cited equations, 6 symbols and no
macros. If the gaps were an artefact of prompting, that is where it would show.

**Every substantive gap the first run found reappeared in the second, and the
reverse** — 4 of 4 topics, both directions. The second split one of them in two.
`assets/tests/test_expander_agreement.py` measures it on every run.

The two disagree about **where to hang a gap and what to call its `kind`**: the
same variable-capture finding sits at `s01/symbol-rebound` in one and
`s02/variable-capture` in the other. Agreement is therefore matched on substance,
not on `step_id` or `kind` — matching on either would measure the labels rather
than the mathematics. That `kind` is free text is a real weakness, and this is the
measurement that shows it.

**One lemma is one lemma.** Two expanders agreeing on four gaps in a seven-step
proof is the strongest evidence available and it is not a sample.

## Measured results

**Against the bare agent (protocol X1, 2026-11), on planted single-step errors: not measured,
because the bare agent was already at ceiling.** Asked only to explain a proof, with no mention of
errors, the bare agent flagged a planted false step (a flipped inequality, a wrong constant or
exponent, a dropped lemma condition) in 22/22 runs, and in 18/20 runs on subtler plants. It never
justified a false step. So the guard against a manufactured licence had nothing to catch at this
plant strength. The one failure was a **silent correction**: the companion wrote the right
constant and never said the paper prints a wrong one (one plant, both runs, in an 8,000-character
proof). A follow-up (X2) planted 8 more harmless constant and exponent slips of that kind. The bare
agent flagged all of them at the step, 16/16, so the failure did not reproduce. What the skill
adds over the bare agent on proofs of this length remains unmeasured.

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

## Passages shortened in SKILL.md (X3), kept here word for word

Free text is refused by `fragment.py`. **If one guard in this skill survives, it
should be this one.** `local-result` was added after a real expansion had nowhere
to put the licence it was actually using — a lemma of the same paper — and
smuggled the label into the `move` field instead. A closed set that leaves out a
common referent does not prevent free text; it displaces it somewhere worse. The `expert-shorthand` register otherwise invites a
confident-sounding reason for a step nobody checked, and a fabricated
justification is worse than an admitted gap. `not-established` is a first-class
answer, not a failure.

Not a seven-column table: wide tables run off the right margin and the text is
clipped silently. **Render the pages and look at them** after any layout change —
`build.py` scrapes the log for overfull boxes and missing glyphs, because both
produce a PDF anyway.

- **`kind` on a gap is free text and two expanders will not agree on it.**
  Measured: the same finding came back as `symbol-rebound` and as
  `variable-capture`, on different steps. Read the gap, not its label.

- **One PDF per theorem at `undergrad` register is a lot of paper.** A 40-step
  proof produces something nobody reads end to end. `--only-flagged` narrows to
  steps a checker flagged or the author hedged; the gap ledger stays complete
  either way, and it is the part that carries the finding.

A question for the user, never an install. The `.tex` is written, the run exits
`2`, and `index.md` shows the document with **not built** in place of a PDF.
Losing the expansion — the expensive part — to preserve the build would be the
wrong trade.
