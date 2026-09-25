# tests/test_build.py
import os, shutil, tempfile, unittest
from proofread.build import toggle_final, latexmk_available, compile_pdf, render_with_bisect
from proofread.ledger import Row

PRE_LINE = "\\usepackage[commandnameprefix=always,todonotes={textsize=tiny,color=yellow!30}]{changes}"

class TestToggle(unittest.TestCase):
    def test_toggle_final_rewrites_the_option_list(self):
        out = toggle_final("a\n" + PRE_LINE + "\nb\n")
        self.assertIn("\\usepackage[final,commandnameprefix=always]{changes}", out)
        self.assertNotIn("todonotes=", out)

    def test_toggle_is_idempotent(self):
        once = toggle_final(PRE_LINE)
        self.assertEqual(toggle_final(once), once)

@unittest.skipUnless(latexmk_available(), "latexmk not installed")
class TestCompile(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.paper = os.path.join(self.d, "paper"); os.makedirs(self.paper)
        self.scratch = os.path.join(self.d, "scratch")
        with open(os.path.join(self.paper, "ok.tex"), "w") as fh:
            fh.write("\\documentclass{article}\\begin{document}hi\\end{document}\n")
        with open(os.path.join(self.paper, "bad.tex"), "w") as fh:
            fh.write("\\documentclass{article}\\begin{document}\\undefinedmacro\\end{document}\n")

    def tearDown(self):
        shutil.rmtree(self.d)

    def test_ok_compiles(self):
        r = compile_pdf(os.path.join(self.paper, "ok.tex"), self.scratch)
        self.assertTrue(r.ok); self.assertTrue(os.path.exists(r.pdf))

    def test_bad_fails_with_log_tail(self):
        r = compile_pdf(os.path.join(self.paper, "bad.tex"), self.scratch)
        self.assertFalse(r.ok); self.assertIn("undefinedmacro", r.log_tail)

    def test_bisect_drops_levels_until_build_passes(self):
        base = ("\\documentclass{article}\n\\usepackage{xcolor}\n" + PRE_LINE + "\n"
                "\\definechangesauthor[name={Claude}, color=blue]{CL}\n\\setlength{\\marginparwidth}{1.6cm}\n"
                "\\definechangesauthor[name={Claude (writing)}, color=green!50!black]{LG}\n"
                "\\begin{document}\n\nGood prose here. More prose.\n\n\\end{document}\n")
        rows = [Row("W1", "mechanics", "1", 1, "Good prose", "Fine prose", "", "r", "", 0.9, "kept"),
                Row("W2", "flow", "1", 1, "Good prose here", None, "W2: \\brokenmacro", "r", "defaults:x", 0.9, "kept")]
        tex, builds, dropped = render_with_bisect(base, rows, self.paper, "annot.tex", self.scratch)
        self.assertTrue(builds["markup"])
        self.assertEqual(dropped, ["flow", "framing"])
        self.assertIn("{Fine prose}{Good prose}", tex); self.assertNotIn("brokenmacro", tex)
        self.assertEqual(rows[1].status, "kept")   # reset, not applied
