# The step ledger

`_shared/latexmath` turns a document into one JSON object, schema
`latexmath-ledger/1`. Both `verifying-proofs` and `explaining-derivations` read
it and nothing else. The machine-readable field reference ships as
`_shared/latexmath/schema.json`; this file explains the parts whose *design* is
not obvious.

Flat entity lists with stable ids, cross-linked. Hierarchical would force the
explainer (which wants per-claim subtrees) and the verifier (which wants a flat
step stream) into different traversals of the same data.

## Why a "step" is hard, and how one is delimited

A proof is prose with mathematics embedded in it, and the unit a checker needs —
one inference — corresponds to no single LaTeX construct. The segmenter runs
these rules in this order:

1. **Comments are blanked, not stripped.** Offsets must survive, because a step
   records the byte span it came from. Authors leave whole commented-out `aligned`
   blocks in appendices, and scanning them produces steps that are not in the
   paper.
2. **Math is masked before sentences are split.** A period inside `$…$`, or inside
   `i.e.`, `Eq.`, `w.l.o.g.`, `s.t.`, `i.i.d.`, does not end a sentence.
3. **Displays attach backwards.** "By Jensen's inequality," followed by a display
   is **one** inference written across two lines. Treating the prose as its own
   step yields a step with no mathematics and a display with no justification —
   two unverifiable halves in place of one checkable whole. A sentence that ends
   in a full stop does *not* capture the display that follows it.
4. **A multi-row display explodes into one step per row.** Nearly all mechanically
   checkable content lives here.
5. **A top-level relation chain inside one row explodes** (`a \le b = c` becomes
   two claims sharing a source span).
6. **Every remaining sentence is exactly one step**, classified `inline-assert`,
   `prose-move`, `case-open`, `narration` or `qed`.
7. **Narration merges forward into the inference it introduces.** Without this the
   gap ledger fills with `UNVERIFIED: "Recall the setting of Section 3"`, and a
   reader who sees three of those stops reading the fourth.

Measured on three real papers: **narration / inference = 0.25**, proof text
captured **100%**. The capture figure is a hard gate — below 90% the segmenter is
dropping content and every verdict downstream describes a different document.

## `claim_forms`: adjacent and anchored

An `align` chain is not a list of equations. Row 3 reads `&= \int q(z)\ldots` and
means "the previous right-hand side equals this". Two readings are produced:

- **adjacent** — `rhs_{k-1} REL rhs_k`, the inference the author actually made
- **anchored** — `lhs_1 REL* rhs_k`, the cumulative claim

`REL*` is the composition of every relation so far, and composition is not
cosmetic. A chain `=` then `\ge` then `=` proves `lhs_1 \ge rhs_k`. A chain `\le`
then `\ge` proves **nothing** about its endpoints, so **no anchored form is
emitted** — inventing one would manufacture a claim the paper never made and then
check it.

## `symbols[].domain_provenance`: the field the ladder rests on

`declared` · `inferred` · `user-supplied` · `unknown`.

Only the first three may license a refutation. `declared` patterns fire **near
first use only**: a paper that says `$\beta > 0$` on page 9 has told the reader
nothing about the `$\beta$` on page 2, and a tool that pretends otherwise is
inventing a hypothesis.

Every declared domain carries the sentence it was read from, so the tool's reading
can be checked against the paper without opening the paper.

## `checkable` and `opacity_reasons`

`candidate` · `opaque` · `structural`. A step is `opaque` when a reason from the
**controlled vocabulary** applies:

`undefined-operator:<name>` · `unbound-index:<sym>` ·
`expectation-over-unspecified-measure` · `asymptotic` ·
`probabilistic-quantifier` · `matrix-shape-unknown` ·
`references-external-result` · `natural-language-only` · `macro-unexpandable`

A closed vocabulary is what makes the coverage histogram comparable across papers
and the gap ledger in `explaining-derivations` writable in one language. On the
three-paper corpus the two dominant reasons were
`expectation-over-unspecified-measure` (58) and `asymptotic` (26).

## `content_hash`

The identity of a step: its tokens, not its layout. Stable when the source is
reflowed, sensitive when a symbol changes.

This is what lets an explanation written weeks later be *refused* rather than
silently reattached to a step that has since changed. `explaining-derivations`
carries the hash on every row it produces and rejects a fragment whose hash no
longer matches.

## `coverage`

Not bookkeeping. The histogram heads every report, and on a real paper *"54 of 138
inference steps were mechanically checkable"* is frequently the most important
thing the run learned. A report that leads with three findings and hides the
coverage invites the reader to believe the other 135 steps were checked and
passed.

## `proofs[].attachment`

`explicit-arg` · `adjacent` · `none`. Recorded so the report can say how a proof
was bound to its claim. `\begin{proof}[Proof of Theorem 2]` binds by its argument,
because appendices reorder proofs relative to statements constantly and adjacency
would attach the proof to whatever happens to precede it. An orphan proof is a
diagnostic, never a guess.
