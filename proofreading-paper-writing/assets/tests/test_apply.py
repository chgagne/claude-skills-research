# tests/test_apply.py
import os, unittest
from proofread.ledger import Row
from proofread.apply import apply_ledger

HERE = os.path.dirname(__file__)
with open(os.path.join(HERE, "fixtures", "tiny.tex"), encoding="utf-8") as fh:
    TEX = fh.read()

def row(id, level, anchor, replacement, comment="", rule="defaults:x", status="kept"):
    if level in ("flow", "framing"):
        replacement = None
    if level != "mechanics" and not comment:
        comment = f"{id}: note"
    return Row(id=id, level=level, section="1", para=1, anchor=anchor, replacement=replacement,
               comment=comment, rationale="r", rule=rule, confidence=0.8, status=status)

class TestApply(unittest.TestCase):
    def test_unique_prose_anchor_is_applied(self):
        r = row("W1", "mechanics", "Our method is very novel", "Our method is novel")
        out = apply_ledger(TEX, [r])
        self.assertEqual(r.status, "applied")
        self.assertIn(r"\chreplaced[id=LG]{Our method is novel}{Our method is very novel}", out.tex)
        self.assertEqual(out.applied, 1)

    def test_ambiguous_anchor_degrades_to_paragraph_comment(self):
        r = row("W2", "style", "The widget count vary across runs", "The widget count varies across runs")
        out = apply_ledger(TEX, [r])
        self.assertEqual(r.status, "degraded")
        self.assertIn("2 matches", r.cut_reason)
        self.assertNotIn(r"\chreplaced", out.tex)
        # comment sits at the start of the first paragraph containing the anchor
        self.assertTrue(out.tex[out.tex.index(r"\chcomment[id=LG]{W2"):].split("}", 1)[1].lstrip().startswith("The widget count vary across runs~"))

    def test_apply_matches_across_line_break(self):
        r = row("W3", "mechanics", "We observe that the widget count vary", "We observe that the widget count varies")
        out = apply_ledger(TEX, [r])
        self.assertEqual(r.status, "applied")
        self.assertIn(r"\chreplaced[id=LG]{We observe that the widget count varies}{We observe that", out.tex)

    def test_forbidden_context_degrades_with_kind(self):
        r = row("W4", "mechanics", "Also very novel", "Also novel")
        out = apply_ledger(TEX, [r])
        self.assertEqual(r.status, "degraded")
        self.assertIn("footnote", r.cut_reason)

    def test_not_whole_token_degrades(self):
        r = row("W5", "mechanics", "ery novel. It is", "ery new. It is")
        apply_ledger(TEX, [r])
        self.assertEqual(r.status, "degraded")
        self.assertIn("whole token", r.cut_reason)

    def test_overlapping_rows_second_degrades(self):
        a = row("W6", "style", "Our method is very novel", "Our method is novel")
        b = row("W7", "mechanics", "very novel. It", "very novel; it")
        out = apply_ledger(TEX, [a, b])
        self.assertEqual(a.status, "applied")
        self.assertEqual(b.status, "degraded")
        self.assertIn("overlaps W6", b.cut_reason)

    def test_flow_row_is_comment_at_paragraph_start(self):
        r = row("W8", "flow", "Our method is very novel", None, comment="W8: claim before evidence")
        out = apply_ledger(TEX, [r])
        self.assertEqual(r.status, "applied")
        i = out.tex.index(r"\chcomment[id=LG]{W8: claim before evidence}")
        self.assertTrue(out.tex[i + len(r"\chcomment[id=LG]{W8: claim before evidence}"):].startswith("Our method"))

    def test_fragile_macro_degrades(self):
        tex2 = TEX + "\n\\section{More}\n\\backto{app:x}\nText after.\n"
        r = row("W20", "mechanics", "\\backto{app:x}", "\\backto*{app:x}")
        apply_ledger(tex2, [r])
        self.assertEqual(r.status, "degraded")
        self.assertIn("fragile macro", r.cut_reason)

    def test_allowed_macros_still_apply(self):
        r = row("W21", "mechanics", "It is described in Section~\\ref{sec:m}", "It is described in \\sref{sec:m}")
        apply_ledger(TEX, [r])
        self.assertEqual(r.status, "applied")

    def test_style_edit_in_caption_keeps_edit_drops_comment(self):
        r = row("W30", "style", "Blue marks the median", "Blue marks the mean")
        out = apply_ledger(TEX, [r])
        self.assertEqual(r.status, "applied")
        self.assertIn(r"\chreplaced[id=LG]{Blue marks the mean}{Blue marks the median}", out.tex)
        self.assertNotIn(r"\chcomment[id=LG]{W30", out.tex)
        self.assertIn("comment omitted", r.cut_reason)

    def test_flow_row_in_caption_comments_before_the_float(self):
        r = row("W31", "flow", "Blue marks the median", None)
        out = apply_ledger(TEX, [r])
        i = out.tex.index(r"\chcomment[id=LG]{W31")
        self.assertTrue(out.tex[i:].split("}", 1)[1].startswith("\\begin{figure}"))

    def test_unanchored_row(self):
        r = row("W9", "mechanics", "this sentence does not exist", "x")
        out = apply_ledger(TEX, [r])
        self.assertEqual(r.status, "unanchored")
        self.assertEqual(out.unanchored, 1)
        self.assertNotIn("W9", out.tex)

    def test_only_kept_rows_and_selected_levels(self):
        a = row("W10", "mechanics", "Our method is very novel", "Our method is novel", status="cut")
        b = row("W11", "flow", "Our method is very novel", None)
        out = apply_ledger(TEX, [a, b], levels={"mechanics", "style"})
        self.assertEqual(a.status, "cut")
        self.assertEqual(b.status, "kept")
        self.assertNotIn("LG", out.tex)

    def test_offsets_stay_valid_with_many_edits(self):
        rows = [row("W12", "mechanics", "Our method is very novel", "Our method is novel"),
                row("W13", "mechanics", "ends the section", "closes the section"),
                row("W14", "mechanics", "Blue marks the median", "Blue marks the mean")]
        out = apply_ledger(TEX, rows)
        self.assertEqual([r.status for r in rows], ["applied"] * 3)
        for r in rows:
            self.assertIn("{%s}{%s}" % (r.replacement, r.anchor), out.tex)
