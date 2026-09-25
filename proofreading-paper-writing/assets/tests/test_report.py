# tests/test_report.py
import unittest
from proofread.ledger import Row
from proofread.report import RunHeader, render_report

def row(id, level, status, cut_reason=None, replacement="new"):
    if level in ("flow", "framing"):
        replacement = None
    return Row(id=id, level=level, section="2", para=3, anchor="old words", replacement=replacement,
               comment=f"{id}: c", rationale="because", rule="field:hedging", confidence=0.7,
               status=status, cut_reason=cut_reason)

HDR = RunHeader(paper="main.tex", mode="A", date="2026-09-25", field_profile="fields/demo",
                author_profile=None, run_rules=["keep hedges in Limitations"], dropped_levels=[],
                builds={"markup": True, "final": False})

class TestReport(unittest.TestCase):
    def setUp(self):
        self.rows = [row("W1", "mechanics", "applied"), row("W2", "style", "applied"),
                     row("W3", "flow", "degraded", "ambiguous anchor (2 matches)"),
                     row("W4", "style", "cut", "taste, not defect"), row("W5", "framing", "unanchored", "anchor not found")]
        self.md = render_report(self.rows, HDR)

    def test_header_lines(self):
        for s in ("**Mode:** A", "**Field profile:** fields/demo", "**Author profile:** none",
                  "keep hedges in Limitations", "**Markup build:** passed", "**Accept-all build:** failed"):
            self.assertIn(s, self.md)

    def test_counts_table(self):
        self.assertIn("| style | 1 | 0 | 1 |", self.md)   # level | applied | degraded | cut

    def test_entries_have_before_after_and_rule(self):
        i = self.md.index("### W2")
        block = self.md[i:self.md.index("### W3")]
        self.assertIn("**Before:**", block)
        self.assertIn("old words", block)
        self.assertIn("**After:**", block)
        self.assertIn("**Rule:** field:hedging", block)

    def test_flow_entry_has_no_after(self):
        i = self.md.index("### W3")
        block = self.md[i:self.md.index("## Cut")]
        self.assertNotIn("**After:**", block)
        self.assertIn("degraded", block)

    def test_cut_appendix_lists_cut_and_unanchored_with_reasons(self):
        i = self.md.index("## Cut")
        tail = self.md[i:]
        self.assertIn("W4", tail); self.assertIn("taste, not defect", tail)
        self.assertIn("W5", tail); self.assertIn("anchor not found", tail)
        self.assertNotIn("W1", tail)
