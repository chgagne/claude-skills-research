"""Loading verdicts from `verifying-proofs`.

The *Checked* column is the join between the two skills, and it is the one place
where "no evidence" and "evidence not supplied" look identical in the finished
PDF. A verdicts file that loads to nothing must therefore fail loudly: the
expander is forbidden to write a verdict it did not receive, so a silent empty
mapping yields a document of *not run* cells that reads exactly like a paper on
which no engine could fire.
"""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))

from explain import ledger_io as L  # noqa: E402

CSV = """claim,proof,step,kind,engine,verdict,severity,detail,script
claim/lem:a,proof/lem:a,proof/lem:a/s01,narration,,SKIP,SKIP,not an inference,
claim/lem:a,proof/lem:a,proof/lem:a/s02,display,sympy,REFUTED,CRITICAL,rhs - lhs < 0,checks/a-s02.py
"""


class TestLoadVerdicts(unittest.TestCase):
    def _write(self, name, text):
        path = pathlib.Path(self.tmp.name) / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_no_path_is_no_verdicts(self):
        self.assertEqual(L.load_verdicts(None), {})

    def test_a_missing_file_is_an_error_not_an_empty_mapping(self):
        with self.assertRaises(ValueError):
            L.load_verdicts(str(pathlib.Path(self.tmp.name) / "absent.csv"))

    def test_proofsteps_csv_keys_on_step_id_and_carries_the_script(self):
        got = L.load_verdicts(self._write("proofsteps.csv", CSV))
        self.assertEqual(sorted(got), ["proof/lem:a/s01", "proof/lem:a/s02"])
        self.assertEqual(got["proof/lem:a/s02"],
                         {"verdict": "CRITICAL", "engine": "sympy",
                          "script": "checks/a-s02.py"})

    def test_a_json_object_keyed_by_step_is_accepted(self):
        payload = {"proof/lem:a/s02": {"verdict": "MAJOR", "engine": "sideconds"}}
        got = L.load_verdicts(self._write("v.json", json.dumps(payload)))
        self.assertEqual(got, payload)

    def test_a_wrapper_object_is_unwrapped(self):
        payload = {"verdicts": {"proof/lem:a/s02": {"verdict": "WEAK"}}}
        got = L.load_verdicts(self._write("v.json", json.dumps(payload)))
        self.assertEqual(sorted(got), ["proof/lem:a/s02"])

    def test_the_step_ledger_is_refused_rather_than_read_as_empty(self):
        """The wrong file that is easy to reach for: it sits in the same
        directory, it is the one named in older notes, and every key it has is a
        section of the ledger rather than a step."""
        ledger = {"schema": "latexmath-ledger/1", "claims": [], "proofs": [],
                  "steps": [{"id": "proof/lem:a/s01"}], "symbols": []}
        path = self._write("proof-ledger.json", json.dumps(ledger))
        with self.assertRaises(ValueError) as caught:
            L.load_verdicts(path)
        self.assertIn("proofsteps.csv", str(caught.exception))

    def test_an_empty_json_mapping_is_still_allowed(self):
        """A paper on which no engine fired is a real result, not a mistake."""
        self.assertEqual(L.load_verdicts(self._write("v.json", "{}")), {})


if __name__ == "__main__":
    unittest.main()
