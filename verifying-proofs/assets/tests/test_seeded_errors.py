"""Seeded-error benchmark. Offline, deterministic, and shippable.

Unlike the sibling skills' acceptance suites this one measures against *synthetic*
fixtures rather than unpublished drafts, so it lives in the repo where a
contributor can run it:

    cd verifying-proofs/assets && python3 -m unittest tests.test_seeded_errors -v

Each case is a small correct derivation and a copy with one realistic defect
injected. The defective copy is a **must-fire** case; the untouched original is a
**must-stay-silent** case.

**The headline metric is the false-alarm rate on the untouched originals, not
recall.** Seeded errors are cleaner than real ones and will overstate recall no
matter how carefully they are written; a false alarm on correct mathematics is the
thing that makes a reader stop reading, and it is measurable honestly here.

Errors the *default* engine set cannot reach are listed in `NEEDS_TRANSLATION`
with the engine that would be needed. Counting them as misses is right; hiding
them would make the coverage claim dishonest.
"""
import unittest, sys, pathlib, tempfile, os
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))

from proofcheck import compose, ledger_io  # noqa: E402
from latexmath import named as _named  # noqa: E402

PREAMBLE = "\n".join([
    r"\documentclass{article}",
    r"\newtheorem{thm}{Theorem}",
    r"\newtheorem{lem}[thm]{Lemma}",
    r"\begin{document}",
])
CLOSING = r"\end{document}"


def paper(body):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "main.tex")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(PREAMBLE + "\n" + body + "\n" + CLOSING)
    return p


def findings(body, named=False):
    """Structural findings, optionally with the `named` engine's side conditions.

    `named` is template matching over the ledger rather than a generated script,
    so it is applied here the way `__main__` applies it: its output joins the
    step's `side_conditions` and travels the same severity path as `sideconds`.
    """
    led = ledger_io.build(paper(body))
    if named:
        symbols = {s["symbol"]: s for s in led["symbols"]}
        for step in led["steps"]:
            got = _named.conditions(step, symbols)
            if got:
                step.setdefault("side_conditions", []).extend(got)
    return compose.structural_findings(led)


def kinds(body):
    return [f["kind"] for f in findings(body)]


# --------------------------------------------------------------------------
# Cases the default engine set must catch. Each pairs a correct derivation with
# one seeded defect.
# --------------------------------------------------------------------------

MISSING_BASE_CASE_OK = r"""
\begin{thm}\label{t:ind} For every $n$, $P(n)$ holds. \end{thm}
\begin{proof}
We argue by induction on $n$. When $n = 1$ the claim is immediate.
Assume $P(n)$ holds; then $P(n+1)$ follows by the same estimate.
\end{proof}
"""

MISSING_BASE_CASE_BAD = r"""
\begin{thm}\label{t:ind} For every $n$, $P(n)$ holds. \end{thm}
\begin{proof}
We argue by induction on $n$.
Assume $P(n)$ holds; then $P(n+1)$ follows by the same estimate.
\end{proof}
"""

VANISHING_DENOMINATOR_OK = r"""
\begin{thm}\label{t:div} Let $c \in \mathbb{R}$ and let $b > 0$. Then $a/b$ is defined.
\end{thm}
\begin{proof}
Since $b > 0$, we may write $\frac{a}{b}$ and the claim follows.
\end{proof}
"""

VANISHING_DENOMINATOR_BAD = r"""
\begin{thm}\label{t:div} Let $c \in \mathbb{R}$ and let $b \in \mathbb{R}$.
Then $a/b$ is defined. \end{thm}
\begin{proof}
We may write $\frac{a}{b}$ and the claim follows.
\end{proof}
"""

LIMIT_INTERCHANGE_OK = r"""
\begin{thm}\label{t:lim} The limit equals the finite sum. \end{thm}
\begin{proof}
Taking limits, $\lim_{t} \sum_{i=1}^n a_i^{(t)}$ is a finite sum, so the
interchange is unconditional and the claim follows.
\end{proof}
"""

LIMIT_INTERCHANGE_BAD = r"""
\begin{thm}\label{t:lim} The limit equals the series. \end{thm}
\begin{proof}
Taking limits, $\lim_{t} \int f_t \, dx$ equals the integral of the limit, and
the claim follows.
\end{proof}
"""

HYPOTHESIS_DRIFT_OK = r"""
\begin{thm}\label{t:body} Let $f$ be convex and let $f$ be bounded.
Then $f$ attains its minimum. \end{thm}
\begin{proof} Immediate from compactness. \end{proof}
\begin{thm}\label{t:app} Let $f$ be convex and let $f$ be bounded.
Then $f$ attains its minimum. \end{thm}
\begin{proof} As above. \end{proof}
"""

HYPOTHESIS_DRIFT_BAD = r"""
\begin{thm}\label{t:body} Let $f$ be convex and let $f$ be bounded.
Then $f$ attains its minimum. \end{thm}
\begin{proof} Immediate from compactness. \end{proof}
\begin{thm}\label{t:app} Let $f$ be convex.
Then $f$ attains its minimum. \end{thm}
\begin{proof} As above. \end{proof}
"""

CIRCULAR_OK = r"""
\begin{lem}\label{l:one} A holds. \end{lem}
\begin{proof} Direct computation. \end{proof}
\begin{thm}\label{t:two} B holds. \end{thm}
\begin{proof} By \ref{l:one}, the claim follows. \end{proof}
"""

CIRCULAR_BAD = r"""
\begin{lem}\label{l:one} A holds. \end{lem}
\begin{proof} By \ref{t:two}, the claim follows. \end{proof}
\begin{thm}\label{t:two} B holds. \end{thm}
\begin{proof} By \ref{l:one}, the claim follows. \end{proof}
"""

DANGLING_REF_OK = r"""
\begin{thm}\label{t:r} C holds. \end{thm}
\begin{equation}\label{eq:one} x = 1 \end{equation}
\begin{proof} By \eqref{eq:one}, the claim follows. \end{proof}
"""

DANGLING_REF_BAD = r"""
\begin{thm}\label{t:r} C holds. \end{thm}
\begin{equation}\label{eq:one} x = 1 \end{equation}
\begin{proof} By \eqref{eq:missing}, the claim follows. \end{proof}
"""

#: (name, correct, defective, expected finding kind)
MUST_FIRE = [
    ("induction with no base case", MISSING_BASE_CASE_OK, MISSING_BASE_CASE_BAD,
     "induction-no-base-case"),
    ("division by a quantity that can vanish", VANISHING_DENOMINATOR_OK,
     VANISHING_DENOMINATOR_BAD, "side-condition-unstated"),
    ("limit interchanged with an integral", LIMIT_INTERCHANGE_OK,
     LIMIT_INTERCHANGE_BAD, "side-condition-unstated"),
    ("restatement drops a hypothesis", HYPOTHESIS_DRIFT_OK, HYPOTHESIS_DRIFT_BAD,
     "restatement-hypothesis-drift"),
    ("circular dependency between claims", CIRCULAR_OK, CIRCULAR_BAD,
     "claim-cycle"),
    ("reference to a label that does not exist", DANGLING_REF_OK,
     DANGLING_REF_BAD, "dangling-ref"),
]

JENSEN_OK = r"""
\begin{thm}\label{t:jok} Let $f$ be a convex function. Then the bound holds. \end{thm}
\begin{proof}
By Jensen's inequality,
\begin{align}
\mathbb{E}[f(X)] &\geq f(\mathbb{E}[X]).
\end{align}
\end{proof}
"""

#: The same step with the inequality applied the wrong way round. Reachable only
#: by the `named` engine, which reads the result the step invokes by name and
#: checks the one hypothesis that is mechanically visible: for convex $f$,
#: $\mathbb{E}[f(X)]$ is the larger side.
JENSEN_BAD = JENSEN_OK.replace(
    r"\mathbb{E}[f(X)] &\geq f(\mathbb{E}[X])",
    r"f(\mathbb{E}[X]) &\geq \mathbb{E}[f(X)]")


class TestNamedEngine(unittest.TestCase):
    """The one defect class that needed an engine that did not exist.

    It was listed in `NEEDS_TRANSLATION` as unreachable until `named` was built.
    Direction is the whole content of Jensen's inequality, and it is checkable
    precisely when the paper declared its function convex -- which is also the
    only case in which claiming the step is wrong would be fair.
    """

    def test_jensen_the_wrong_way_round_is_found(self):
        kinds_bad = [f["kind"] for f in findings(JENSEN_BAD, named=True)]
        self.assertIn("side-condition-unstated", kinds_bad)

    def test_jensen_the_right_way_round_is_silent(self):
        got = [f for f in findings(JENSEN_OK, named=True)
               if f["kind"] == "side-condition-unstated"]
        self.assertEqual(got, [], "false alarm on a correct application")

    def test_without_the_engine_neither_fires(self):
        """It is genuinely out of reach of the default set, which is why it sat
        in NEEDS_TRANSLATION."""
        for body in (JENSEN_OK, JENSEN_BAD):
            self.assertEqual(
                [f for f in findings(body) if f["kind"] == "side-condition-unstated"],
                [])

    def test_an_undeclared_function_makes_no_claim_either_way(self):
        """Without a declared convexity the direction is unknowable from the
        source, and saying so is the honest answer."""
        plain = JENSEN_BAD.replace("Let $f$ be a convex function.", "Let $f$ be given.")
        got = [f for f in findings(plain, named=True)
               if f["kind"] == "side-condition-unstated"]
        self.assertEqual(got, [])


#: Defects the default engines cannot reach, and what would be needed. Counted as
#: misses. Hiding them would make the coverage claim dishonest.
NEEDS_TRANSLATION = {
    "flipped inequality direction": "rational or smt, with a translated script",
    "sign error in a rearrangement": "rational, with a translated script",
    "off-by-one in a summation bound": "rational, with a translated script",
    "quantifier order swapped between statement and use": "structural audit by a "
                                                          "reader; see "
                                                          "reference/structural-audit.md",
}


class TestMustFire(unittest.TestCase):
    def test_each_seeded_defect_is_found(self):
        missed = []
        for name, _, bad, kind in MUST_FIRE:
            if kind not in kinds(bad):
                missed.append(name)
        self.assertEqual(missed, [], "seeded defects not detected: %s" % missed)


class TestMustStaySilent(unittest.TestCase):
    """The headline. A false alarm on correct mathematics is what kills a tool."""

    def test_no_correct_derivation_triggers_its_defect(self):
        alarms = []
        for name, ok, _, kind in MUST_FIRE:
            got = [f for f in findings(ok) if f["kind"] == kind]
            if got:
                alarms.append("%s: %s" % (name, got[0]["detail"][:90]))
        self.assertEqual(alarms, [], "false alarms on correct derivations: %s"
                                     % alarms)

    def test_no_correct_derivation_produces_any_critical(self):
        alarms = []
        for name, ok, _, _ in MUST_FIRE:
            crit = [f for f in findings(ok) if f["severity"] == "CRITICAL"]
            if crit:
                alarms.append("%s: %s" % (name, crit[0]["kind"]))
        self.assertEqual(alarms, [],
                         "CRITICAL on correct mathematics: %s" % alarms)

    def test_no_correct_derivation_produces_a_major(self):
        """MAJOR is a missing licence. On these fixtures none is missing."""
        alarms = []
        for name, ok, _, _ in MUST_FIRE:
            major = [f for f in findings(ok) if f["severity"] == "MAJOR"]
            if major:
                alarms.append("%s: %s -- %s"
                              % (name, major[0]["kind"], major[0]["detail"][:80]))
        self.assertEqual(alarms, [], "MAJOR on correct mathematics: %s" % alarms)


class TestDegradation(unittest.TestCase):
    def test_a_paper_with_no_proofs_reports_nothing_rather_than_passing_it(self):
        led = ledger_io.build(paper(r"\section{Results} We observe that $x = 1$."))
        self.assertEqual(led["coverage"]["proofs"], 0)
        self.assertEqual(compose.structural_findings(led), [])

    def test_an_unknown_induction_variable_never_escalates(self):
        body = r"""
\begin{thm}\label{t:u} D holds. \end{thm}
\begin{proof} The result follows by structural induction; the step is routine.
\end{proof}"""
        got = [f for f in findings(body)]
        self.assertNotIn("induction-no-base-case", [f["kind"] for f in got])
        self.assertIn("induction-base-case-unclear", [f["kind"] for f in got])


class TestSummary(unittest.TestCase):
    """Prints the measurement table rather than asserting on it."""

    def test_summary(self):
        tp = fp = 0
        rows = []
        for name, ok, bad, kind in MUST_FIRE:
            fired = kind in kinds(bad)
            alarmed = bool([f for f in findings(ok) if f["kind"] == kind])
            tp += 1 if fired else 0
            fp += 1 if alarmed else 0
            rows.append("  %-42s fired=%-5s false alarm=%s"
                        % (name[:42], fired, alarmed))
        n = len(MUST_FIRE)
        print("\n\nSeeded-error benchmark (default engines, no external checker)")
        print("\n".join(rows))
        print("  %-42s %d/%d" % ("detected", tp, n))
        print("  %-42s %d/%d  <-- the headline" % ("false alarms", fp, n))
        print("\n  Not reachable without a translated check script:")
        for name, need in sorted(NEEDS_TRANSLATION.items()):
            print("    %-52s %s" % (name[:52], need))
        self.assertEqual(fp, 0, "the false-alarm rate must be zero")


if __name__ == "__main__":
    unittest.main()
