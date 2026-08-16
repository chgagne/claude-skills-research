# The move vocabulary

A closed list of names for what a proof step *does*, each with a canonical
**Breaks if** clause. An expansion may specialise the clause to the step at hand;
it may not contradict it.

Two reasons this is a fixed list rather than free description:

1. **Fragments are written independently.** Thirty subagents inventing their own
   verbs produce thirty documents that do not read as one.
2. **`Breaks if` becomes comparable across proofs.** A reader who has seen
   `interchange-limit-and-sum` once knows what to check the second time.

An off-vocabulary move is **flagged, not dropped**. Losing the row would lose the
explanation; the warning exists so the list gets extended deliberately, by editing
this file.

Qualify a move with a colon where it helps: `apply-named-inequality:jensen`.

## Algebra

| Move | Breaks if |
|---|---|
| `substitute-definition` | the definition has a side condition, or the substituted object is only defined on part of the range |
| `algebraic-rearrangement` | a step divides by something that can vanish, or takes an even root of something that can be negative |
| `expand-product` | the product is infinite, or the terms do not commute |
| `factor` | the factorisation is not valid over the ring in play |
| `collect-terms` | the series is only conditionally convergent, so regrouping changes the value |
| `cancel-common-factor` | the cancelled factor can be zero |
| `add-and-subtract` | nothing, but the added term must be well-defined everywhere the expression is |
| `multiply-by-one` | the "one" is a ratio whose denominator can vanish |
| `change-of-variable` | the map is not injective on the domain, or its Jacobian vanishes |

## Sums, integrals and indices

| Move | Breaks if |
|---|---|
| `reindex-sum` | the new index does not range over exactly the same terms |
| `split-sum` | either piece diverges, even though the whole converges |
| `swap-sum-order` | the double sum is not absolutely convergent |
| `linearity-of-expectation` | the sum is infinite, so the interchange needs a dominating bound |
| `linearity-of-integral` | either integral fails to exist separately |
| `interchange-limit-and-sum` | there is no dominating summable bound and no uniform convergence |
| `interchange-limit-and-integral` | dominated or monotone convergence does not apply |
| `differentiate-both-sides` | the function is not differentiable throughout, or differentiation passes an integral without justification |
| `integrate-both-sides` | the integrand is not integrable on the stated set |
| `apply-product-rule` | a factor is not differentiable where the identity is used. The reverse direction — recognising $f'g+fg'$ as $(fg)'$ — is where an integrating-factor argument lives, and it is exactly the line a deleted martingale term makes available |

## Approximation

Moves that replace an object with a different one. Each is a modelling decision
rather than a deduction, so the canonical clause is about what was discarded.

| Move | Breaks if |
|---|---|
| `drop-lower-order-term` | the discarded term is not smaller than what is kept on the regime in play — check the ordering of the rates that decide it, and check it against the paper's own parameter values |
| `mean-field-closure` | the fluctuation is unbounded: replacing a process by its conditional mean needs the drift to be affine in the state, the coefficients to be deterministic given what is conditioned on, and a bound on what the replacement costs |

## Inequalities

| Move | Breaks if |
|---|---|
| `apply-named-inequality` | the named result's hypotheses are not established — check convexity direction, non-negativity, integrability, independence |
| `apply-monotone-function` | the function is decreasing, which reverses the inequality |
| `bound-term-above` | the bound is not uniform over what the argument later quantifies |
| `bound-term-below` | as above, and the bound must be non-vacuous |
| `triangle-inequality-split` | the pieces are not each finite |
| `union-bound` | the events are not the ones the conclusion quantifies over |
| `take-limits` | the inequality is strict, and strictness is not preserved in the limit |

## Probability

| Move | Breaks if |
|---|---|
| `conditioning` | the conditioning event has probability zero |
| `tower-property` | the inner expectation is not integrable |
| `definition-unfolding` | the measure the expectation is over changes silently between the two sides |

## Structure

| Move | Breaks if |
|---|---|
| `apply-hypothesis` | the hypothesis is not in scope at this point of the proof |
| `apply-previous-result` | the cited result's hypotheses are not established here, or it depends on the claim being proved |
| `case-split` | the cases do not cover the domain, or they overlap and disagree |
| `induction-hypothesis` | the hypothesis is applied outside the range the base case and step together cover |

## Using this list

The `move` field carries the name. The `breaks_if` field carries the clause,
**specialised to this step**:

> `interchange-limit-and-sum` — canonical: *there is no dominating summable bound
> and no uniform convergence*
> specialised: *the sum over $i$ is infinite here and the paper exhibits no
> summable dominating sequence, so the interchange at (14) is unsupported*

The specialisation is what makes the row useful. The canonical clause is what
makes it comparable.

## Adding a move

Add it here with its canonical `Breaks if`, then use it. A move whose failure mode
cannot be stated in one clause is usually two moves.
