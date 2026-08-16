"""Symbol inventory and domain provenance.

This module decides whether a refutation is allowed to exist. A counterexample at
$x = -11/5$ for a step that obviously means $x > 0$ is the canonical cry-wolf
event, and the defence is not a better sampler -- it is knowing that the domain
of $x$ was never established, and refusing to refute.

So `provenance` is the field that matters. `declared` carries a quote from the
paper. `inferred` is a guess the tool made and says so. `unknown` is the honest
default and it can never license a refutation.
"""
import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from latexmath import symbols as SY  # noqa: E402


def inv(text):
    return {s.symbol: s for s in SY.inventory(text)}


class TestDeclaredDomains(unittest.TestCase):
    def test_interval_membership_is_declared_with_its_quote(self):
        got = inv(r"Let $\gamma \in [0,1)$ be the discount factor. "
                  r"Then $\gamma^t \to 0$.")[r"\gamma"]
        self.assertEqual(got.domain_hint, "unit-interval-half-open")
        self.assertEqual(got.domain_provenance, "declared")
        self.assertIn(r"[0,1)", got.domain_evidence[0]["quote"])

    def test_closed_unit_interval(self):
        self.assertEqual(inv(r"Suppose $p \in [0,1]$.")["p"].domain_hint,
                         "unit-interval")

    def test_reals_and_dimension(self):
        got = inv(r"Let $x \in \mathbb{R}^d$ be the input.")["x"]
        self.assertEqual(got.domain_hint, "real-vector")
        self.assertEqual(got.role_hint, "vector")

    def test_scalar_reals(self):
        self.assertEqual(inv(r"Let $t \in \mathbb{R}$.")["t"].domain_hint, "real")

    def test_naturals(self):
        self.assertEqual(inv(r"Let $k \in \mathbb{N}$.")["k"].domain_hint,
                         "natural")

    def test_positivity_from_prose(self):
        got = inv(r"Let $\eta > 0$ denote the step size.")[r"\eta"]
        self.assertEqual(got.domain_hint, "positive")
        self.assertEqual(got.domain_provenance, "declared")

    def test_positive_definite_matrix(self):
        got = inv(r"Let $A \succ 0$ be the Gram matrix.")["A"]
        self.assertEqual(got.domain_hint, "positive-definite")
        self.assertEqual(got.role_hint, "matrix")

    def test_probability_distribution_from_prose(self):
        got = inv(r"Let $q$ be a probability distribution over $\mathcal{Z}$.")["q"]
        self.assertEqual(got.domain_hint, "probability-distribution")
        self.assertEqual(got.domain_provenance, "declared")

    def test_declaration_far_from_first_use_is_not_claimed(self):
        """High precision means near first use only."""
        text = (r"We study $\beta$ throughout. " + ("Filler sentence. " * 40)
                + r"Elsewhere, $\beta > 0$ holds.")
        self.assertEqual(inv(text)[r"\beta"].domain_provenance, "unknown")


class TestInferredDomains(unittest.TestCase):
    def test_summation_index_is_an_integer_but_only_inferred(self):
        got = inv(r"Consider $\sum_{i=1}^n a_i$.")["i"]
        self.assertEqual(got.domain_hint, "natural")
        self.assertEqual(got.domain_provenance, "inferred")

    def test_inference_never_upgrades_to_declared(self):
        got = inv(r"Consider $\sum_{i=1}^n a_i$ and $\prod_{i=1}^n b_i$.")["i"]
        self.assertEqual(got.domain_provenance, "inferred")

    def test_declared_beats_inferred(self):
        got = inv(r"Let $i \in \mathbb{N}$. Consider $\sum_{i=1}^n a_i$.")["i"]
        self.assertEqual(got.domain_provenance, "declared")

    def test_matrix_inverse_implies_invertible(self):
        got = inv(r"The update uses $A^{-1} b$.")["A"]
        self.assertEqual(got.domain_hint, "invertible")
        self.assertEqual(got.domain_provenance, "inferred")


class TestUnknownIsTheDefault(unittest.TestCase):
    def test_a_symbol_with_no_evidence_is_unknown(self):
        got = inv(r"We have $z = w + 1$.")["z"]
        self.assertEqual(got.domain_hint, None)
        self.assertEqual(got.domain_provenance, "unknown")
        self.assertEqual(got.domain_evidence, [])

    def test_unknown_symbols_cannot_license_a_refutation(self):
        """The rule the whole severity ladder rests on, asserted here."""
        got = inv(r"We have $z = w + 1$.")["z"]
        self.assertFalse(SY.can_refute(got))
        declared = inv(r"Let $u > 0$.")["u"]
        self.assertTrue(SY.can_refute(declared))

    def test_inferred_domains_may_refute(self):
        got = inv(r"Consider $\sum_{i=1}^n a_i$.")["i"]
        self.assertTrue(SY.can_refute(got))


class TestInventory(unittest.TestCase):
    def test_symbols_are_found_only_inside_mathematics(self):
        got = inv("The letter x appears in prose. Also $y = 1$.")
        self.assertIn("y", got)
        self.assertNotIn("x", got)

    def test_occurrences_and_first_use_are_recorded(self):
        got = inv(r"First $a$. Then $a + a$.")["a"]
        self.assertEqual(got.occurrences, 3)
        self.assertLess(got.first_use["start"], 12)

    def test_control_sequences_that_are_operators_are_not_symbols(self):
        got = inv(r"$\sum_{i} \log f(x) + \sin y$")
        for op in (r"\sum", r"\log", r"\sin"):
            self.assertNotIn(op, got)

    def test_greek_letters_are_symbols(self):
        self.assertIn(r"\gamma", inv(r"$\gamma + 1$"))

    def test_subscripted_symbols_collapse_to_their_base(self):
        got = inv(r"$a_1 + a_2 + a_i$")
        self.assertIn("a", got)
        self.assertEqual(got["a"].occurrences, 3)

    def test_package_notation_macros_are_not_symbols(self):
        """Measured on a real draft using `\\usepackage{physics}`.

        `\\dd` is that package's differential operator. The macro table only reads
        `\\newcommand` from the *source*, so package-provided notation is never
        expanded and lands in the inventory as an unknown-domain quantity --
        which then blocks refutation on every step it touches. `\\dd` alone
        blocked 108 of 470 checkable steps.
        """
        got = inv(r"$\dd r_t^2 = a \dd t + b \dd W_t$")
        for op in (r"\dd",):
            self.assertNotIn(op, got, "%s entered the symbol inventory" % op)
        self.assertIn("a", got, "real quantities must still be inventoried")

    def test_the_other_physics_derivative_macros_are_excluded_too(self):
        for tex, op in ((r"$\dv{f}{x}$", r"\dv"), (r"$\pdv{f}{x}$", r"\pdv"),
                        (r"$\Tr(A)$", r"\Tr"), (r"$\ev{H}$", r"\ev")):
            self.assertNotIn(op, inv(tex), "%s entered the inventory" % op)

    def test_differential_d_is_not_a_symbol(self):
        self.assertNotIn("d", inv(r"$\int f(x) \, dx$"))


class TestUndefinedSymbols(unittest.TestCase):
    def test_a_symbol_used_before_any_definition_is_reported(self):
        text = (r"We bound $\kappa$ directly. "
                r"Here $\kappa \in \mathbb{R}$ is the condition number.")
        names = [s.symbol for s in SY.undefined_symbols(SY.inventory(text))]
        self.assertIn(r"\kappa", names)

    def test_a_symbol_defined_at_first_use_is_not_reported(self):
        text = r"Let $\kappa \in \mathbb{R}$ be given. Then $\kappa > 0$."
        names = [s.symbol for s in SY.undefined_symbols(SY.inventory(text))]
        self.assertNotIn(r"\kappa", names)


class TestUserSuppliedTable(unittest.TestCase):
    def test_user_domains_override_and_are_marked(self):
        got = SY.apply_user_domains(
            SY.inventory(r"We have $z = w + 1$."), {"z": "positive"})
        z = {s.symbol: s for s in got}["z"]
        self.assertEqual(z.domain_hint, "positive")
        self.assertEqual(z.domain_provenance, "user-supplied")
        self.assertTrue(SY.can_refute(z))


class TestTheZeroInABoundIsTheWholeNumber(unittest.TestCase):
    r"""`\varepsilon \leq 0.006` is not `\varepsilon \leq 0`.

    The bound pattern stopped at the first `0` and read a numeric tolerance as a
    sign constraint. Measured on Bubeck's monograph, the most heavily vetted
    document in the corpus and one this skill had driven to zero findings: it put
    a `MAJOR` back, on a square root, by declaring a positive tolerance
    non-positive. `< 0.5` reading as "negative" is the same shape.
    """

    def test_a_numeric_tolerance_is_not_a_sign_constraint(self):
        got = inv(r"We observe that for $\varepsilon \leq 0.006$ the bound holds.")
        self.assertNotEqual(got[r"\varepsilon"].domain_hint, "nonpositive")

    def test_a_strict_numeric_bound_is_not_negativity(self):
        self.assertNotEqual(inv(r"Assume $\eta < 0.5$ throughout.")["\\eta"].domain_hint,
                            "negative")

    def test_a_real_sign_constraint_still_reads(self):
        self.assertEqual(inv(r"Let $u \ge 0$ be given.")["u"].domain_hint,
                         "nonnegative")
        self.assertEqual(inv(r"Let $v \le 0$ be given.")["v"].domain_hint,
                         "nonpositive")

    def test_a_bound_of_zero_followed_by_prose_still_reads(self):
        self.assertEqual(inv(r"Suppose $w > 0$, so that $\log w$ is defined.")["w"]
                         .domain_hint, "positive")


class TestSubscriptsAreNotTheDeclaredSymbol(unittest.TestCase):
    r"""`y_t \in [0,1]` declares $y$. It says nothing about $t$.

    Measured on a 250-page online-learning monograph, where nearly every quantity
    is subscripted by the round index. The search for `t \in [0,1]` matched
    inside `y_t \in [0,1]`, so $t$ -- an integer index occurring 9147 times --
    was recorded as `unit-interval`, provenance `declared`.

    That is worse than a missing domain. `declared` is a refuting provenance, so
    the tool would have been entitled to evaluate a step at $t = 1/2$ and report
    a counterexample against correct mathematics. Every guard in this module
    exists to prevent exactly that.
    """

    def test_a_declaration_on_a_subscripted_symbol_is_not_read_as_the_subscript(self):
        got = inv(r"An adversary chooses a real number $y_t \in [0,1]$ and the "
                  r"player pays a loss at each round.")
        self.assertEqual(got["t"].domain_provenance, "unknown",
                         "the subscript inherited the declaration meant for $y$")
        self.assertEqual(got["y"].domain_hint, "unit-interval")

    def test_the_subscripted_symbol_itself_still_gets_the_domain(self):
        self.assertEqual(inv(r"Let $x_i \in [0,1]$ for every $i$.")["x"].domain_hint,
                         "unit-interval")

    def test_a_genuine_declaration_of_the_index_still_lands(self):
        got = inv(r"Fix $t \in [0,1]$ and set $z = t a + (1-t) b$.")["t"]
        self.assertEqual(got.domain_hint, "unit-interval")
        self.assertEqual(got.domain_provenance, "declared")

    def test_a_subscript_on_a_greek_symbol_is_not_the_declared_one_either(self):
        self.assertEqual(inv(r"Let $\alpha_t \in [0,1]$ index the combination.")
                         ["t"].domain_provenance, "unknown")

    def test_the_summation_index_inference_still_works(self):
        got = inv(r"$\sum_{t=1}^{T} a_t \le \sum_{t=1}^{T} b_t$")["t"]
        self.assertEqual(got.domain_hint, "natural")
        self.assertEqual(got.domain_provenance, "inferred")


if __name__ == "__main__":
    unittest.main()
