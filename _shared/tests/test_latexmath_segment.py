"""Proof segmentation.

The ratio of narration steps to inference steps is the number that decides
whether the whole tool is usable. Over-fragment, and the gap ledger fills with
"could not verify: Recall the setting of Section 3" until the reader stops
reading it. Under-fragment, and two inferences share one verdict and neither can
be located.

`test_narration_merges_forward_into_the_inference` and
`test_a_sentence_and_its_display_are_one_step` are the two that guard that ratio.
"""
import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from latexmath import segment as S  # noqa: E402


def kinds(steps):
    return [s.kind for s in steps]


class TestSentenceSplitting(unittest.TestCase):
    def test_abbreviations_do_not_end_sentences(self):
        for abbr in ("i.e.", "e.g.", "cf.", "Eq.", "Fig.", "Sec.", "resp.",
                     "w.l.o.g.", "s.t.", "a.s.", "i.i.d.", "et al."):
            body = "We use %s the bound. It follows." % abbr
            self.assertEqual(len(S.sentences(body)), 2,
                             "%r split the sentence" % abbr)

    def test_a_period_inside_math_does_not_end_a_sentence(self):
        body = r"Let $S = \{1.5, 2.5\}$ be the set. Then $|S| = 2$."
        self.assertEqual(len(S.sentences(body)), 2)

    def test_a_period_before_a_lowercase_word_does_not_split(self):
        self.assertEqual(len(S.sentences("See Thm. 2 for the bound.")), 1)


class TestDisplayAttachment(unittest.TestCase):
    def test_a_sentence_and_its_display_are_one_step(self):
        """"By Jensen's inequality," plus a display is one inference, not two."""
        steps = S.segment_proof(
            r"By Jensen's inequality, \[ \log \int f \ge \int \log f \]")
        self.assertEqual(len(steps), 1)
        self.assertIn("Jensen", steps[0].prose_tex)
        self.assertIn(r"\ge", steps[0].math_tex)

    def test_a_colon_also_attaches_the_display_backwards(self):
        steps = S.segment_proof(r"We now bound the first term: \[ a = b \]")
        self.assertEqual(len(steps), 1)

    def test_a_finished_sentence_leaves_the_display_standing_alone(self):
        steps = S.segment_proof(
            r"We recall the setting of Section 3. \[ p = q \]")
        self.assertEqual(len(steps), 2)
        self.assertEqual(kinds(steps), ["narration", "display"])

    def test_ordinals_are_stable_when_a_display_is_reflowed(self):
        flat = r"By Jensen, \[ a \ge b \] Hence $c \ge d$."
        broken = "By Jensen,\n\\[\n  a \\ge b\n\\]\nHence $c \\ge d$."
        self.assertEqual([(s.ordinal, s.kind) for s in S.segment_proof(flat)],
                         [(s.ordinal, s.kind) for s in S.segment_proof(broken)])


class TestChainExplosion(unittest.TestCase):
    BODY = r"""By linearity,
\begin{align}
  X &= a + b \\
    &= c + d \\
    &\le e
\end{align}
which proves the claim."""

    def test_a_multi_row_display_becomes_one_step_per_row(self):
        steps = S.segment_proof(self.BODY)
        rows = [s for s in steps if s.kind == "chain-row"]
        self.assertEqual(len(rows), 3)
        self.assertEqual([r.chain["row"] for r in rows], [1, 2, 3])
        self.assertEqual(rows[0].chain["of_rows"], 3)

    def test_the_leading_prose_attaches_to_the_first_row_only(self):
        steps = S.segment_proof(self.BODY)
        rows = [s for s in steps if s.kind == "chain-row"]
        self.assertIn("linearity", rows[0].prose_tex)
        self.assertEqual(rows[1].prose_tex.strip(), "")

    def test_claim_forms_survive_onto_the_step(self):
        steps = S.segment_proof(self.BODY)
        rows = [s for s in steps if s.kind == "chain-row"]
        self.assertEqual(rows[2].claim_forms[0]["relation"], r"\le")
        self.assertTrue(rows[2].chain["carried"])

    def test_a_relation_chain_in_one_row_explodes(self):
        steps = S.segment_proof(r"\begin{equation} a \le b = c \end{equation}")
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0].derived_from, "relation-chain")
        self.assertEqual(steps[0].source, steps[1].source,
                         "sub-steps share the source span they came from")


class TestClassification(unittest.TestCase):
    def test_inline_assertion(self):
        steps = S.segment_proof(r"We know that $x = y$.")
        self.assertEqual(kinds(steps), ["inline-assert"])

    def test_discourse_marker_makes_a_prose_move(self):
        steps = S.segment_proof("Combining the two bounds gives the result.")
        self.assertEqual(kinds(steps), ["prose-move"])

    def test_standalone_narration_is_kept_but_not_an_inference(self):
        steps = S.segment_proof("Recall the setting of Section 3.")
        self.assertEqual(kinds(steps), ["narration"])
        self.assertEqual(steps[0].checkable, "structural")

    def test_narration_merges_forward_into_the_inference(self):
        """Without this the gap ledger fills with unverifiable scene-setting."""
        steps = S.segment_proof(
            "Recall the setting of Section 3. Therefore $x = y$.")
        self.assertEqual(kinds(steps), ["prose-move"])
        self.assertIn("Recall", steps[0].prose_tex)
        self.assertIn("Therefore", steps[0].prose_tex)

    def test_qed_is_its_own_kind(self):
        steps = S.segment_proof(r"Thus $a = b$. This completes the proof.")
        self.assertEqual(kinds(steps), ["prose-move", "qed"])

    def test_case_marker_opens_a_case_and_the_path_propagates(self):
        steps = S.segment_proof(
            r"\textbf{Case 1.} Suppose $x > 0$. Then $f(x) = x$. "
            r"\textbf{Case 2.} Suppose $x \le 0$. Then $f(x) = -x$.")
        opens = [s for s in steps if s.kind == "case-open"]
        self.assertEqual(len(opens), 2)
        after_first = [s for s in steps if s.case_path == ["Case 1."]]
        after_second = [s for s in steps if s.case_path == ["Case 2."]]
        self.assertTrue(after_first and after_second)

    def test_steps_outside_any_case_have_an_empty_path(self):
        steps = S.segment_proof(r"First, $a = b$. \textbf{Case 1.} Then $c = d$.")
        self.assertEqual(steps[0].case_path, [])


class TestJustification(unittest.TestCase):
    def test_a_named_result_is_recognised(self):
        steps = S.segment_proof(r"By Jensen's inequality, $\log E X \ge E \log X$.")
        self.assertEqual(steps[0].justification["kind"], "named-result")
        self.assertEqual(steps[0].justification["name"], "jensen")

    def test_an_internal_reference_is_recorded(self):
        steps = S.segment_proof(r"By \eqref{eq:3}, $a = b$.")
        self.assertEqual(steps[0].justification["kind"], "internal-ref")
        self.assertEqual(steps[0].justification["refs"], ["eq:3"])

    def test_a_citation_is_recorded(self):
        steps = S.segment_proof(r"By \citet{vapnik1998}, $a \le b$.")
        self.assertEqual(steps[0].justification["kind"], "citation")
        self.assertEqual(steps[0].justification["cites"], ["vapnik1998"])

    def test_an_assumption_is_recognised(self):
        steps = S.segment_proof(r"By Assumption 2, $\gamma < 1$.")
        self.assertEqual(steps[0].justification["kind"], "assumption")

    def test_a_hedge_is_recorded_not_swallowed(self):
        steps = S.segment_proof(r"Clearly $x = y$.")
        self.assertEqual(steps[0].justification["hedges"], ["clearly"])

    def test_an_unjustified_step_says_so(self):
        steps = S.segment_proof(r"Then $x = y$.")
        self.assertEqual(steps[0].justification["kind"], "none")


class TestCoverage(unittest.TestCase):
    def test_captured_fraction_accounts_for_the_whole_body(self):
        body = ("By Jensen, $a \\ge b$. Recall Section 3. "
                "\\begin{align} x &= y \\\\ &= z \\end{align} Done.")
        steps = S.segment_proof(body)
        self.assertGreater(S.captured_fraction(body, steps), 0.9)

    def test_ordinals_are_contiguous_from_one(self):
        steps = S.segment_proof(
            r"By Jensen, $a \ge b$. Hence $c = d$. This completes the proof.")
        self.assertEqual([s.ordinal for s in steps], list(range(1, len(steps) + 1)))


if __name__ == "__main__":
    unittest.main()
