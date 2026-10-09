"""Finding the draft's main file. arXiv sources rarely use main.tex (iclr2027_conference.tex,
neurips_2026.tex, ...), and an alphabetical guess can land on an appendix."""
import unittest, sys, pathlib, tempfile, os
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from survey.__main__ import _find_main_tex, _resolve_main


class TestMainTex(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def write(self, name, body):
        with open(os.path.join(self.d, name), "w") as fh:
            fh.write(body)

    def test_prefers_the_file_with_documentclass(self):
        self.write("appendix.tex", "\\section{Proofs}")
        self.write("neurips_2026.tex", "\\documentclass{article}\\begin{document}\\end{document}")
        self.assertTrue(_find_main_tex(self.d).endswith("neurips_2026.tex"))

    def test_main_tex_still_wins(self):
        self.write("main.tex", "\\documentclass{article}")
        self.write("aaa.tex", "\\documentclass{article}")
        self.assertTrue(_find_main_tex(self.d).endswith("main.tex"))

    def test_relative_main_is_resolved_against_the_paper_dir(self):
        self.write("SMILE.tex", "\\documentclass{article}")
        self.assertEqual(_resolve_main(self.d, "SMILE.tex"), os.path.join(self.d, "SMILE.tex"))

    def test_absolute_main_is_kept(self):
        self.assertEqual(_resolve_main(self.d, "/abs/x.tex"), "/abs/x.tex")


if __name__ == "__main__":
    unittest.main()
