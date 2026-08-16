r"""The CAS path, end to end, against a real published error. Offline; needs SymPy.

    cd verifying-proofs/assets && python3 -m unittest tests.test_adam_refutation -v

Everything else that ships measures the *default* engine set, which is a hygiene
checker: on thirteen real papers it found none of the six documented defects. This
file is the counterweight — the one case where a filled-in `build()` turned the
tool into a correctness checker and refuted a step that a published paper exists
to correct.

**The step.** Adam (arXiv:1412.6980v8), Lemma 10.4 in the appendix
(`lemma:momentum_sum`), the step justified by

    For $\gamma < 1$, using the upper bound on the arithmetic-geometric series,
    $\sum_t t\gamma^t < 1/(1-\gamma)^2$

The bound is quoted correctly and applied to the wrong sum. In
$\sum_{j=0}^{T} t\gamma^j$ the index is $j$ and $t$ is a constant factor, so the
sum is $t\,(1-\gamma^{T+1})/(1-\gamma)$ and the $t$ cannot be dropped. The proof
drops it. arXiv:1804.10587 exists to repair this proof.

**Why it must keep refuting.** If a future change makes this test stop finding the
counterexample, that change is wrong — this is the only end-to-end evidence that
the pipeline can find a real mathematical error rather than a missing licence.

**What it also pins.** The three-way behaviour around domains, which is the guard
that nearly buried this result: with the domains unknown the refutation is
*suppressed as a claim but reported as an event* at MAJOR, naming the symbols to
supply; with them supplied the same script returns CRITICAL. That asymmetry is the
most actionable thing the tool produces and it is easy to break by accident.
"""
import os
import pathlib
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))

from proofcheck import compose, ledger_io, stubs  # noqa: E402

try:
    import sympy  # noqa: F401
    HAVE_SYMPY = True
except ImportError:                                # pragma: no cover
    HAVE_SYMPY = False

#: The lemma and proof verbatim from arXiv:1412.6980v8, trimmed to the passage
#: that carries the defect. `\hm`/`\hv` are the paper's macros for the
#: bias-corrected moment estimates.
FIXTURE = r"""\documentclass{article}
\usepackage{amsmath,amssymb}
\newtheorem{lemma}{Lemma}
\newcommand{\hm}{\hat{m}}
\newcommand{\hv}{\hat{v}}
\begin{document}
\begin{lemma}
\label{lemma:momentum_sum}
Let $\gamma \triangleq { \beta_1^2 \over \sqrt{\beta_2}}$. For $\beta_1$,
$\beta_2 \in [0,1)$ that satisfy ${ \beta_1^2 \over \sqrt{\beta_2}} < 1$ and
bounded $g_t$, $\|g_t\|_2 \le G $, $\|g_t\|_\infty \le G_\infty $, the following
inequality holds
\[
\sum_{t=1}^T{\hm^2_{t,i} \over \sqrt{t\hv_{t,i}}} \le
 {2\over 1-\gamma}{1\over \sqrt{1-\beta_2}}\|g_{1:T,i}\|_2
\]
\end{lemma}

\begin{proof}
We can upper bound the terms in the summation.
\begin{align*}
\sum_{t=1}^T{\hm^2_{t,i} \over \sqrt{t\hv_{t,i}}}
&\le \sum_{t=1}^{T}{\|g_{t,i}\|_2\over \sqrt{t(1-\beta_2)}} \sum_{j=0}^{T-t}t\gamma^j  \\
&\le \sum_{t=1}^{T}{\|g_{t,i}\|_2\over \sqrt{t(1-\beta_2)}} \sum_{j=0}^{T}t\gamma^j  \\
\end{align*}
For $\gamma < 1$, using the upper bound on the arithmetic-geometric series,
$\sum_t t\gamma^t < {1\over(1-\gamma)^2}$:
\begin{align*}
\sum_{t=1}^{T}{\|g_{t,i}\|_2\over \sqrt{t(1-\beta_2)}} \sum_{j=0}^{T}t\gamma^j
&\le {1\over (1-\gamma)^2\sqrt{1-\beta_2}}\sum_{t=1}^T{\|g_{t,i}\|_2 \over \sqrt{t}}
\end{align*}
\end{proof}
\end{document}
"""

#: The distinctive text of the defective step, used to find its script rather
#: than hard-coding an ordinal that moves whenever segmentation changes.
DEFECT_MARK = r"\sum_{j=0}^{T}t\gamma^j"

#: The translation. Every value is inside the domains the paper states for the
#: symbols it bothers to bound, and `beta_2 = 0` sits at the closed end of
#: $\beta_2 \in [0,1)$.
#:
#: Substituting concrete admissible values is what refuting a universally
#: quantified inequality *is*, so the translation stays `faithful`: nothing is
#: idealised, no constant is dropped, no opaque atom is invented. The guard
#: against a badly chosen point is not the confidence flag but `domains_known`,
#: which is exactly why this refutation was blocked until `--symbols` supplied
#: the domains Adam never states.
FILLED_BUILD = '''
IGNORED_SYMBOLS = ['T', 'beta', 'g', 'gamma', 'i', 'j', 't']
TRANSLATION_CONFIDENCE = "faithful"
TRANSLATION_NOTES = (
    "Evaluated at T=4, gamma=1/2, beta_2=0, and all gradient norms 1 -- a point "
    "inside every domain the paper states. The claim is universal in these, so "
    "one admissible point decides it.")


def build():
    import sympy
    T, gamma, beta2 = 4, sympy.Rational(1, 2), sympy.Integer(0)
    gnorm = sympy.Integer(1)
    lhs = sum((gnorm / sympy.sqrt(t * (1 - beta2)))
              * sum(t * gamma ** j for j in range(0, T + 1))
              for t in range(1, T + 1))
    rhs = (1 / ((1 - gamma) ** 2 * sympy.sqrt(1 - beta2))) \\
        * sum(gnorm / sympy.sqrt(t) for t in range(1, T + 1))
    return lhs, rhs, "\\\\le"
'''

#: The grid the robustness claim in SKILL.md is measured on. Stated here so the
#: number is reproducible rather than remembered: a violation count quoted
#: without the grid it was counted on says nothing.
GRID_T = (2, 3, 4, 5, 8, 12)
GRID_GAMMA = ("1/3", "1/2", "2/3", "3/4", "9/10")


def _false_gammas(T):
    """The gammas on the grid at which the step's inequality is false at horizon T."""
    import sympy
    bad = []
    for g in GRID_GAMMA:
        gamma = sympy.Rational(g)
        lhs = sum((1 / sympy.sqrt(t)) * sum(t * gamma ** j for j in range(0, T + 1))
                  for t in range(1, T + 1))
        rhs = (1 / (1 - gamma) ** 2) * sum(1 / sympy.sqrt(t) for t in range(1, T + 1))
        if sympy.simplify(rhs - lhs) < 0:
            bad.append(g)
    return bad


def _fixture_dir():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "main.tex")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(FIXTURE)
    return d, path


def _fill(script_path):
    """Replace the stub's placeholder `build()` with the real translation.

    The header, the inlined harness and the `__main__` block are kept exactly as
    generated: this test is worth having only if it runs the script the tool
    actually writes, so it edits the one function a user edits and nothing else.
    """
    text = pathlib.Path(script_path).read_text(encoding="utf-8")
    for marker in ("STEP_ID = ", 'if __name__ == "__main__":'):
        assert marker in text, "stub layout changed: no %r" % marker
    head = text[:text.index("STEP_ID = ")]
    consts = text[text.index("STEP_ID = "):text.index('if __name__ == "__main__":')]
    main = text[text.index('if __name__ == "__main__":'):]
    for name in ("IGNORED_SYMBOLS", "TRANSLATION_CONFIDENCE", "TRANSLATION_NOTES"):
        consts = re.sub(r"^%s = .*$" % name, "", consts, flags=re.M)
    consts = re.sub(r"\n{3,}", "\n\n", consts).rstrip() + "\n"
    pathlib.Path(script_path).write_text(
        head + consts + FILLED_BUILD + "\n\n" + main, encoding="utf-8")


def _run_the_step():
    """Ledger -> stub -> filled translation -> executed script, as a user would."""
    workdir, main_tex = _fixture_dir()
    out = os.path.join(workdir, "review-assets")
    led = ledger_io.build(main_tex)
    stubs.write_stubs(led, out, ("symbolic",), 24)

    checks = pathlib.Path(out, "checks")
    target = None
    for path in sorted(checks.glob("*.py")):
        if DEFECT_MARK in path.read_text(encoding="utf-8"):
            target = path
    assert target is not None, (
        "no check script carries the defective step; the segmenter stopped "
        "finding it, which is a bigger problem than this test")
    _fill(str(target))

    step_id = re.search(r"STEP_ID = '([^']+)'",
                        target.read_text(encoding="utf-8")).group(1)
    results = [r for r in stubs.collect(out, 60, 300) if r.get("step_id") == step_id]
    step = next(s for s in led["steps"] if s["id"] == step_id)
    return led, step, results


@unittest.skipUnless(HAVE_SYMPY, "sympy not installed")
class TestAdamRefutation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger, cls.step, cls.results = _run_the_step()

    def test_the_step_is_refuted(self):
        self.assertTrue(self.results, "the check script produced no result")
        r = self.results[0]
        self.assertEqual(r["outcome"], "refuted",
                         "Adam Lemma 10.4 stopped refuting: %s" % r.get("detail"))

    def test_the_counterexample_is_the_published_one(self):
        detail = self.results[0].get("detail") or ""
        self.assertIn("29", detail)
        self.assertIn("sqrt(3)", detail)

    def test_unknown_domains_report_the_blocked_refutation_rather_than_burying_it(self):
        """The guard that prevents false alarms had hidden a true one. It now
        reports the event at MAJOR and names what to supply."""
        v = compose.compose_step(self.step, self.results, False,
                                 ["gamma", "beta", "T"])
        self.assertEqual(v["severity"], "MAJOR")
        self.assertEqual(v.get("kind"), "refutation-blocked-by-unknown-domain")
        self.assertTrue(v.get("symbols_to_supply"),
                        "a blocked refutation that names no symbol cannot be acted on")

    def test_supplying_the_domains_makes_the_same_script_critical(self):
        v = compose.compose_step(self.step, self.results, True, [])
        self.assertEqual(v["severity"], "CRITICAL",
                         "the decisive path is broken: %s" % v.get("detail"))

    def test_an_unfaithful_translation_cannot_reach_critical(self):
        """Rule 2 of composition, on the case that matters most."""
        weakened = [dict(self.results[0], translation_confidence="approximate")]
        self.assertEqual(compose.compose_step(self.step, weakened, True, [])["severity"],
                         "WEAK")

    def test_the_violation_region_grows_with_the_horizon(self):
        """One failing point could be a modelling slip. A region that widens
        monotonically in $T$ is the asymptotics of the dropped factor, which is
        what makes this a proof error rather than a numerical accident."""
        counts = [len(_false_gammas(T)) for T in GRID_T]
        self.assertEqual(counts, sorted(counts),
                         "the violation stopped growing with T: %s" % counts)
        self.assertEqual(counts[0], 0, "it should hold at small T")
        self.assertGreater(counts[-1], 1)

    def test_summary(self):
        """Prints the measurement; asserts nothing."""
        print("\n  Adam (arXiv:1412.6980v8) Lemma 10.4, the step that applies")
        print("  sum_t t*gamma^t < 1/(1-gamma)^2 to sum_{j=0}^{T} t*gamma^j.")
        print("  FALSE marks a setting where the claimed inequality does not hold,")
        print("  with all gradient norms 1 and beta_2 = 0.\n")
        print("  T    " + "  ".join("%7s" % g for g in GRID_GAMMA))
        total = 0
        for T in GRID_T:
            bad = _false_gammas(T)
            total += len(bad)
            print("  %-4d " % T + "  ".join("%7s" % ("FALSE" if g in bad else "ok")
                                            for g in GRID_GAMMA))
        print("\n  refuted at %d of %d settings; the region widens with T, as the"
              % (total, len(GRID_T) * len(GRID_GAMMA)))
        print("  dropped factor of t demands.")
        print("  Exact counterexample at T=4, gamma=1/2: "
              "rhs - lhs = -29*sqrt(3)/48 + sqrt(2)/16 + 3/16")


if __name__ == "__main__":
    unittest.main()
