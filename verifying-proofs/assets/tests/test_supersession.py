r"""`LOCAL`: a refutation that was not observed to travel.

    cd verifying-proofs/assets && python3 -m unittest tests.test_supersession -v

Stage 1 of the correctness-verification work produced two `CRITICAL`s on papers
that are in the benchmark precisely because they are believed correct. Both were
real -- checked by hand, refuted by two independent translations, `faithful`
both times -- and neither touched the result:

- a line printed with `\lambda T` where the algebra gives `\lambda^T`, on a row
  whose successor holds under either reading and was confirmed;
- a stated sufficient condition looser than the inequality it licenses, on a
  standalone display with nothing after it.

Reported as `CRITICAL` they read as "this theorem is wrong", which the evidence
does not support. Reported as nothing at all they would be suppressed, which is
worse. `LOCAL` is the rung between, and this file pins how narrow it is.

**The one property that must not break:** an unchecked later row is not a
confirmation. Every genuine finding this pipeline has produced sits on the last
row of a chain or outside a chain entirely, so the rule cannot reach them today
-- but the way it would start reaching them is by treating silence as
supersession.
"""
import unittest, sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))

from proofcheck import compose as C  # noqa: E402


def row(n, row_no, of_rows, proof="proof/t"):
    return {"id": "%s/s%02d" % (proof, n), "proof_id": proof, "ordinal": n,
            "kind": "chain-row", "checkable": "candidate",
            "chain": {"row": row_no, "of_rows": of_rows, "carried": False,
                      "label": None, "numbered": False, "anchor_tex": ""},
            "symbols_used": [], "opacity_reasons": [], "side_conditions": []}


def loose(n, proof="proof/t"):
    """A step outside any chain: both counters are None."""
    s = row(n, None, None, proof)
    s["chain"] = {"row": None, "of_rows": None, "carried": False,
                  "label": None, "numbered": False, "anchor_tex": ""}
    return s


def verdict(step, severity, confirmed=False):
    return {"step": step["id"], "proof": step["proof_id"], "severity": severity,
            "detail": "counterexample at x = 1/16", "confirmed": confirmed,
            "counterexample": {"x": "1/16"}}


class TestTheShapeThatIsDemoted(unittest.TestCase):
    """`1804.10587` theorem:Main_Theorem/s51, row 6 of 7, s52 confirmed."""

    def setUp(self):
        self.steps = [row(51, 6, 7), row(52, 7, 7)]
        self.verdicts = [verdict(self.steps[0], "CRITICAL"),
                         verdict(self.steps[1], "SKIP", confirmed=True)]

    def test_a_refuted_row_whose_successor_is_confirmed_becomes_local(self):
        self.assertEqual(C.apply_supersession(self.verdicts, self.steps), 1)
        self.assertEqual(self.verdicts[0]["severity"], "LOCAL")

    def test_it_names_the_rows_that_superseded_it(self):
        """A demotion a reader cannot check is a demotion they must take on
        trust, which is the thing this project refuses everywhere else."""
        C.apply_supersession(self.verdicts, self.steps)
        self.assertEqual(self.verdicts[0]["superseded_by"], ["proof/t/s52"])
        self.assertIn("s52", self.verdicts[0]["detail"])

    def test_the_counterexample_survives_the_demotion(self):
        """Demoted is not withdrawn. The step is still refuted and the witness
        still reproduces."""
        C.apply_supersession(self.verdicts, self.steps)
        self.assertEqual(self.verdicts[0]["counterexample"], {"x": "1/16"})
        self.assertIn("counterexample at x = 1/16", self.verdicts[0]["detail"])

    def test_the_detail_refuses_to_claim_the_chain_now_holds(self):
        """A broken link is still broken; confirming the links after it does not
        repair the chain, and the report must not imply that it does."""
        C.apply_supersession(self.verdicts, self.steps)
        self.assertIn("not thereby established", self.verdicts[0]["detail"])


class TestTheShapesThatAreNot(unittest.TestCase):
    def test_a_refutation_on_the_last_row_stays_critical(self):
        r"""`1905.10936` lemma:error_bound/s11 is row 7 of 7 -- the chain's own
        conclusion failing. Nothing can supersede it, by construction. This is
        the real finding on that paper and the rule must not reach it."""
        steps = [row(11, 7, 7)]
        v = [verdict(steps[0], "CRITICAL")]
        self.assertEqual(C.apply_supersession(v, steps), 0)
        self.assertEqual(v[0]["severity"], "CRITICAL")

    def test_a_refutation_outside_any_chain_stays_critical(self):
        r"""`1405.4980` th:V1/s16 -- a standalone display, `row` and `of_rows`
        both None. `None == None` would read as "last row" under a careless
        comparison; it means "not a chain row at all"."""
        steps = [loose(16)]
        v = [verdict(steps[0], "CRITICAL")]
        self.assertEqual(C.apply_supersession(v, steps), 0)
        self.assertEqual(v[0]["severity"], "CRITICAL")

    def test_an_unchecked_later_row_is_not_a_confirmation(self):
        """The safety property. Silence is not supersession."""
        steps = [row(51, 6, 7), row(52, 7, 7)]
        v = [verdict(steps[0], "CRITICAL"),
             verdict(steps[1], "UNVERIFIED")]
        self.assertEqual(C.apply_supersession(v, steps), 0)
        self.assertEqual(v[0]["severity"], "CRITICAL")

    def test_a_later_row_only_not_refuted_is_not_a_confirmation(self):
        """`WEAK` means sampled, which is evidence and not proof. It cannot
        carry a demotion any more than it can carry a finding."""
        steps = [row(51, 6, 7), row(52, 7, 7)]
        v = [verdict(steps[0], "CRITICAL"), verdict(steps[1], "WEAK")]
        self.assertEqual(C.apply_supersession(v, steps), 0)

    def test_every_later_row_must_be_confirmed_not_just_the_next_one(self):
        steps = [row(1, 1, 3), row(2, 2, 3), row(3, 3, 3)]
        v = [verdict(steps[0], "CRITICAL"),
             verdict(steps[1], "SKIP", confirmed=True),
             verdict(steps[2], "UNVERIFIED")]
        self.assertEqual(C.apply_supersession(v, steps), 0)
        self.assertEqual(v[0]["severity"], "CRITICAL")

    def test_a_severity_that_is_not_critical_is_left_alone(self):
        """`WEAK` from a non-faithful translation must not be promoted into a
        rung that sounds more definite than it is."""
        steps = [row(51, 6, 7), row(52, 7, 7)]
        v = [verdict(steps[0], "WEAK"), verdict(steps[1], "SKIP", confirmed=True)]
        C.apply_supersession(v, steps)
        self.assertEqual(v[0]["severity"], "WEAK")


class TestChainMembership(unittest.TestCase):
    r"""Two rows can both read `7/7` and belong to different chains -- which is
    what `lemma:error_bound` in `1905.10936` actually does. There is no chain id
    in the ledger, so membership is the run of consecutive increasing rows."""

    def test_a_restarted_counter_begins_a_new_chain(self):
        steps = [row(1, 1, 2), row(2, 2, 2), row(3, 1, 2), row(4, 2, 2)]
        self.assertEqual([s["id"] for s in C.chain_rows_after(steps[0], steps)],
                         ["proof/t/s02"])

    def test_two_rows_reading_the_same_position_are_not_the_same_chain(self):
        steps = [row(11, 7, 7), row(12, 7, 7)]
        self.assertEqual(C.chain_rows_after(steps[0], steps), [])

    def test_a_chain_does_not_run_past_a_non_chain_step(self):
        steps = [row(1, 1, 3), loose(2), row(3, 3, 3)]
        self.assertEqual(C.chain_rows_after(steps[0], steps), [])

    def test_a_chain_does_not_cross_into_another_proof(self):
        steps = [row(1, 1, 2, proof="proof/a"), row(2, 2, 2, proof="proof/b")]
        self.assertEqual(C.chain_rows_after(steps[0], steps), [])

    def test_the_last_row_has_nothing_after_it(self):
        steps = [row(1, 1, 2), row(2, 2, 2)]
        self.assertEqual(C.chain_rows_after(steps[1], steps), [])


if __name__ == "__main__":
    unittest.main()
