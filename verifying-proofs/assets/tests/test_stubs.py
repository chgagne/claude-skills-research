"""Generated check scripts.

A stub nobody has filled in must come back `untranslatable`, which composes to
`UNVERIFIED`. It must never look like a step that passed. That is the single most
important property here: the tool writes one script per checkable step, and if the
unfilled ones read as clean, a run that translated nothing would report a clean
paper.

The scripts are also the audit trail. Each one carries the source LaTeX, the
macro-expanded LaTeX, the symbol domains with their provenance, and the side
conditions -- so a reader who distrusts a verdict can open the file and see
exactly what was modelled.
"""
import unittest, sys, pathlib, tempfile, os, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))

from proofcheck import stubs as S, sandbox  # noqa: E402

STEP = {
    "id": "proof/thm:x/s07", "proof_id": "proof/thm:x", "ordinal": 7,
    "kind": "chain-row", "checkable": "candidate", "opacity_reasons": [],
    "math_tex": r"(\gamma + y)^2 = \gamma^2 + 2\gamma y + y^2",
    "prose_tex": "By expanding the square,",
    "claim_forms": [{"form": "adjacent", "lhs_tex": r"(\gamma + y)^2",
                     "relation": "=", "rhs_tex": r"\gamma^2 + 2\gamma y + y^2"}],
    "symbols_used": [r"\gamma", "y"],
    "side_conditions": [{"kind": "nonzero-denominator", "expr_tex": "y",
                         "status": "undetermined", "established": False,
                         "by": None}],
    "justification": {"kind": "none", "name": None, "refs": [], "cites": [],
                      "hedges": []},
    "content_hash": "abc123", "case_path": [],
    "source": {"file": "main.tex", "offset": 100},
}

LEDGER = {
    "schema": "latexmath-ledger/1", "source": {"root": "/tmp/main.tex",
                                               "files": ["main.tex"]},
    "claims": [], "proofs": [{"id": "proof/thm:x", "claim_id": "claim/thm:x"}],
    "steps": [STEP],
    "symbols": [{"symbol": r"\gamma", "normalized": "gamma",
                 "domain_hint": "unit-interval-half-open",
                 "domain_provenance": "declared",
                 "domain_evidence": [{"quote": r"$\gamma \in [0,1)$"}],
                 "first_use": {"start": 0, "end": 1}, "occurrences": 3,
                 "defined_at": {"start": 0, "end": 1}, "role_hint": "scalar",
                 "scopes": []},
                {"symbol": "y", "normalized": "y", "domain_hint": None,
                 "domain_provenance": "unknown", "domain_evidence": [],
                 "first_use": {"start": 2, "end": 3}, "occurrences": 2,
                 "defined_at": None, "role_hint": "scalar", "scopes": []}],
    "equations": [], "refs": {"labels": {}, "edges": [], "dangling": [],
                              "unused_labels": [], "forward_refs": [], "cycles": []},
    "coverage": {}, "diagnostics": [], "macros_unexpandable": [],
}


class TestStubGeneration(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp()
        self.paths = S.write_stubs(LEDGER, self.out, engines=("rational",))

    def read(self):
        with open(self.paths[0]) as fh:
            return fh.read()

    def test_one_script_per_checkable_step(self):
        self.assertEqual(len(self.paths), 1)
        self.assertTrue(os.path.basename(self.paths[0]).endswith(".py"))

    def test_the_script_name_is_derived_from_the_step_id(self):
        self.assertIn("thm-x", os.path.basename(self.paths[0]))
        self.assertNotIn("/", os.path.basename(self.paths[0]))

    def test_the_contract_file_is_written_alongside(self):
        self.assertTrue(os.path.exists(
            os.path.join(self.out, "checks", "_contract.md")))

    def test_the_source_latex_is_in_the_script(self):
        self.assertIn(r"\gamma^2 + 2\gamma y + y^2", self.read())

    def test_the_declared_domain_and_its_quote_are_in_the_script(self):
        text = self.read()
        self.assertIn("unit-interval-half-open", text)
        self.assertIn("declared", text)
        self.assertIn(r"[0,1)", text)

    def test_an_unknown_domain_is_marked_as_blocking_refutation(self):
        text = self.read()
        self.assertIn("unknown", text)
        self.assertRegex(text, r"(?i)no counterexample|cannot refute|never refute")

    def test_side_conditions_are_carried_into_the_script(self):
        self.assertIn("nonzero-denominator", self.read())

    def test_the_step_content_hash_is_recorded(self):
        self.assertIn("abc123", self.read())

    def test_the_generated_script_passes_the_sandbox_guard(self):
        self.assertEqual(sandbox.guard(self.read()), [])

    def test_structural_steps_get_no_script(self):
        led = dict(LEDGER, steps=[dict(STEP, checkable="structural")])
        self.assertEqual(S.write_stubs(led, tempfile.mkdtemp()), [])

    def test_opaque_steps_get_no_script(self):
        led = dict(LEDGER, steps=[dict(STEP, checkable="opaque",
                                       opacity_reasons=["asymptotic"])])
        self.assertEqual(S.write_stubs(led, tempfile.mkdtemp()), [])


class TestEveryEngineEmitsAScript(unittest.TestCase):
    """A stub emitted with the wrong harness reports `untranslatable` forever,
    and the run then looks like a coverage problem rather than a wiring bug."""

    ENGINES = ("rational", "symbolic", "gradient", "smt")

    def test_each_engine_produces_a_script_that_passes_the_guard(self):
        for eng in self.ENGINES:
            out = tempfile.mkdtemp()
            paths = S.write_stubs(LEDGER, out, engines=(eng,))
            self.assertEqual(len(paths), 1, "%s emitted no script" % eng)
            with open(paths[0]) as fh:
                src = fh.read()
            self.assertEqual(sandbox.guard(src), [],
                             "%s emitted a script the sandbox refuses" % eng)

    def test_each_engine_declares_itself_in_its_script(self):
        for eng in self.ENGINES:
            out = tempfile.mkdtemp()
            with open(S.write_stubs(LEDGER, out, engines=(eng,))[0]) as fh:
                self.assertIn("ENGINE = %r" % eng, fh.read())

    def test_an_engine_that_emits_no_script_is_an_error_not_a_silent_default(self):
        with self.assertRaises(ValueError):
            S.stub_source(STEP, {}, engine="sideconds")

    def test_an_absent_checker_degrades_to_unverified_never_to_a_pass(self):
        """z3 is not installed here; the script must not read as a pass."""
        out = tempfile.mkdtemp()
        path = S.write_stubs(LEDGER, out, engines=("smt",))[0]
        r = sandbox.run_script(path, timeout=25)
        self.assertIn(r["outcome"], ("untranslatable", "unverified"))
        self.assertNotIn(r["outcome"], ("not-refuted", "confirmed"))


class TestUnfilledStubs(unittest.TestCase):
    def test_an_unfilled_stub_reports_untranslatable_not_a_pass(self):
        out = tempfile.mkdtemp()
        path = S.write_stubs(LEDGER, out, engines=("rational",))[0]
        r = sandbox.run_script(path, timeout=20)
        self.assertEqual(r["outcome"], "untranslatable")
        self.assertNotEqual(r["outcome"], "not-refuted")

    def test_collect_reports_every_unfilled_stub(self):
        out = tempfile.mkdtemp()
        S.write_stubs(LEDGER, out, engines=("rational",))
        results = S.collect(out, timeout=20)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["outcome"], "untranslatable")


class TestFilledStubs(unittest.TestCase):
    def fill(self, body, engine="rational"):
        out = tempfile.mkdtemp()
        path = S.write_stubs(LEDGER, out, engines=(engine,))[0]
        with open(path) as fh:
            text = fh.read().replace(S.UNFILLED_BODY, body)
        self.assertNotIn(S.UNFILLED_BODY, text, "the stub body marker moved")
        with open(path, "w") as fh:
            fh.write(text)
        return path

    def test_a_correct_translation_is_not_refuted(self):
        path = self.fill(
            "    return (lambda e: (e['gamma'] + e['y']) ** 2,\n"
            "            lambda e: e['gamma']**2 + 2*e['gamma']*e['y'] + e['y']**2,\n"
            "            '=')\n")
        r = sandbox.run_script(path, timeout=30)
        self.assertEqual(r["outcome"], "not-refuted")
        self.assertNotIn("verified", (r["detail"] or "").lower())

    def test_a_wrong_translation_is_refuted_with_a_counterexample(self):
        path = self.fill(
            "    return (lambda e: (e['gamma'] + e['y']) ** 2,\n"
            "            lambda e: e['gamma']**2 + e['y']**2,\n"
            "            '=')\n")
        r = sandbox.run_script(path, timeout=30)
        self.assertEqual(r["outcome"], "refuted")
        self.assertTrue(r["counterexample"])

    def test_the_declared_domain_is_honoured_when_sampling(self):
        """gamma is declared in [0,1); no sample may fall outside it."""
        path = self.fill(
            "    return (lambda e: e['gamma'], lambda e: e['gamma'] + 1, '=')\n")
        r = sandbox.run_script(path, timeout=30)
        self.assertEqual(r["outcome"], "refuted")
        from fractions import Fraction
        g = Fraction(r["counterexample"]["gamma"])
        self.assertTrue(0 <= g < 1, "sampled %s outside the declared domain" % g)

    def test_a_result_carries_the_step_id_back(self):
        path = self.fill(
            "    return (lambda e: e['gamma'], lambda e: e['gamma'], '=')\n")
        r = sandbox.run_script(path, timeout=30)
        self.assertEqual(r["step_id"], "proof/thm:x/s07")

    def test_translation_confidence_is_reported(self):
        path = self.fill(
            "    return (lambda e: e['gamma'], lambda e: e['gamma'], '=')\n")
        r = sandbox.run_script(path, timeout=30)
        self.assertEqual(r.get("translation_confidence"), "faithful")


if __name__ == "__main__":
    unittest.main()
