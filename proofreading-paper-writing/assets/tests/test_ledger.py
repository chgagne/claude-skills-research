# tests/test_ledger.py
import json, os, tempfile, unittest
from proofread.ledger import Row, validate, load_ledger, dump_ledger, parse_line

GOOD = {"id": "W1", "level": "style", "section": "3.1", "para": 2,
        "anchor": "Their location vary", "replacement": "Their location varies",
        "comment": "W1: agreement", "rationale": "singular subject",
        "rule": "defaults:agreement", "confidence": 0.9}

class TestValidate(unittest.TestCase):
    def test_good_row_has_no_errors(self):
        self.assertEqual(validate(parse_line(json.dumps(GOOD))), [])

    def test_style_row_needs_rule(self):
        r = parse_line(json.dumps({**GOOD, "rule": ""}))
        self.assertTrue(any("rule" in e for e in validate(r)))

    def test_flow_row_must_not_replace(self):
        r = parse_line(json.dumps({**GOOD, "level": "flow"}))
        self.assertTrue(any("replacement" in e for e in validate(r)))

    def test_comment_word_cap(self):
        r = parse_line(json.dumps({**GOOD, "comment": "W1: " + "word " * 16}))
        self.assertTrue(any("15 words" in e for e in validate(r)))

    def test_bad_level_and_id(self):
        r = parse_line(json.dumps({**GOOD, "level": "taste", "id": "12"}))
        errs = validate(r)
        self.assertTrue(any("level" in e for e in errs))
        self.assertTrue(any("id" in e for e in errs))

class TestIO(unittest.TestCase):
    def test_roundtrip(self):
        rows = [parse_line(json.dumps(GOOD)), parse_line(json.dumps({**GOOD, "id": "W2", "level": "mechanics", "comment": "", "rule": ""}))]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "l.jsonl")
            dump_ledger(rows, p)
            back = load_ledger(p)
        self.assertEqual([r.id for r in back], ["W1", "W2"])
        self.assertEqual(back[1].status, "proposed")

    def test_load_reports_every_error_with_line_number(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "l.jsonl")
            with open(p, "w") as fh:
                fh.write(json.dumps(GOOD) + "\n")
                fh.write(json.dumps({**GOOD, "id": "bad"}) + "\n")
                fh.write("not json\n")
            with self.assertRaises(ValueError) as cm:
                load_ledger(p)
        msg = str(cm.exception)
        self.assertIn("line 2", msg)
        self.assertIn("line 3", msg)
