# tests/test_preamble.py
import unittest
from proofread.preamble import ensure_changes, has_changes, has_author, LG_AUTHOR_LINE, ULEM_WORKAROUND

PRE = ("\\usepackage[commandnameprefix=always,todonotes={textsize=tiny,color=yellow!30}]{changes}\n"
       "\\definechangesauthor[name={Claude}, color=blue]{CL}\n"
       "\\setlength{\\marginparwidth}{1.6cm}\n")

PLAIN = "\\documentclass{article}\n\\usepackage{graphicx}\n\\usepackage{xcolor}\n\\begin{document}\nx\n\\end{document}\n"

class TestEnsure(unittest.TestCase):
    def test_inserts_preamble_after_last_usepackage_and_author_once(self):
        out = ensure_changes(PLAIN, PRE)
        self.assertTrue(has_changes(out))
        self.assertEqual(out.count(LG_AUTHOR_LINE), 1)
        self.assertLess(out.index("\\usepackage{xcolor}"), out.index("{changes}"))
        self.assertLess(out.index("{changes}"), out.index("\\begin{document}"))
        self.assertLess(out.index("{CL}"), out.index("{LG}"))
        # idempotent
        self.assertEqual(ensure_changes(out, PRE), out)

    def test_existing_changes_load_gets_only_the_author(self):
        tex = PLAIN.replace("\\begin{document}", PRE + "\\begin{document}")
        out = ensure_changes(tex, PRE)
        self.assertEqual(out.count("{changes}"), 1)
        self.assertTrue(has_author(out))

    def test_todo_defined_before_insertion_point_is_freed(self):
        tex = PLAIN.replace("\\usepackage{xcolor}", "\\newcommand{\\todo}[1]{\\textbf{#1}}\n\\usepackage{xcolor}")
        out = ensure_changes(tex, PRE)
        self.assertLess(out.index("\\let\\todo\\relax"), out.index("{changes}"))

    def test_todo_defined_after_insertion_point_is_commented(self):
        tex = PLAIN.replace("\\begin{document}", "\\newcommand{\\todo}[1]{\\textbf{#1}}\n\\begin{document}")
        out = ensure_changes(tex, PRE)
        self.assertIn("% LG: freed for todonotes -- \\newcommand{\\todo}[1]{\\textbf{#1}}", out)
        self.assertNotIn("\n\\newcommand{\\todo}", out)

    def test_forbid_ulem_adds_workaround_after_changes(self):
        out = ensure_changes(PLAIN, PRE, forbid_ulem=True)
        self.assertLess(out.index("{changes}"), out.index(ULEM_WORKAROUND.strip()))

    def test_no_usepackage_inserts_after_documentclass(self):
        tex = "\\documentclass{article}\n\\begin{document}\nx\n\\end{document}\n"
        out = ensure_changes(tex, PRE)
        self.assertLess(out.index("\\documentclass"), out.index("{changes}"))
        self.assertLess(out.index("{changes}"), out.index("\\begin{document}"))
