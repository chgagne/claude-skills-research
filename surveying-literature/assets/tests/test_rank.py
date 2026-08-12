import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from survey.rank import rank
from survey.traverse import Candidate
from survey.seeds import Seed

SEED = Seed(cited_keys=set(), cited_titles=[],
            contributions=["an execution-guided repair loop for chart code"],
            angles=["execution-guided repair", "chart code"])


def c(title, paths, cites=0, year=2024):
    return Candidate(title=title, authors=[], year=year, venue="V", doi=None,
                     paths=list(paths), cited_by_count=cites)


class TestRank(unittest.TestCase):
    def test_multi_path_plus_angle_overlap_is_a_threat(self):
        cand = c("Execution-guided repair of generated chart code",
                 ["backward:X", "forward:Y"], 30)
        self.assertEqual(rank({"k": cand}, SEED)[0][2], "THREAT")

    def test_topical_single_path_is_related_not_threat(self):
        cand = c("Chart code generation from prose", ["forward:Y"], 10)
        self.assertEqual(rank({"k": cand}, SEED)[0][2], "RELATED")

    def test_multi_path_without_topic_overlap_is_related(self):
        cand = c("A study of compiler register allocation",
                 ["backward:X", "forward:Y"], 5)
        self.assertEqual(rank({"k": cand}, SEED)[0][2], "RELATED")

    def test_unrelated_single_path_is_background(self):
        cand = c("A study of compiler register allocation", ["backward:X"], 5)
        self.assertEqual(rank({"k": cand}, SEED)[0][2], "BACKGROUND")

    def test_threats_sort_above_related(self):
        threat = c("Execution-guided repair of chart code",
                   ["backward:X", "forward:Y"], 1)
        rel = c("Chart code generation", ["forward:Y"], 9999)
        out = rank({"a": threat, "b": rel}, SEED)
        self.assertEqual(out[0][2], "THREAT",
                         "a citation-heavy RELATED must not outrank a THREAT")

    def test_within_a_grade_score_orders(self):
        low = c("Chart code generation", ["forward:Y"], 1, year=2005)
        high = c("Chart code synthesis", ["forward:Y"], 5000, year=2005)
        out = rank({"a": low, "b": high}, SEED)
        self.assertEqual(out[0][0].title, "Chart code synthesis")

    def test_empty_input(self):
        self.assertEqual(rank({}, SEED), [])

    def test_no_angles_never_produces_a_threat(self):
        """With no contributions parsed, everything is at most RELATED."""
        bare = Seed(cited_keys=set(), cited_titles=[], contributions=[], angles=[])
        cand = c("Execution-guided repair of chart code",
                 ["backward:X", "forward:Y"], 10)
        self.assertEqual(rank({"k": cand}, bare)[0][2], "RELATED")

    def test_returns_candidate_score_grade_triples(self):
        cand = c("Chart code generation", ["forward:Y"], 3)
        item = rank({"k": cand}, SEED)[0]
        self.assertEqual(len(item), 3)
        self.assertIsInstance(item[1], float)
        self.assertIn(item[2], ("THREAT", "RELATED", "BACKGROUND"))


class TestUnknownCitationCounts(unittest.TestCase):
    """arXiv and DBLP publish no citation counts. Reading that absence as zero
    penalises recent parallel work -- the very thing a gap sweep exists to find."""

    def test_unknown_is_not_treated_as_zero(self):
        known_zero = c("Known zero cites", ["topical:x"], cites=0)
        unknown = c("Unknown cites", ["topical:x"], cites=None)
        peers = [c("Peer A", ["topical:x"], cites=100),
                 c("Peer B", ["topical:x"], cites=200)]
        pool = {str(i): x for i, x in enumerate([known_zero, unknown] + peers)}
        out = rank(pool, SEED)
        pos = {t.title: i for i, (t, _, _) in enumerate(out)}
        self.assertLess(pos["Unknown cites"], pos["Known zero cites"],
                        "an unknown count must not rank below a genuine zero")

    def test_unknown_is_imputed_from_known_peers(self):
        from survey.rank import _impute
        self.assertEqual(_impute([10, 20, 30]), 20)
        self.assertEqual(_impute([]), 0)

    def test_citations_are_age_normalised(self):
        """40 cites since 2010 is weaker evidence than 20 cites since 2024."""
        old = c("Old and cited", ["topical:x"], cites=40, year=2010)
        new = c("Recent and cited", ["topical:x"], cites=20, year=2025)
        out = rank({"a": old, "b": new}, SEED)
        self.assertEqual(out[0][0].title, "Recent and cited")

    def test_all_unknown_does_not_crash(self):
        pool = {"a": c("A", ["topical:x"], cites=None),
                "b": c("B", ["topical:x"], cites=None)}
        self.assertEqual(len(rank(pool, SEED)), 2)


if __name__ == "__main__":
    unittest.main()
