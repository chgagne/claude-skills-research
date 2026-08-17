"""The severity ladder, and the rules that keep it from crying wolf.

Three assertions here are the whole design:

- an unknown domain can never produce a refutation
- a non-`faithful` translation caps severity at WEAK
- engines that disagree yield UNVERIFIED, never CRITICAL

Everything else is bookkeeping. If those three break, the tool starts reporting
its own bugs as the paper's mistakes.
"""
import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))

from proofcheck import compose as C  # noqa: E402


def step(**kw):
    base = {"id": "proof/t/s01", "proof_id": "proof/t", "ordinal": 1,
            "kind": "chain-row", "checkable": "candidate", "opacity_reasons": [],
            "side_conditions": [], "symbols_used": [], "math_tex": "a = b",
            "prose_tex": "", "case_path": [], "claim_forms": [],
            "justification": {"kind": "none", "name": None, "refs": [],
                              "cites": [], "hedges": []},
            "content_hash": "h", "source": {"file": "main.tex", "offset": 0}}
    base.update(kw)
    return base


def ledger(**kw):
    base = {"schema": "latexmath-ledger/1", "claims": [], "proofs": [],
            "steps": [], "symbols": [], "equations": [],
            "refs": {"labels": {}, "edges": [], "dangling": [],
                     "unused_labels": [], "forward_refs": [], "cycles": []},
            "coverage": {"steps": 0, "inference_steps": 0}, "diagnostics": [],
            "macros_unexpandable": []}
    base.update(kw)
    return base


class TestSeverityOrder(unittest.TestCase):
    def test_the_ladder_is_ordered_as_the_siblings_order_it(self):
        self.assertEqual(list(C.SEVERITIES),
                         ["CRITICAL", "MAJOR", "LOCAL", "MINOR", "WEAK",
                          "UNVERIFIED", "SKIP"])

    def test_local_sits_below_major_and_above_minor(self):
        """A refutation that did not travel is less serious than a theorem left
        unproved, and more serious than something that merely impedes reading."""
        order = list(C.SEVERITIES)
        self.assertLess(order.index("MAJOR"), order.index("LOCAL"))
        self.assertLess(order.index("LOCAL"), order.index("MINOR"))

    def test_unverified_is_not_a_pass(self):
        self.assertFalse(C.is_pass("UNVERIFIED"))
        self.assertFalse(C.is_pass("WEAK"))

    def test_local_is_not_a_pass_either(self):
        self.assertFalse(C.is_pass("LOCAL"))

    def test_local_does_not_claim_the_result_is_safe(self):
        """The label is a statement about reach, and the failure mode to avoid
        is a reader taking it as a clean bill for the theorem."""
        self.assertIn("does not say the result", C.SEVERITY_BLURB["LOCAL"])


class TestStructuralFindings(unittest.TestCase):
    def test_induction_with_no_base_case_is_critical(self):
        led = ledger(claims=[{"id": "claim/t1", "kind": "theorem", "label": "t1",
                              "hypotheses_diff": [], "duplicate_of": None,
                              "source": {"start": 0, "end": 1}}],
                     proofs=[{"id": "proof/t1", "claim_id": "claim/t1",
                              "attachment": "adjacent", "body_tex": "",
                              "structure": {"is_induction": True,
                                            "base_case": {"verdict": "not-found",
                                                          "variable": "n",
                                                          "evidence": "x"},
                                            "cases": [], "hedges": [],
                                            "qed_present": True},
                              "source": {"start": 0, "end": 1}}])
        f = C.structural_findings(led)
        self.assertEqual([x["severity"] for x in f if x["kind"] == "induction-no-base-case"],
                         ["CRITICAL"])

    def test_an_unknown_base_case_verdict_is_never_critical(self):
        """Measured: 4 of 4 NTK inductions. `unknown` means look, not accuse."""
        led = ledger(proofs=[{"id": "proof/t1", "claim_id": "claim/t1",
                              "attachment": "adjacent", "body_tex": "",
                              "structure": {"is_induction": True,
                                            "base_case": {"verdict": "unknown",
                                                          "variable": None,
                                                          "evidence": ""},
                                            "cases": [], "hedges": [],
                                            "qed_present": True},
                              "source": {"start": 0, "end": 1}}])
        f = C.structural_findings(led)
        self.assertNotIn("CRITICAL", [x["severity"] for x in f])
        self.assertIn("induction-base-case-unclear", [x["kind"] for x in f])

    def test_a_claim_cycle_is_critical(self):
        led = ledger()
        led["refs"]["cycles"] = [["claim/a", "claim/b", "claim/a"]]
        f = C.structural_findings(led)
        self.assertEqual([x["severity"] for x in f if x["kind"] == "claim-cycle"],
                         ["CRITICAL"])

    def test_hypothesis_drift_in_a_restatement_is_major(self):
        led = ledger(claims=[{"id": "claim/t1r", "kind": "theorem", "label": "t1r",
                              "duplicate_of": "claim/t1",
                              "hypotheses_diff": ["-let $f$ be bounded"],
                              "source": {"start": 0, "end": 1}}])
        f = C.structural_findings(led)
        self.assertEqual([x["severity"] for x in f
                          if x["kind"] == "restatement-hypothesis-drift"], ["MAJOR"])

    def test_a_dangling_reference_is_minor(self):
        led = ledger()
        led["refs"]["dangling"] = [{"from": "proof/t1", "label": "eq:ghost",
                                    "cmd": "eqref"}]
        f = C.structural_findings(led)
        self.assertEqual([x["severity"] for x in f if x["kind"] == "dangling-ref"],
                         ["MINOR"])

    def test_an_orphan_proof_is_minor_and_named(self):
        led = ledger(diagnostics=[{"code": "orphan-proof", "severity": "warn",
                                   "message": "m", "source": None}])
        self.assertIn("orphan-proof", [x["kind"] for x in C.structural_findings(led)])


class TestSideConditionSeverity(unittest.TestCase):
    def test_an_unstated_side_condition_is_major(self):
        led = ledger(steps=[step(side_conditions=[
            {"kind": "nonzero-denominator", "expr_tex": "t", "status": "unstated",
             "established": False, "by": None}])])
        f = C.structural_findings(led)
        self.assertEqual([x["severity"] for x in f
                          if x["kind"] == "side-condition-unstated"], ["MAJOR"])

    def test_an_undetermined_side_condition_is_never_major(self):
        """84 of 94 on a real paper. Alleging these is how a report dies."""
        led = ledger(steps=[step(side_conditions=[
            {"kind": "nonzero-denominator", "expr_tex": "w",
             "status": "undetermined", "established": False, "by": None}])])
        f = C.structural_findings(led)
        sev = [x["severity"] for x in f if "side-condition" in x["kind"]]
        self.assertEqual(sev, ["UNVERIFIED"])

    def test_an_established_side_condition_produces_nothing(self):
        led = ledger(steps=[step(side_conditions=[
            {"kind": "nonzero-denominator", "expr_tex": "e", "status": "established",
             "established": True, "by": "$e > 0$"}])])
        self.assertEqual([x for x in C.structural_findings(led)
                          if "side-condition" in x["kind"]], [])

    def test_the_same_obligation_across_steps_is_reported_once_per_proof(self):
        sc = {"kind": "nonzero-denominator", "expr_tex": r"\mu(B)",
              "status": "unstated", "established": False, "by": None}
        led = ledger(steps=[step(id="proof/t/s01", side_conditions=[sc]),
                            step(id="proof/t/s02", ordinal=2, side_conditions=[sc]),
                            step(id="proof/t/s03", ordinal=3, side_conditions=[sc])])
        f = [x for x in C.structural_findings(led)
             if x["kind"] == "side-condition-unstated"]
        self.assertEqual(len(f), 1, "one obligation, not one per row")


class TestHedges(unittest.TestCase):
    def test_a_hedge_on_an_opaque_step_is_minor(self):
        led = ledger(steps=[step(
            checkable="opaque", opacity_reasons=["asymptotic"],
            justification={"kind": "none", "name": None, "refs": [], "cites": [],
                           "hedges": ["clearly"]})])
        f = C.structural_findings(led)
        self.assertEqual([x["severity"] for x in f if x["kind"] == "hedged-step"],
                         ["MINOR"])

    def test_a_hedge_on_a_step_that_checks_out_is_not_reported(self):
        led = ledger(steps=[step(
            justification={"kind": "named-result", "name": "jensen", "refs": [],
                           "cites": [], "hedges": ["clearly"]})])
        self.assertEqual([x for x in C.structural_findings(led)
                          if x["kind"] == "hedged-step"], [])


class TestEngineComposition(unittest.TestCase):
    def test_a_faithful_refutation_inside_a_declared_domain_is_critical(self):
        v = C.compose_step(step(), [
            {"engine": "rational", "outcome": "refuted",
             "translation_confidence": "faithful",
             "counterexample": {"x": "7/3"}, "detail": "lhs != rhs"}],
            domains_known=True)
        self.assertEqual(v["severity"], "CRITICAL")

    def test_an_unknown_domain_can_never_refute(self):
        """The rule is about the *claim*, not the loudness.

        A failed check on unstated domains is surfaced -- see
        TestSuppressedRefutation -- but it may never be reported as a
        counterexample, because the failing point may lie outside what the paper
        meant.
        """
        v = C.compose_step(step(), [
            {"engine": "rational", "outcome": "refuted",
             "translation_confidence": "faithful",
             "counterexample": {"x": "-11/5"}, "detail": "lhs != rhs"}],
            domains_known=False)
        self.assertNotEqual(v["severity"], "CRITICAL")
        self.assertIsNone(v["counterexample"])
        self.assertIn("domain", v["detail"].lower())

    def test_an_approximate_translation_caps_at_weak(self):
        v = C.compose_step(step(), [
            {"engine": "symbolic", "outcome": "refuted",
             "translation_confidence": "approximate", "detail": "d"}],
            domains_known=True)
        self.assertEqual(v["severity"], "WEAK")

    def test_a_partial_translation_caps_at_weak(self):
        v = C.compose_step(step(), [
            {"engine": "rational", "outcome": "refuted",
             "translation_confidence": "partial", "detail": "d"}],
            domains_known=True)
        self.assertEqual(v["severity"], "WEAK")

    def test_disagreement_resolves_to_unverified_never_critical(self):
        v = C.compose_step(step(), [
            {"engine": "rational", "outcome": "refuted",
             "translation_confidence": "faithful", "detail": "d"},
            {"engine": "symbolic", "outcome": "confirmed",
             "translation_confidence": "faithful", "detail": "d"}],
            domains_known=True)
        self.assertEqual(v["severity"], "UNVERIFIED")
        self.assertIn("disagree", v["detail"].lower())

    def test_only_symbolic_may_confirm_an_equality(self):
        v = C.compose_step(step(), [
            {"engine": "rational", "outcome": "not-refuted",
             "translation_confidence": "faithful", "trials": 24, "detail": "d"}],
            domains_known=True)
        self.assertEqual(v["severity"], "WEAK")
        self.assertNotIn("verified", v["detail"].lower())

    def test_a_symbolic_confirmation_is_a_pass(self):
        v = C.compose_step(step(), [
            {"engine": "symbolic", "outcome": "confirmed",
             "translation_confidence": "faithful", "detail": "simplify -> 0"}],
            domains_known=True)
        self.assertEqual(v["severity"], "SKIP")
        self.assertTrue(v["confirmed"])

    def test_a_timeout_is_unverified_not_a_refutation(self):
        v = C.compose_step(step(), [
            {"engine": "symbolic", "outcome": "unverified",
             "detail": "timeout after 10s"}], domains_known=True)
        self.assertEqual(v["severity"], "UNVERIFIED")

    def test_a_structural_step_is_skipped(self):
        v = C.compose_step(step(kind="narration", checkable="structural"), [],
                           domains_known=True)
        self.assertEqual(v["severity"], "SKIP")

    def test_an_opaque_step_with_no_results_is_unverified_with_its_reason(self):
        v = C.compose_step(step(checkable="opaque",
                                opacity_reasons=["asymptotic"]), [],
                           domains_known=True)
        self.assertEqual(v["severity"], "UNVERIFIED")
        self.assertIn("asymptotic", v["detail"])

    def test_a_candidate_with_no_results_is_unverified_not_a_pass(self):
        v = C.compose_step(step(), [], domains_known=True)
        self.assertEqual(v["severity"], "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()


class TestSymbolicInequalities(unittest.TestCase):
    """Measured gap: the symbolic engine declined every inequality.

    With Z3 absent that made inequalities unreachable -- and inequalities are most
    of what optimization papers prove, which is why three papers with documented
    proof errors produced no findings at all in the first evaluation run.
    """

    def setUp(self):
        from proofcheck.engines import symbolic
        self.H = {}
        exec(compile(symbolic.HARNESS, "<h>", "exec"), self.H)

    def test_a_false_concrete_inequality_is_refuted(self):
        sympy = self.H["sympy"]
        r = self.H["check"](sympy.Integer(3), sympy.Integer(2), r"\le", [], [], "s")
        self.assertEqual(r["outcome"], "refuted")

    def test_a_true_concrete_inequality_is_confirmed(self):
        sympy = self.H["sympy"]
        r = self.H["check"](sympy.Integer(2), sympy.Integer(3), r"\le", [], [], "s")
        self.assertEqual(r["outcome"], "confirmed")

    def test_an_exact_irrational_comparison_is_decided(self):
        sympy = self.H["sympy"]
        r = self.H["check"](sympy.sqrt(2) + sympy.sqrt(3), sympy.Integer(3),
                            r"\le", [], [], "s")
        self.assertEqual(r["outcome"], "refuted")

    def test_an_undecidable_symbolic_inequality_is_unverified(self):
        sympy = self.H["sympy"]
        x = sympy.Symbol("x")
        r = self.H["check"](x, sympy.Integer(0), r"\le", ["x"], [], "s")
        self.assertEqual(r["outcome"], "unverified")

    def test_a_provable_symbolic_inequality_is_confirmed(self):
        sympy = self.H["sympy"]
        x = sympy.Symbol("x", positive=True)
        r = self.H["check"](sympy.Integer(0), x, r"\le", ["x"], [], "s")
        self.assertEqual(r["outcome"], "confirmed")

    def test_equalities_still_work(self):
        sympy = self.H["sympy"]
        x = sympy.Symbol("x")
        r = self.H["check"]((x + 1) ** 2, x ** 2 + 2 * x + 1, "=", ["x"], [], "s")
        self.assertEqual(r["outcome"], "confirmed")


class TestSuppressedRefutation(unittest.TestCase):
    """Measured on arXiv:1412.6980v8 (Adam), Lemma 10.4 step 10.

    A faithful, exact SymPy refutation of that step -- the very error
    arXiv:1804.10587 was written to correct -- was suppressed to a generic
    `UNVERIFIED` because the paper never states domains for $T$, $\\gamma$ or
    $\\beta_2$. Suppressing the *claim* is right; burying the *event* is not. A
    blocked decisive check is the most actionable thing the tool can report.
    """

    def test_a_suppressed_refutation_is_reported_distinctly(self):
        v = C.compose_step(
            step(symbols_used=["T", "\\gamma"]),
            [{"engine": "symbolic", "outcome": "refuted",
              "translation_confidence": "faithful", "detail": "slack is -0.77"}],
            domains_known=False)
        self.assertEqual(v["kind"], "refutation-blocked-by-unknown-domain")
        self.assertNotEqual(v["severity"], "UNVERIFIED")

    def test_it_names_the_symbols_to_supply(self):
        v = C.compose_step(
            step(symbols_used=["T", "\\gamma"]),
            [{"engine": "symbolic", "outcome": "refuted",
              "translation_confidence": "faithful", "detail": "d"}],
            domains_known=False, unknown_symbols=["T", "\\gamma"])
        self.assertEqual(v["symbols_to_supply"], ["T", "\\gamma"])
        self.assertIn("--symbols", v["detail"])

    def test_it_does_not_assert_the_paper_is_wrong(self):
        v = C.compose_step(
            step(), [{"engine": "symbolic", "outcome": "refuted",
                      "translation_confidence": "faithful", "detail": "d"}],
            domains_known=False)
        self.assertNotEqual(v["severity"], "CRITICAL")
        self.assertFalse(v.get("counterexample"))

    def test_an_unfaithful_translation_is_not_promoted_this_way(self):
        v = C.compose_step(
            step(), [{"engine": "rational", "outcome": "refuted",
                      "translation_confidence": "approximate", "detail": "d"}],
            domains_known=False)
        self.assertNotEqual(v.get("kind"), "refutation-blocked-by-unknown-domain")

    def test_a_plain_unverified_step_is_unaffected(self):
        v = C.compose_step(step(), [], domains_known=False)
        self.assertEqual(v["severity"], "UNVERIFIED")
        self.assertIsNone(v.get("kind"))


class TestConfirmationIsGatedToo(unittest.TestCase):
    """The translation gate was asymmetric: it capped refutations at WEAK but let
    a confirmation through as a pass.

    Measured while checking a real draft. A step was 'confirmed' by a script that
    had substituted the lemma's own assumption and then simplified to `p = p` --
    a true statement about the model, not about the step. A confirmation under an
    idealised translation is exactly as untrustworthy as a refutation under one.
    """

    def test_an_approximate_confirmation_does_not_become_a_pass(self):
        v = C.compose_step(step(), [
            {"engine": "symbolic", "outcome": "confirmed",
             "translation_confidence": "approximate",
             "detail": "simplify(lhs - rhs) = 0"}], domains_known=True)
        self.assertEqual(v["severity"], "WEAK")
        self.assertFalse(v["confirmed"])
        self.assertFalse(C.is_pass(v["severity"]))

    def test_a_partial_confirmation_does_not_become_a_pass(self):
        v = C.compose_step(step(), [
            {"engine": "symbolic", "outcome": "confirmed",
             "translation_confidence": "partial", "detail": "d"}],
            domains_known=True)
        self.assertEqual(v["severity"], "WEAK")

    def test_a_faithful_confirmation_is_still_a_pass(self):
        v = C.compose_step(step(), [
            {"engine": "symbolic", "outcome": "confirmed",
             "translation_confidence": "faithful", "detail": "d"}],
            domains_known=True)
        self.assertEqual(v["severity"], "SKIP")
        self.assertTrue(v["confirmed"])
