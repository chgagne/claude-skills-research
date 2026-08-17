import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from claimstrength.scale import classify, RUNGS


class TestRungOrdering(unittest.TestCase):
    def test_levels_are_contiguous_and_ascending(self):
        self.assertEqual([r[0] for r in RUNGS], [1, 2, 3, 4, 5, 6])

    def test_labels_are_unique(self):
        labels = [r[1] for r in RUNGS]
        self.assertEqual(len(labels), len(set(labels)))


class TestClassify(unittest.TestCase):
    def test_causal_verb_is_the_top_rung(self):
        a = classify("The proposed gate causes the observed gain.")
        self.assertEqual(a.level, 6)
        self.assertEqual(a.label, "causes")
        self.assertEqual(a.phrase, "causes")
        self.assertTrue(a.found)

    def test_association_is_rung_two(self):
        a = classify("Accuracy is associated with corpus size.")
        self.assertEqual(a.level, 2)
        self.assertEqual(a.label, "associated-with")

    def test_highest_rung_wins_when_several_match(self):
        a = classify("The method improves accuracy and causes faster convergence.")
        self.assertEqual(a.level, 6)

    def test_hedge_demotes_one_rung_and_is_flagged(self):
        a = classify("The gate may cause the observed gain.")
        self.assertEqual(a.level, 5)
        self.assertTrue(a.hedged)

    def test_hedge_cannot_demote_below_one(self):
        a = classify("Results may be consistent with the prior estimate.")
        self.assertEqual(a.level, 1)
        self.assertTrue(a.hedged)

    def test_no_match_invents_nothing(self):
        a = classify("Section 4 describes the training corpus.")
        self.assertEqual(a.level, 0)
        self.assertEqual(a.label, "none")
        self.assertEqual(a.phrase, "")
        self.assertFalse(a.found)

    def test_matching_is_case_insensitive(self):
        self.assertEqual(classify("Causes a regression.").level, 6)

    def test_substring_of_a_longer_word_does_not_match(self):
        a = classify("The decreased latency was recorded.")
        self.assertEqual(a.level, 0)


if __name__ == "__main__":
    unittest.main()
