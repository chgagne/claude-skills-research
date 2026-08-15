"""The randomized exact-rational engine.

It can only ever refute. That asymmetry is the whole design: a step that survives
24 sample points is *not refuted*, which is evidence and not proof, and the word
"verified" must never appear next to it.

The sampling rules are all defensive. 0 and +-1 are excluded because they satisfy
too many false identities. Degenerate points are rejected and counted rather than
silently passed. A failure is re-run at higher density to report the smallest
counterexample, because one a reader can check by hand in thirty seconds is worth
ten they cannot.
"""
import unittest, sys, pathlib
from fractions import Fraction
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from proofcheck.engines import rational as R  # noqa: E402

H = {}
exec(compile(R.HARNESS, "<harness>", "exec"), H)


class TestSamplePool(unittest.TestCase):
    def test_zero_and_one_are_excluded(self):
        vals = {abs(v) for v in H["_pool"]("real", 200)}
        self.assertNotIn(Fraction(0), vals)
        self.assertNotIn(Fraction(1), vals)

    def test_positive_domain_yields_only_positive_samples(self):
        self.assertTrue(all(v > 0 for v in H["_pool"]("positive", 60)))

    def test_unit_interval_samples_lie_inside_it(self):
        self.assertTrue(all(0 < v < 1 for v in H["_pool"]("unit-interval", 60)))

    def test_half_open_unit_interval_excludes_one(self):
        self.assertTrue(all(0 <= v < 1
                            for v in H["_pool"]("unit-interval-half-open", 60)))

    def test_natural_domain_yields_integers(self):
        self.assertTrue(all(v.denominator == 1 and v > 0
                            for v in H["_pool"]("natural", 40)))

    def test_an_unknown_domain_still_samples_the_reals(self):
        self.assertTrue(H["_pool"](None, 20))


class TestDeterminism(unittest.TestCase):
    def test_the_same_step_id_gives_the_same_points(self):
        a = H["_points"](["x", "y"], {"x": "real", "y": "positive"}, "step/a", 12)
        b = H["_points"](["x", "y"], {"x": "real", "y": "positive"}, "step/a", 12)
        self.assertEqual(a, b, "two runs must be byte-identical")

    def test_different_steps_give_different_points(self):
        a = H["_points"](["x"], {"x": "real"}, "step/a", 12)
        b = H["_points"](["x"], {"x": "real"}, "step/b", 12)
        self.assertNotEqual(a, b)


class TestEvaluation(unittest.TestCase):
    def run_check(self, lhs, rhs, relation="=", domains=None, trials=24,
                  symbols=("x", "y")):
        return H["check"](lhs, rhs, relation, list(symbols),
                          domains or {}, "step/t", trials)

    def test_a_true_identity_is_not_refuted(self):
        r = self.run_check(lambda e: (e["x"] + e["y"]) ** 2,
                           lambda e: e["x"] ** 2 + 2 * e["x"] * e["y"] + e["y"] ** 2)
        self.assertEqual(r["outcome"], "not-refuted")
        self.assertEqual(r["trials"], 24)

    def test_the_word_verified_never_appears(self):
        r = self.run_check(lambda e: e["x"], lambda e: e["x"])
        self.assertNotIn("verified", (r.get("detail") or "").lower())

    def test_a_false_identity_is_refuted(self):
        r = self.run_check(lambda e: (e["x"] + e["y"]) ** 2,
                           lambda e: e["x"] ** 2 + e["y"] ** 2)
        self.assertEqual(r["outcome"], "refuted")
        self.assertTrue(r["counterexample"])

    def test_the_smallest_refuting_point_is_reported(self):
        """A counterexample a human can check by hand beats ten they cannot."""
        r = self.run_check(lambda e: e["x"] ** 2, lambda e: e["x"] ** 3,
                           symbols=("x",))
        self.assertEqual(r["outcome"], "refuted")
        val = abs(Fraction(r["counterexample"]["x"]))
        self.assertLessEqual(val, Fraction(3),
                             "a larger counterexample than necessary was reported")

    def test_a_sign_error_is_caught(self):
        r = self.run_check(lambda e: e["x"] - e["y"], lambda e: e["y"] - e["x"])
        self.assertEqual(r["outcome"], "refuted")

    def test_an_inequality_that_holds_is_not_refuted(self):
        r = self.run_check(lambda e: e["x"] ** 2, lambda e: Fraction(0), r"\ge",
                           symbols=("x",))
        self.assertEqual(r["outcome"], "not-refuted")

    def test_an_inequality_in_the_wrong_direction_is_refuted(self):
        r = self.run_check(lambda e: e["x"] ** 2, lambda e: Fraction(0), r"\le",
                           symbols=("x",))
        self.assertEqual(r["outcome"], "refuted")


class TestDegenerateRejection(unittest.TestCase):
    def test_a_zero_division_point_is_rejected_and_counted(self):
        def lhs(e):
            return Fraction(1) / (e["x"] - e["x"])
        r = H["check"](lhs, lambda e: Fraction(0), "=", ["x"], {}, "s", 24)
        self.assertEqual(r["outcome"], "unverified")
        self.assertGreater(r["rejected_samples"], 0)

    def test_half_or_more_rejected_is_unverified_never_a_pass(self):
        state = {"n": 0}

        def lhs(e):
            state["n"] += 1
            if state["n"] % 2:
                raise ZeroDivisionError
            return e["x"]
        r = H["check"](lhs, lambda e: e["x"], "=", ["x"], {}, "s", 24)
        self.assertEqual(r["outcome"], "unverified")
        self.assertIn("sampl", r["detail"].lower())

    def test_a_coincidental_double_zero_is_not_counted_as_evidence(self):
        r = H["check"](lambda e: Fraction(0), lambda e: Fraction(0), "=",
                       ["x"], {}, "s", 24)
        self.assertEqual(r["outcome"], "unverified")

    def test_an_untranslatable_step_says_so(self):
        def lhs(e):
            raise H["Untranslatable"]("no model for \\operatorname{pool}")
        r = H["check"](lhs, lambda e: e["x"], "=", ["x"], {}, "s", 24)
        self.assertEqual(r["outcome"], "untranslatable")


class TestBoundaryPoints(unittest.TestCase):
    def test_inequalities_get_domain_endpoints_added(self):
        """Inequalities fail at boundaries and hold on a random interior."""
        pts = H["_points"](["g"], {"g": "unit-interval"}, "s", 8, relation=r"\le")
        vals = [p["g"] for p in pts]
        self.assertTrue(any(v < Fraction(1, 50) for v in vals),
                        "no point near the lower endpoint was tried")


if __name__ == "__main__":
    unittest.main()
