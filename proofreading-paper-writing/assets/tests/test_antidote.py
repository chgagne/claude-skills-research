# tests/test_antidote.py
import os, unittest
from proofread.antidote import antidote_rows
from proofread.anchors import find_normalised
from proofread.apply import apply_ledger
from proofread.ledger import Row, validate

HERE = os.path.dirname(__file__)
def _read(name):
    with open(os.path.join(HERE, "fixtures", name), encoding="utf-8") as fh:
        return fh.read()
ORIG, CORR = _read("antidote-orig.tex"), _read("antidote-corrected.tex")


class TestAntidoteRows(unittest.TestCase):
    def setUp(self):
        self.rows, self.rejected = antidote_rows(ORIG, CORR, start=900)
        self.by_anchor = {" ".join(r.anchor.split()): r for r in self.rows}

    def _has(self, before, after):
        for r in self.rows:
            if before in " ".join(r.anchor.split()) and after in r.replacement:
                return r
        self.fail(f"no row {before!r} -> {after!r}; rows: {[(r.anchor, r.replacement) for r in self.rows]}")

    def test_word_fixes_become_mechanics_rows(self):
        self._has("profond", "profonds")
        self._has("révolutionnés", "révolutionné")
        self._has("tres", "très")
        self._has("encourageant", "encourageants")
        self._has("attein", "a atteint")
        self._has("préliminaire,", "préliminaires,")

    def test_ambiguous_word_gets_context(self):
        r = self._has("comparativement a", "comparativement à")
        self.assertEqual(len(find_normalised(ORIG, r.anchor)), 1)

    def test_rows_are_valid_unique_and_numbered_from_start(self):
        self.assertTrue(self.rows)
        for i, r in enumerate(self.rows):
            self.assertEqual(r.id, f"W{900 + i}")
            self.assertEqual(r.level, "mechanics")
            self.assertEqual(validate(r), [])
            self.assertEqual(len(find_normalised(ORIG, r.anchor)), 1, r.anchor)

    def test_unescaped_percent_is_rejected(self):
        self.assertTrue(any("unescaped %" in x["reason"] for x in self.rejected), self.rejected)
        for r in self.rows:
            self.assertNotRegex(r.replacement, r"(?<!\\)%")

    def test_markup_and_garble_never_become_rows(self):
        for r in self.rows:
            self.assertNotIn("\\cite", r.anchor + r.replacement)
            self.assertNotIn("he2016deep", r.replacement)
            self.assertNotIn("suggèrent", r.anchor)    # garbled into "su~he2016deep."
        reasons = " ".join(x["reason"] for x in self.rejected)
        self.assertIn("LaTeX markup", reasons)          # référence \cite -> référence\cite
        self.assertIn("citation key", reasons)          # su~he2016deep.

    def test_rewrite_goes_to_review_not_rows(self):
        self.assertTrue(any("tel que" in x["before"] for x in self.rejected))
        self.assertFalse(any("tel" in r.anchor for r in self.rows))

    def test_spacing_only_changes_are_dropped(self):
        # "~:" before a colon and line merges are neither rows nor review items
        for x in self.rejected:
            self.assertNotEqual(x["before"].replace("~", " ").split(), x["after"].replace("~", " ").split())

    def test_rows_apply_cleanly_to_the_original(self):
        for r in self.rows:
            r.status = "kept"
        out = apply_ledger(ORIG, self.rows)
        self.assertEqual(out.degraded + out.unanchored, 0, [(r.anchor, r.cut_reason) for r in self.rows])
        self.assertIn(r"94,2\%", out.tex)               # the original escape survives

    def test_rows_overlapping_existing_ledger_are_skipped(self):
        existing = [Row(id="W101", level="style", section="1", para=1,
                        anchor="Les réseaux de neurones profond", replacement="Les réseaux profonds",
                        comment="W101: x", rationale="r", rule="defaults:x", confidence=0.9)]
        rows, rejected = antidote_rows(ORIG, CORR, start=900, existing=existing)
        self.assertFalse(any("profond" in r.anchor for r in rows))
        self.assertTrue(any("duplicate of W101" in x["reason"] for x in rejected))

    def test_section_and_paragraph_are_located(self):
        r = self._has("attein", "a atteint")
        self.assertEqual(r.section, "1")
        self.assertEqual(r.para, 2)


class TestAntidoteCLI(unittest.TestCase):
    def setUp(self):
        import importlib.util, json, shutil, tempfile
        spec = importlib.util.spec_from_file_location("antidote_cli", os.path.join(HERE, "..", "antidote-rows.py"))
        self.cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.cli)
        self.d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.d)
        for name, dst in (("antidote-orig.tex", "main.tex"), ("antidote-corrected.tex", "antidote.tex")):
            shutil.copy(os.path.join(HERE, "fixtures", name), os.path.join(self.d, dst))
        self.ledger = os.path.join(self.d, "writing-ledger.jsonl")
        with open(self.ledger, "w") as fh:
            fh.write(json.dumps({"id": "W205", "level": "mechanics", "section": "1", "para": 1,
                                 "anchor": "Dans cet article", "replacement": "Ici", "comment": "",
                                 "rationale": "r", "rule": "", "confidence": 0.9}) + "\n")

    def test_appends_after_the_last_block_and_writes_review(self):
        from proofread.ledger import load_ledger
        p = lambda n: os.path.join(self.d, n)
        rc = self.cli.main(["--orig", p("main.tex"), "--corrected", p("antidote.tex"),
                            "--ledger", self.ledger, "--review", p("antidote-review.md")])
        self.assertEqual(rc, 0)
        rows = load_ledger(self.ledger)
        self.assertEqual(rows[0].id, "W205")
        self.assertEqual(rows[1].id, "W300")
        self.assertTrue(all(r.rule == "tool:antidote" for r in rows[1:]))
        with open(p("antidote-review.md"), encoding="utf-8") as fh:
            review = fh.read()
        self.assertIn("unescaped %", review)
        self.assertNotIn("antidote-orig", review)          # comment edits are counted, not listed
        self.assertIn("edits inside LaTeX comments ignored", review)
        with open(p("main.tex"), encoding="utf-8") as fh:
            self.assertIn(r"94,2\%", fh.read())          # the original is never touched


if __name__ == "__main__":
    unittest.main()
