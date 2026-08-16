---
name: verifying-proofs
description: Use when checking the mathematics of a paper rather than its claims — verifying a theorem's proof, an algebraic derivation, a bound, or an appendix full of lemmas. Triggers on "check this proof", "verify the derivation", "is Lemma 3 correct", "does the algebra work", a paper directory containing theorem/proof environments, or a referee asking whether a mathematical argument holds.
---

# Verifying Proofs

## Overview

**A proof is refuted one step at a time, and reported one gap at a time.** The
useful output of this skill is rarely "the theorem is false" — it is *this step
needs a hypothesis nobody stated*, *this induction has no base case*, *this
lemma's appendix restatement drops a condition its proof uses*.

**Core principle: the tool may never report its own limitations as the paper's
mistakes.** Every rule below exists to keep that true. A checker that says
"counterexample at $x = -11/5$" about a step that plainly meant $x > 0$ has not
found an error; it has taught its reader to ignore the next twenty findings.

Two consequences, both measured on real papers:

- **A symbol whose domain the paper never stated can never produce a
  counterexample.** On arXiv:1509.01240, 54 of 61 symbols had no readable domain.
  Sampling those freely would have produced dozens of "errors" against correct
  mathematics.
- **The default run is a hygiene checker, not a correctness checker.** Measured
  against six papers with documented, localised proof errors, the no-CAS engines
  found **none of them**. What they do find — a dependency cycle, an induction
  with no base case, a restatement that drops a hypothesis, a division by
  something nobody proved non-zero — is worth having, and it is not the same
  thing as checking whether the mathematics is right. **To check correctness you
  must fill in check scripts**, and doing so refuted a step in Adam's convergence
  proof exactly. See *Measured results*.

## Run it

```sh
python3 ~/.claude/skills/verifying-proofs/assets/run-proofcheck.py main.tex \
    --out review-assets/
```

Run it by absolute path from the paper directory. Stdlib only — no install, no
venv, no dependencies. SymPy and Z3 are *optional external checkers*: probed at
runtime, never installed, and their absence degrades the run instead of breaking
it.

- `--engines sideconds,rational,symbolic` — default is `sideconds` alone, which
  needs nothing external and produced every finding in the measurements below.
  Every scripted engine named gets **its own script per step**
  (`checks/<step>.<engine>.py`), and engines that disagree compose to
  `UNVERIFIED` rather than to a finding
- `--claims thm:main,lem:2` — restrict to named claims
- `--symbols symbols.json` — `{"\\gamma": "unit-interval-half-open"}`; one minute
  of your time unblocks more checking than any amount of inference
- `--emit-stubs-only` — write every check script and run nothing, so you can read
  what would run first
- `--ledger-only` — write `proof-ledger.json` and stop
- Exit code `2` means degraded coverage — a checker was missing, a script was not
  translated, or the segmenter dropped proof text

Outputs into `--out`: `proof-ledger.json`, `proofcheck-report.md`,
`proofsteps.csv`, and `checks/*.py`.

## What gets checked, and by what

```
0. side conditions + structure   stdlib      always runs, needs nothing
1. randomized exact rationals    stdlib      can refute; never confirms
2. SymPy equivalence             optional    the only engine that may confirm
3. named-result templates        stdlib      Jensen's *direction*, Markov, AM-GM
4. finite-difference gradients   stdlib      derivative and update-rule claims
5. Z3 / SMT                      optional    opt-in escape hatch, not routine
```

Engine 3 is template matching over the ledger; its output is a side condition and
it joins the same severity path as engine 0. **It is deliberately narrow.** Most
named results need something no parser sees — that a norm is finite, that a
dominating summable bound exists — and those emit nothing rather than a row
saying so. `_shared/latexmath/named.py` lists every catalogued result that is not
checked, with the reason, so "checked and fine" is distinguishable from "not
looked at".

What it does check is worth having: for a convex $f$, $\mathbb{E}[f(X)]$ is the
larger side, and a step that names Jensen, declares its function convex, and puts
that on the smaller side has applied it backwards. That defect sat in the
seeded-error benchmark's *not reachable* list until this engine existed. Where
convexity is **not** declared the direction is unknowable from the source and
nothing is claimed.

Engines 1, 2, 4 and 5 work through **generated check scripts**, one per checkable
step **per engine**, written into `checks/<step>.<engine>.py`. The tool does not translate LaTeX into SymPy: `parse_latex`
needs `antlr4`, and its grammar has no `\mathbb{E}`, no `\operatorname{}`, no
norms and no user macros. A hand-rolled translator's bugs would surface as false
counterexamples, which is the one failure this skill cannot survive.

**So you translate.** Each stub arrives carrying the source LaTeX, the
macro-expanded LaTeX, every symbol's domain *and where that domain came from*, and
the side conditions the step needs. Fill in `build()`, rerun, and the verdict
cites the script — a file the author can open and argue with. See
`checks/_contract.md`, written alongside.

**An unfilled stub reports `untranslatable`**, which composes to `UNVERIFIED`. A
run that translated nothing reports nothing checked, never a clean paper.

## Severity

| Level | Meaning for a proof |
|---|---|
| `CRITICAL` | A reproduced counterexample under a **faithful** translation at a point inside the **stated** domain. Or a structural break: an induction with no base case, a claim dependency cycle. |
| `MAJOR` | Not refuted, but the **licence is missing** — a side condition nowhere assumed, an unjustified limit interchange, a restatement whose hypotheses differ from the body version. *The algebra can be right and the theorem still unproved.* |
| `MINOR` | Impedes checking: an undefined symbol at first use, a `\ref` to nothing, a hedge on a step nothing could verify. |
| `WEAK` | Not refuted by sampling alone, or refuted under a translation that was not faithful. **Not verified.** |
| `UNVERIFIED` | No engine could reach it: opaque operator, unreadable domain, engines disagreed, checker absent, timeout, script rejected. **A finding, not a pass.** |
| `SKIP` | Not an inference, or confirmed symbolically. |

**A dense cluster of `UNVERIFIED` inside one proof is the headline**, not a
footnote. The report's coverage table comes before its findings for that reason.

Three composition rules, each asserted in `assets/tests/test_compose.py`:

1. An unknown domain can never refute.
2. A translation that is not `faithful` caps severity at `WEAK`.
3. Engines that disagree yield `UNVERIFIED`, never `CRITICAL`.

## Where domains come from

`declared` (the paper says so, with the quote kept) ·
`inferred` (`\sum_{i=1}^n` makes $i$ an integer — honest, usable, never promoted
to declared) · `user-supplied` (`--symbols`) · `unknown` (the default).

Only the first three may license a refutation. When a check fails on a step
carrying an unknown domain, the report says the domain was never stated rather
than naming a counterexample — and lists the symbol so you can supply it.

**Domains are resolved where the step is, not where the symbol first appeared.**
The declarations inside the enclosing proof and its statement are read in source
order, and the last one before the step wins; a symbol the proof says nothing
about keeps whatever the document established. A monograph that declares
$\alpha \in [0,1]$ on page 12 for a convex combination and opens a proof on page
300 with *"for any $\alpha \in (0,1)$"* means the second one there, and reading
the first cost nine `MAJOR` against correct mathematics.

## The structural audit is yours, not the tool's

The tool finds what is mechanical. `reference/structural-audit.md` is the half
that is not, and it is where most real referee findings come from: whether the
hypothesis is *used*, whether quantifier order survives the proof, whether an
inequality points the way the argument needs, whether the induction actually
covers its claim. Work that checklist against every load-bearing proof.

## When a checker is absent

SymPy or Z3 missing is a question for the user, never a `pip install`. The run
continues: steps routed to that engine become `UNVERIFIED`, the report header
names the checker and its status, and the exit code is `2`.

**Say "nothing wrong was found in a degraded run", not "the proofs are correct".**
They are different sentences and only one of them is true.

## Limits

State these rather than implying completeness.

- **It can refute; it can almost never certify.** Only symbolic confirmation of an
  equality, or an SMT `unsat`, ever confirms anything. Everything else is failure
  to refute.
- **Measure-theoretic and asymptotic reasoning is out of reach.** `\mathbb{E}` over
  an unspecified measure and $O(\cdot)$ claims are `UNVERIFIED` by construction.
  On three real papers these were the two largest opacity categories.
- **A proof written as running prose rather than `\begin{proof}` is invisible.**
  The report says so instead of reporting a clean document — but measure the cost:
  **2 of 6 papers in the flawed corpus were invisible for exactly this reason**,
  one of them a withdrawn cs.LG paper that declares no theorem environment at all.
  Older and weaker papers are likelier to be written this way, and that is the
  population where errors concentrate.
- **A proof that invokes its own theorem is not reported as circular.** Nothing
  distinguishes "by Theorem 1, which we are proving" from "recall the hypotheses
  of Theorem 1", and the second is what proofs actually do. Genuine multi-claim
  cycles are still caught.
- **The sandbox is not a security boundary.** It is a guard against a generated
  script importing `os`, touching the paper directory, or looping forever.
- **No local ground truth exists for proofs.** The benchmark uses seeded errors,
  which are cleaner than real ones and overstate recall. The honest headline is
  the false-alarm rate on untouched correct derivations.

## Measured results

**Seeded-error benchmark** (`assets/tests/test_seeded_errors.py`, offline and
deterministic — run it yourself). Six realistic defects injected into correct
derivations, each paired with its untouched original:

| | |
|---|---|
| Seeded defects detected | **6 of 6** |
| **False alarms on the correct originals** | **0 of 6** |
| `CRITICAL` or `MAJOR` raised against correct mathematics | **0** |

Five further defect classes — a flipped inequality, a sign error, an off-by-one
summation bound, Jensen applied the wrong way, a swapped quantifier — are **not
reachable by the default engines** and are listed as such in the benchmark rather
than quietly omitted. The first three need a translated check script; the last
needs a reader working `reference/structural-audit.md`.

**Real papers, against known ground truth.** Thirteen arXiv papers: **six with a
documented, localised defect** (three author withdrawals naming the lemma, two
published corrections naming the bound) and **seven validated** — two of them
reference monographs, two the corrections themselves. Proof text segmented
**100%** on every one.

| | papers | CRITICAL | MAJOR | papers with any |
|---|---|---|---|---|
| **validated** | 7 | 0 | 5 | 2 of 7 |
| **documented defect** | 6 | 0 | **0** | **0 of 6** |

Re-measured 2026-08-15 by an acceptance benchmark that fetches all thirteen
e-prints and runs the shipped entry point. Every number in this section comes
from that run.

**Seven further papers, none in that corpus**, were run to find out whether the
false-alarm rate had settled. It has not, and the shape of the answer is more
useful than the answer:

| Fresh paper | steps | new false-alarm classes |
|---|---|---|
| quantum Shannon theory | 2692 | **0** |
| online-learning monograph | 1494 | **5** |
| matrix-concentration monograph | 540 | **3** |
| bandit survey | 470 | 0 |
| computational optimal transport | 178 | 0 |
| Rényi differential privacy | 122 | 0 |
| PAC-Bayes primer | 59 | 0 |
| wide-network analysis | 37 | 0 |

The two monographs that came before the fixes produced new classes; nothing under
500 steps ever has.
Eight of those classes (14–21 in `reference/false-alarms.md`) were found and
fixed. Six of the eight are *wrong domains* — a symbol given a range it does not
have, recorded as `declared`, which is a refuting provenance. That is the worst
failure available to this skill: the tool becomes entitled to evaluate a step
outside the paper's meaning and report a counterexample against correct
mathematics.

The reason long documents dominate is not subtle. They reuse their letters. `t`
is a round index in one chapter and a convex weight in another, `a` is bounded on
one page and free on the next, and every rule that reads a domain from *somewhere
in the document* rather than *here* breaks on exactly that.

**The stopping criterion, and where it stands.** "Further papers with no new
class" proved unreachable, so it is a rate: **a fresh document of at least 500
steps yielding fewer than one new false-alarm class per 1000 steps.** The
monographs measured 3.3 and 5.6 before their classes were fixed. The 2692-step
quantum-information book, run afterwards and four times the size of anything else
tested, measured **0.0 — the criterion is met.** Its four `MAJOR` are one
recurrence of an existing class and three legitimate findings, each a proof
dividing by or taking the logarithm of a quantity whose stated range includes
zero.

**One document is one document.** And the same run turned up a defect of a
different kind that no amount of false-alarm counting would have caught: **158
step ids collided** on it, because a claim proved twice produced two proofs with
the same id. Re-checking found 24 more on one corpus paper and 16 on another that
had been there from the beginning. Nothing failed — a duplicate id silently
wins — and a verdict computed on one proof had been reported against a step in
another. See class 22.

Two of the eight classes were caught by nothing but the acceptance benchmark:
a fix that passed the entire unit suite put a `MAJOR` back on Bubeck — the
corpus's most heavily vetted document — and a second one silently removed four
genuine findings. Both surfaced only on re-running the thirteen papers.

**With a translated check script it is a different tool.** Given the step ledger
and one filled-in `build()`, the SymPy engine **exactly refuted** Adam's
Lemma 10.4 step 10 — the step arXiv:1804.10587 exists to correct:

```
rhs - lhs = -29*sqrt(3)/48 + sqrt(2)/16 + 3/16   (~ -0.771)
```

at $T=4,\ \gamma=1/2,\ \beta_2=0$, all gradient norms 1 — every value inside the
domains the paper states. The violation is robust: false at 13 of 20 parameter
settings tried, growing with $T$ as the asymptotics demand.

**And `--symbols` is not optional.** That refutation was initially **suppressed**,
because Adam never states domains for $T$, $\gamma$ or $\beta_2$ and an unknown
domain may not refute. The guard that prevents false alarms had hidden a true one.
It now reports `refutation-blocked-by-unknown-domain` at `MAJOR`, naming the
symbols to supply — and with them supplied the same step returns `CRITICAL`.
**A blocked decisive check is the most actionable thing this skill produces.**

**False alarms.** Every rule in `reference/false-alarms.md` was earned on a real
paper. Twenty-two entries so far, including: 4 fabricated `CRITICAL`s from an
induction detector that hard-coded the variable name; 54 spurious opacity reasons
from `\operatorname{\mathbb{E}}`; `\sqrt{t}` under `\sum_{t=1}^{T}`, which fired
on every optimization paper; `\rho^{-1}` on a scalar step size reported as
needing matrix invertibility; sibling theorems in a family read as restatements;
`differentiate-under-integral` fired on Taylor's theorem with integral remainder;
`y_t \in [0,1]` read as a declaration about the subscript $t$; one `x \ge 0`
declaring seven symbols at once; `\varepsilon \leq 0.006` read as
`\varepsilon \leq 0`; and `\int_0^\infty f = \lim_L \int_0^L f` reported as an
unjustified interchange when it is the definition.

**Net effect on the validated set: 14 `MAJOR` → 5, and 0 fabricated `CRITICAL`s
throughout.** Bubeck's monograph — at 451 steps the largest and most heavily
vetted document in either corpus — went from 7 `MAJOR` to **zero**.

## See also

- `reference/structural-audit.md` — the non-mechanical checklist, and what each
  failure looks like in the source
- `reference/engines.md` — what each engine can and cannot license
- `reference/step-ledger.md` — the schema, field by field
- `reference/false-alarms.md` — every false alarm observed, and the rule that
  killed it
- `explaining-derivations` — consumes these verdicts to expand a proof step by
  step, and treats a step it cannot expand as evidence against the derivation
- `reviewing-paper-sources` — phase 0 offers this skill; phase 4 invokes it
- Shared parsing layer: `_shared/latexmath`
