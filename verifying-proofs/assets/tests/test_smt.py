r"""The SMT engine, which is the only one that can *confirm*.

    cd verifying-proofs/assets && python3 -m unittest tests.test_smt -v

Every other engine either refutes or fails to refute. This one asserts the
**negation** of the claim under the stated domains: `unsat` means no
counterexample exists there, which is a proof on the fragment Z3 decides. That
fragment is polynomial real arithmetic; anything with an expectation over an
unspecified measure, an integral or a limit is outside it permanently.

Two defects were found here before the engine was ever pointed at a paper, and
both are the shape this project treats as unrecoverable if it reaches a report.
"""
import unittest, sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))

from proofcheck.engines import smt  # noqa: E402

try:
    import z3
    HAVE_Z3 = True
except ImportError:                                # pragma: no cover
    HAVE_Z3 = False

_NS = {}
exec(compile(smt.HARNESS, "<harness>", "exec"), _NS)
check = _NS.get("check")


@unittest.skipUnless(HAVE_Z3, "z3-solver not installed")
class TestItCanConfirm(unittest.TestCase):
    def test_a_true_bound_on_a_stated_domain_is_confirmed(self):
        g = z3.Real("gamma")
        got = check(1 / (1 - g) > 1, {"gamma": g},
                    {"gamma": "open-unit-interval"}, "s1")
        self.assertEqual(got["outcome"], "confirmed")

    def test_confirmation_names_the_domains_it_relied_on(self):
        """A confirmation is only as good as the domains it was given, so the
        report has to say which ones they were."""
        g = z3.Real("gamma")
        got = check(1 / (1 - g) > 1, {"gamma": g},
                    {"gamma": "open-unit-interval"}, "s1")
        self.assertIn("open-unit-interval", got["detail"])


@unittest.skipUnless(HAVE_Z3, "z3-solver not installed")
class TestItRefutesCleanly(unittest.TestCase):
    def test_a_bound_false_at_an_endpoint_is_refuted(self):
        g = z3.Real("gamma")
        got = check(1 / (1 - g) > 1, {"gamma": g},
                    {"gamma": "unit-interval-half-open"}, "s2")
        self.assertEqual(got["outcome"], "refuted")

    def test_the_counterexample_is_only_the_declared_variables(self):
        r"""Z3's model also carries its interpretation of partial functions --
        `/0 = [(1, 1) -> 1, else -> 0]` for division. A finding that prints that
        reads as a parser artifact, and that costs the reader's trust in the
        finding itself. Same lesson as the `\limits_` case in false-alarms.md."""
        g = z3.Real("gamma")
        got = check(1 / (1 - g) > 1, {"gamma": g},
                    {"gamma": "unit-interval-half-open"}, "s2")
        self.assertEqual(sorted(got["counterexample"]), ["gamma"])
        self.assertNotIn("/0", got["detail"])

    def test_an_auxiliary_the_translation_introduced_is_reported_too(self):
        """Found on Adam, not in a fixture. A translator that needs a second
        gradient entry or a named square root declares a constant that is not a
        DOMAINS name. Printing only the DOMAINS names gave counterexamples whose
        coordinates were incomplete -- `g = 0` on a step refuted by the *other*
        entry -- and a counterexample the reader cannot reproduce is worth no
        more than none at all."""
        g, aux = z3.Real("gamma"), z3.Real("g_2")
        got = check(z3.And(g > 0, aux * aux == 4, aux > 0, aux < 1),
                    {"gamma": g}, {"gamma": "open-unit-interval"}, "s5")
        self.assertEqual(got["outcome"], "refuted")
        self.assertIn("g_2", got["auxiliaries"])
        self.assertIn("g_2", got["detail"])

    def test_the_auxiliaries_are_named_as_the_translation_s_own(self):
        """They are not the paper's symbols and must not read as if they were:
        the paper never stated a domain for them, and the severity ladder rests
        on that distinction."""
        g, aux = z3.Real("gamma"), z3.Real("g_2")
        got = check(z3.And(g > 0, aux * aux == 4, aux > 0, aux < 1),
                    {"gamma": g}, {"gamma": "open-unit-interval"}, "s5")
        self.assertIn("auxiliaries introduced by the translation", got["detail"])
        self.assertNotIn("g_2", got["counterexample"])


@unittest.skipUnless(HAVE_Z3, "z3-solver not installed")
class TestAnUnknownDomainCannotRefute(unittest.TestCase):
    """The rule the whole severity ladder rests on, asserted in the engine.

    With no domain the solver is free to pick the point where the expression is
    undefined, and the answer comes back as a counterexample. `compose_step`
    refuses to turn that into a finding -- but an engine that has to be saved
    downstream is one gate away from a fabricated `CRITICAL`, and the sampling
    engines have always declined on their own. This one now does too.
    """

    def test_an_unstated_domain_yields_unverified_not_refuted(self):
        g = z3.Real("gamma")
        got = check(1 / (1 - g) > 1, {"gamma": g}, {"gamma": None}, "s3")
        self.assertEqual(got["outcome"], "unverified")
        self.assertIsNone(got["counterexample"])

    def test_it_names_the_symbols_to_supply(self):
        """A blocked check that names no symbol cannot be acted on."""
        g, b = z3.Real("gamma"), z3.Real("beta")
        got = check(g > b, {"gamma": g, "beta": b},
                    {"gamma": "positive", "beta": None}, "s4")
        self.assertIn("beta", got["detail"])
        self.assertIn("--symbols", got["detail"])

    def test_one_unstated_domain_blocks_the_whole_step(self):
        """Not a partial answer: a counterexample is a point, and a point needs
        every coordinate to be admissible."""
        g, b = z3.Real("gamma"), z3.Real("beta")
        got = check(g > b, {"gamma": g, "beta": b},
                    {"gamma": "positive", "beta": None}, "s4")
        self.assertEqual(got["outcome"], "unverified")


if __name__ == "__main__":
    unittest.main()
