# The structural audit

No code here. This is the half of proof checking a machine cannot do, and it is
where most real referee findings come from. Work it against every load-bearing
proof — the ones the paper's contribution actually rests on, not all of them.

The tool has already given you a step ledger. Use it: each item below names what
to grep or which ledger field to read, so the audit is evidence-gathering rather
than re-reading.

## 1. Is the hypothesis used?

A theorem whose proof never touches one of its hypotheses is either stating more
than it needs (harmless, but tells you the result is stronger than claimed) or
proving less than it states (fatal).

- Take `claims[].hypotheses` and, for each, grep the proof body for the symbols it
  constrains.
- A hypothesis whose symbols never appear in the proof is the finding. Ask the
  authors which it is; do not guess.
- **The reverse is the sharper check**: a symbol the proof leans on that appears
  in no hypothesis. Cross-reference `steps[].symbols_used` against the claim's
  hypotheses and the assumptions in scope.

## 2. Does the induction cover its claim?

The tool checks whether a base case exists. It cannot check whether it is the
*right* base case, and that is the usual defect.

- Does the base case establish the claim, or a weaker statement?
- Does the inductive step assume the claim at $n$ and prove it at $n+1$, or does
  it quietly assume it for *all* $k \le n$ while the base case only covers one
  value? (Strong induction with a weak base is common and usually fine — but say
  so.)
- Does the induction variable range over what the theorem quantifies over? An
  induction on depth proves nothing about width.
- Read `proofs[].structure.base_case`. A verdict of `unknown` means the variable
  was never named — go look.

## 3. Quantifier order

The single most common silent error in an analysis proof.

- $\forall \epsilon \exists N$ and $\exists N \forall \epsilon$ are different
  theorems. Check that the $N$ produced in the proof does not depend on anything
  the statement quantifies *after* it.
- In a bound of the form "there exists $C$ such that for all $n$…", confirm $C$ is
  constructed before $n$ is fixed, and does not mention $n$.
- `steps[].quantifiers_in_scope` records the binders the ledger saw. It records
  what is there, not whether the order is right.

## 4. Inequality direction

- Every inequality chain has a direction the argument needs. Track it: the ledger
  composes relations across an `align` chain and refuses to compose `\le` with
  `\ge`, which is exactly the place a direction flips unnoticed.
- Applying a *decreasing* function reverses an inequality. Grep for `\log`, `-`,
  `1/x`, `\exp(-\cdot)` inside a chain and check the direction on both sides.
- A named inequality has a direction: Jensen for a convex function points the
  opposite way from Jensen for a concave one. Check which one the paper needs.

## 5. Named results and their hypotheses

`steps[].justification.name` tells you which result was invoked. The hypotheses
are yours to check.

| Invoked | What must hold, and is usually unstated |
|---|---|
| Jensen | convexity *in the right direction*; integrability |
| Cauchy–Schwarz | both factors square-integrable |
| Markov / Chebyshev | non-negativity; finite moment |
| Dominated convergence | a dominating function that is *integrable*, exhibited |
| Fubini / Tonelli | σ-finiteness, or non-negativity for Tonelli |
| Fatou | non-negativity |
| Borel–Cantelli (2nd) | independence |
| Taylor with remainder | the stated smoothness on the *whole* interval |
| Contraction mapping | completeness of the space, and modulus strictly below 1 |

A result invoked whose hypotheses are not established is `MAJOR`: the algebra can
be right and the theorem still unproved.

## 6. Limits, sums and integrals interchanged

The tool flags the interchange. It cannot supply the justification.

- Which theorem licenses it — dominated convergence, monotone convergence,
  uniform convergence, Tonelli?
- Is the dominating function exhibited, or merely asserted to exist?
- A *finite* sum interchanges unconditionally; an infinite one does not. Check the
  bound.

## 7. Edge cases the statement admits

- Empty sums, empty sets, $n = 0$, $n = 1$.
- A denominator that vanishes at a boundary of the stated domain.
- A supremum that may not be attained, treated as a maximum.
- Equality cases in a strict inequality.

## 8. The proof of the wrong statement

Read the theorem, then read the last line of its proof. They should be the same
claim. Common drift:

- The theorem is stated for all $x$; the proof fixes a particular $x$ and never
  generalises.
- The theorem claims a bound; the proof establishes it in expectation.
- The theorem claims convergence; the proof establishes that a subsequence
  converges.
- The appendix restatement is what was actually proved, and it differs from the
  body version. The ledger reports this as `restatement-hypothesis-drift` — but
  only when the hypotheses differ textually. Read both statements yourself.

## 9. What the paper does not prove at all

- A claim in the abstract or introduction with no corresponding theorem.
- A theorem stated without proof and without a citation.
- A "proof sketch" doing load-bearing work.
- An assumption introduced mid-proof that is not in the theorem statement. Grep
  the proof body for `assume`, `suppose`, `note that we may` — anything after the
  first line is a hypothesis the theorem does not carry.

## Reporting

Findings from this audit go into the review with the same severities the tool
uses. Say which are mechanical and which are yours: a reader who cannot tell the
difference will trust the wrong ones.
