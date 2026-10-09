"""Environment hooks the eval harness needs. `claude plugin eval` gives each run a fresh
HOME and passes only EVAL_* variables, so the usual key file and S2_API_KEY never arrive;
and a measured run must be able to switch an engine off for every arm alike."""
import unittest, sys, pathlib, os, tempfile, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from scholarly import retrieval as R


class EnvCase(unittest.TestCase):
    KEYS = ("S2_API_KEY", "EVAL_S2_API_KEY", "SCHOLARLY_DISABLE", "EVAL_SCHOLARLY_DISABLE")

    def setUp(self):
        self.saved = {k: os.environ.pop(k, None) for k in self.KEYS}
        self.keyfile = R.S2_KEY_FILE
        R.S2_KEY_FILE = os.path.join(tempfile.mkdtemp(), "absent")
        R.set_cache_dir(tempfile.mkdtemp())
        R.reset_breaker()
        self.urls = []
        self.orig = R._raw_get
        R._raw_get = lambda url, h=None: (self.urls.append(url), json.dumps({"ok": 1}).encode())[1]

    def tearDown(self):
        for k, v in self.saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v
        R.S2_KEY_FILE = self.keyfile
        R._raw_get = self.orig


class TestS2Key(EnvCase):
    def test_eval_variable_supplies_the_key(self):
        os.environ["EVAL_S2_API_KEY"] = "k-eval"
        self.assertEqual(R.s2_api_key(), "k-eval")

    def test_regular_variable_wins_over_the_eval_one(self):
        os.environ["S2_API_KEY"] = "k-main"
        os.environ["EVAL_S2_API_KEY"] = "k-eval"
        self.assertEqual(R.s2_api_key(), "k-main")

    def test_no_key_anywhere(self):
        self.assertIsNone(R.s2_api_key())


class TestDisabledEngines(EnvCase):
    def test_disabled_engine_is_never_contacted_and_is_not_a_failure(self):
        os.environ["EVAL_SCHOLARLY_DISABLE"] = "openalex"
        self.assertIsNone(R.get_json("https://api.openalex.org/works?filter=title.search:x"))
        self.assertEqual(self.urls, [])
        self.assertEqual(R.SOURCE_FAILURES, {}, "a deliberate switch-off must not read as degraded coverage")
        self.assertIn("openalex", R.disabled_engines())

    def test_other_engines_still_answer(self):
        os.environ["SCHOLARLY_DISABLE"] = "openalex, dblp"
        self.assertEqual(R.get_json("https://api.crossref.org/works/10.1/x"), {"ok": 1})
        self.assertIsNone(R.get_json("https://sparql.dblp.org/sparql?query=x"))
        self.assertEqual(len(self.urls), 1)

    def test_unknown_engine_name_is_rejected(self):
        os.environ["SCHOLARLY_DISABLE"] = "opnealex"
        with self.assertRaises(ValueError):
            R.disabled_engines()


if __name__ == "__main__":
    unittest.main()
