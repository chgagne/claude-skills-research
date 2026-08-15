# The three registers

`--level` picks one. Each is a **contract**, not a mood: it says what must be
explained and what may be assumed, so an expansion can be checked against it.

The audience this skill was built for sits in the middle: an undergraduate
engineer through to an ML graduate student **without formal mathematical
training** — comfortable with calculus, linear algebra and probability as
*tools*, not with measure theory, functional analysis, or the conventions of a
proof.

## `undergrad`

Assumed: single- and multivariable calculus, matrix algebra, basic probability
(expectation, variance, independence).

**Must be explained, every time:**

- every symbol at first use, including ones the paper never defines
- every named theorem or inequality invoked, in one sentence, before it is used
- measure theory in all forms — "almost surely", $\sigma$-algebras, measurability,
  Lebesgue versus Riemann
- functional analysis — norms other than Euclidean, completeness, compactness,
  operator notation
- asymptotic notation — what $O(\cdot)$ quantifies over and what it hides
- concentration inequalities — what the randomness is over
- why an interchange of limit, sum or integral needs justification at all
- index conventions: what ranges over what, and where the bounds come from

**`gloss` is mandatory on every row.** It is the row a reader in this register
actually reads.

**Expand aggressively.** Use `expanded_into` to break one authorial move into
three explicit ones. "Rearranging" is not a step in this register; the two
operations it hides are.

## `grad-ml` *(default)*

Assumed: linear algebra, probability, optimisation, the standard ML vocabulary
(gradients, expectations over a data distribution, convergence rates).

**Must be explained:**

- measure theory and functional analysis, as above
- concentration inequalities beyond Markov and Chebyshev — state the hypotheses
- any exchange of limit, sum, integral, expectation or derivative, with the
  theorem that licenses it named
- asymptotics when the quantified variable is not obvious
- any step whose justification in the paper is a hedge (`clearly`, `it is easy to
  see`) — those are exactly the steps this register exists to open up

**`gloss` is mandatory** on any row whose move is not
`algebraic-rearrangement`. Pure algebra may stand on the FROM/TO pair.

**Expand where the paper compressed.** A step that took the authors one line and
takes three moves to justify gets three sub-steps.

## `expert-shorthand`

Assumed: a reader who could follow the paper but wants the moves named and the
licences made explicit.

Moves are named, not explained. `gloss` is optional.

> **This register carries the skill's main failure mode.** Because it does not
> explain, it invites a confident-sounding `licensed_by` for a step nobody
> checked — the reader has no gloss against which to notice that the licence is
> hand-waving. The closed four-shape `licensed_by` set exists precisely for this
> register, and `not-established` should appear *more* often here, not less.

Even here, three things are never omitted:

1. `breaks_if` on every row.
2. A `BLOCKING` gap wherever a licence cannot be named.
3. The domain provenance table, including symbols the paper never pinned down.

## What no register changes

- The **mathematics** is identical across registers. Registers change what is said
  *about* a step, never what the step is.
- `Licensed by` is the same closed set.
- A gap is a gap. Lowering the register does not turn an unjustified step into a
  justified one.
- The notation table always shows where each domain came from, including
  "never stated".

## Choosing

| Situation | Register |
|---|---|
| Teaching a derivation to someone outside the field | `undergrad` |
| A collaborator or student who cannot follow one appendix | `grad-ml` |
| A referee establishing *why* a step does not follow | `grad-ml` |
| A co-author auditing their own algebra | `expert-shorthand` |

When unsure, use `grad-ml`. An expansion that says too much can be skimmed; one
that says too little sends the reader back to the paper, which is where they
started.
