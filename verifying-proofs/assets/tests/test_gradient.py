"""The finite-difference gradient engine.

The Richardson check is the assertion to read first. Without it, every derivative
claim evaluated near a kink or a cancellation looks refuted, and this becomes the
noisiest engine in the set — reporting arithmetic as mathematics.
"""
import unittest, sys, pathlib
from decimal import Decimal
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from proofcheck.engines import gradient as G  # noqa: E402

H = {}
exec(compile(G.HARNESS, "<harness>", "exec"), H)


def check(f, claimed, point, var="x"):
    return H["check"](f, claimed, point, var, "step/t")


class TestCorrectDerivatives(unittest.TestCase):
    def test_a_polynomial_derivative_is_not_refuted(self):
        r = check(lambda e: e["x"] ** 3, lambda e: 3 * e["x"] ** 2, {"x": 2})
        self.assertEqual(r["outcome"], "not-refuted")

    def test_the_word_verified_never_appears(self):
        r = check(lambda e: e["x"] ** 2, lambda e: 2 * e["x"], {"x": 3})
        self.assertNotIn("verified", r["detail"].lower())

    def test_a_partial_derivative_in_a_named_variable(self):
        r = check(lambda e: e["x"] * e["y"] ** 2,
                  lambda e: e["y"] ** 2, {"x": 2, "y": 3}, var="x")
        self.assertEqual(r["outcome"], "not-refuted")

    def test_the_other_partial_of_the_same_expression(self):
        r = check(lambda e: e["x"] * e["y"] ** 2,
                  lambda e: 2 * e["x"] * e["y"], {"x": 2, "y": 3}, var="y")
        self.assertEqual(r["outcome"], "not-refuted")

    def test_a_quotient_rule_derivative(self):
        r = check(lambda e: 1 / (1 - e["x"]),
                  lambda e: 1 / (1 - e["x"]) ** 2, {"x": Decimal("0.5")})
        self.assertEqual(r["outcome"], "not-refuted")


class TestWrongDerivatives(unittest.TestCase):
    def test_a_missing_factor_is_refuted(self):
        r = check(lambda e: e["x"] ** 3, lambda e: e["x"] ** 2, {"x": 2})
        self.assertEqual(r["outcome"], "refuted")
        self.assertTrue(r["counterexample"])

    def test_a_sign_error_is_refuted(self):
        r = check(lambda e: e["x"] ** 2, lambda e: -2 * e["x"], {"x": 3})
        self.assertEqual(r["outcome"], "refuted")

    def test_an_off_by_one_exponent_is_refuted(self):
        r = check(lambda e: e["x"] ** 4, lambda e: 4 * e["x"] ** 2, {"x": 2})
        self.assertEqual(r["outcome"], "refuted")

    def test_the_refutation_names_the_point_and_both_values(self):
        r = check(lambda e: e["x"] ** 3, lambda e: e["x"] ** 2, {"x": 2})
        self.assertIn("x = 2", r["detail"])


class TestNumericalHonesty(unittest.TestCase):
    def test_an_unevaluable_point_is_unverified_not_a_refutation(self):
        r = check(lambda e: 1 / (e["x"] - e["x"]), lambda e: Decimal(0), {"x": 2})
        self.assertEqual(r["outcome"], "unverified")
        self.assertNotEqual(r["outcome"], "refuted")

    def test_an_untranslatable_model_says_so(self):
        def f(e):
            raise H["Untranslatable"]("no model for the operator")
        r = check(f, lambda e: Decimal(0), {"x": 1})
        self.assertEqual(r["outcome"], "untranslatable")

    def test_a_claimed_derivative_that_raises_is_not_a_refutation(self):
        def claimed(e):
            raise ZeroDivisionError
        r = check(lambda e: e["x"] ** 2, claimed, {"x": 2})
        self.assertEqual(r["outcome"], "unverified")


class TestRichardson(unittest.TestCase):
    def test_the_order_check_exists_and_bounds_are_around_four(self):
        """A central difference has error O(h^2): halving h should quarter it."""
        self.assertLess(H["_ORDER_LO"], Decimal(4))
        self.assertGreater(H["_ORDER_HI"], Decimal(4))

    def test_steps_halve_so_the_ratio_is_meaningful(self):
        steps = H["_STEPS"]
        for a, b in zip(steps, steps[1:]):
            self.assertEqual(a / b, Decimal(2))


if __name__ == "__main__":
    unittest.main()
