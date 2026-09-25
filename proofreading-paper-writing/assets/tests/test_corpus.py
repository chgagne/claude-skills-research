# proofreading-paper-writing/assets/tests/test_corpus.py
import unittest
from unittest import mock
from proofread import corpus

BIB = """@inproceedings{good, title={Nice paper}, booktitle={International Conference on Learning Representations}, eprint={2401.00001}}
@article{arx, title={Preprint only}, journal={arXiv preprint arXiv:2402.00002}}
@inproceedings{noid, title={No arxiv}, booktitle={ICLR}}
@inproceedings{other, title={Other venue}, booktitle={CVPR}, eprint={2403.00003}}"""

class TestPropose(unittest.TestCase):
    def test_keeps_venue_matches_with_arxiv_ids(self):
        out = corpus.propose_field_corpus(BIB, ["ICLR", "Learning Representations"])
        self.assertEqual([r["key"] for r in out], ["good"])
        self.assertEqual(out[0]["arxiv_id"], "2401.00001")

class TestAuthor(unittest.TestCase):
    def test_author_papers_uses_s2_and_maps_fields(self):
        search = {"data": [{"authorId": "1", "name": "Some Name", "paperCount": 12}]}
        papers = {"data": [{"title": "T", "year": 2024, "venue": "ICLR", "citationCount": 10,
                            "externalIds": {"ArXiv": "2404.00004"}, "authors": [{"name": "Some Name"}, {"name": "B"}]},
                           {"title": "U", "year": 2023, "venue": "", "citationCount": 1, "externalIds": {},
                            "authors": [{"name": "Some Name"}]},
                           {"title": "V", "year": 2025, "venue": "", "citationCount": 99, "externalIds": {},
                            "authors": [{"name": "Other Person"}, {"name": "Some Name"}]}]}
        with mock.patch.object(corpus, "get_json", side_effect=[search, papers]), \
             mock.patch.object(corpus, "s2_api_key", return_value="k"):
            out = corpus.author_papers("Some Name", limit=5)
        self.assertEqual(out[0], {"title": "T", "year": 2024, "venue": "ICLR", "arxiv_id": "2404.00004", "citations": 10,
                                  "first_author": True})
        self.assertEqual([r["title"] for r in out], ["T", "U"])   # V is not first-authored
        self.assertEqual(corpus.last_author_match, {"authorId": "1", "name": "Some Name", "paperCount": 12})

    def test_author_papers_without_key_returns_empty(self):
        with mock.patch.object(corpus, "s2_api_key", return_value=None):
            self.assertEqual(corpus.author_papers("X"), [])

class TestFetch(unittest.TestCase):
    def test_fetch_writes_source_and_meta(self):
        import tempfile, os, json
        with tempfile.TemporaryDirectory() as d, \
             mock.patch.object(corpus, "get_bytes", return_value=b"\x1f\x8b" + b"x"), \
             mock.patch.object(corpus, "tex_from_eprint", return_value="\\documentclass{article}"):
            p = corpus.fetch_arxiv_source("2401.00001", d)
            self.assertTrue((p / "source.tex").exists())
            self.assertEqual(json.loads((p / "meta.json").read_text())["arxiv_id"], "2401.00001")

    def test_fetch_returns_none_when_no_tex(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d, \
             mock.patch.object(corpus, "get_bytes", return_value=None):
            self.assertIsNone(corpus.fetch_arxiv_source("2401.00001", d))
