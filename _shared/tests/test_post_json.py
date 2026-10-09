"""post_json: cached on url + body, disabled engines never contacted, failures counted."""
import unittest, sys, pathlib, json, tempfile, io, os, urllib.error
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from scholarly import retrieval as R


class FakeResp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False


class TestPostJson(unittest.TestCase):
    def setUp(self):
        R.set_cache_dir(tempfile.mkdtemp()); R.reset_breaker()
        self.calls = []; self.orig = R.urllib.request.urlopen; self.sleep = R.time.sleep
        R.time.sleep = lambda s: None
        os.environ.pop("SCHOLARLY_DISABLE", None); os.environ.pop("EVAL_SCHOLARLY_DISABLE", None)

    def tearDown(self):
        R.urllib.request.urlopen = self.orig; R.time.sleep = self.sleep

    def serve(self, payload):
        def fake(req, timeout=None):
            self.calls.append((req.full_url, req.data, req.get_method()))
            if isinstance(payload, Exception): raise payload
            return FakeResp(json.dumps(payload).encode())
        R.urllib.request.urlopen = fake

    def test_posts_and_caches_on_body(self):
        self.serve({"recommendedPapers": [{"title": "A"}]})
        url = "https://api.semanticscholar.org/recommendations/v1/papers?fields=title"
        a = R.post_json(url, {"positivePaperIds": ["x", "y"]})
        b = R.post_json(url, {"positivePaperIds": ["x", "y"]})
        R.post_json(url, {"positivePaperIds": ["z"]})
        self.assertEqual(a, b); self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.calls[0][2], "POST")

    def test_disabled_engine_is_not_contacted(self):
        os.environ["SCHOLARLY_DISABLE"] = "s2"
        self.serve({"ok": 1})
        self.assertIsNone(R.post_json("https://api.semanticscholar.org/x", {"a": 1}))
        self.assertEqual(self.calls, [])
        os.environ.pop("SCHOLARLY_DISABLE")

    def test_failure_is_counted_after_retries(self):
        self.serve(TimeoutError("slow"))
        self.assertIsNone(R.post_json("https://api.semanticscholar.org/y", {"a": 1}))
        self.assertEqual(R.SOURCE_FAILURES.get("api.semanticscholar.org"), 1)


if __name__ == "__main__":
    unittest.main()
