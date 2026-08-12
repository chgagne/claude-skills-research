"""A host that is down must not cost 3 retries on every entry.

Observed: arXiv began answering 429, every request cost 3 attempts x 15s plus
backoff, and a 57-entry run that normally takes minutes ran for 6.5 hours.
"""
import unittest, sys, pathlib, tempfile, urllib.error
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bibcheck import sources


class TestBreaker(unittest.TestCase):
    def setUp(self):
        sources.set_cache_dir(tempfile.mkdtemp())
        sources.reset_breaker()
        sources._last_hit.clear()
        sources._HOST_DELAY["example.org"] = 0.0
        self.orig = sources._raw_get

    def tearDown(self):
        sources._raw_get = self.orig
        sources.reset_breaker()

    def test_breaker_opens_after_repeated_failures(self):
        calls = []

        def dead(url, extra_headers=None):
            calls.append(url)
            raise ConnectionError("down")

        sources._raw_get = dead
        for i in range(10):
            sources.get_json(f"https://example.org/{i}")

        # 3 failures x 3 attempts = 9 calls, then the circuit opens.
        self.assertEqual(len(calls), 9, f"expected 9 attempts, got {len(calls)}")
        self.assertIn("example.org", sources.HOSTS_DISABLED)

    def test_disabled_host_fails_fast(self):
        sources.HOSTS_DISABLED.add("example.org")
        called = []
        sources._raw_get = lambda u, h=None: called.append(u)
        self.assertIsNone(sources.get_json("https://example.org/x"))
        self.assertEqual(called, [], "must not touch the network once the circuit is open")

    def test_success_resets_the_failure_count(self):
        state = {"fail": True}

        def flaky(url, extra_headers=None):
            if state["fail"]:
                raise ConnectionError("down")
            return b'{"ok": 1}'

        sources._raw_get = flaky
        sources.get_json("https://example.org/a")          # 1 failure
        state["fail"] = False
        sources.get_json("https://example.org/b")          # success resets
        state["fail"] = True
        sources.get_json("https://example.org/c")          # 1 failure again
        self.assertNotIn("example.org", sources.HOSTS_DISABLED)

    def test_404_does_not_trip_the_breaker(self):
        """A 404 means the host is healthy and the record is absent."""
        def gone(url, extra_headers=None):
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

        sources._raw_get = gone
        for i in range(6):
            sources.get_json(f"https://example.org/{i}")
        self.assertNotIn("example.org", sources.HOSTS_DISABLED)

    def test_absurd_retry_after_opens_the_circuit_instead_of_sleeping(self):
        """OpenAlex answers an exhausted daily budget with Retry-After: 77547.

        Sleeping 21.5 hours is indistinguishable from a hang -- and did hang a
        run for 10 minutes before being killed.
        """
        slept = []
        real_sleep = sources.time.sleep
        sources.time.sleep = lambda s: slept.append(s)

        def budget_exhausted(url, extra_headers=None):
            raise urllib.error.HTTPError(
                url, 429, "Too Many Requests", {"Retry-After": "77547"}, None)

        try:
            sources._raw_get = budget_exhausted
            self.assertIsNone(sources.get_json("https://example.org/z"))
            self.assertIn("example.org", sources.HOSTS_DISABLED)
            self.assertTrue(all(s <= 30 for s in slept),
                            f"slept for {slept}; must never wait out a daily quota")
        finally:
            sources.time.sleep = real_sleep

    def test_short_retry_after_is_still_honoured(self):
        slept = []
        real_sleep = sources.time.sleep
        sources.time.sleep = lambda s: slept.append(s)

        def busy(url, extra_headers=None):
            raise urllib.error.HTTPError(
                url, 429, "Too Many Requests", {"Retry-After": "5"}, None)

        try:
            sources._raw_get = busy
            sources.get_json("https://example.org/y")
            self.assertIn(5.0, slept)
        finally:
            sources.time.sleep = real_sleep

    def test_arxiv_throttle_respects_the_three_second_guidance(self):
        self.assertGreaterEqual(sources._HOST_DELAY["export.arxiv.org"], 3.0)


if __name__ == "__main__":
    unittest.main()
