r"""Hypotheses of results invoked by name.

`segment.NAMED_RESULTS` normalises "by Jensen's inequality" into `jensen`, and
its own comment said what was missing: an entry nobody checks the hypotheses of
is decoration. This is the checker, and its value is in what it declines to say.

Most named results need something no parser sees -- that a norm is finite, that a
dominating summable bound exists. Those emit nothing at all. Emitting
`undetermined` for every hypothesis of every named result would have added about
120 rows on one monograph, and a report nobody finishes is worse than none.
"""
import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from latexmath import named as N  # noqa: E402


def step(name, lhs, rhs, relation=r"\geq", symbols_used=("f", "X")):
    return {"id": "proof/x/s01", "claim_forms": [
        {"form": "adjacent", "lhs_tex": lhs, "relation": relation,
         "rhs_tex": rhs}],
        "symbols_used": list(symbols_used),
        "justification": {"kind": "named-result", "name": name}}


CONVEX = {"f": {"symbol": "f", "domain_hint": "convex",
                "domain_provenance": "declared"}}
NOTHING = {"f": {"symbol": "f", "domain_hint": None,
                 "domain_provenance": "unknown"}}


class TestJensenDirection(unittest.TestCase):
    r"""Direction is the whole content of the inequality.

    For convex $f$, $\mathbb{E}[f(X)] \ge f(\mathbb{E}[X])$. A step that names
    Jensen, declares its function convex and then puts $f(\mathbb{E}[X])$ on the
    larger side has applied it backwards -- the defect the seeded-error benchmark
    listed as unreachable until this engine existed.
    """

    def test_the_wrong_way_round_is_reported(self):
        got = N.conditions(step("jensen", r"f(\mathbb{E}[X])", r"\mathbb{E}[f(X)]"),
                           CONVEX)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["status"], "unstated")
        self.assertIn("larger side", got[0]["detail"])

    def test_the_right_way_round_is_established(self):
        got = N.conditions(step("jensen", r"\mathbb{E}[f(X)]", r"f(\mathbb{E}[X])"),
                           CONVEX)
        self.assertEqual(got[0]["status"], "established")

    def test_a_reversed_relation_reverses_the_verdict(self):
        """`\\le` with E[f] on the left is the same error, written the other way."""
        got = N.conditions(
            step("jensen", r"\mathbb{E}[f(X)]", r"f(\mathbb{E}[X])", r"\leq"),
            CONVEX)
        self.assertEqual(got[0]["status"], "unstated")

    def test_no_declared_convexity_claims_nothing(self):
        got = N.conditions(step("jensen", r"f(\mathbb{E}[X])", r"\mathbb{E}[f(X)]"),
                           NOTHING)
        self.assertEqual(got[0]["status"], "undetermined")

    def test_a_step_with_no_expectation_shape_is_skipped(self):
        self.assertEqual(N.conditions(step("jensen", "a", "b"), CONVEX), [])


class TestWhatItDeclinesToSay(unittest.TestCase):
    def test_a_result_with_no_mechanical_hypothesis_emits_nothing(self):
        for name in ("cauchy-schwarz", "fubini", "union-bound", "taylor"):
            self.assertEqual(
                N.conditions(step(name, "a", "b"), CONVEX), [],
                "%s has no checkable hypothesis and must stay silent" % name)

    def test_every_silent_result_says_why_it_is_silent(self):
        """The difference between "checked and fine" and "not looked at" is the
        reason this table exists rather than being an empty set."""
        from latexmath.segment import NAMED_RESULTS
        catalogued = {k for k, _ in NAMED_RESULTS}
        accounted = set(N.UNCHECKED) | set(N._CHECKS)
        self.assertEqual(catalogued - accounted, set(),
                         "a catalogued result is neither checked nor explained")

    def test_a_step_invoking_nothing_by_name_is_skipped(self):
        s = step("jensen", r"\mathbb{E}[f(X)]", r"f(\mathbb{E}[X])")
        s["justification"] = {"kind": "none", "name": None}
        self.assertEqual(N.conditions(s, CONVEX), [])


class TestNonNegativeSubject(unittest.TestCase):
    def test_markov_on_a_declared_nonnegative_quantity_is_established(self):
        syms = {"Z": {"symbol": "Z", "domain_hint": "nonnegative",
                      "domain_provenance": "declared"}}
        got = N.conditions(step("markov", "a", "b", symbols_used=("Z",)), syms)
        self.assertEqual(got[0]["status"], "established")

    def test_markov_on_a_declared_real_quantity_is_reported(self):
        syms = {"Z": {"symbol": "Z", "domain_hint": "real",
                      "domain_provenance": "declared"}}
        got = N.conditions(step("markov", "a", "b", symbols_used=("Z",)), syms)
        self.assertEqual(got[0]["status"], "unstated")

    def test_markov_with_nothing_declared_claims_nothing(self):
        syms = {"Z": {"symbol": "Z", "domain_hint": None,
                      "domain_provenance": "unknown"}}
        got = N.conditions(step("markov", "a", "b", symbols_used=("Z",)), syms)
        self.assertEqual(got[0]["status"], "undetermined")


if __name__ == "__main__":
    unittest.main()
