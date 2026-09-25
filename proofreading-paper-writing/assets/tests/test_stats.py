# tests/test_stats.py
import unittest
from proofread.stats import sentences, passive_rate, first_person_rate, vocab, tense_by_section, ref_style, length_quantiles, HEDGES

TXT = ("We propose a widget. It was trained by us on 3.5 million images, i.e., the full set. "
       "Results are shown in Fig.~\\ref{f}. The model may fail. Prior work et al. is cited. "
       "This suggests that widgets are useful!")

class TestSentences(unittest.TestCase):
    def test_split_protects_abbreviations_and_decimals(self):
        s = sentences(TXT)
        self.assertEqual(len(s), 6)
        self.assertTrue(s[1].startswith("It was trained"))
        self.assertIn("i.e., the full set.", s[1])
        self.assertTrue(s[2].startswith("Results are shown in Fig."))

    def test_rates(self):
        s = sentences(TXT)
        self.assertAlmostEqual(passive_rate(s), 3 / 6)      # was trained, are shown, is cited
        self.assertAlmostEqual(first_person_rate(s), 2 / 6)  # We propose; trained by us
        self.assertEqual(vocab(s, HEDGES)["may"], 1)
        self.assertEqual(vocab(s, HEDGES)["suggests"], 1)

    def test_quantiles(self):
        q = length_quantiles(["a b c", "a b c d e", "a"])
        self.assertEqual(q["q50"], 3); self.assertEqual(q["max"], 5)

class TestSections(unittest.TestCase):
    def test_tense_by_section(self):
        secs = [("Introduction", "We propose a model. It is fast."), ("Experiments", "We trained it. It was evaluated.")]
        t = tense_by_section(secs)
        self.assertGreater(t["Introduction"]["present"], t["Introduction"]["past"])
        self.assertGreater(t["Experiments"]["past"], t["Experiments"]["present"])

    def test_ref_style_counts(self):
        r = ref_style("See Figure~\\ref{a} and Fig.~\\ref{b}; Table~\\ref{c}; Section~\\ref{d}; \\fref{e}; \\S\\ref{f}.")
        self.assertEqual(r["Figure~\\ref"], 1); self.assertEqual(r["Fig.~\\ref"], 1)
        self.assertEqual(r["Table~\\ref"], 1); self.assertEqual(r["Section~\\ref"], 1)
        self.assertEqual(r["\\fref"], 1); self.assertEqual(r["\\S\\ref"], 1)
