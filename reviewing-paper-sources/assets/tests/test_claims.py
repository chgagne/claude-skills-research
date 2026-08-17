import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))
from claimstrength.claims import (abstract_text, results_bodies, sentences,
                                  content_tokens, pair)

TEX = r"""
\begin{abstract}
Our gate causes a 12 point gain on the benchmark. We release the code.
\end{abstract}
\section{Method}
The gate is a linear layer.
\section{Results}
We observe that the gate is associated with a 12 point gain on the benchmark.
Latency is unchanged.
"""


class TestAbstract(unittest.TestCase):
    def test_extracts_abstract_body(self):
        self.assertIn("causes a 12 point gain", abstract_text(TEX))

    def test_absent_abstract_returns_empty(self):
        self.assertEqual(abstract_text(r"\section{Intro} text"), "")

    def test_extracts_command_form_abstract(self):
        # IEEE/VGTC and several ACM classes take \abstract{...} rather than the
        # environment. One real paper in the local corpus uses this form, and the
        # environment-only extractor read it as having no abstract at all.
        tex = r"\abstract{Our gate causes a gain on the benchmark.}"
        self.assertIn("causes a gain", abstract_text(tex))

    def test_command_form_stops_at_its_closing_brace(self):
        tex = r"\abstract{We report \textbf{strong} gains.}" "\n" r"\section{Intro} body"
        got = abstract_text(tex)
        self.assertIn("strong", got)
        self.assertNotIn("Intro", got)


class TestResultsBodies(unittest.TestCase):
    def test_matches_results_heading(self):
        got = results_bodies([("Method", "a"), ("Results", "b")])
        self.assertEqual(got, [("Results", "b")])

    def test_matches_evaluation_and_experiments(self):
        got = results_bodies([("Evaluation", "a"), ("Experiments", "b"), ("Intro", "c")])
        self.assertEqual([h for h, _ in got], ["Evaluation", "Experiments"])

    def test_no_results_section_returns_empty(self):
        self.assertEqual(results_bodies([("Intro", "a")]), [])


class TestSentences(unittest.TestCase):
    def test_splits_on_terminal_punctuation(self):
        self.assertEqual(len(sentences("One claim here. Two claims here.")), 2)

    def test_decimal_point_does_not_split(self):
        self.assertEqual(len(sentences("Accuracy reached 92.4 percent overall.")), 1)


class TestPairing(unittest.TestCase):
    def test_pairs_on_shared_content_tokens_and_reports_delta(self):
        a = ["Our gate causes a 12 point gain on the benchmark."]
        r = ["The gate is associated with a 12 point gain on the benchmark."]
        got = pair(a, r)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].abstract_rung.level, 6)
        self.assertEqual(got[0].results_rung.level, 2)
        self.assertEqual(got[0].delta, 4)

    def test_unrelated_sentences_do_not_pair(self):
        got = pair(["Our gate causes a gain."], ["Latency is unchanged overall."])
        self.assertEqual(got[0].results, "")
        self.assertEqual(got[0].delta, 0)

    def test_abstract_sentence_with_no_assertion_is_dropped(self):
        self.assertEqual(pair(["We release the code."], ["Latency is unchanged."]), [])

    def test_stopwords_do_not_count_as_shared_content(self):
        self.assertNotIn("the", content_tokens("the gate of the benchmark"))


if __name__ == "__main__":
    unittest.main()
