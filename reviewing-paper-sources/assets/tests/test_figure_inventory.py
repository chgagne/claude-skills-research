"""Offline tests for figure-inventory.py and check-review-form.py --inventory (stdlib only)."""
import importlib.util, json, pathlib, tempfile, unittest

HERE = pathlib.Path(__file__).resolve().parent
def load(name, fn):
    spec = importlib.util.spec_from_file_location(name, HERE.parent / fn); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
fi = load("fi", "figure-inventory.py"); crf = load("crf2", "check-review-form.py")

PAPER = r"""\documentclass{article}
\usepackage{graphicx}\graphicspath{{figs/}}
\begin{document}
\input{sec}
\begin{figure*}[t]\centering\includegraphics[width=\linewidth]{overview}
\caption{Overview of the method. More text.}\label{fig:ov}\end{figure*}
\begin{table}\caption{Main results on three benchmarks.}\label{tab:main}\begin{tabular}{c}x\end{tabular}\end{table}
\begin{figure}\includegraphics{missing}\caption{Unreferenced plot}\label{fig:un}\end{figure}
\end{document}
"""
SEC = "As Fig.~\\ref{fig:ov} shows, it works. Table~\\ref{tab:main} reports gains.\n\nOther text, see \\cref{fig:ov,tab:main}.\n"

class Inventory(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        (self.d / "paper.tex").write_text(PAPER); (self.d / "sec.tex").write_text(SEC)
        (self.d / "figs").mkdir(); (self.d / "figs" / "overview.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        self.out = self.d / "out"; self.out.mkdir()
        self.items = fi.inventory(self.d, self.out)

    def test_items_and_ids(self):
        self.assertEqual([i["id"] for i in self.items], ["F1", "T1", "F2"])
        self.assertEqual(self.items[0]["labels"], ["fig:ov"])
        self.assertEqual(self.items[0]["caption"], "Overview of the method")

    def test_files_resolved_and_rendered(self):
        f = self.items[0]["files"][0]; self.assertTrue(f["found"]); self.assertTrue(f["render"].endswith("F1_1.png"))
        self.assertFalse(self.items[2]["files"][0]["found"])

    def test_citing_sentences_include_multi_ref(self):
        self.assertEqual(len(self.items[0]["cited_by"]), 2)
        self.assertEqual(len(self.items[1]["cited_by"]), 2)
        self.assertEqual(self.items[2]["cited_by"], [])

    def test_markdown_lists_every_id(self):
        fi.write_md(self.items, self.out); md = (self.out / "inventory.md").read_text()
        for i in ("F1", "T1", "F2"): self.assertIn(f"| {i} | | | |", md)
        self.assertIn("never referenced", md); self.assertIn("FILE MISSING", md)

class InventoryRows(unittest.TestCase):
    INV = [{"id": "F1", "kind": "figure", "labels": ["fig:a"]}, {"id": "T1", "kind": "table", "labels": []}]
    def review(self, rows):
        return "## 6. Figures and tables\n\n| id | shows | supports citing claim | problem |\n|---|---|---|---|\n" + rows + "\n## 7. Detailed comments by section\n\nx\n"
    def test_complete_rows_pass(self):
        r = self.review("| F1 | a bar chart | partly | no error bars |\n| T1 | accuracy per dataset | not cited | — |")
        self.assertEqual(crf.check_inventory(r, self.INV), [])
    def test_missing_row(self):
        p = crf.check_inventory(self.review("| F1 | a bar chart | yes | — |"), self.INV)
        self.assertTrue(any("no row for T1" in x for x in p), p)
    def test_bad_supports_and_empty_shows(self):
        p = crf.check_inventory(self.review("| F1 |  | maybe | x |\n| T1 | t | yes | — |"), self.INV)
        self.assertTrue(any("'shows' is empty" in x for x in p)); self.assertTrue(any("yes / partly" in x for x in p))

if __name__ == "__main__":
    unittest.main()
