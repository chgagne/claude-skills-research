# False alarms, and the rules that killed them

Every rule in this skill's suppression logic exists because the thing it
suppresses actually fired, on a real paper, against correct mathematics. This
file records each one with the measurement, so nobody removes a rule that looks
arbitrary.

**A checker that cries wolf is worse than no checker**, because it teaches its
reader to skim. The numbers below are the argument for every piece of apparent
over-caution in the code.

Corpus, in two rounds. **Round 1** — three public arXiv papers with substantial
appendices (arXiv:1509.01240, 1806.07572, 1810.02054): 80 claims, 46 proofs,
429 steps; entries 1–8 below. **Round 2** — an evaluation against known ground
truth, adding three papers with documented proof errors (arXiv:1412.6980v8 Adam,
1905.10936 dist-EF-SGD, 2505.02888v1 withdrawn) and two published corrections
(2003.04706, 1804.10587); entries 9–10.

---

## 1. Induction base case, hard-coded variable

**Fired:** 4 of 4 induction proofs in arXiv:1806.07572, each as a `CRITICAL`.

**Why:** the detector matched `for $n=0$` / `when $n=1$` literally. Those proofs
induct on network *depth* `$L$` and open with *"When $L=1$, there are no hidden
layers"*.

**Rule:** read the induction variable out of the induction phrase
(`induction on the depth $L$`), then look for a base value of *that* variable.
Fall back to any `When $X = 0|1|2$` opener that is not the induction hypothesis.
**When no variable can be identified the verdict is `unknown`, not an
accusation** — only `not-found` escalates, and only when there was a named
variable to look for.

**After:** 3 `found`, 1 `unknown`, **0 fabricated `CRITICAL`s**. The `unknown` is
`prop:pos-def`, which inducts without ever naming a variable — a genuine "check
this by hand".

---

## 2. Comma-separated definitions read as a transitive chain

**Fired:** on a draft whose display row read
`C_0 = \{c_{i0}\}_{i=1}^{B}, O_0 = \{o_{i0}\}_{i=1}^{B}`.

**Why:** the row was read as one relation chain, producing the left-hand side
`\{c_{i0}\}_{i=1}^{B}, O_0` — which is not an expression. A checker handed that
reports on a claim the paper never made.

**Rule:** `chains.split_clauses`. A top-level comma separates clauses only when
*both* sides carry a top-level relation, so `f(x, y) = z` and
`S = 1, 2, \ldots, n` stay whole. A multi-clause row also breaks the chain, so
nothing downstream carries a left-hand side that would be a guess.

**After:** 0 suspect left-hand sides across 60 displays.

---

## 3. Angle-bracket inner products read as relations

**Fired:** arXiv:1806.07572, which writes inner products as `<a, b>`.

**Why:** `<` and `>` are relations. The step
`\partial_t W = \frac{1}{\sqrt{n}}<\alpha, d>` was truncated to
`\partial_t W = \frac{1}{\sqrt{n}}` — a different claim, and one the authors
never wrote.

**Rule:** a `<` with a matching `>` at the same brace depth and a top-level comma
between them is a delimiter pair, not two relations. `x < 1` and `0 < x < 1` have
no such pairing and still split.

---

## 4. `\operatorname{\mathbb{E}}` read as an operator named `\mathbb{E`

**Fired:** 54 spurious `undefined-operator` opacity reasons on arXiv:1509.01240,
every one of them double-counting a step already marked
`expectation-over-unspecified-measure`.

**Why:** the paper writes `\DeclareMathOperator{\E}{\mathbb{E}}`, which the macro
table expands to `\operatorname{\mathbb{E}}`. Reading the argument with `[^}]*`
stopped at the inner brace.

**Rule:** brace-balanced argument extraction, plus an alias list so an operator
whose body is `\mathbb{E}` / `\mathbb{P}` / `\Var` is recognised as the standard
quantity it is.

**After:** 0.

---

## 5. A proof referencing its own theorem read as a dependency cycle

**Fired:** `claim/thm:conv-ntk-training -> claim/thm:conv-ntk-training`, a
`CRITICAL`, on arXiv:1806.07572.

**Why:** proofs routinely write "recall the hypotheses of Theorem 1". Nothing in
the reference distinguishes that from invoking the theorem under proof.

**Rule:** self-edges are dropped from the claim graph. Two-claim and longer cycles
are unaffected.

**Cost, stated in Limits:** a genuinely self-invoking proof is missed. Accepted,
because the alternative fires on ordinary writing.

---

## 6. Even roots and log arguments

**Fired:** 55 `even-root-nonnegative` on arXiv:1810.02054 — nearly all
`\sqrt{2\pi}`, `\sqrt{m}`, `\sqrt{\log(n/\delta)}`. Plus five
`log-argument-positive` whose recorded argument was the literal string `\left`.

**Rules:**
- Constants (`\pi`, `e`) and count names are stripped before deciding whether a
  radicand could be negative; what remains must be arithmetic.
- A radicand that is manifestly a square or a norm never fires.
- `\log\left(...\right)` groups are read as arguments — `_delimited_arg` handles
  `\left…\right`, parentheses and braces.

---

## 7. `\lim` matching the spacing directive `\limits`

**Fired:** 10 of 10 `limit-interchange` hits on arXiv:1810.02054 came from
`\lim\limits_{r \to 0+}`.

**Rules:** `\lim(?![a-zA-Z])`, so `\limits` is not a limit. And separately:
`\liminf\b` **never matched** `\liminf_{n}`, because `_` is a word character —
`(?![a-zA-Z])` is required there too. Same bug class as `\le` matching inside
`\leq`.

Also: the reported expression is quoted from after the `\limits_{...}` sub- and
superscripts. A finding whose quoted expression opens with `\limits_` reads as a
parser artifact, and that costs the reader's trust in the finding itself.

---

## 8. Side conditions: 100% of them reported as unmet

**Fired:** 84, 98 and 97 side conditions on the three papers — *every one*
reported as an obligation the paper failed to discharge. That is not a report; it
is a reason to stop reading.

**Why:** the same fact the whole severity ladder rests on. 54 of 61 symbols in one
paper had a domain the tool could not read. **If it could not read the domain, it
cannot claim the licence is missing either.**

**Rule:** three states, not two.

| Status | Meaning | Severity |
|---|---|---|
| `established` | a stated domain discharges it, and the quote is kept | none |
| `unstated` | the domain is known and does **not** discharge it | `MAJOR` |
| `undetermined` | no domain could be read | `UNVERIFIED` |

Plus: dividing by a bare count name (`n`, `m`, `N`, `T`, `B`, `K`) is suppressed
outright — every paper writes `\frac{1}{n}\sum_{i=1}^n` — and identical
obligations within a step, or within a proof, are reported once rather than once
per row.

**After:**

| paper | conditions | undetermined | unstated | reportable |
|---|---|---|---|---|
| 1509.01240 | 66 | 58 | 8 | **5** across 4 proofs |
| 1806.07572 | 98 | 97 | 1 | **1** across 1 proof |
| 1810.02054 | 94 | 84 | 10 | **3** across 1 proof |

---

## 9. `\sqrt{t}` and `1/t` where `t` is the index of the enclosing sum

**Fired:** on *every* optimization paper in the arXiv evaluation corpus —
arXiv:1412.6980v8, 1509.01240, 2003.04706 — as `MAJOR`.

**Why:** `\sum_{t=1}^{T} \|g_t\| / \sqrt{t(1-\beta_2)}` is the shape of nearly
every adaptive learning rate ever published. The rule that *inferred* domains
never discharge an obligation treated $t$ as unconstrained — but the paper did
state its range, by writing the sum.

**Rule:** an inference may discharge an obligation when it is a fact the paper
wrote down (`summation-index`) rather than a guess. Plus `_positive_form`, which
propagates through products, powers and roots that cannot cancel, so
`\frac{\cdot}{\sqrt{t}}` is discharged along with $t$ itself.

**The circularity that had to be excluded:** an inference drawn *from* `A^{-1}`
must never discharge the invertibility obligation that `A^{-1}` raises. Only
`summation-index` discharges; `negative-exponent` is explicitly excluded, and
there is a regression test for exactly that.

---

## 10. `\rho^{-1}` on a scalar reported as needing "invertibility"

**Fired:** arXiv:2003.04706 (`(\rho^{-1}/2)\lVert b\rVert^2`, a Young's-inequality
step) and arXiv:1509.01240 (`\nu^{-1} Q_\nu(w)`), both `MAJOR`.

**Why:** `X^{-1}` raised an `invertible` condition for any `X`. For a scalar step
size that is a category error: the obligation is $\rho \neq 0$, and "needs
$\rho$ to be invertible" reads as a tool that does not know what it is looking at.

**Compounding circularity:** inferring `invertible` from `A^{-1}` also set the
symbol's role to *matrix*, which then justified calling it a matrix inverse. The
guess about the obligation was answering the question the obligation asked.

**Rule:** a declared matrix domain wins; otherwise a single uppercase Latin letter
(or a bold symbol) is a matrix by convention in this literature and everything
else — Greek lowercase, lowercase Latin — is a scalar reciprocal raising a
non-vanishing condition. An inferred `negative-exponent` no longer sets the role.

**After 9 and 10 together:** MAJOR findings across the eight-paper evaluation
corpus fell from **17 to 6**, with three papers going to zero and arXiv:1509.01240
going from 6 to 1.

---

---

## 11. Sibling theorems in a family read as restatements

**Fired:** 4 `MAJOR`s on arXiv:1405.4980 (Bubeck, *Convex Optimization*, a
Foundations & Trends monograph) and contributed to 2 more elsewhere — 6 of the
14 `MAJOR`s the validated corpus produced.

**Why:** the pairs were *different theorems*. Gradient descent versus
**projected** gradient descent; Nesterov's method for convex versus for
**strongly** convex functions; stochastic mirror descent versus its smooth
variant. Any family of results reads as near-identical text with differing
hypotheses — which is precisely the shape of a genuine restatement drift.

**Rule:** a restatement must **reach the same conclusion**. A sibling theorem
states a different bound; a restatement does not. The conclusion match is the
*primary* signal rather than an extra gate, because a restatement that drops a
hypothesis necessarily has *lower* whole-statement similarity — the missing text
is the finding. An explicit marker (`restatable`, or a title saying "restatement
of") overrides both thresholds, because then the author has said so.

**After:** Bubeck 4 → 0. Genuine drift, including the seeded case and two real
ones on arXiv:1810.02054 and 1509.01240, is retained.

---

## 12. `differentiate-under-integral` on Taylor's theorem

**Fired:** 3 `MAJOR`s on arXiv:1405.4980, all on

```
\nabla f(x_k) = \int_0^1 \nabla^2 f(x^* + s(x_k - x^*))(x_k - x^*)\,ds
```

**Why:** that is Taylor's theorem with integral remainder. **Nothing is
interchanged** — the gradient is a term on the left and the integral is a term on
the right. The rule fired because a derivative token appeared *anywhere* before
an integral token in the same expression.

**Rule:** the derivative must be applied *to* the integral — only spacing,
delimiters and grouping may sit between them. `\frac{\partial}{\partial\theta}
\int`, `\nabla_\theta \int` and `\frac{d}{dt}\int` still fire; a gradient
standing beside an integral does not.

**After:** Bubeck 3 → 0. The monograph, at 451 steps the largest and most heavily
vetted document in either corpus, now reports **zero** `CRITICAL` and **zero**
`MAJOR`.

---

---

## 13. Hypothesis drift diffed against a statement that could not be split

**Fired:** on a real draft, a `MAJOR` reporting that an appendix restatement had
*added* four hypotheses. It had not. The **body** statement had no
`Let ... Then ...` shape, so `split_method` was `unsplit`, its hypothesis list
was empty, and every hypothesis of the restatement showed as newly added.

**Why it matters more than its count:** an empty hypothesis list from `unsplit`
means *not parsed*, not *none stated*. Diffing against it is precisely the error
this module refuses to make everywhere else — `_split_statement` returns
`unsplit` rather than guess, and then the diff went and guessed anyway.

**Rule:** report `hypotheses_diff` only when **both** statements were actually
split. The restatement is still linked, so the pair is visible; only the
unusable diff is withheld.

**After:** one fewer `MAJOR` on the draft and one fewer on the validated corpus
(6 rather than 7). Genuine drift — where both sides split and a hypothesis is
*removed* — is retained, including the real case on arXiv:1509.01240.

**The shape to remember:** a diff that is entirely additions, against an
original the tool could not parse, is a statement about the parser.

---

## What the corpus could *not* fix

The same evaluation showed the default engines scoring **zero** on all three
papers with documented proof errors. Those errors are false *statements*; this
engine set looks for missing *licences*. No amount of suppression tuning closes
that gap — it needs a translated check script, and `SKILL.md` now says so with
the measurement attached.

## Adding to this file

If you change extraction or matching behaviour, add the case with a **real**
example. Every table above is drawn from something that actually went wrong, and
a rule without a measurement behind it is one the next person will delete.
