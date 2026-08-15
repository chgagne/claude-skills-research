# The gap ledger

**An expansion that cannot be completed is evidence against the derivation.**

This is the file that says what that means operationally. A step nobody can make
explicit is not a formatting problem and not a limitation of the reader — it is a
place where the proof does not, as written, get from one line to the next. The
ledger converts that into a row with a severity, and those rows become review
findings.

## Severities

| Severity | Meaning | In a review |
|---|---|---|
| `BLOCKING` | The step could not be justified at all. No licence could be named, from the paper or from mathematics. **The derivation has a hole here** until someone supplies what `what_would_close_it` names. | `MAJOR` |
| `SUBSTANTIVE` | The step is justifiable, but only under an assumption the paper never states. The algebra may be right and the theorem still unproved. | `MAJOR` |
| `NOTATIONAL` | A symbol collision, a symbol used before it is defined, or notation that shifts meaning mid-proof. Impedes reading; rarely threatens the argument. | `MINOR` |
| `COSMETIC` | An index slip, an off-by-one in a bound that the surrounding text makes obvious. | `MINOR` |

Default view shows `SUBSTANTIVE` and above. `--all-gaps` shows everything.

## Every gap must name its remedy

`what_would_close_it` is required on `BLOCKING` and `SUBSTANTIVE`, and the
validator refuses a fragment without it.

> "This step is unclear" is not a finding. It puts the burden on the author to
> guess what was wanted, and it is indistinguishable from a reader who did not
> concentrate.
>
> "This needs a dominating summable bound, or uniform convergence on the index
> set" is a finding. The author can supply it, cite it, or explain why the
> interchange is unconditional here — and each of those closes the matter.

Good remedies name a *thing*: a hypothesis to add, a theorem to cite, a bound to
exhibit, a case to rule out.

## Where a gap appears

Three places, deliberately:

1. **Inline in the document**, as a red block where the step would have been. A
   gap relegated to an appendix reads as an afterthought; a break in the middle of
   the derivation reads as what it is.
2. **In the gap ledger** at the end of that document.
3. **In `gaps.json` and `index.md`**, rolled up across every expanded derivation,
   and as findings ready to paste into a review.

## "No gaps" is stated, never implied

An empty section reads as *nothing was looked for*. So the document says:

> **No gaps.** Every step above was made explicit with a stated licence. That is a
> statement about this expansion, not a proof that the theorem is true.

The second sentence matters as much as the first. A completed expansion means
somebody could justify every move — not that the moves are correct, and not that
the theorem holds. Only `verifying-proofs` speaks to correctness, and even there
only rarely.

## Over-fragmentation is the failure mode to watch

The main way this ledger becomes useless is length. Dozens of rows that are really
one inference, or gaps opened on narration, and a reader skims — at which point
the one row that mattered is lost.

Three defences:

- The step ledger **merges narration forward** into the inference it introduces,
  so scene-setting never becomes its own unexplainable step.
- Steps and *inference* steps are counted separately everywhere, so a proof that
  is thirty sentences of prose and two inferences is costed as a short job.
- The default view holds back `NOTATIONAL` and `COSMETIC`.

If a ledger still runs long, that is itself the finding, and it belongs in the
review as one: *the proof of Theorem 2 required 14 steps that could not be
justified from what the paper states.*

## Feeding gaps back into a review

`gaps.json` carries a `findings` array already mapped onto the review severity
ladder, with the claim, the step, the detail and the remedy. In
`reviewing-paper-sources` these join the phase-4b findings from `verifying-proofs`.

Say which findings are mechanical and which came from a failed expansion. They
carry different weight: a mechanical `CRITICAL` is a counterexample, while a
`BLOCKING` gap is a considered failure to justify — strong evidence, but evidence
that an author may rebut by supplying the missing licence. Let them.
