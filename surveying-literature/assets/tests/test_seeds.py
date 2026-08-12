import unittest, sys, pathlib, tempfile, os
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from survey.seeds import extract, tex_sources

TEX = r"""
\section{Introduction}
We present a gate loop that repairs generated visualisation code
\cite{dibia2023lida,narechania2021nl4dv}.
Our contributions are: (1) an execution-guided repair loop; (2) a study.
\section{Related Work}
Prior NL2Vis systems \citep{dibia2023lida} generate charts from prose.
"""
BIB = """
@inproceedings{dibia2023lida, title={LIDA: A Tool for Automatic Generation}, year={2023}}
@article{narechania2021nl4dv, title={NL4DV: A Toolkit}, year={2021}}
"""


class TestSeeds(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.tex = os.path.join(self.d, "main.tex")
        with open(self.tex, "w") as fh:
            fh.write(TEX)
        self.bib = os.path.join(self.d, "refs.bib")
        with open(self.bib, "w") as fh:
            fh.write(BIB)

    def test_collects_cited_keys(self):
        s = extract([self.tex], self.bib)
        self.assertEqual(s.cited_keys, {"dibia2023lida", "narechania2021nl4dv"})

    def test_handles_citep_citet_and_optional_arguments(self):
        tex = os.path.join(self.d, "v.tex")
        with open(tex, "w") as fh:
            fh.write(r"\citet[p.~4]{dibia2023lida} and \citeauthor{narechania2021nl4dv}")
        self.assertEqual(extract([tex], self.bib).cited_keys,
                         {"dibia2023lida", "narechania2021nl4dv"})

    def test_resolves_cited_titles_from_the_bib(self):
        s = extract([self.tex], self.bib)
        self.assertTrue(any("LIDA" in t for t in s.cited_titles))
        self.assertEqual(len(s.cited_titles), 2)

    def test_extracts_contribution_sentences(self):
        s = extract([self.tex], self.bib)
        self.assertTrue(any("repair loop" in c for c in s.contributions),
                        f"got {s.contributions}")

    def test_ignores_commented_out_citations(self):
        tex = os.path.join(self.d, "c.tex")
        with open(tex, "w") as fh:
            fh.write("% \\cite{ghost2020}\n\\cite{dibia2023lida}\n")
        self.assertEqual(extract([tex], self.bib).cited_keys, {"dibia2023lida"})

    def test_ignores_trailing_comments_but_not_escaped_percent(self):
        tex = os.path.join(self.d, "t.tex")
        with open(tex, "w") as fh:
            fh.write(r"90\% agreement \cite{dibia2023lida} % \cite{ghost2020}" + "\n")
        self.assertEqual(extract([tex], self.bib).cited_keys, {"dibia2023lida"})

    def test_angles_are_lowercased_and_deduplicated(self):
        s = extract([self.tex], self.bib)
        self.assertTrue(s.angles, "expected at least one query angle")
        self.assertEqual(len(s.angles), len(set(s.angles)))
        self.assertTrue(all(a == a.lower() for a in s.angles))

    def test_missing_bib_key_does_not_crash(self):
        tex = os.path.join(self.d, "m.tex")
        with open(tex, "w") as fh:
            fh.write(r"\cite{not_in_bib}")
        s = extract([tex], self.bib)
        self.assertEqual(s.cited_keys, {"not_in_bib"})
        self.assertEqual(s.cited_titles, [])


    # --- added after the Task 2 checkpoint on real drafts ---
    def test_tex_sources_follows_input_and_skips_unincluded_files(self):
        """A template's sample .tex contributed 7 phantom cite keys on a real paper."""
        main = os.path.join(self.d, "paper.tex")
        with open(main, "w") as fh:
            fh.write("\\input{sections/intro}\n\\include{sections/method}\n")
        os.makedirs(os.path.join(self.d, "sections"), exist_ok=True)
        for name in ("intro", "method"):
            with open(os.path.join(self.d, "sections", name + ".tex"), "w") as fh:
                fh.write(f"content of {name}\n")
        with open(os.path.join(self.d, "template_reference.tex"), "w") as fh:
            fh.write(r"\cite{Lorensen:1987:MCA}")

        got = {os.path.basename(p) for p in tex_sources(main)}
        self.assertEqual(got, {"paper.tex", "intro.tex", "method.tex"})

    def test_unincluded_template_citations_are_excluded(self):
        main = os.path.join(self.d, "paper2.tex")
        with open(main, "w") as fh:
            fh.write(r"\cite{dibia2023lida}" + "\n")
        with open(os.path.join(self.d, "stray.tex"), "w") as fh:
            fh.write(r"\cite{Lorensen:1987:MCA}")
        s = extract(tex_sources(main), self.bib)
        self.assertEqual(s.cited_keys, {"dibia2023lida"})

    def test_section_headings_do_not_leak_into_contributions(self):
        tex = os.path.join(self.d, "s.tex")
        with open(tex, "w") as fh:
            fh.write(r"\section{Conclusion} We presented an execution-verified "
                     r"framework that repairs generated code.")
        s = extract([tex], self.bib)
        self.assertTrue(s.contributions)
        self.assertNotIn("conclusion", s.contributions[0].lower())

    def test_angles_exclude_presentation_verbs(self):
        tex = os.path.join(self.d, "a.tex")
        with open(tex, "w") as fh:
            fh.write(r"\section{Conclusion} We presented an execution-verified "
                     r"framework that repairs generated code.")
        s = extract([tex], self.bib)
        for a in s.angles:
            self.assertNotIn("presented", a)
            self.assertNotIn("conclusion", a)


ABSTRACT_TEX = r"""
\title{A Framework for Chart Repair}
\begin{abstract}
Large language models generate visualization code that often fails to execute.
We introduce a sandbox that validates visualization code and repairs it.
Our visualization code repair loop improves reliability on chart generation.
\end{abstract}
\section{Introduction}
Body text \cite{dibia2023lida}.
"""


class TestAbstractAngles(unittest.TestCase):
    """The abstract is written to be topically dense; repeated terms are the
    paper's actual concepts, and they make better queries than a title alone."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.bib = os.path.join(self.d, "refs.bib")
        with open(self.bib, "w") as fh:
            fh.write(BIB)
        self.tex = os.path.join(self.d, "a.tex")
        with open(self.tex, "w") as fh:
            fh.write(ABSTRACT_TEX)

    def test_abstract_is_extracted(self):
        s = extract([self.tex], self.bib)
        self.assertIn("sandbox", s.abstract)
        self.assertNotIn("Introduction", s.abstract)

    def test_repeated_abstract_concepts_become_angles(self):
        angles = extract([self.tex], self.bib).angles
        self.assertIn("visualization code", angles)

    def test_abstract_angles_rank_above_one_off_phrases(self):
        angles = extract([self.tex], self.bib).angles
        joined = angles[:8]
        self.assertIn("visualization code", joined,
                      f"thrice-repeated concept missing from top angles: {joined}")

    def test_abstract_environment_variants(self):
        p = os.path.join(self.d, "b.tex")
        with open(p, "w") as fh:
            fh.write(r"\abstract{Chart repair for visualization code.}")
        self.assertIn("Chart repair", extract([p], self.bib).abstract)

    def test_missing_abstract_does_not_crash(self):
        p = os.path.join(self.d, "c.tex")
        with open(p, "w") as fh:
            fh.write(r"\title{T}")
        self.assertEqual(extract([p], self.bib).abstract, "")


class TestTitleAngles(unittest.TestCase):
    """The draft's own title is the single best topical query it contains."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.bib = os.path.join(self.d, "refs.bib")
        with open(self.bib, "w") as fh:
            fh.write(BIB)

    def _tex(self, body, name="t.tex"):
        p = os.path.join(self.d, name)
        with open(p, "w") as fh:
            fh.write(body)
        return p

    def test_title_is_extracted(self):
        p = self._tex(r"\title{Execution Verified Multiagent Pipelines for "
                      r"Natural Language Visualization Code Generation}")
        self.assertIn("Natural Language Visualization", extract([p], self.bib).title)

    def test_title_phrases_lead_the_angles(self):
        p = self._tex(r"\title{Execution Verified Multiagent Pipelines for "
                      r"Natural Language Visualization Code Generation}"
                      "\n Our contributions are: (1) a repair loop that works.")
        angles = extract([p], self.bib).angles
        self.assertTrue(angles)
        joined = " | ".join(angles[:6])
        self.assertIn("natural language visualization", joined)

    def test_clause_spanning_fragments_are_dropped(self):
        p = self._tex(r"\title{A Title}" "\n"
                      r"We present a loop that repairs chart code until the "
                      r"sandbox execution succeeds and supports multiple charts.")
        for a in extract([p], self.bib).angles:
            self.assertNotIn("until", a)
            self.assertNotIn("succeeds", a)
            self.assertNotIn("supports", a)

    def test_missing_title_does_not_crash(self):
        p = self._tex("no title here")
        s = extract([p], self.bib)
        self.assertEqual(s.title, "")


if __name__ == "__main__":
    unittest.main()
