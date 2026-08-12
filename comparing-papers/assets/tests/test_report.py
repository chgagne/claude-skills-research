import unittest, sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))
from compare.report import to_json, to_markdown
from compare.assemble import Row
from compare.axes import AXES, Evidence
from compare.resolve import PaperRef


def ev(value, quote="a quote", section="Setup", found=True):
    return Evidence(axis="x", value=value, quote=quote, section=section, found=found)


ROWS = [
    Row(axis="training_scale",
        draft=ev("6.4M examples (100K updates x 64 batch)", "10^5 updates", "Optimization"),
        others={"SNIP": ev("60M examples (stated)", "60 million examples", "Pre-training")},
        note="SNIP: 6.4M vs 60M — about 11% of the other paper's scale"),
    Row(axis="checkpoint", draft=Evidence(axis="checkpoint"),
        others={"SNIP": Evidence(axis="checkpoint")}, note=""),
]

REFS = {"SNIP": PaperRef(title="SNIP: Bridging Realms", year=2023, venue="ICLR",
                         arxiv_id="2310.02227")}
SOURCES = {"(draft)": ("local-latex", False), "SNIP": ("arxiv-latex", False)}


class TestMarkdown(unittest.TestCase):
    def test_axis_headings_appear_in_canonical_order(self):
        md = to_markdown(ROWS, REFS, SOURCES)
        self.assertLess(md.index("training_scale"), md.index("checkpoint"))

    def test_note_is_shown_prominently(self):
        md = to_markdown(ROWS, REFS, SOURCES)
        self.assertIn("about 11%", md)

    def test_not_found_renders_as_a_dash_never_blank(self):
        md = to_markdown(ROWS, REFS, SOURCES)
        row = [l for l in md.splitlines()
               if l.startswith("|") and "SNIP" in l and "60M" not in l]
        self.assertTrue(any("—" in l for l in row), row)

    def test_quotes_carry_their_section(self):
        md = to_markdown(ROWS, REFS, SOURCES)
        self.assertIn("Optimization", md)
        self.assertIn("10^5 updates", md)

    def test_pipes_in_quotes_are_escaped(self):
        import re
        rows = [Row(axis="results", draft=ev("v", "a | b", "S"), others={}, note="")]
        md = to_markdown(rows, {}, SOURCES)
        line = [l for l in md.splitlines() if "a \\| b" in l]
        self.assertTrue(line, "pipe was not escaped")

    def test_degraded_source_raises_a_banner(self):
        md = to_markdown(ROWS, REFS, {"SNIP": ("abstract", True)})
        self.assertIn("abstract", md.lower())
        self.assertIn("degraded", md.lower())

    def test_no_banner_when_every_document_is_full_text(self):
        self.assertNotIn("degraded", to_markdown(ROWS, REFS, SOURCES).lower())

    def test_paper_identity_is_stated(self):
        md = to_markdown(ROWS, REFS, SOURCES)
        self.assertIn("2310.02227", md)
        self.assertIn("2023", md)

    def test_evidence_not_judgement_is_stated_in_the_report(self):
        md = to_markdown(ROWS, REFS, SOURCES)
        self.assertIn("judge", md.lower())


class TestJson(unittest.TestCase):
    def test_round_trips_with_provenance(self):
        data = json.loads(to_json(ROWS))
        first = data[0]
        self.assertEqual(first["axis"], "training_scale")
        self.assertEqual(first["draft"]["section"], "Optimization")
        self.assertIn("SNIP", first["others"])
        self.assertIn("11%", first["note"])

    def test_not_found_is_explicit_in_json(self):
        data = json.loads(to_json(ROWS))
        self.assertFalse(data[1]["draft"]["found"])


if __name__ == "__main__":
    unittest.main()
