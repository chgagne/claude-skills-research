# tests/test_second_pass.py
import importlib.util, json, os, pathlib, subprocess, sys, tempfile, unittest

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT = HERE.parent / "second-pass.py"
spec = importlib.util.spec_from_file_location("sp", SCRIPT)
sp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sp)

TEX = r"""\documentclass{article}
\begin{document}
\begin{abstract}
We study things. The results shows gains.
\end{abstract}
\section{Introduction}
Intro text one. Intro text two is here.
\section{Method}\label{sec:m}
Method text with a duplicated the the word.
\subsection{Detail}
Detail text.
\appendix
\section{Extra}
Appendix text.
\end{document}
"""


def row(anchor, level="mechanics", **kw):
    r = {"level": level, "section": "1", "para": 1, "anchor": anchor, "replacement": "x",
         "comment": "", "rationale": "r", "rule": "", "confidence": 0.9}
    r.update(kw)
    return r


class TestSplit(unittest.TestCase):
    def test_sections_in_order_with_abstract(self):
        secs = sp.sections(TEX)
        self.assertEqual([s["title"] for s in secs], ["Abstract", "Introduction", "Method", "Extra"])
        self.assertIn("duplicated the the", secs[2]["text"])
        self.assertIn("Detail text", secs[2]["text"])   # subsections stay with their section

    def test_split_writes_files_and_anchors(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)
            (p / "paper.tex").write_text(TEX)
            led = p / "writing-ledger.jsonl"
            led.write_text(json.dumps({**row("Intro text two"), "id": "W1"}) + "\n")
            sp.split(p / "paper.tex", led, p / "pass2")
            meta = json.loads((p / "pass2" / "sections.json").read_text())
            self.assertEqual(len(meta), 4)
            self.assertTrue((p / "pass2" / "sec-02.tex").exists())
            self.assertIn("Intro text two", (p / "pass2" / "sec-02.anchors.txt").read_text())


class TestMerge(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); p = self.p = pathlib.Path(self.d.name)
        (p / "paper.tex").write_text(TEX)
        self.led = p / "writing-ledger.jsonl"
        self.led.write_text(json.dumps({**row("Intro text two"), "id": "W1"}) + "\n" +
                            json.dumps({**row("We study things"), "id": "W7"}) + "\n")
        sp.split(p / "paper.tex", self.led, p / "pass2")

    def tearDown(self):
        self.d.cleanup()

    def put(self, k, lines):
        (self.p / "pass2" / f"sec-{k:02d}.jsonl").write_text("\n".join(json.dumps(x) for x in lines) + "\n")

    def test_refuses_missing_section(self):
        self.put(1, [{"none": "re-read abstract"}])
        with self.assertRaises(SystemExit) as cm:
            sp.merge(self.led, self.p / "pass2")
        self.assertIn("sec-02", str(cm.exception))

    def test_refuses_bare_none(self):
        for k in range(1, 5):
            self.put(k, [{"none": ""}])
        with self.assertRaises(SystemExit):
            sp.merge(self.led, self.p / "pass2")

    def test_merge_appends_with_new_ids(self):
        self.put(1, [{"none": "re-read the abstract"}])
        self.put(2, [{"none": "intro re-read"}])
        self.put(3, [row("duplicated the the word", replacement="duplicated the word")])
        self.put(4, [row("Appendix text", level="style", rule="clarity: vague", comment="W0: vague")])
        n = sp.merge(self.led, self.p / "pass2")
        self.assertEqual(n, 2)
        rows = [json.loads(l) for l in self.led.read_text().splitlines() if l.strip()]
        self.assertEqual([r["id"] for r in rows], ["W1", "W7", "W8", "W9"])
        self.assertEqual(rows[3]["comment"], "W9: vague")     # tag rewritten to the new id
        self.assertEqual(rows[2]["status"], "proposed")

    def test_merge_twice_refused(self):
        for k in range(1, 5):
            self.put(k, [{"none": "re-read the section"}])
        sp.merge(self.led, self.p / "pass2")
        with self.assertRaises(SystemExit):
            sp.merge(self.led, self.p / "pass2")

    def test_duplicate_anchor_dropped(self):
        for k in (1, 2, 4):
            self.put(k, [{"none": "re-read the section"}])
        self.put(3, [row("Intro text two")])          # already in the ledger
        self.assertEqual(sp.merge(self.led, self.p / "pass2"), 0)


class TestCLI(unittest.TestCase):
    def test_split_cli(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d); (p / "paper.tex").write_text(TEX); (p / "writing-ledger.jsonl").write_text("")
            o = subprocess.run([sys.executable, str(SCRIPT), "split", "paper.tex", "--ledger", "writing-ledger.jsonl"],
                               cwd=d, capture_output=True, text=True)
            self.assertEqual(o.returncode, 0, o.stderr)
            self.assertIn("4 sections", o.stdout)


if __name__ == "__main__":
    unittest.main()
