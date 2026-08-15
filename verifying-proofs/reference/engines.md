# The engines: what each can and cannot license

Six engines, run in this order. Only two of them can ever *confirm* anything;
the rest can only refute or fail to refute, and the report's wording reflects
that everywhere.

| # | Engine | Needs | Can refute | Can confirm |
|---|---|---|---|---|
| 0 | `sideconds` | nothing | — (reports missing licences) | — |
| 1 | `rational` | nothing | yes | **never** |
| 2 | `symbolic` | SymPy | yes | equalities only |
| 3 | `named` | nothing | — (reports unmet hypotheses) | — |
| 4 | `gradient` | nothing | yes | **never** |
| 5 | `smt` | Z3 | yes | inequalities, on `unsat` |

## 0 — side conditions and structure

The default, and on real papers the one that produced every finding. It reads the
argument rather than the arithmetic: a division by something nobody proved
non-zero, an induction with no base case, a claim cycle, a restatement that drops
a hypothesis, a `\ref` to nothing.

It reports three states per obligation — `established`, `unstated`,
`undetermined` — and only `unstated` is a `MAJOR`. See `false-alarms.md` §8 for
why that distinction had to exist.

## 1 — randomized exact rationals

Substitutes `Fraction` values for free symbols and evaluates both sides.

- **0 and ±1 are never sampled.** They satisfy far too many false identities:
  $x^a = x^b$ holds at 1 for every $a$ and $b$.
- **Samples respect each symbol's declared domain.** A symbol declared in $[0,1)$
  is never sampled outside it.
- **Degenerate points are rejected and counted.** At half or more rejected, the
  verdict is `UNVERIFIED` — the domain was too constrained for the run to mean
  anything.
- **Both sides zero everywhere is not evidence** and yields `UNVERIFIED`.
- **The smallest refuting point is reported**, because a counterexample a reader
  can check by hand in thirty seconds is worth ten they cannot.
- **Inequalities get domain endpoints added deliberately**; they fail at
  boundaries and hold across a random interior.
- Seeded by the step id, so two runs are byte-identical.

The report never prints "verified" for this engine. It prints
`NOT REFUTED — 24 sample points inside the stated domain`.

**Non-polynomial functions.** Default to opaque-atom substitution: `\exp(u)` with
structurally identical `u` on both sides becomes one fresh rational variable. This
makes `log(exp x) = x` uncheckable and makes the overwhelming majority of ML
algebra — which shuffles exp/log/softmax terms around — exactly checkable. Say so
in `TRANSLATION_NOTES` and keep `TRANSLATION_CONFIDENCE` at `approximate` when it
matters.

## 2 — SymPy equivalence

The only engine that may confirm an equality, and **it will confirm far less than
you expect**. `simplify` on expressions containing opaque function symbols returns
something non-zero much more readily than it proves zero, so most of its verdicts
are `UNVERIFIED (simplify could not decide)`. That is the honest answer.

Two guards run before a refutation becomes a finding:

- **Round-trip display.** `sympy.latex()` of what was actually parsed is printed
  beside the source, so a dropped subscript is visible rather than argued about.
- **Symbol coverage.** Every symbol the ledger says the step uses must appear in
  the expression or in `IGNORED_SYMBOLS`, or the verdict is downgraded to
  `UNVERIFIED (translation incomplete)`.

## 3 — named-result templates

Reports when a named inequality is invoked whose hypotheses the paper has not
established. Catalogue is small on purpose: an entry nobody checks the hypotheses
of is decoration. See `structural-audit.md` §5 for the table.

## 4 — gradient, by finite differences

Central differences at high `decimal` precision plus a **Richardson
order-of-accuracy check**: if the observed error does not shrink like $h^2$, the
disagreement is numerical rather than mathematical, and the verdict is
`UNVERIFIED (numerically inconclusive)` rather than a refutation.

No JAX. It adds a large install and a tracing-failure mode that produces
`UNVERIFIED` rather than answers, with no capability finite differences lack for
the scalar and small-vector expressions that appear in papers.

## 5 — Z3, opt-in

An escape hatch the agent routes a specific step to, not a rung in the ladder. Z3
is not installed by default, and putting it in the routine path would make the
first run demand an install. It is also a poor match for the corpus: ML-paper
quantified claims are asymptotic ($\forall \epsilon > 0 \; \exists N$), which Z3
cannot decide either.

Use it for a concrete inequality over reals or integers with explicit bounds.
Assert the negation; `unsat` confirms.

## Composition

```
any engine may refute
only symbolic (simplify -> 0) may confirm an equality
only smt (unsat on the negation) may confirm an inequality
refuted + confirmed          -> UNVERIFIED (engines disagree), never CRITICAL
translation not faithful     -> severity capped at WEAK
unknown domain on any symbol -> refutation suppressed entirely
timeout / missing checker /
  rejected script            -> UNVERIFIED, never a refutation
```

The last three lines are the ones that matter. They are asserted directly in
`assets/tests/test_compose.py`, and they are what stops the tool reporting its own
limitations as the paper's mistakes.
