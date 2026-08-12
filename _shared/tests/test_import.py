import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))


class TestSharedModule(unittest.TestCase):
    def test_retrieval_surface(self):
        from scholarly import retrieval
        for name in ("get_json", "get_bytes", "set_cache_dir", "reset_breaker",
                     "SOURCE_FAILURES", "HOSTS_DISABLED", "Record", "resolve",
                     "fetch_crossref", "fetch_acl", "fetch_arxiv", "search_dblp",
                     "search_openalex", "search_s2", "is_preprint", "s2_api_key",
                     "arxiv_id_of", "arxiv_id_from_doi", "url_ok"):
            self.assertTrue(hasattr(retrieval, name), f"missing {name}")

    def test_textnorm_surface(self):
        from scholarly import textnorm
        for name in ("latex_to_unicode", "fold", "norm_title", "split_authors",
                     "family_key", "given_initial", "author_diff",
                     "strip_dblp_suffix"):
            self.assertTrue(hasattr(textnorm, name), f"missing {name}")

    def test_cache_defaults_to_scholarly(self):
        from scholarly import retrieval
        self.assertIn("scholarly", retrieval.default_cache_dir())

    def test_retrieval_does_not_import_bibcheck(self):
        """The shared layer must not depend on any skill that consumes it."""
        src = (pathlib.Path(__file__).resolve().parents[1]
               / "scholarly" / "retrieval.py").read_text()
        self.assertNotIn("bibcheck", src)


if __name__ == "__main__":
    unittest.main()
