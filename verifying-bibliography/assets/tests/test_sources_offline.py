import unittest, sys, pathlib, json, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bibcheck import sources

CROSSREF_DRACO = {"message": {
    "title": ["Formalizing Visualization Design Knowledge as Constraints: "
              "Actionable and Extensible Models in Draco"],
    "author": [{"given": "Dominik", "family": "Moritz"},
               {"given": "Chenglong", "family": "Wang"}],
    "container-title": ["IEEE Transactions on Visualization and Computer Graphics"],
    "volume": "25", "issue": "1", "page": "438-448",
    "issued": {"date-parts": [[2019, 1]]}, "DOI": "10.1109/TVCG.2018.2865240"}}


class TestSources(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        sources.set_cache_dir(self.tmp)

    def test_crossref_record_mapping(self):
        r = sources._crossref_to_record(CROSSREF_DRACO["message"])
        self.assertTrue(r.title.startswith("Formalizing Visualization Design Knowledge"))
        self.assertEqual(r.authors, ["Dominik Moritz", "Chenglong Wang"])
        self.assertEqual((r.volume, r.issue, r.pages, r.year), ("25", "1", "438-448", 2019))
        self.assertTrue(r.strong)
        self.assertEqual(r.source, "crossref")

    def test_cache_roundtrip_avoids_second_fetch(self):
        calls = []

        def fake(url, extra_headers=None):
            calls.append(url)
            return json.dumps(CROSSREF_DRACO).encode()

        sources._raw_get = fake
        sources.get_json("https://example.org/x")
        sources.get_json("https://example.org/x")
        self.assertEqual(len(calls), 1, "second call must be served from cache")

    def test_dblp_suffix_stripped_in_record(self):
        hit = {"info": {"title": "Structured Representations for Program Synthesis",
                        "authors": {"author": [{"text": "Elena Rossi 0001"}]},
                        "venue": "PPSN", "year": "2026"}}
        r = sources._dblp_to_record(hit)
        self.assertEqual(r.authors, ["Elena Rossi"])
        self.assertFalse(r.strong)


if __name__ == "__main__":
    unittest.main()
