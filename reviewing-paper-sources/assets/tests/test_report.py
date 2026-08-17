import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from claimstrength.claims import Pairing
from claimstrength.scale import classify
from claimstrength.report import render


def _p(a, r):
    pa, pr = classify(a), classify(r)
    return Pairing(abstract=a, results=r, shared=4, abstract_rung=pa,
                   results_rung=pr, delta=max(0, pa.level - pr.level))


class TestRender(unittest.TestCase):
    def test_coverage_line_precedes_the_table(self):
        out = render([_p("The gate causes a gain.",
                         "The gate is associated with a gain.")], [])
        self.assertLess(out.index("paired"), out.index("| Abstract"))

    def test_reports_both_rungs_and_the_difference(self):
        out = render([_p("The gate causes a gain.",
                         "The gate is associated with a gain.")], [])
        self.assertIn("causes", out)
        self.assertIn("associated-with", out)
        self.assertIn("4", out)

    def test_renders_no_verdict_words(self):
        out = render([_p("The gate causes a gain.",
                         "The gate is associated with a gain.")], [])
        for word in ("overclaim", "unsupported", "misleading", "wrong"):
            self.assertNotIn(word, out.lower())

    def test_unpaired_claim_is_named_as_unpaired(self):
        out = render([Pairing(abstract="The gate causes a gain.",
                              abstract_rung=classify("The gate causes a gain."))], [])
        self.assertIn("no matching results sentence", out)

    def test_degraded_inputs_are_stated(self):
        out = render([], ["no abstract environment found"])
        self.assertIn("no abstract environment found", out)


if __name__ == "__main__":
    unittest.main()
