"""Offline tests for check-review-form.py --floats / --list-floats (stdlib only)."""
import importlib.util, pathlib, tempfile, unittest

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("crf3", HERE.parent / "check-review-form.py")
crf = importlib.util.module_from_spec(spec); spec.loader.exec_module(crf)

PAPER = r"""\documentclass{article}
\begin{document}
\input{sec}
\begin{figure*}\begin{subfigure}{a}\includegraphics{x}\caption{sub a}\end{subfigure}
\caption{Overview of the method. More.}\label{fig:ov}\end{figure*}
\begin{table}\caption{Main results.}\label{tab:main}\end{table}
\end{document}
"""
SEC = r"\begin{figure}\includegraphics{y}\caption{Early plot}\label{fig:early}\end{figure}" + "\n"

class Floats(unittest.TestCase):
    def setUp(self):
        d = pathlib.Path(tempfile.mkdtemp()); (d / "paper.tex").write_text(PAPER); (d / "sec.tex").write_text(SEC)
        self.items = crf.floats(d / "paper.tex")
    def test_ids_in_source_order_including_inputs(self):
        self.assertEqual([i["id"] for i in self.items], ["F1", "F2", "T1"])
        self.assertEqual(self.items[0]["labels"], ["fig:early"])
    def test_main_caption_not_subcaption(self):
        self.assertTrue(self.items[1]["caption"].startswith("Overview of the method"))

class Rows(unittest.TestCase):
    INV = [{"id": "F1", "kind": "figure", "labels": ["fig:a"], "caption": "A plot"}, {"id": "T1", "kind": "table", "labels": [], "caption": "Results"}]
    def review(self, rows):
        return "## 6. Figures and tables\n\n| id | shows | supports citing claim | problem |\n|---|---|---|---|\n" + rows + "\n## 7. Detailed comments by section\n\nx\n"
    def test_complete_rows_pass(self):
        self.assertEqual(crf.check_inventory(self.review("| F1 | a bar chart | partly | x |\n| T1 | accuracy | not cited | — |"), self.INV), [])
    def test_missing_row_names_caption(self):
        p = crf.check_inventory(self.review("| F1 | a bar chart | yes | — |"), self.INV)
        self.assertTrue(any("no row for T1" in x and "Results" in x for x in p), p)
    def test_bad_supports_and_empty_shows(self):
        p = crf.check_inventory(self.review("| F1 |  | maybe | x |\n| T1 | t | yes | — |"), self.INV)
        self.assertTrue(any("'shows' is empty" in x for x in p)); self.assertTrue(any("yes / partly" in x for x in p))

if __name__ == "__main__":
    unittest.main()
