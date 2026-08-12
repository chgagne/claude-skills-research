import unittest, sys, pathlib, io, tarfile, gzip
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))
from compare import fulltext as F
from compare.resolve import PaperRef


def _tar(members):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, body in members:
            data = body.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


class TestLadder(unittest.TestCase):
    def setUp(self):
        self.orig = (F._arxiv_source, F._arxiv_pdf, F._oa_pdf, F._abstract)
        F._arxiv_source = lambda r: None
        F._arxiv_pdf = lambda r: None
        F._oa_pdf = lambda r: None
        F._abstract = lambda r: "an abstract"

    def tearDown(self):
        (F._arxiv_source, F._arxiv_pdf, F._oa_pdf, F._abstract) = self.orig

    def test_latex_source_is_preferred_over_pdf(self):
        F._arxiv_source = lambda r: _tar(
            [("main.tex", r"\section{Method}We train for 100 epochs.")])
        F._arxiv_pdf = lambda r: b"should not be used"
        doc = F.fetch(PaperRef(title="T", arxiv_id="2310.02227"))
        self.assertEqual(doc.source, "arxiv-latex")
        self.assertFalse(doc.degraded)
        self.assertIn("Method", [s for s, _ in doc.sections])

    def test_falls_back_to_abstract_and_marks_degraded(self):
        doc = F.fetch(PaperRef(title="T"))
        self.assertTrue(doc.degraded)
        self.assertEqual(doc.source, "abstract")
        self.assertIn("an abstract", doc.sections[0][1])

    def test_multi_file_latex_is_concatenated(self):
        F._arxiv_source = lambda r: _tar([
            ("main.tex", r"\section{Intro}A"),
            ("appendix.tex", r"\section{Appendix H}trained with seed 0")])
        doc = F.fetch(PaperRef(title="T", arxiv_id="x"))
        heads = [s for s, _ in doc.sections]
        self.assertIn("Intro", heads)
        self.assertIn("Appendix H", heads)

    def test_source_without_tex_is_not_full_text(self):
        F._arxiv_source = lambda r: _tar([("figure.pdf", "%PDF-1.4 binary junk")])
        doc = F.fetch(PaperRef(title="T", arxiv_id="x"))
        self.assertTrue(doc.degraded)

    def test_bare_gzipped_tex_is_handled(self):
        """arXiv serves single-file submissions as a plain gzipped .tex."""
        F._arxiv_source = lambda r: gzip.compress(
            rb"\section{Method}A single-file submission.")
        doc = F.fetch(PaperRef(title="T", arxiv_id="x"))
        self.assertEqual(doc.source, "arxiv-latex")
        self.assertIn("Method", [s for s, _ in doc.sections])

    def test_pdf_rung_used_when_source_unavailable(self):
        F._arxiv_pdf = lambda r: "text from pdf \\section{Results}numbers"
        doc = F.fetch(PaperRef(title="T", arxiv_id="x"))
        self.assertEqual(doc.source, "arxiv-pdf")
        self.assertFalse(doc.degraded)

    def test_open_access_pdf_is_the_third_rung(self):
        F._oa_pdf = lambda r: "text from an open access pdf"
        doc = F.fetch(PaperRef(title="T", doi="10.1/x"))
        self.assertEqual(doc.source, "oa-pdf")


class TestSections(unittest.TestCase):
    def test_split_keeps_appendices_and_starred_headings(self):
        text = r"\section{Method}m\section*{Appendix H}h\subsection{H.1}x"
        heads = [s for s, _ in F.split_sections(text)]
        self.assertIn("Method", heads)
        self.assertIn("Appendix H", heads)
        self.assertIn("H.1", heads)

    def test_body_text_is_attached_to_its_heading(self):
        text = r"\section{Method}we train for 100 epochs\section{Results}0.73"
        got = dict(F.split_sections(text))
        self.assertIn("100 epochs", got["Method"])
        self.assertNotIn("0.73", got["Method"])

    def test_text_before_the_first_heading_is_kept(self):
        got = F.split_sections("preamble words \\section{Method}m")
        self.assertTrue(any("preamble" in body for _, body in got))

    def test_comments_are_stripped(self):
        text = "\\section{Method}real text\n% a deleted caveat\nmore text"
        body = dict(F.split_sections(text))["Method"]
        self.assertNotIn("deleted caveat", body)

    def test_math_delimiters_are_removed_from_numbers(self):
        """SNIP writes its scale as "$60$ million"; SNIP++ writes "$10^5$ updates"."""
        got = dict(F.split_sections(
            r"\section{Pre-training}pre-trained on approximately $60$ million pairs"))
        self.assertIn("60 million", got["Pre-training"])
        self.assertNotIn("$", got["Pre-training"])

    def test_common_math_commands_become_readable(self):
        got = dict(F.split_sections(
            r"\section{Setup}a total of $\approx 220$ epochs and $10^5$ updates"))
        body = got["Setup"]
        self.assertIn("220", body)
        self.assertIn("10^5", body)
        self.assertNotIn("approx", body)

    def test_paragraph_headings_lose_their_trailing_period(self):
        heads = [h for h, _ in F.split_sections(
            r"\paragraph{Optimization.}we train\paragraph{Setup:}x")]
        self.assertIn("Optimization", heads)
        self.assertIn("Setup", heads)

    def test_no_headings_yields_one_body_section(self):
        got = F.split_sections("just a plain abstract with no markup")
        self.assertEqual(len(got), 1)


if __name__ == "__main__":
    unittest.main()
