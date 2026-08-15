"""Cross-reference graph and claim-level dependency cycles.

A proof of Lemma 3 that leans on Theorem 1 whose proof leans on Lemma 3 is
circular, and the paper is wrong. It is one of the few CRITICALs available
without any computer algebra at all, which is why it is worth getting exactly
right -- and why a *forward* reference, which is legal LaTeX and completely
ordinary practice, must stay informational.
"""
import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from latexmath import environments as E, refs as R  # noqa: E402

PRE = "\\newtheorem{thm}{Theorem}\n\\newtheorem{lem}[thm]{Lemma}\n"


def build(body):
    text = PRE + body
    claims = E.extract_claims(text, E.theorem_registry(text))
    proofs, _ = E.attach_proofs(claims, text)
    return R.build_refs(text, claims, proofs)


class TestLabels(unittest.TestCase):
    def test_label_kinds_are_classified(self):
        g = build(r"""
\begin{thm}\label{thm:a} A \end{thm}
\begin{equation}\label{eq:a} x = 1 \end{equation}
\section{Setup}\label{sec:a}
\begin{proof} By \eqref{eq:a} and \ref{sec:a}, done. \end{proof}""")
        self.assertEqual(g["labels"]["thm:a"]["kind"], "theorem")
        self.assertEqual(g["labels"]["eq:a"]["kind"], "equation")
        self.assertEqual(g["labels"]["sec:a"]["kind"], "section")

    def test_every_reference_command_is_recognised(self):
        for cmd in ("ref", "eqref", "cref", "Cref", "autoref", "pageref"):
            g = build(r"\begin{equation}\label{eq:a} x=1 \end{equation}"
                      + "\n\\begin{thm}\\label{t} A \\end{thm}"
                      + "\n\\begin{proof} By \\%s{eq:a}. \\end{proof}" % cmd)
            self.assertIn("eq:a", [e["label"] for e in g["edges"]],
                          "\\%s was not recognised" % cmd)

    def test_cref_with_several_labels(self):
        g = build(r"""
\begin{equation}\label{eq:a} x=1 \end{equation}
\begin{equation}\label{eq:b} y=2 \end{equation}
\begin{thm}\label{t} A \end{thm}
\begin{proof} By \cref{eq:a,eq:b}, done. \end{proof}""")
        self.assertEqual(sorted(e["label"] for e in g["edges"]), ["eq:a", "eq:b"])


class TestDanglingAndUnused(unittest.TestCase):
    def test_a_reference_to_a_missing_label_is_dangling(self):
        g = build(r"""
\begin{thm}\label{t} A \end{thm}
\begin{proof} By \eqref{eq:ghost}, done. \end{proof}""")
        self.assertEqual([d["label"] for d in g["dangling"]], ["eq:ghost"])

    def test_an_unreferenced_label_is_reported(self):
        g = build(r"""
\begin{equation}\label{eq:orphan} x = 1 \end{equation}
\begin{thm}\label{t} A \end{thm}
\begin{proof} Immediate. \end{proof}""")
        self.assertIn("eq:orphan", g["unused_labels"])

    def test_a_forward_reference_is_informational_not_a_defect(self):
        g = build(r"""
\begin{thm}\label{t1} A \end{thm}
\begin{proof} By \ref{t2}, done. \end{proof}
\begin{thm}\label{t2} B \end{thm}
\begin{proof} Immediate. \end{proof}""")
        self.assertEqual([f["label"] for f in g["forward_refs"]], ["t2"])
        self.assertEqual(g["dangling"], [])


class TestCycles(unittest.TestCase):
    def test_a_two_claim_cycle_is_found(self):
        g = build(r"""
\begin{lem}\label{lem3} L \end{lem}
\begin{proof} By \ref{thm1}, done. \end{proof}
\begin{thm}\label{thm1} T \end{thm}
\begin{proof} By \ref{lem3}, done. \end{proof}""")
        self.assertTrue(g["cycles"])
        cycle = set(g["cycles"][0])
        self.assertEqual(cycle, {"claim/lem3", "claim/thm1"})

    def test_a_self_reference_is_deliberately_exempt(self):
        """Superseded by measurement: this used to assert a cycle.

        Nothing distinguishes "by Theorem 1, which we are proving" from "recall
        the hypotheses of Theorem 1" by reference alone, and the second is what
        real proofs do. Precision first: the self-edge is dropped, and the cost
        is stated in Limits.
        """
        g = build(r"""
\begin{thm}\label{t1} T \end{thm}
\begin{proof} By \ref{t1}, done. \end{proof}""")
        self.assertEqual(g["cycles"], [])

    def test_a_linear_dependency_chain_is_not_a_cycle(self):
        g = build(r"""
\begin{lem}\label{l1} L1 \end{lem}
\begin{proof} Immediate. \end{proof}
\begin{lem}\label{l2} L2 \end{lem}
\begin{proof} By \ref{l1}, done. \end{proof}
\begin{thm}\label{t1} T \end{thm}
\begin{proof} By \ref{l2} and \ref{l1}, done. \end{proof}""")
        self.assertEqual(g["cycles"], [])

    def test_a_proof_referring_to_its_own_theorem_is_not_circular(self):
        """Measured false alarm on arXiv:1806.07572.

        Proofs routinely say "the statement of Theorem 1" or restate their own
        hypotheses by `\\ref`. Calling that a circular dependency reports a
        CRITICAL against ordinary writing.
        """
        g = build(r"""
\begin{thm}\label{t1} T \end{thm}
\begin{proof} Recall the hypotheses of \ref{t1}. The claim follows. \end{proof}""")
        self.assertEqual(g["cycles"], [])

    def test_a_genuine_two_claim_cycle_survives_that_exemption(self):
        g = build(r"""
\begin{lem}\label{l1} L \end{lem}
\begin{proof} By \ref{t1} and \ref{l1}, done. \end{proof}
\begin{thm}\label{t1} T \end{thm}
\begin{proof} By \ref{l1}, done. \end{proof}""")
        self.assertTrue(g["cycles"])

    def test_referencing_an_equation_is_not_a_claim_dependency(self):
        g = build(r"""
\begin{thm}\label{t1} T \end{thm}
\begin{proof} By \eqref{eq:a}, done. \end{proof}
\begin{equation}\label{eq:a} x = 1 \end{equation}""")
        self.assertEqual(g["cycles"], [])


if __name__ == "__main__":
    unittest.main()
