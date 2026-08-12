import unittest, sys, pathlib, json, tempfile, os
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))
from compare import resolve as R


class TestResolve(unittest.TestCase):
    def setUp(self):
        self.orig = (R._by_doi, R._by_arxiv, R._by_title)
        R._by_doi = lambda d: R.PaperRef(title="By DOI", doi=d, source="crossref")
        R._by_arxiv = lambda a: R.PaperRef(title="By arXiv", arxiv_id=a, source="arxiv")
        R._by_title = lambda t: R.PaperRef(title=t, source="s2")

    def tearDown(self):
        (R._by_doi, R._by_arxiv, R._by_title) = self.orig

    def test_doi_is_recognised(self):
        self.assertEqual(R.resolve("10.1109/TVCG.2018.2865240").source, "crossref")

    def test_doi_url_is_recognised(self):
        self.assertEqual(
            R.resolve("https://doi.org/10.1145/3583131.3590423").source, "crossref")

    def test_arxiv_id_is_recognised(self):
        self.assertEqual(R.resolve("arXiv:2206.10540").source, "arxiv")
        self.assertEqual(R.resolve("2206.10540").source, "arxiv")
        self.assertEqual(R.resolve("2206.10540v2").source, "arxiv")

    def test_arxiv_url_is_recognised(self):
        self.assertEqual(R.resolve("https://arxiv.org/abs/2206.10540").source, "arxiv")

    def test_bare_title_falls_through_to_search(self):
        self.assertEqual(R.resolve("SNIP: Bridging Realms").source, "s2")

    def test_title_mismatch_is_rejected(self):
        R._by_title = lambda t: R.PaperRef(title="A Completely Different Paper",
                                           source="s2")
        self.assertIsNone(R.resolve("SNIP: Bridging Realms"),
                          "a near-miss title must not be silently compared")

    def test_identity_check_tolerates_punctuation_and_case(self):
        R._by_title = lambda t: R.PaperRef(title="snip - bridging realms!",
                                           source="s2")
        self.assertIsNotNone(R.resolve("SNIP: Bridging Realms"))

    def test_unresolvable_query_returns_none(self):
        R._by_title = lambda t: None
        self.assertIsNone(R.resolve("a paper that does not exist anywhere"))

    def test_title_resolution_captures_the_arxiv_id(self):
        """Without it the LaTeX-source rung can never fire, and that rung is the
        only one that reaches appendices reliably."""
        R._by_title = lambda t: R.PaperRef(title=t, source="s2",
                                           arxiv_id="2310.02227",
                                           doi="10.48550/arXiv.2310.02227")
        ref = R.resolve("SNIP: Bridging Realms")
        self.assertEqual(ref.arxiv_id, "2310.02227")

    def test_from_candidates_selects_by_grade(self):
        rows = [{"title": "T1", "grade": "THREAT", "doi": "10.1/a"},
                {"title": "R1", "grade": "RELATED", "doi": "10.1/b"}]
        d = tempfile.mkdtemp()
        p = os.path.join(d, "candidates.json")
        with open(p, "w") as fh:
            json.dump(rows, fh)
        R._by_doi = lambda doi: R.PaperRef(title="T1", doi=doi, source="crossref")
        got = R.from_candidates(p, grades=("THREAT",))
        self.assertEqual([r.title for r in got], ["T1"])

    def test_from_candidates_falls_back_to_title_when_no_doi(self):
        rows = [{"title": "No DOI Paper", "grade": "THREAT", "doi": None}]
        d = tempfile.mkdtemp()
        p = os.path.join(d, "candidates.json")
        with open(p, "w") as fh:
            json.dump(rows, fh)
        got = R.from_candidates(p, grades=("THREAT",))
        self.assertEqual([r.title for r in got], ["No DOI Paper"])


if __name__ == "__main__":
    unittest.main()
