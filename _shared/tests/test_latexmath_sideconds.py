"""Side conditions a step needs and whether anything establishes them.

This is the highest-value engine in the whole design and it needs no computer
algebra: a step that divides by a quantity nobody proved non-zero is a real gap
whether or not the algebra checks out.

It is also the engine most likely to cry wolf. Every paper ever written divides
by $n$ without saying $n \\neq 0$, and a tool that reports that has just told its
reader to ignore it. The suppression tests below are therefore not edge cases --
they are the feature.
"""
import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from latexmath import sideconds as SC, symbols as SY  # noqa: E402


def conds(math_tex, context=""):
    inv = SY.inventory(context or ("$" + math_tex + "$"))
    return SC.conditions(math_tex, {s.symbol: s for s in inv})


def kinds(cs):
    return sorted({c["kind"] for c in cs})


class TestDenominators(unittest.TestCase):
    def test_a_symbolic_denominator_needs_a_non_zero_condition(self):
        cs = conds(r"\frac{a}{1-\gamma}")
        self.assertIn("nonzero-denominator", kinds(cs))
        self.assertFalse(cs[0]["established"])
        self.assertIn(r"1-\gamma", cs[0]["expr_tex"])

    def test_a_declared_discount_factor_establishes_it(self):
        cs = conds(r"\frac{a}{1-\gamma}",
                   context=r"Let $\gamma \in [0,1)$ be the discount factor. "
                           r"$\frac{a}{1-\gamma}$")
        c = [c for c in cs if c["kind"] == "nonzero-denominator"][0]
        self.assertTrue(c["established"])
        self.assertIn("[0,1)", c["by"])

    def test_a_positive_symbol_establishes_its_own_denominator(self):
        cs = conds(r"\frac{a}{\eta}",
                   context=r"Let $\eta > 0$ be the step size. $\frac{a}{\eta}$")
        c = [c for c in cs if c["kind"] == "nonzero-denominator"][0]
        self.assertTrue(c["established"])

    def test_a_numeric_denominator_never_fires(self):
        self.assertEqual(conds(r"\frac{1}{2} x"), [])

    def test_dividing_by_a_summation_bound_is_suppressed(self):
        """Every paper writes $\\frac{1}{n}\\sum_{i=1}^n$. Reporting it is noise."""
        self.assertEqual(
            conds(r"\frac{1}{n}\sum_{i=1}^n a_i"), [],
            "the standard-practice false alarm that would fire on every paper")

    def test_dividing_by_a_sample_size_alias_is_suppressed(self):
        for v in ("n", "N", "m", "T", "B", "K"):
            self.assertEqual(
                conds(r"\frac{1}{%s}\sum_{i=1}^%s a_i" % (v, v)), [],
                "division by the summation bound %s fired" % v)

    def test_a_genuine_symbolic_denominator_still_fires(self):
        self.assertIn("nonzero-denominator", kinds(conds(r"\frac{a}{b - c}")))


class TestLogarithmsAndRoots(unittest.TestCase):
    def test_log_needs_a_positive_argument(self):
        cs = conds(r"\log u")
        self.assertIn("log-argument-positive", kinds(cs))
        self.assertFalse(cs[0]["established"])

    def test_a_declared_positive_argument_establishes_it(self):
        cs = conds(r"\log u", context=r"Let $u > 0$. $\log u$")
        c = [c for c in cs if c["kind"] == "log-argument-positive"][0]
        self.assertTrue(c["established"])

    def test_log_of_a_probability_density_is_established(self):
        cs = conds(r"\log q",
                   context=r"Let $q$ be a probability density. $\log q$")
        self.assertTrue(
            [c for c in cs if c["kind"] == "log-argument-positive"][0]["established"])

    def test_a_numeric_log_argument_never_fires(self):
        self.assertEqual(conds(r"\log 2"), [])

    def test_square_root_needs_a_non_negative_argument(self):
        self.assertIn("even-root-nonnegative", kinds(conds(r"\sqrt{x - y}")))

    def test_a_square_root_of_a_square_is_suppressed(self):
        self.assertEqual(conds(r"\sqrt{x^2}"), [],
                         "a square is never negative; reporting it is noise")

    def test_a_square_root_of_a_norm_is_suppressed(self):
        self.assertEqual(conds(r"\sqrt{\|x\|^2}"), [])


class TestInverses(unittest.TestCase):
    def test_matrix_inverse_needs_invertibility(self):
        cs = conds(r"A^{-1} b")
        self.assertIn("invertible", kinds(cs))

    def test_a_declared_positive_definite_matrix_establishes_it(self):
        cs = conds(r"A^{-1} b", context=r"Let $A \succ 0$. $A^{-1} b$")
        self.assertTrue([c for c in cs if c["kind"] == "invertible"][0]["established"])

    def test_a_numeric_negative_exponent_is_not_a_matrix_inverse(self):
        self.assertEqual(conds(r"2^{-1}"), [])


class TestInterchange(unittest.TestCase):
    def test_a_limit_crossing_a_sum_needs_justification(self):
        cs = conds(r"\lim_{n \to \infty} \sum_{i=1}^\infty a_i^{(n)}")
        self.assertIn("limit-interchange", kinds(cs))

    def test_a_limit_crossing_an_integral_needs_justification(self):
        self.assertIn("limit-interchange",
                      kinds(conds(r"\lim_{n} \int f_n \, dx")))

    def test_a_finite_sum_inside_a_limit_is_suppressed(self):
        """Interchange with a finite sum is unconditional; only infinite ones bite."""
        self.assertNotIn("limit-interchange",
                         kinds(conds(r"\lim_{t} \sum_{i=1}^n a_i")))

    def test_a_bare_limit_does_not_fire(self):
        self.assertEqual(conds(r"\lim_{n \to \infty} a_n"), [])

    def test_differentiating_under_an_integral_is_flagged(self):
        self.assertIn("differentiate-under-integral",
                      kinds(conds(r"\frac{\partial}{\partial \theta} \int f \, dx")))


class TestMeasuredFalseAlarms(unittest.TestCase):
    """Every case here fired on a real paper (arXiv:1810.02054) and was wrong.

    Before these rules that paper produced 155 unestablished side conditions,
    which is not a report anyone reads -- it is a reason to stop reading.
    """

    def test_lim_does_not_match_the_spacing_command_limits(self):
        """`\\limits` is a spacing directive. 10 of 10 interchange hits came from it."""
        cs = conds(r"\sum\limits_{i=1}^n a_i")
        self.assertNotIn("limit-interchange", kinds(cs))

    def test_a_real_liminf_still_counts_as_a_limit(self):
        self.assertIn("limit-interchange",
                      kinds(conds(r"\liminf_{n} \int f_n \, dx")))

    def test_the_reported_expression_does_not_start_with_a_spacing_command(self):
        """`\\lim\\limits_{r\\to 0+}` is the common idiom, and a finding whose
        quoted expression opens with `\\limits_` reads as a parser artifact --
        which costs the reader's trust in the finding itself."""
        cs = conds(r"\lim\limits_{r \to 0+} \frac{1}{\mu(B)} \int_{B} f")
        c = [c for c in cs if c["kind"] == "limit-interchange"][0]
        self.assertFalse(c["expr_tex"].lstrip().startswith(r"\limits"))
        self.assertIn(r"\int", c["expr_tex"])

    def test_log_of_a_delimited_group_reads_the_group_not_the_delimiter(self):
        """`\\log\\left(x\\right)` reported its argument as `\\left`."""
        cs = conds(r"\log\left(\frac{a}{b}\right)")
        args = [c["expr_tex"] for c in cs if c["kind"] == "log-argument-positive"]
        for a in args:
            self.assertNotIn(r"\left", a)

    def test_square_root_of_a_numeric_constant_is_suppressed(self):
        for r in (r"\sqrt{2\pi}", r"\sqrt{2}", r"\sqrt{\pi}", r"\sqrt{2 \pi n}"):
            self.assertEqual(conds(r), [], "%s should not fire" % r)

    def test_square_root_of_a_count_is_suppressed(self):
        """$\\sqrt{m}$ over a sample size is not an unguarded even root."""
        for v in ("m", "n", "N", "T", "d", "B", "K"):
            self.assertEqual(conds(r"\sqrt{%s}" % v), [],
                             r"\sqrt{%s} should not fire" % v)

    def test_a_genuinely_signed_radicand_still_fires(self):
        self.assertIn("even-root-nonnegative", kinds(conds(r"\sqrt{x - y}")))

    def test_repeated_conditions_within_a_step_are_reported_once(self):
        cs = conds(r"\frac{a}{\mu(B)} + \frac{c}{\mu(B)}")
        self.assertEqual(len([c for c in cs if c["kind"] == "nonzero-denominator"]),
                         1, "the same obligation stated twice is one obligation")


class TestThreeWayStatus(unittest.TestCase):
    """Measured: 84, 98 and 97 side conditions on three real papers, 100% of them
    "unestablished". That is not a report -- it is a reason to stop reading.

    The cause is the same one the whole severity ladder rests on: 54 of 61 symbols
    in one paper have an unknown domain. If the tool could not read the domain, it
    cannot claim the licence is missing either. So there are three states, and
    only `unstated` -- domain known, and it does not discharge -- is a finding.
    """

    def test_a_discharging_domain_is_established(self):
        cs = conds(r"\frac{a}{\eta}",
                   context=r"Let $\eta > 0$ be the step size. $\frac{a}{\eta}$")
        self.assertEqual(cs[0]["status"], "established")

    def test_a_known_but_non_discharging_domain_is_a_finding(self):
        cs = conds(r"\frac{a}{t}", context=r"Let $t \in \mathbb{R}$. $\frac{a}{t}$")
        c = [c for c in cs if c["kind"] == "nonzero-denominator"][0]
        self.assertEqual(c["status"], "unstated")
        self.assertFalse(c["established"])

    def test_an_unknown_domain_is_undetermined_not_an_accusation(self):
        cs = conds(r"\frac{a}{w}")
        c = [c for c in cs if c["kind"] == "nonzero-denominator"][0]
        self.assertEqual(c["status"], "undetermined")
        self.assertFalse(c["established"])

    def test_only_unstated_conditions_are_reportable(self):
        known = conds(r"\frac{a}{t}", context=r"Let $t \in \mathbb{R}$. $\frac{a}{t}$")
        unknown = conds(r"\frac{a}{w}")
        self.assertEqual(len(SC.findings(known)), 1)
        self.assertEqual(SC.findings(unknown), [],
                         "an unreadable domain is a gap to state, not a defect to allege")

    def test_undetermined_conditions_are_still_carried_for_the_report(self):
        self.assertEqual(len(SC.undetermined(conds(r"\frac{a}{w}"))), 1)

    def test_a_lone_count_denominator_is_suppressed_outright(self):
        """$\\frac{1}{m}$ with no sum in sight is still averaging. Every paper."""
        for v in ("n", "m", "N", "T", "B", "K"):
            self.assertEqual(conds(r"\frac{1}{%s} x" % v), [],
                             r"\frac{1}{%s} fired" % v)


class TestMeasuredOnFlawedPaperCorpus(unittest.TestCase):
    """Both classes fired on every optimization paper in the evaluation corpus
    (arXiv:1412.6980v8, 1509.01240, 2003.04706), against correct mathematics.
    """

    def test_a_summation_index_discharges_its_own_root_and_denominator(self):
        """`\\sum_{t=1}^{T} 1/\\sqrt{t}` is universal in optimization papers.

        The paper *did* state the range of $t$ -- it is the index of the sum. A
        rule that inferred domains never discharge anything turns every learning
        rate of the form $\\alpha/\\sqrt{t}$ into a MAJOR.
        """
        for tex in (r"\sum_{t=1}^{T} \frac{\|g_t\|}{\sqrt{t}}",
                    r"\sum_{t=1}^{T} \frac{1}{t} a_t",
                    r"\prod_{s=t+1}^{T} \frac{1}{s}"):
            cs = conds(tex)
            self.assertTrue(all(c["status"] == "established" for c in cs),
                            "%s left an obligation open: %s"
                            % (tex, [(c["kind"], c["status"]) for c in cs]))
            self.assertEqual(SC.findings(cs), [], "%s produced a MAJOR" % tex)

    def test_a_free_symbol_still_fires(self):
        """The discharge is about *indices*, not about single letters."""
        self.assertIn("even-root-nonnegative", kinds(conds(r"\sqrt{u}")))
        self.assertIn("nonzero-denominator", kinds(conds(r"\frac{a}{u - v}")))

    def test_an_uppercase_letter_is_still_treated_as_a_matrix(self):
        self.assertIn("invertible", kinds(conds(r"A^{-1} b")))

    def test_a_scalar_reciprocal_is_a_nonzero_condition_not_invertibility(self):
        """`(\\rho^{-1}/2)\\|b\\|^2` asks for $\\rho \\ne 0$, not for a matrix inverse."""
        cs = conds(r"(\rho/2)\|a\|^2 + (\rho^{-1}/2)\|b\|^2")
        self.assertIn("nonzero-denominator", kinds(cs))
        self.assertNotIn("invertible", kinds(cs))

    def test_a_declared_matrix_still_needs_invertibility(self):
        cs = conds(r"A^{-1} b", context=r"Let $A \succ 0$. $A^{-1} b$")
        self.assertIn("invertible", kinds(cs))

    def test_an_inference_never_discharges_the_obligation_it_created(self):
        """`A^{-1}` infers invertibility; that inference cannot license itself."""
        cs = conds(r"A^{-1} b")
        inv = [c for c in cs if c["kind"] in ("invertible", "nonzero-denominator")]
        self.assertTrue(inv)
        self.assertFalse(inv[0]["established"],
                         "the tool discharged an obligation using its own guess "
                         "about that same obligation")


class TestDifferentiationUnderIntegral(unittest.TestCase):
    """Measured on arXiv:1405.4980 (Bubeck), 3 MAJORs on one identity.

    `\\nabla f(x_k) = \\int_0^1 \\nabla^2 f(\\cdot)(x_k - x^*) ds` is Taylor with
    integral remainder. Nothing is interchanged: the gradient is a term on the
    left and the integral is a term on the right. The rule fired because a
    derivative token appeared *anywhere* before an integral token.
    """

    def test_a_gradient_beside_an_integral_is_not_an_interchange(self):
        for tex in (r"\nabla f(x) = \int_0^1 \nabla^2 f(x^* + s d)\, d\,ds",
                    r"= x - x^* - [\nabla^2 f(x)]^{-1} \int_0^1 \nabla^2 f(u)\,ds",
                    r"\nabla g = \int_0^1 h(s)\,ds + \nabla r"):
            self.assertNotIn("differentiate-under-integral", kinds(conds(tex)),
                             "fired on %s" % tex)

    def test_a_derivative_applied_to_an_integral_still_fires(self):
        for tex in (r"\frac{\partial}{\partial \theta} \int f(x,\theta)\,dx",
                    r"\nabla_\theta \int f(x,\theta)\,dx",
                    r"\frac{d}{dt}\int_0^1 g(t,s)\,ds"):
            self.assertIn("differentiate-under-integral", kinds(conds(tex)),
                          "missed %s" % tex)

    def test_an_integral_with_no_derivative_never_fires(self):
        self.assertNotIn("differentiate-under-integral",
                         kinds(conds(r"\int_0^1 f(s)\,ds")))


class TestReporting(unittest.TestCase):
    def test_each_condition_carries_the_expression_it_is_about(self):
        for c in conds(r"\frac{a}{b} + \log v"):
            self.assertTrue(c["expr_tex"], "a condition with no expression is unusable")

    def test_established_conditions_name_their_evidence(self):
        cs = conds(r"\log u", context=r"Let $u > 0$. $\log u$")
        c = [c for c in cs if c["established"]][0]
        self.assertTrue(c["by"])


class TestNaturalMeansAtLeastOne(unittest.TestCase):
    r"""The three parts of this codebase must agree about $\mathbb{N}$.

    `smt.py` asserts `var >= 1` for a natural and `rational.py` samples one from
    $2, 3, 5, \dots$; this table alone treated it as possibly zero. The
    disagreement was silent and it fired: on a 250-page online-learning monograph
    every $1/t$ and $\ln t$ appearing outside a summation reported that nothing
    established $t$ as admissible, about a round index the paper had bounded
    below by 1 in the summation that introduced it.

    Erring this way costs a missed obligation rather than a false alarm, which is
    the right direction for a tool whose measured problem is firing only on
    sound papers.
    """

    def test_a_round_index_in_a_denominator_is_established(self):
        cs = conds(r"\frac{1}{t}",
                   context=r"$\sum_{t=1}^{T} a_t$ and later $\frac{1}{t}$")
        c = [c for c in cs if c["kind"] == "nonzero-denominator"][0]
        self.assertTrue(c["established"],
                        "a summation index bounded below by 1 is not zero")

    def test_a_logarithm_of_a_round_index_is_established(self):
        cs = conds(r"\ln t",
                   context=r"$\sum_{t=1}^{T} a_t$ and separately $\ln t$")
        c = [c for c in cs if c["kind"] == "log-argument-positive"][0]
        self.assertTrue(c["established"])

    def test_an_open_unit_interval_denominator_is_established(self):
        """$(0,1)$ excludes zero by construction. It was in the positive set and
        not the non-zero one, so scoping a proof's own `\\alpha \\in (0,1)` to the
        step that divides by it changed nothing until this was fixed."""
        cs = conds(r"\frac{1}{\alpha}",
                   context=r"For any $\alpha \in (0,1)$, $\frac{1}{\alpha}$")
        c = [c for c in cs if c["kind"] == "nonzero-denominator"][0]
        self.assertTrue(c["established"])

    def test_a_half_open_interval_containing_zero_is_not_established(self):
        """$[0,1)$ does contain zero, and the distinction is the whole point."""
        cs = conds(r"\frac{1}{\gamma}",
                   context=r"Let $\gamma \in [0,1)$. Then $\frac{1}{\gamma}$")
        c = [c for c in cs if c["kind"] == "nonzero-denominator"][0]
        self.assertFalse(c["established"])

    def test_an_unknown_symbol_in_a_denominator_is_still_reported(self):
        c = [c for c in conds(r"\frac{1}{w}")
             if c["kind"] == "nonzero-denominator"][0]
        self.assertFalse(c["established"],
                         "the suppression must not generalise past naturals")


class TestTheDefinitionOfAnImproperIntegralIsNotAnInterchange(unittest.TestCase):
    r"""`\int_0^\infty f = \lim_{L} \int_0^L f` interchanges nothing.

    It is the definition, and `\lim_N \sum_{i=1}^N` is the same shape for a
    series. Measured on Tropp's matrix-concentration monograph. A finding here
    tells the reader the tool has not understood the line, which costs more than
    the finding is worth.

    The test is whether the limit variable **is a bound of the operator**.
    Requiring it in the integrand instead was tried and was wrong: in
    `\lim_{r \to 0} \frac{1}{\mu(B)} \int_B f` the radius enters only through
    the set $B$, and that is a real interchange -- four of them on
    arXiv:1810.02054, silently dropped by the stricter rule.
    """

    def test_an_improper_integral_written_as_its_definition_is_silent(self):
        self.assertNotIn("limit-interchange", kinds(conds(
            r"\int_0^\infty f(u) \, du = \lim_{L\to \infty} \int_0^L f(u) \, du")))

    def test_a_series_written_as_its_definition_is_silent(self):
        self.assertNotIn("limit-interchange",
                         kinds(conds(r"\lim_{N\to\infty} \sum_{i=1}^N a_i")))

    def test_a_limit_entering_through_a_set_still_fires(self):
        self.assertIn("limit-interchange", kinds(conds(
            r"\lim\limits_{r \to 0+} \frac{1}{\mu(B)} \int_{B} f")))

    def test_a_shrinking_domain_of_integration_still_fires(self):
        """The form the four real interchanges on arXiv:1810.02054 are written
        in. The limit variable is *inside* the bound, not the whole of it: a
        shrinking domain is an argument, an endpoint running to infinity is a
        definition. Suppressing on "appears in the bound" dropped all four."""
        self.assertIn("limit-interchange", kinds(conds(
            r"\lim\limits_{r\rightarrow 0+}\frac{1}{\mu(B_r^+)}"
            r"\int_{B_r^+}\phi(x_j)(w)dw")))

    def test_a_limit_over_the_integrand_still_fires(self):
        self.assertIn("limit-interchange",
                      kinds(conds(r"\lim_{n} \int f_n \, dx")))

    def test_an_unreadable_limit_variable_still_fires(self):
        """Silence must not be bought with a parse failure."""
        self.assertIn("limit-interchange",
                      kinds(conds(r"\lim \int f_n \, dx")))


class TestTheBaseOfANegativeExponentCarriesItsSubscript(unittest.TestCase):
    r"""`H_u^{-1/2}` inverts $H_u$. It says nothing about $u$.

    The base pattern stopped at the letter adjacent to the caret, so the finding
    read "needs $u$ to be non-zero" about an index -- measured on Tropp, where
    the quantity being inverted was a positive-definite matrix. Same family as
    the subscript confusion in the symbol inventory.
    """

    def test_the_subscript_is_not_the_thing_being_inverted(self):
        got = conds(r"H_u^{-1/2} A H_u^{-1/2}")
        self.assertTrue(got)
        for c in got:
            self.assertNotEqual(c["expr_tex"], "u")

    def test_a_matrix_inverse_is_still_reported_against_the_matrix(self):
        got = conds(r"A^{-1} b")
        self.assertIn("invertible", kinds(got))
        self.assertEqual(got[0]["expr_tex"], "A")

    def test_a_wrapped_base_keeps_its_wrapper(self):
        """`\\bm{H}_u^{-1/2}` is how the real paper writes it, and matching bare
        letters made the base `u` again even after the subscript was handled."""
        got = conds(r"\bm{0} \prec \bm{H}_u^{-1/2} \bm{A}_u \bm{H}_u^{-1/2}")
        self.assertTrue(got)
        for c in got:
            self.assertNotEqual(c["expr_tex"], "u")

    def test_a_scalar_negative_exponent_still_asks_for_non_vanishing(self):
        self.assertIn("nonzero-denominator", kinds(conds(r"\rho^{-1} g")))


if __name__ == "__main__":
    unittest.main()
