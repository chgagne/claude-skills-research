r"""The finite-difference engine, end to end, on a derivative a real paper states.

    cd verifying-proofs/assets && python3 -m unittest tests.test_gradient_on_a_real_claim -v

`engines/gradient.py` was unit-tested from the day it was written and had **never
run on a real paper**. This is the same evidence `test_adam_refutation.py`
provides for the SymPy path: a fixture built from published source, a stub
generated through the shipped code path, one filled-in `build()`, the script
executed in the sandbox, and `compose_step` on the result.

**The claim.** Wilde, *From Classical to Quantum Shannon Theory*
(arXiv:1106.1445), the calculus lemma behind Pinsker's inequality. The proof sets

    g(a,b) = a ln(a/b) + (1-a) ln((1-a)/(1-b)) - 2(a-b)^2

and states its partial derivative in `b`. That derivative is **correct**, so the
engine must return `not-refuted` — an engine whose only demonstration is finding
an error tells you nothing about how often it invents one. The second case
perturbs the stated coefficient and must be refuted, with the point named.

Offline and deterministic: stdlib `decimal` at 50 digits, no external checker.
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

#: The passage verbatim from arXiv:1106.1445, trimmed to the derivative claim.
FIXTURE = r"""\documentclass{article}
\usepackage{amsmath}
\newtheorem{lemma}{Lemma}
\begin{document}
\begin{lemma}
\label{lem:calc-lemma-pinsker}
For $a, b \in (0,1)$, the bound holds.
\end{lemma}

\begin{proof}
So suppose that $b\in\left(  0,1\right)  $. Consider the following function:
\begin{equation}
g(a,b)\equiv a\ln\left(  \frac{a}{b}\right)  +\left(  1-a\right)  \ln\left(
\frac{1-a}{1-b}\right)  -2\left(  a-b\right)  ^{2},
\end{equation}
Then
\begin{align}
\frac{\partial g(a,b)}{\partial b}  &  =-\frac{a}{b}+\frac{1-a}{1-b}-4\left(
b-a\right)
\end{align}
\end{proof}
\end{document}
"""

#: The text that identifies the step carrying the derivative claim. Located by
#: content rather than by ordinal: how a proof segments is one of the things this
#: suite exists to notice changing.
DERIVATIVE_MARK = r"\partial g(a,b)"

#: The translation. `a` and `b` are both in $(0,1)$, which the proof states on the
#: line above, so the evaluation point is inside the stated domain.
FILLED_BUILD = '''
IGNORED_SYMBOLS = ['g']
TRANSLATION_CONFIDENCE = "faithful"
TRANSLATION_NOTES = (
    "g and its stated partial derivative in b, evaluated at a point inside the "
    "(0,1) range the proof states one line earlier.")

_COEFF = Decimal("4")


def build():
    def g(p):
        a, b = p["a"], p["b"]
        return a * (a / b).ln() + (1 - a) * ((1 - a) / (1 - b)).ln() \\
            - 2 * (a - b) ** 2

    def claimed(p):
        a, b = p["a"], p["b"]
        return -a / b + (1 - a) / (1 - b) - _COEFF * (b - a)

    return g, claimed, {"a": Decimal("0.3"), "b": Decimal("0.5")}, "b"
'''


def _fixture_dir(text=FIXTURE):
    d = tempfile.mkdtemp()
    path = os.path.join(d, "main.tex")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return d, path


def _fill(script_path, body):
    """Replace the stub's placeholder `build()`, keeping everything else."""
    text = pathlib.Path(script_path).read_text(encoding="utf-8")
    for marker in ("STEP_ID = ", 'if __name__ == "__main__":'):
        assert marker in text, "stub layout changed: no %r" % marker
    head = text[:text.index("STEP_ID = ")]
    consts = text[text.index("STEP_ID = "):text.index('if __name__ == "__main__":')]
    main = text[text.index('if __name__ == "__main__":'):]
    for name in ("IGNORED_SYMBOLS", "TRANSLATION_CONFIDENCE", "TRANSLATION_NOTES"):
        consts = re.sub(r"^%s = .*$" % name, "", consts, flags=re.M)
    consts = re.sub(r"\n{3,}", "\n\n", consts).rstrip() + "\n"
    pathlib.Path(script_path).write_text(head + consts + body + "\n\n" + main,
                                         encoding="utf-8")


def _run(build_body):
    """Ledger -> gradient stub -> filled translation -> executed script."""
    workdir, main_tex = _fixture_dir()
    out = os.path.join(workdir, "review-assets")
    led = ledger_io.build(main_tex)
    stubs.write_stubs(led, out, ("gradient",), 24)

    target = None
    for path in sorted(pathlib.Path(out, "checks").glob("*.py")):
        if DERIVATIVE_MARK in path.read_text(encoding="utf-8"):
            target = path
    assert target is not None, (
        "no check script carries the derivative claim; the segmenter stopped "
        "finding it, which is a bigger problem than this test")
    _fill(str(target), build_body)

    step_id = re.search(r"STEP_ID = '([^']+)'",
                        target.read_text(encoding="utf-8")).group(1)
    results = [r for r in stubs.collect(out, 60, 300) if r.get("step_id") == step_id]
    step = next(s for s in led["steps"] if s["id"] == step_id)
    return step, results


class TestGradientOnARealClaim(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.step, cls.results = _run(FILLED_BUILD)
        cls.bad_step, cls.bad_results = _run(
            FILLED_BUILD.replace('_COEFF = Decimal("4")', '_COEFF = Decimal("2")'))

    def test_the_engine_generates_a_script_for_this_step(self):
        self.assertTrue(self.results, "the check script produced no result")

    def test_a_correct_derivative_is_not_refuted(self):
        """The half that matters. An engine whose only demonstration is finding
        an error says nothing about how often it invents one."""
        self.assertEqual(self.results[0]["outcome"], "not-refuted",
                         self.results[0].get("detail"))

    def test_a_perturbed_coefficient_is_refuted(self):
        self.assertEqual(self.bad_results[0]["outcome"], "refuted",
                         self.bad_results[0].get("detail"))

    def test_the_refutation_names_the_point(self):
        """A finding a reader cannot reproduce by hand is not worth having."""
        detail = self.bad_results[0].get("detail") or ""
        self.assertIn("0.3", detail)
        self.assertIn("0.5", detail)

    def test_a_correct_derivative_never_composes_to_a_finding(self):
        v = compose.compose_step(self.step, self.results, True, [])
        self.assertNotIn(v["severity"], ("CRITICAL", "MAJOR"), v.get("detail"))

    def test_an_unfaithful_translation_caps_the_refutation_at_weak(self):
        """Rule 2 of composition, on the engine that had never been exercised."""
        weakened = [dict(self.bad_results[0], translation_confidence="approximate")]
        self.assertEqual(
            compose.compose_step(self.bad_step, weakened, True, [])["severity"],
            "WEAK")

    def test_an_unknown_domain_blocks_the_refutation_rather_than_burying_it(self):
        v = compose.compose_step(self.bad_step, self.bad_results, False, ["b"])
        self.assertEqual(v["severity"], "MAJOR")
        self.assertEqual(v.get("kind"), "refutation-blocked-by-unknown-domain")


if __name__ == "__main__":
    unittest.main()
