import unittest, sys, pathlib, tempfile, os
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))
from proofcheck import twotrans


STUB = '''\
import sys
STEP_ID = "proof/th:x/s1"
IGNORED_SYMBOLS = []
TRANSLATION_CONFIDENCE = "approximate"
TRANSLATION_NOTES = ""


def build():
    raise Untranslatable("fill me in")


if __name__ == "__main__":
    sys.exit(0)
'''


class TestFillStub(unittest.TestCase):
    def test_build_body_is_substituted(self):
        out = twotrans.fill_stub(STUB, {"build": "    return 1"})
        self.assertIn("def build():\n    return 1", out)
        self.assertNotIn("fill me in", out)

    def test_honesty_fields_are_carried_across(self):
        out = twotrans.fill_stub(STUB, {
            "build": "    return 1",
            "ignored_symbols": ["k"],
            "translation_confidence": "faithful",
            "translation_notes": "dropped nothing",
        })
        self.assertIn("IGNORED_SYMBOLS = ['k']", out)
        self.assertIn("TRANSLATION_CONFIDENCE = 'faithful'", out)
        self.assertIn("TRANSLATION_NOTES = 'dropped nothing'", out)

    def test_missing_build_becomes_untranslatable_not_a_pass(self):
        # A translation that returned nothing must not silently run as an empty
        # model that confirms. Absence is Untranslatable.
        out = twotrans.fill_stub(STUB, {})
        self.assertIn("Untranslatable", out)

    def test_confidence_defaults_to_approximate(self):
        out = twotrans.fill_stub(STUB, {"build": "    return 1"})
        self.assertIn("TRANSLATION_CONFIDENCE = 'approximate'", out)


def _r(step_id, outcome):
    return {"step_id": step_id, "outcome": outcome, "engine": "symbolic",
            "detail": "", "script": "checks/x.py"}


STEP = {"id": "proof/th:x/s1", "claim_latex": "a = b", "kind": "chain",
        "symbols": [], "side_conditions": []}


class TestAdjudicate(unittest.TestCase):
    def test_both_refute_is_the_only_route_to_a_finding(self):
        rows, s = twotrans.adjudicate({STEP["id"]: STEP}, {},
                                      {STEP["id"]: _r(STEP["id"], "refuted")},
                                      {STEP["id"]: _r(STEP["id"], "refuted")})
        self.assertEqual(s["both_refuted"], [STEP["id"]])
        self.assertEqual(rows[0].agree, True)

    def test_one_refutes_one_does_not_is_unverified_not_a_weaker_finding(self):
        rows, s = twotrans.adjudicate({STEP["id"]: STEP}, {},
                                      {STEP["id"]: _r(STEP["id"], "refuted")},
                                      {STEP["id"]: _r(STEP["id"], "confirmed")})
        self.assertEqual(rows[0].severity, "UNVERIFIED")
        self.assertEqual(rows[0].agree, False)
        self.assertEqual(s["both_refuted"], [])

    def test_disagreement_never_yields_critical(self):
        rows, _ = twotrans.adjudicate({STEP["id"]: STEP}, {},
                                      {STEP["id"]: _r(STEP["id"], "refuted")},
                                      {STEP["id"]: _r(STEP["id"], "unverified")})
        self.assertNotEqual(rows[0].severity, "CRITICAL")

    def test_both_confirm_is_recorded(self):
        _, s = twotrans.adjudicate({STEP["id"]: STEP}, {},
                                   {STEP["id"]: _r(STEP["id"], "confirmed")},
                                   {STEP["id"]: _r(STEP["id"], "confirmed")})
        self.assertEqual(s["both_confirmed"], [STEP["id"]])

    def test_agreement_rate_is_reported(self):
        steps = {"a": dict(STEP, id="a"), "b": dict(STEP, id="b")}
        ra = {"a": _r("a", "refuted"), "b": _r("b", "confirmed")}
        rb = {"a": _r("a", "refuted"), "b": _r("b", "unverified")}
        _, s = twotrans.adjudicate(steps, {}, ra, rb)
        self.assertEqual(s["n"], 2)
        self.assertEqual(s["agreement"], 1)

    def test_steps_only_one_translation_covered_are_named_not_dropped(self):
        steps = {"a": dict(STEP, id="a"), "b": dict(STEP, id="b")}
        ra = {"a": _r("a", "refuted"), "b": _r("b", "refuted")}
        rb = {"a": _r("a", "refuted")}
        _, s = twotrans.adjudicate(steps, {}, ra, rb)
        self.assertEqual(s["only_a"], ["b"])
        self.assertEqual(s["only_b"], [])
        self.assertEqual(s["n"], 1, "coverage is the intersection, not the union")


class TestStage(unittest.TestCase):
    def test_stages_only_scripts_the_translation_covers(self):
        with tempfile.TemporaryDirectory() as d:
            checks = os.path.join(d, "checks")
            os.makedirs(checks)
            for name in ("proof-th-x-s1.symbolic.py", "proof-th-x-s2.symbolic.py"):
                with open(os.path.join(checks, name), "w") as fh:
                    fh.write(STUB)
            n = twotrans.stage(checks, os.path.join(d, "runA"),
                               {"proof/th:x/s1": {"build": "    return 1"}},
                               engine="symbolic")
            self.assertEqual(n, 1)
            staged = os.listdir(os.path.join(d, "runA", "checks"))
            self.assertEqual(staged, ["proof-th-x-s1.symbolic.py"])


class TestCliGuards(unittest.TestCase):
    """One translation is not a second opinion, and the CLI must say so."""

    def _run(self, extra):
        from proofcheck.__main__ import main
        import io, contextlib
        tex = pathlib.Path(__file__).resolve().parents[1] / "tests" / "_tt.tex"
        tex.write_text(r"\documentclass{article}\begin{document}"
                       r"\begin{theorem}\label{t}$a=a$\end{theorem}"
                       r"\begin{proof}$a=a$\end{proof}\end{document}")
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                with tempfile.TemporaryDirectory() as d:
                    rc = main([str(tex), "--out", d] + extra)
            return rc, err.getvalue()
        finally:
            tex.unlink(missing_ok=True)

    def test_single_translation_is_refused(self):
        rc, err = self._run(["--translations", "only-one.json"])
        self.assertEqual(rc, 1)
        self.assertIn("exactly two", err)

    def test_missing_translation_file_is_named(self):
        rc, err = self._run(["--translations", "nope-a.json,nope-b.json"])
        self.assertEqual(rc, 1)
        self.assertIn("no such file", err)


if __name__ == "__main__":
    unittest.main()
