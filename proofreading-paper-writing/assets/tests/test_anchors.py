# tests/test_anchors.py
import os, unittest
from proofread.anchors import in_caption, find_all, find_normalised, spans, forbidden_context, paragraph_start, whole_token

HERE = os.path.dirname(__file__)
with open(os.path.join(HERE, "fixtures", "tiny.tex"), encoding="utf-8") as fh:
    TEX = fh.read()

class TestFind(unittest.TestCase):
    def test_find_all_counts_caption_occurrence(self):
        # once in prose, once in the caption -> ambiguous
        self.assertEqual(len(find_all(TEX, "The widget count vary across runs")), 2)

    def test_find_normalised_crosses_line_break(self):
        hits = find_normalised(TEX, "We observe that the widget count vary")
        self.assertEqual(len(hits), 1)
        s, e = hits[0]
        self.assertTrue(TEX[s:e].startswith("We observe"))
        self.assertTrue(TEX[s:e].endswith("vary"))

    def test_whole_token(self):
        pos = TEX.index("vary across")
        self.assertTrue(whole_token(TEX, pos, pos + 4))
        self.assertFalse(whole_token(TEX, pos + 1, pos + 4))   # "ary"

class TestForbidden(unittest.TestCase):
    def _ctx(self, needle, occurrence=0):
        pos = find_all(TEX, needle)[occurrence]
        return forbidden_context(TEX, pos, pos + len(needle))

    def test_cite(self):
        self.assertEqual(self._ctx("a2020"), "cite")

    def test_inline_math(self):
        self.assertEqual(self._ctx("mathrm{vary}"), "math")

    def test_tabular_inside_resizebox_reports_innermost(self):
        self.assertEqual(self._ctx("very novel", 1), "tabular")

    def test_footnote(self):
        self.assertEqual(self._ctx("Also very novel"), "footnote")

    def test_section_heading_is_forbidden(self):
        tex = "\\section{Where the widget forms\\backto{app:x}}\\label{sec:w}\nProse here."
        pos = tex.index("backto")
        self.assertEqual(forbidden_context(tex, pos, pos + 6), "heading")
        pos = tex.index("Prose")
        self.assertIsNone(forbidden_context(tex, pos, pos + 5))

    def test_caption_is_allowed(self):
        self.assertIsNone(self._ctx("Blue marks the median"))

    def test_prose_is_allowed(self):
        self.assertIsNone(self._ctx("Our method is very novel"))

    def test_existing_changes_markup_is_forbidden(self):
        tex = r"Some \chreplaced[id=CL]{new words}{old words} here."
        pos = tex.index("old")
        self.assertEqual(forbidden_context(tex, pos, pos + 3), "CL-markup")

class TestBoundaries(unittest.TestCase):
    def test_paragraph_start_after_begin_abstract_without_blank_line(self):
        tex = "\\usepackage{x}\n\n\\begin{document}\n\\maketitle\n\\begin{abstract}\nWe study widgets. More.\n\\end{abstract}\n"
        pos = tex.index("We study")
        self.assertEqual(paragraph_start(tex, pos), pos)

    def test_paragraph_start_inside_float_is_float_start(self):
        tex = "Prose.\n\n\\begin{figure}\n\\centering\n\\caption{A caption here.}\n\\end{figure}\n"
        pos = tex.index("A caption")
        self.assertEqual(paragraph_start(tex, pos), tex.index("\\begin{figure}"))

    def test_row_terminator_does_not_open_display_math(self):
        tex = "\\begin{tabular}{l}\na \\\\[2pt]\nb\n\\end{tabular}\nLater $x_{vary}$ prose."
        pos = tex.index("vary")
        self.assertEqual(forbidden_context(tex, pos, pos + 4), "math")

    def test_normalised_match_stops_at_paragraph_break(self):
        tex = "one two\n\nthree four"
        self.assertEqual(find_normalised(tex, "two three"), [])
        self.assertEqual(len(find_normalised("one two\nthree", "two three")), 1)

    def test_caption_context_is_reported(self):
        tex = "\\begin{figure}\\caption{Blue marks the median.}\\end{figure}"
        pos = tex.index("Blue")
        self.assertEqual(in_caption(tex, pos), True)
        self.assertEqual(in_caption(tex, 0), False)


class TestParagraph(unittest.TestCase):
    def test_paragraph_start_is_after_blank_line(self):
        pos = TEX.index("It is described")
        start = paragraph_start(TEX, pos)
        self.assertTrue(TEX[start:].startswith("Our method is very novel"))

    def test_paragraph_start_after_section_heading(self):
        pos = TEX.index("The widget count vary across runs~")
        start = paragraph_start(TEX, pos)
        self.assertTrue(TEX[start:].startswith("The widget count"))
