import unittest, sys, pathlib, tempfile, os
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bibcheck import sources


class TestS2Key(unittest.TestCase):
    def setUp(self):
        self.env = os.environ.pop("S2_API_KEY", None)
        self.orig_file = sources.S2_KEY_FILE
        sources.set_cache_dir(tempfile.mkdtemp())

    def tearDown(self):
        os.environ.pop("S2_API_KEY", None)
        if self.env is not None:
            os.environ["S2_API_KEY"] = self.env
        sources.S2_KEY_FILE = self.orig_file

    def test_env_var_wins(self):
        os.environ["S2_API_KEY"] = "  from-env  "
        self.assertEqual(sources.s2_api_key(), "from-env")

    def test_falls_back_to_key_file(self):
        d = tempfile.mkdtemp()
        sources.S2_KEY_FILE = os.path.join(d, "s2_key")
        with open(sources.S2_KEY_FILE, "w") as fh:
            fh.write("from-file\n")
        self.assertEqual(sources.s2_api_key(), "from-file")

    def test_absent_key_is_none_not_an_error(self):
        sources.S2_KEY_FILE = "/nonexistent/path/s2_key"
        self.assertIsNone(sources.s2_api_key())
        self.assertIsNone(sources.search_s2("anything"), "S2 must be skipped silently")

    def test_key_is_sent_as_header_not_in_url(self):
        seen = {}

        def spy(url, extra_headers=None):
            seen["url"] = url
            seen["headers"] = extra_headers or {}
            return b'{"data": []}'

        sources._raw_get = spy
        os.environ["S2_API_KEY"] = "secret-value"
        sources.search_s2("some title")
        self.assertNotIn("secret-value", seen["url"],
                         "the key must never appear in a URL (URLs are cached to disk)")
        self.assertEqual(seen["headers"].get("x-api-key"), "secret-value")

    def test_s2_throttle_is_above_one_per_second(self):
        self.assertGreaterEqual(sources._HOST_DELAY["api.semanticscholar.org"], 1.0)


if __name__ == "__main__":
    unittest.main()
