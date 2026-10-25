"""lean-certify.py: what counts as a clean certificate, checked without Lean installed.

The parsing is the part that can lie: a theorem the audit never asked about, or a `sorry` reported
only as a warning, would let an unproved certificate read as clean.
"""
import importlib.util
import pathlib
import unittest

_spec = importlib.util.spec_from_file_location(
    "lean_certify", pathlib.Path(__file__).resolve().parents[1] / "lean-certify.py")
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)

SRC = """import Mathlib
open Real

lemma helper (x : ℝ) : 0 ≤ x ^ 2 := sq_nonneg x

namespace Paper
namespace Lem3
theorem step_fails : ¬ ∀ x : ℝ, x ^ 2 ≤ x := by
  sorry
end Lem3
@[simp] theorem top_level : True := trivial
end Paper

private theorem after_end : True := trivial
"""


class TheoremNames(unittest.TestCase):
    def test_namespaces_are_tracked_and_closed(self):
        self.assertEqual(L.theorem_names(SRC),
                         ["helper", "Paper.Lem3.step_fails", "Paper.top_level", "after_end"])


class ParseOutput(unittest.TestCase):
    names = ["helper", "Paper.Lem3.step_fails"]

    def test_clean(self):
        out = ("'helper' depends on axioms: [propext, Classical.choice, Quot.sound]\n"
               "'Paper.Lem3.step_fails' depends on axioms: [propext]\n")
        self.assertTrue(L.parse_output(out, self.names)["clean"])

    def test_sorry_warning_is_not_clean(self):
        out = ("x.lean:7:8: warning: declaration uses 'sorry'\n"
               "'helper' does not depend on any axioms\n"
               "'Paper.Lem3.step_fails' depends on axioms: [sorryAx]\n")
        r = L.parse_output(out, self.names)
        self.assertFalse(r["clean"])
        self.assertTrue(r["sorry"])

    def test_extra_axiom_is_not_clean(self):
        out = ("'helper' depends on axioms: [propext]\n"
               "'Paper.Lem3.step_fails' depends on axioms: [propext, myAxiom]\n")
        r = L.parse_output(out, self.names)
        self.assertFalse(r["clean"])
        self.assertEqual(r["nonstandard"], {"Paper.Lem3.step_fails": ["myAxiom"]})

    def test_theorem_never_audited_is_not_clean(self):
        out = "'helper' depends on axioms: [propext]\n"
        r = L.parse_output(out, self.names)
        self.assertFalse(r["clean"])
        self.assertEqual(r["unchecked"], ["Paper.Lem3.step_fails"])

    def test_error_is_not_clean(self):
        out = ("x.lean:3:0: error: unknown identifier 'foo'\n"
               "'helper' depends on axioms: [propext]\n"
               "'Paper.Lem3.step_fails' depends on axioms: [propext]\n")
        self.assertFalse(L.parse_output(out, self.names)["clean"])

    def test_nothing_to_audit_is_not_clean(self):
        self.assertFalse(L.parse_output("", [])["clean"])


if __name__ == "__main__":
    unittest.main()
