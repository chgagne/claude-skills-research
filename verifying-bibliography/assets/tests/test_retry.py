import unittest, sys, pathlib, tempfile, urllib.error
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bibcheck import sources


class TestRetry(unittest.TestCase):
    def setUp(self):
        sources.set_cache_dir(tempfile.mkdtemp())
        sources.SOURCE_FAILURES.clear()
        sources._last_hit.clear()
        self.orig = sources._raw_get

    def tearDown(self):
        sources._raw_get = self.orig

    def test_transient_failure_is_retried_then_succeeds(self):
        calls = []

        def flaky(url, extra_headers=None):
            calls.append(url)
            if len(calls) < 3:
                raise ConnectionError("Remote end closed connection")
            return b'{"ok": true}'

        sources._raw_get = flaky
        sources._HOST_DELAY["example.org"] = 0.0
        self.assertEqual(sources.get_json("https://example.org/a"), {"ok": True})
        self.assertEqual(len(calls), 3)
        self.assertEqual(sources.SOURCE_FAILURES, {})

    def test_persistent_failure_is_recorded_not_silent(self):
        def dead(url, extra_headers=None):
            raise ConnectionError("down")

        sources._raw_get = dead
        sources._HOST_DELAY["example.org"] = 0.0
        self.assertIsNone(sources.get_json("https://example.org/b"))
        self.assertEqual(sources.SOURCE_FAILURES.get("example.org"), 1)

    def test_404_is_not_retried_and_is_cached(self):
        calls = []

        def gone(url, extra_headers=None):
            calls.append(url)
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

        sources._raw_get = gone
        self.assertIsNone(sources.get_json("https://example.org/c"))
        self.assertEqual(len(calls), 1, "a 404 is definitive; do not retry")
        self.assertIsNone(sources.get_json("https://example.org/c"))
        self.assertEqual(len(calls), 1, "second call must come from the cache")


if __name__ == "__main__":
    unittest.main()
