import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bibcheck.bibparse import parse_bib, latex_to_unicode

MULTILINE = r"""
@inproceedings{muller2026alignment,
  author    = {Dupr\'e, B. and Dupont, C. and Rossi, C.},
  title     = {Structured Representations for Program Synthesis:
  Analyzing Alignment in Latent Space},
  booktitle = {Parallel Problem Solving from Nature (PPSN)},
  year      = {2026}}

@article{vastl2024symformer,
  title={Symformer: End-to-end symbolic regression using transformer-based architecture},
  author={Vastl, Martin and Kulh{\'a}nek, Jon{\'a}{\v{s}}},
  journal={IEEE Access},
  year={2024}
}
"""


class TestParse(unittest.TestCase):
    def test_parses_both_entries(self):
        entries = parse_bib(MULTILINE)
        self.assertEqual([e.key for e in entries],
                         ["muller2026alignment", "vastl2024symformer"])

    def test_entry_type(self):
        self.assertEqual(parse_bib(MULTILINE)[0].etype, "inproceedings")

    def test_multiline_title_is_joined(self):
        t = parse_bib(MULTILINE)[0].fields["title"]
        self.assertIn("Structured Representations for Program Synthesis", t)
        self.assertIn("Analyzing Alignment in Latent Space", t)
        self.assertNotIn("\n", t)

    def test_closing_double_brace_does_not_swallow_next_entry(self):
        self.assertEqual(parse_bib(MULTILINE)[0].fields["year"], "2026")

    def test_latex_accents(self):
        self.assertEqual(latex_to_unicode(r"Dupr\'e, B."), "Dupré, B.")
        self.assertEqual(latex_to_unicode(r"Andr\'e"), "André")
        self.assertEqual(latex_to_unicode(r"Kulh{\'a}nek"), "Kulhánek")
        self.assertEqual(latex_to_unicode(r"Jon{\'a}{\v{s}}"), "Jonáš")

    def test_braces_stripped_from_protected_titles(self):
        e = parse_bib("@article{k, title = {{Draco}: An Approach}, year={2019}}")[0]
        self.assertEqual(e.fields["title"], "Draco: An Approach")


if __name__ == "__main__":
    unittest.main()
