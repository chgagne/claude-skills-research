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

## 14. A subscript read as the symbol a declaration is about

**Fired:** on a 250-page online-learning monograph (arXiv:1912.13213). The
sentence *"An adversary chooses a real number $y_t \in [0,1]$"* declares $y$. The
search for a declaration of $t$ was `t\s*\\in\s*\[0,1\]` with no left boundary,
so it matched **inside `y_t`**, and $t$ — a round index occurring **9147 times** —
was recorded as `unit-interval`, provenance `declared`.

**Why this one is the worst in the file:** every other entry here is a spurious
finding. This is a spurious *domain*, and `declared` is a refuting provenance. The
tool was entitled to evaluate a step at $t = 1/2$ for an integer index and report
a counterexample against correct mathematics — the single failure this skill
cannot survive. It did not, only because no check script on that paper was filled
in.

On a paper where nearly every quantity is subscripted by the round index, this is
not a rare shape. It is the majority of declarations in the document.

**Rule:** a declaration attaches to a symbol only where the symbol starts a token,
and it may carry the symbol's own sub- and superscripts. `y_t \in [0,1]` now
declares $y$; it previously declared $t$, and after a first attempt at the guard
it briefly declared nothing at all.

**The trap inside the fix:** the guard is a lookbehind, and the search ran against
a *slice* beginning at the symbol's first use. With $t$ first used inside
`\alpha_t`, the slice begins at that very `t` and the lookbehind has nothing to
look behind at. Searching the full text with a bounded window is what makes the
guard work; a lookbehind on a slice is a guard that silently does not fire.

**After:** $t$ reads `natural`, provenance `inferred`, from the summation that
introduces it. On the monograph, `UNVERIFIED` fell from 342 to 298.

---

## 15. `\mathbb{N}` meaning two different things in three modules

**Fired:** on the same monograph. Every $1/t$ and $\ln t$ appearing *outside* a
summation reported `nonzero-denominator: nothing establishes $t$`, about a round
index bounded below by 1 in the summation that introduced it. Class 9 suppresses
this when the index is the enclosing sum's; here the uses are outside any sum.

**Why it happened:** the three parts of the codebase disagreed about $\mathbb{N}$.
`engines/smt.py` asserts `var >= 1` for a `natural`, `engines/rational.py` samples
one from $2, 3, 5, \dots$, and `sideconds.py` alone treated it as possibly zero.
Nothing tested the agreement, so the disagreement was invisible.

**Rule:** `natural` means $\ge 1$ everywhere. The cost of being wrong about this
is a *missed* obligation rather than a false alarm, which is the right direction
for a tool whose measured problem is firing only on sound papers.

---

## 16. A domain declared at first use rather than where the step is

**Fired:** on the same monograph, nine `MAJOR` at once. $\alpha \in [0,1]$ is
declared early, for a convex combination; three hundred pages later a proof opens
*"for any $\alpha \in (0,1)$"* and divides by $\alpha$. Domains were global and
first-use-wins, so the open interval in scope never reached the step.

**Rule:** a domain is resolved **at the step's position**, from the declarations
in the enclosing proof and its claim statement, and the **last one before the
step** wins. A symbol the passage says nothing about keeps whatever the document
established. This is a design change rather than a suppression rule, which is why
it waited: guessing here would have been worse than the false alarm.

Scoping to the whole proof and taking the *first* match was tried first and was
not enough — a proof that uses $t$ as a round index for thirty steps and then
writes $t \in [0,1]$ at step thirty-one had the interval applied to all thirty. A
declaration governs what follows it.

**Three things had to be fixed before this had any effect at all**, and each was
invisible on its own:

- **Step offsets were proof-local, not document-global.** The coverage
  measurement rebased every step *in place* before anything else read it, so
  `source.offset` was relative to the enclosing proof. Nothing downstream could
  locate a step in the source — on a multi-file paper `_locate` attributed steps
  to whichever file happened to contain that offset — and resolving a domain *at
  a position* was impossible.
- **`open-unit-interval` was not in the non-zero set.** $(0,1)$ excludes zero by
  construction. The correctly-scoped domain landed in a set that did not
  discharge the obligation, so the whole change measured as a no-op.
- **Class 17, below**, which the scoping then exposed.

---

## 17. One `\ge 0` declaring every symbol in the passage

**Fired:** on the monograph, once class 16 made local declarations visible. Two
of the declared-domain patterns carry a top-level `|`. They are composed onto a
symbol prefix, and unwrapped, `t` + `\geq?\s*0|\ge\s*0` parses as *(t followed by
`>= 0`)* **or** *(any `\ge 0` anywhere)*. A single `x \ge 0` in a proof therefore
declared **seven symbols at once** — two indices and a probability among them —
as `nonnegative`, provenance `declared`.

**Rule:** wrap each declared-domain pattern when composing. The shape to remember
is that a regex fragment written to be *concatenated* must be parenthesised, and
that this one was latent for the whole life of the module because the global
first-use window rarely contained an unrelated `\ge 0`.

---

## 18. `\varepsilon \leq 0.006` read as `\varepsilon \leq 0`

**Fired:** on Bubeck's monograph — the largest and most heavily vetted document
in the corpus, and one this skill had already driven from 7 `MAJOR` to zero. The
bound pattern stopped at the first `0` and read a numeric tolerance as a sign
constraint, declaring a positive $\varepsilon$ **non-positive**, which put a
`MAJOR` back on a square root.

**Rule:** the zero in a sign constraint must be the whole number
(`(?![.,]?\d)`). `< 0.5` reading as "negative" is the same shape and the same
severity of wrong.

**How it was caught:** the acceptance benchmark, on its first run after the
scoping change. Bubeck going 0 → 1 is exactly the regression the ceiling in that
file exists to catch, and nothing else in the suite noticed.

---

## 19. `a, b \geq 0` declaring only `b`

**Fired:** on Tropp's *Matrix Concentration* monograph (arXiv:1501.01571), on the
step `\sqrt{a+b} \le \sqrt{a} + \sqrt{b}`, whose own line reads `a, b \geq 0`. The
declaration pattern matched only the symbol adjacent to the relation, so `a` had
no domain at all, fell through to an unrelated earlier declaration, and the
step's stated side condition reported as unmet.

**Why it is worse than an ordinary miss:** the tool contradicted the sentence it
was reading, in the same line. A reader who sees that stops trusting the report,
and is right to.

**Rule:** a declaration may carry a comma-separated companion list before the
relation, bounded at four. Longer runs before a relation are more often
expressions than declarations.

---

## 20. The definition of an improper integral read as a limit interchange

**Fired:** on the same monograph, on
`\int_0^\infty f = \lim_{L \to \infty} \int_0^L f`. Nothing is interchanged —
that *is* the definition, and `\lim_{N} \sum_{i=1}^{N}` is the same shape for a
series.

**Rule:** suppress only when a bound of the operator **is** the limit variable,
alone. Two weaker rules were tried and each dropped real findings:

| Attempted rule | What it dropped |
|---|---|
| the variable must appear in the integrand | `\lim_{r\to 0} \frac{1}{\mu(B)}\int_B f` — the radius enters through the set |
| the variable must not appear in the bounds | the same argument written `\int_{B_r^+}` — a shrinking domain, not a runaway endpoint |

Both would have silently removed the four interchanges on arXiv:1810.02054, the
only ones in the validated corpus. `\int_0^L` is a definition; `\int_{B_r}` is an
argument. **The second attempt passed the whole unit suite and was caught only by
re-running the corpus** — the acceptance benchmark's second save.

---

## 21. The base of a negative exponent read as its subscript

**Fired:** on Tropp, on `\bm{H}_u^{-1/2}`. The base pattern stopped at the letter
adjacent to the caret, so a matrix inversion reported *"needs $u$ to be
non-zero"* about an index. Same family as class 14, one layer down.

**Rule:** the base carries its own subscript **and** its wrapper —
`\bm{H}_u`, `\mathbf{A}`. Fixing only the subscript was not enough: with
`\bm{H}_u^{-1/2}` the bare-letter match simply moved to `u` again, and the
finding was unchanged. The domain is looked up on the letter inside the wrapper.

---

## 22. Two proofs of one claim sharing every step id — *not* a false alarm

This entry is a different kind from every other in this file. It is not a
spurious finding; it is a silent data-integrity defect, recorded here because it
was found the same way and because the file is where extraction behaviour is
written down.

**Found:** on Wilde's *Quantum Shannon Theory* (arXiv:1106.1445, 2692 steps),
while triaging a finding that appeared twice. **158 step ids collided.**
Re-checking the rest of the corpus found **24 on Tropp** and **16 on Bubeck** —
the latter present from the first day the acceptance benchmark ran.

**Cause:** a proof was named after its claim. A claim proved twice — a second
argument, a converse, an appendix proof alongside a sketch — produced two proofs
with the same id, and therefore steps with the same ids.

**Why nothing noticed:** a duplicate id does not fail. It silently wins.
Everything downstream keys on the step id — the verdict map, the generated
check-script filenames, and the fragment binding in `explaining-derivations` — and
a dict keyed by id keeps one of the two. **A verdict computed on one proof was
reported against a step in another**, and a generated check script overwrote its
neighbour.

**Rule:** the second and later proofs of a claim take `proof/<label>#2`,
`#3`, … The first keeps the plain id, so every id already written down still
resolves.

**The shape to remember:** an identifier built from a name that is not unique is
a bug that reports nothing. Count your ids.

---

## Known recurrence: sibling theorems, again

Wilde also produced one restatement-drift `MAJOR` on a pair that is not a
restatement — the two-variable mutual-information theorem and its three-variable
conditional sibling. That is class 11, whose rule (a restatement reaches the
*same* conclusion) is right but whose similarity threshold does not separate this
pair.

Left alone deliberately: tuning that threshold risks the genuine drift it catches
on arXiv:1509.01240, which is one of only two real ones in the corpus. Recorded
so the next person knows the rule is under-selective rather than absent.

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
