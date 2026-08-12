import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bibcheck.sources import arxiv_id_from_doi


class TestArxivDoi(unittest.TestCase):
    def test_datacite_arxiv_doi_yields_arxiv_id(self):
        """10.48550/* is registered with DataCite, not Crossref."""
        self.assertEqual(arxiv_id_from_doi("10.48550/arXiv.2601.23265"), "2601.23265")
        self.assertEqual(arxiv_id_from_doi("10.48550/ARXIV.2206.10540"), "2206.10540")

    def test_ordinary_doi_is_not_an_arxiv_doi(self):
        self.assertIsNone(arxiv_id_from_doi("10.1109/TVCG.2018.2865240"))
        self.assertIsNone(arxiv_id_from_doi(""))


if __name__ == "__main__":
    unittest.main()
