"""A throttled Semantic Scholar key (429 on every request, while anonymous requests pass)
must not blind the sweep: retry the request once without the key."""
import unittest, sys, pathlib, tempfile, json, urllib.error, io
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from scholarly import retrieval as R


class TestAnonymousFallback(unittest.TestCase):
    def setUp(self):
        R.set_cache_dir(tempfile.mkdtemp()); R.reset_breaker()
        self.calls = []; self.orig = R._raw_get; self.sleep = R.time.sleep
        R.time.sleep = lambda s: None

    def tearDown(self):
        R._raw_get = self.orig; R.time.sleep = self.sleep

    def test_keyed_429_retries_without_the_key(self):
        def fake(url, extra_headers=None):
            self.calls.append(dict(extra_headers or {}))
            if extra_headers and "x-api-key" in extra_headers:
                raise urllib.error.HTTPError(url, 429, "Too Many Requests", {}, io.BytesIO(b""))
            return json.dumps({"data": [{"title": "T"}]}).encode()
        R._raw_get = fake
        d = R.get_json("https://api.semanticscholar.org/graph/v1/paper/search?query=x", {"x-api-key": "k"})
        self.assertEqual(d, {"data": [{"title": "T"}]})
        self.assertTrue(any("x-api-key" not in c for c in self.calls))
        self.assertEqual(R.SOURCE_FAILURES, {})

    def test_other_hosts_never_drop_their_headers(self):
        def fake(url, extra_headers=None):
            self.calls.append(dict(extra_headers or {}))
            raise urllib.error.HTTPError(url, 429, "Too Many Requests", {}, io.BytesIO(b""))
        R._raw_get = fake
        R.get_json("https://api.crossref.org/works/10.1/x", {"x-api-key": "k"})
        self.assertTrue(all("x-api-key" in c for c in self.calls))


if __name__ == "__main__":
    unittest.main()
