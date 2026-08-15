"""Theorem environments, proof attachment, and restatement dedupe.

The hypothesis/conclusion split is the assertion to read first. A guessed split
is worse than no split: it lets a later pass report "hypothesis never used" about
a clause that was never a hypothesis. `unsplit` is a supported outcome.
"""
import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from latexmath import environments as E  # noqa: E402

PREAMBLE = "\n".join([
    r"\newtheorem{thm}{Theorem}",
    r"\newtheorem{lem}[thm]{Lemma}",
    r"\newtheorem{defn}{Definition}",
])


def claims(body, preamble=PREAMBLE):
    text = preamble + "\n" + body
    return E.extract_claims(text, E.theorem_registry(text))


class TestRegistry(unittest.TestCase):
    def test_shared_counter_is_recorded(self):
        reg = E.theorem_registry(PREAMBLE)
        self.assertEqual(reg["lem"].counter, "thm")
        self.assertEqual(reg["lem"].printed, "Lemma")
        self.assertEqual(reg["thm"].counter, "thm")

    def test_numbering_follows_the_shared_counter(self):
        got = claims("\n".join([
            r"\begin{thm}\label{t1} A \end{thm}",
            r"\begin{lem}\label{l1} B \end{lem}",
            r"\begin{defn}\label{d1} C \end{defn}",
        ]))
        self.assertEqual([(c.kind, c.number) for c in got],
                         [("theorem", "1"), ("lemma", "2"), ("definition", "1")])

    def test_unregistered_common_environments_still_parse(self):
        """Most venue classes predefine these; a paper need not declare them."""
        got = E.extract_claims(r"\begin{proposition} P \end{proposition}",
                               E.theorem_registry(""))
        self.assertEqual([c.kind for c in got], ["proposition"])


class TestHypothesisSplit(unittest.TestCase):
    def test_let_then_splits(self):
        c = claims(r"\begin{thm} Let $f$ be convex. Then $f$ is continuous."
                   r"\end{thm}")[0]
        self.assertEqual(c.split_method, "then")
        self.assertEqual(c.split_confidence, "high")
        self.assertIn("convex", " ".join(c.hypotheses))
        self.assertIn("continuous", c.conclusion)

    def test_if_then_splits(self):
        c = claims(r"\begin{lem} If $x > 0$, then $\log x$ is defined."
                   r"\end{lem}")[0]
        self.assertEqual(c.split_method, "if-then")
        self.assertIn("$x > 0$", " ".join(c.hypotheses))

    def test_multiple_hypotheses_are_kept_separate(self):
        c = claims(r"\begin{thm} Suppose $f$ is convex. Suppose $g$ is bounded. "
                   r"Then $f+g$ is lower semicontinuous. \end{thm}")[0]
        self.assertEqual(len(c.hypotheses), 2)

    def test_a_bare_assertion_is_never_split(self):
        c = claims(r"\begin{thm} The map $T$ is a contraction. \end{thm}")[0]
        self.assertEqual(c.split_method, "unsplit")
        self.assertEqual(c.hypotheses, [])
        self.assertEqual(c.conclusion, c.statement_tex.strip())

    def test_then_inside_math_does_not_split(self):
        c = claims(r"\begin{thm} The set $\{x : \text{Then}\}$ is open. \end{thm}")[0]
        self.assertEqual(c.split_method, "unsplit")

    def test_title_argument_is_captured(self):
        c = claims(r"\begin{thm}[ELBO bound] X \end{thm}")[0]
        self.assertEqual(c.title, "ELBO bound")


class TestProofAttachment(unittest.TestCase):
    def test_explicit_argument_beats_adjacency(self):
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{thm}\label{t1} A \end{thm}",
            r"\begin{lem}\label{l1} B \end{lem}",
            r"\begin{proof}[Proof of Theorem 1] body \end{proof}",
        ])
        cs = E.extract_claims(text, E.theorem_registry(text))
        ps, diag = E.attach_proofs(cs, text)
        self.assertEqual(ps[0].attachment, "explicit-arg")
        self.assertEqual(ps[0].claim_id, "claim/t1",
                         "adjacency would have bound this to the lemma")

    def test_explicit_argument_by_ref(self):
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{thm}\label{t1} A \end{thm}",
            r"\begin{lem}\label{l1} B \end{lem}",
            r"\begin{proof}[Proof of \ref{t1}] body \end{proof}",
        ])
        cs = E.extract_claims(text, E.theorem_registry(text))
        ps, _ = E.attach_proofs(cs, text)
        self.assertEqual(ps[0].claim_id, "claim/t1")

    def test_bare_proof_binds_to_nearest_preceding_claim(self):
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{thm}\label{t1} A \end{thm}",
            r"\begin{lem}\label{l1} B \end{lem}",
            r"\begin{proof} body \end{proof}",
        ])
        cs = E.extract_claims(text, E.theorem_registry(text))
        ps, _ = E.attach_proofs(cs, text)
        self.assertEqual(ps[0].attachment, "adjacent")
        self.assertEqual(ps[0].claim_id, "claim/l1")

    def test_orphan_proof_is_reported_not_guessed(self):
        text = PREAMBLE + "\n" + r"\begin{proof} body \end{proof}"
        cs = E.extract_claims(text, E.theorem_registry(text))
        ps, diag = E.attach_proofs(cs, text)
        self.assertEqual(ps[0].attachment, "none")
        self.assertIsNone(ps[0].claim_id)
        self.assertTrue(any(d["code"] == "orphan-proof" for d in diag))

    def test_a_definition_is_not_a_proof_target(self):
        """A proof after a definition belongs to whatever claim preceded it."""
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{thm}\label{t1} A \end{thm}",
            r"\begin{defn}\label{d1} D \end{defn}",
            r"\begin{proof} body \end{proof}",
        ])
        cs = E.extract_claims(text, E.theorem_registry(text))
        ps, _ = E.attach_proofs(cs, text)
        self.assertEqual(ps[0].claim_id, "claim/t1")


class TestStructure(unittest.TestCase):
    def test_induction_with_base_case(self):
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{thm}\label{t1} A \end{thm}",
            r"\begin{proof} We proceed by induction on $n$.",
            r"\textbf{Base case.} For $n=1$ the claim is immediate.",
            r"\textbf{Inductive step.} Assume the claim holds for $n$. \end{proof}",
        ])
        cs = E.extract_claims(text, E.theorem_registry(text))
        ps, _ = E.attach_proofs(cs, text)
        self.assertTrue(ps[0].structure["is_induction"])
        self.assertIsNotNone(ps[0].structure["base_case_offset"])

    def test_induction_without_base_case_is_flagged(self):
        """This is a CRITICAL downstream and it needs no computer algebra."""
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{thm}\label{t1} A \end{thm}",
            r"\begin{proof} We argue by induction on $n$.",
            r"Assume the claim holds for $n$; then it holds for $n+1$. \end{proof}",
        ])
        cs = E.extract_claims(text, E.theorem_registry(text))
        ps, _ = E.attach_proofs(cs, text)
        self.assertTrue(ps[0].structure["is_induction"])
        self.assertIsNone(ps[0].structure["base_case_offset"])

    def test_base_case_on_a_variable_other_than_n(self):
        """Measured false alarm: 4 of 4 induction proofs in arXiv:1806.07572.

        Those proofs induct on network depth $L$ and open their base case with
        "When $L=1$, ...". A detector that hard-codes $n$ reports every one of
        them as an induction with no base case -- four fabricated CRITICALs on a
        correct paper, which is exactly the finding rate that teaches a reader to
        ignore the tool.
        """
        for opener in (r"When $L=1$, there are no hidden layers.",
                       r"For $L = 1$ the claim is immediate.",
                       r"The case $d=0$ is trivial.",
                       r"If $k = 1$, both sides vanish."):
            text = PREAMBLE + "\n" + "\n".join([
                r"\begin{thm}\label{t1} A \end{thm}",
                r"\begin{proof} We prove the result by induction. " + opener +
                r" Now assume it holds up to $L$. \end{proof}",
            ])
            cs = E.extract_claims(text, E.theorem_registry(text))
            ps, _ = E.attach_proofs(cs, text)
            st = ps[0].structure
            self.assertTrue(st["is_induction"])
            self.assertEqual(st["base_case"]["verdict"], "found",
                             "missed the base case in %r" % opener)

    def test_induction_variable_is_identified(self):
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{thm}\label{t1} A \end{thm}",
            r"\begin{proof} The proof is by induction on the depth $L$. "
            r"When $L=1$ this is immediate. \end{proof}",
        ])
        cs = E.extract_claims(text, E.theorem_registry(text))
        ps, _ = E.attach_proofs(cs, text)
        self.assertEqual(ps[0].structure["base_case"]["variable"], "L")

    def test_a_genuinely_missing_base_case_is_still_caught(self):
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{thm}\label{t1} A \end{thm}",
            r"\begin{proof} We argue by induction on $n$. "
            r"Assume the claim holds for $n$; then it holds for $n+1$. \end{proof}",
        ])
        cs = E.extract_claims(text, E.theorem_registry(text))
        ps, _ = E.attach_proofs(cs, text)
        self.assertEqual(ps[0].structure["base_case"]["verdict"], "not-found")

    def test_an_unnamed_induction_variable_yields_unknown_not_an_accusation(self):
        """When the variable cannot be identified, the honest answer is `unknown`.

        `unknown` is reported as a thing to check by hand. Only `not-found`
        escalates, and only when there was a variable to look for.
        """
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{thm}\label{t1} A \end{thm}",
            r"\begin{proof} The result follows by structural induction. "
            r"The inductive step is routine. \end{proof}",
        ])
        cs = E.extract_claims(text, E.theorem_registry(text))
        ps, _ = E.attach_proofs(cs, text)
        self.assertEqual(ps[0].structure["base_case"]["verdict"], "unknown")

    def test_explicit_base_case_marker_always_wins(self):
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{thm}\label{t1} A \end{thm}",
            r"\begin{proof} By induction. \textbf{Base case.} Immediate. "
            r"\textbf{Inductive step.} Routine. \end{proof}",
        ])
        cs = E.extract_claims(text, E.theorem_registry(text))
        ps, _ = E.attach_proofs(cs, text)
        bc = ps[0].structure["base_case"]
        self.assertEqual(bc["verdict"], "found")
        self.assertEqual(bc["evidence"], "explicit-marker")

    def test_non_induction_proofs_are_not_asked_about_base_cases(self):
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{thm}\label{t1} A \end{thm}",
            r"\begin{proof} Apply the triangle inequality twice. \end{proof}",
        ])
        cs = E.extract_claims(text, E.theorem_registry(text))
        ps, _ = E.attach_proofs(cs, text)
        self.assertFalse(ps[0].structure["is_induction"])
        self.assertEqual(ps[0].structure["base_case"]["verdict"], "n/a")

    def test_case_markers_are_collected(self):
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{thm}\label{t1} A \end{thm}",
            r"\begin{proof} \textbf{Case 1.} x. \textbf{Case 2.} y. \end{proof}",
        ])
        cs = E.extract_claims(text, E.theorem_registry(text))
        ps, _ = E.attach_proofs(cs, text)
        self.assertEqual(len(ps[0].structure["cases"]), 2)


class TestRestatementDedupe(unittest.TestCase):
    def test_appendix_restatement_is_linked_and_diffed(self):
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{thm}\label{t1} Let $f$ be convex and let $f$ be bounded. "
            r"Then $f$ attains its minimum. \end{thm}",
            r"\appendix",
            r"\begin{thm}[Restatement of Theorem 1] Let $f$ be convex. "
            r"Then $f$ attains its minimum. \end{thm}",
        ])
        cs = E.dedupe_restatements(E.extract_claims(text, E.theorem_registry(text)))
        dup = [c for c in cs if c.duplicate_of]
        self.assertEqual(len(dup), 1)
        self.assertEqual(dup[0].duplicate_of, "claim/t1")
        self.assertTrue(dup[0].hypotheses_diff,
                        "a restatement that drops a hypothesis must not pass silently")

    def test_identical_restatement_has_no_diff(self):
        stmt = r"Let $f$ be convex. Then $f$ is continuous."
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{thm}\label{t1} " + stmt + r" \end{thm}",
            r"\begin{thm}\label{t1r} " + stmt + r" \end{thm}",
        ])
        cs = E.dedupe_restatements(E.extract_claims(text, E.theorem_registry(text)))
        dup = [c for c in cs if c.duplicate_of]
        self.assertEqual(len(dup), 1)
        self.assertEqual(dup[0].hypotheses_diff, [])

    def test_unrelated_claims_are_not_deduped(self):
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{thm}\label{t1} The map $T$ is a contraction. \end{thm}",
            r"\begin{thm}\label{t2} The sequence $x_n$ is Cauchy. \end{thm}",
        ])
        cs = E.dedupe_restatements(E.extract_claims(text, E.theorem_registry(text)))
        self.assertEqual([c.duplicate_of for c in cs], [None, None])

    def test_sibling_theorems_in_a_family_are_not_restatements(self):
        """Measured on arXiv:1405.4980 (Bubeck), where four pairs of *different*
        theorems were reported as restatements dropping a hypothesis.

        A monograph states gradient descent and *projected* gradient descent,
        Nesterov for convex and for strongly convex functions. Those read as
        near-identical text with differing hypotheses -- which is exactly the
        shape of a real restatement drift, except that the conclusions differ
        too. A restatement reaches the same conclusion; a sibling does not.
        """
        pairs = [
            # unconstrained vs projected: different conclusion, different domain
            (r"Let $f$ be convex and $\beta$-smooth on $\mathbb{R}^n$. Then "
             r"gradient descent with $\eta = 1/\beta$ satisfies "
             r"$f(x_t) - f(x^*) \leq \frac{2\beta \|x_1-x^*\|^2}{t-1}$.",
             r"Let $f$ be convex and $\beta$-smooth on $\mathcal{X}$. Then "
             r"projected gradient descent with $\eta = 1/\beta$ satisfies "
             r"$f(x_t) - f(x^*) \leq \frac{3\beta \|x_1-x^*\|^2 + f(x_1)}{t}$."),
            # convex vs strongly convex: different rate
            (r"Let $f$ be a convex and $\beta$-smooth function, then Nesterov's "
             r"accelerated gradient descent satisfies "
             r"$f(y_t) - f(x^*) \leq \frac{2\beta \|x_1-x^*\|^2}{t^2}$.",
             r"Let $f$ be $\alpha$-strongly convex and $\beta$-smooth, then "
             r"Nesterov's accelerated gradient descent satisfies "
             r"$f(y_t) - f(x^*) \leq \frac{\alpha+\beta}{2}\|x_1-x^*\|^2 "
             r"\exp(-t/\sqrt{\kappa})$."),
        ]
        for first, second in pairs:
            text = PREAMBLE + "\n" + "\n".join([
                r"\begin{thm}\label{a} " + first + r" \end{thm}",
                r"\begin{thm}\label{b} " + second + r" \end{thm}"])
            cs = E.dedupe_restatements(
                E.extract_claims(text, E.theorem_registry(text)))
            drift = [c for c in cs if c.duplicate_of and c.hypotheses_diff]
            self.assertEqual(drift, [],
                             "sibling theorems reported as a restatement: %r"
                             % [(c.id, c.hypotheses_diff) for c in drift])

    def test_a_restatement_reaching_the_same_conclusion_is_still_caught(self):
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{thm}\label{t1} Let $f$ be convex and let $f$ be bounded. "
            r"Then $f$ attains its minimum on $\mathcal{X}$. \end{thm}",
            r"\begin{thm}\label{t1r} Let $f$ be convex. "
            r"Then $f$ attains its minimum on $\mathcal{X}$. \end{thm}"])
        cs = E.dedupe_restatements(E.extract_claims(text, E.theorem_registry(text)))
        drift = [c for c in cs if c.duplicate_of and c.hypotheses_diff]
        self.assertEqual(len(drift), 1, "a genuine hypothesis drift was lost")

    def test_drift_is_not_reported_against_an_unsplittable_original(self):
        """Measured on a real draft: a body theorem whose statement could not be
        split reported all four of its restatement's hypotheses as "added".

        An empty hypothesis list from `split_method: unsplit` means *not parsed*,
        not *none stated*. Diffing against it is the same error as guessing a
        split -- which this module refuses to do everywhere else.
        """
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{thm}\label{t1} The radius scales as $r_t \sim t^{1/2}$. \end{thm}",
            r"\begin{thm}\label{t1r} Consider the joint SDE. Let $\tau$ be the "
            r"first hitting time. Then the radius scales as $r_t \sim t^{1/2}$. "
            r"\end{thm}"])
        cs = E.extract_claims(text, E.theorem_registry(text))
        self.assertEqual(cs[0].split_method, "unsplit")
        cs = E.dedupe_restatements(cs)
        drift = [c for c in cs if c.duplicate_of and c.hypotheses_diff]
        self.assertEqual(drift, [],
                         "reported drift against a statement it could not split")

    def test_the_link_survives_even_when_the_diff_is_suppressed(self):
        """The restatement is still linked; only the unusable diff is withheld.

        Stated on a pair similar enough to link regardless of thresholds, so the
        test measures the suppression rule rather than the similarity cutoff.
        """
        stmt = (r"The radius of the iterate scales as $r_t \sim t^{1/2}$ in the "
                r"late-stage regime of the dynamics.")
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{thm}\label{t1} " + stmt + r" \end{thm}",
            r"\begin{thm}\label{t1r} Let $\tau$ be the hitting time. Then " +
            stmt[0].lower() + stmt[1:] + r" \end{thm}"])
        cs = E.dedupe_restatements(E.extract_claims(text, E.theorem_registry(text)))
        linked = [c for c in cs if c.duplicate_of]
        self.assertTrue(linked, "the restatement was not linked at all")
        self.assertEqual(linked[0].hypotheses_diff, [],
                         "a diff was reported against an unsplittable original")

    def test_a_dropped_hypothesis_is_still_reported_when_both_split(self):
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{thm}\label{t1} Let $f$ be convex and let $f$ be bounded. "
            r"Then $A$ holds. \end{thm}",
            r"\begin{thm}\label{t1r} Let $f$ be convex. Then $A$ holds. \end{thm}"])
        cs = E.dedupe_restatements(E.extract_claims(text, E.theorem_registry(text)))
        drift = [c for c in cs if c.duplicate_of and c.hypotheses_diff]
        self.assertEqual(len(drift), 1)
        self.assertTrue(any(d.startswith("-") for d in drift[0].hypotheses_diff))

    def test_a_label_naming_convention_beats_text_similarity(self):
        """Measured on a real draft: `thm:generalization_radius_scaling_restated`
        was linked to `thm:memorization_radius_scaling`.

        The two theorems are sibling scaling laws with near-identical shape, and
        the memorization one came first, so similarity picked it. The author had
        already said which is which by naming the label. An explicit convention
        beats a text heuristic every time -- the same lesson as `restatable`.
        """
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{thm}\label{thm:memorization_scaling} Let $a$ hold. "
            r"Then the memorization radius scales as $\rho_M \sim f(\lambda)$. \end{thm}",
            r"\begin{thm}\label{thm:generalization_scaling} Let $a$ hold. "
            r"Then the generalization radius scales as $\rho_G \sim f(\lambda)$. \end{thm}",
            r"\begin{thm}\label{thm:generalization_scaling_restated} Let $a$ hold. "
            r"Then the generalization radius scales as $\rho_G \sim f(\lambda)$. \end{thm}"])
        cs = E.dedupe_restatements(E.extract_claims(text, E.theorem_registry(text)))
        by = {c.id.split("/")[-1]: c for c in cs}
        self.assertEqual(by["thm:generalization_scaling_restated"].duplicate_of,
                         "claim/thm:generalization_scaling",
                         "linked to the wrong sibling")

    def test_an_appendix_suffix_is_also_a_convention(self):
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{lem}\label{lem:sde} Let $a$ hold. Then $X$. \end{lem}",
            r"\begin{lem}\label{lem:sde_appendix} Let $a$ hold. Then $X$. \end{lem}"])
        cs = E.dedupe_restatements(E.extract_claims(text, E.theorem_registry(text)))
        by = {c.id.split("/")[-1]: c for c in cs}
        self.assertEqual(by["lem:sde_appendix"].duplicate_of, "claim/lem:sde")

    def test_a_convention_link_survives_a_low_similarity_score(self):
        """The convention is the author speaking; thresholds do not override it."""
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{thm}\label{t:x} Short. \end{thm}",
            r"\begin{thm}\label{t:x_restated} Let $a$ be given, let $b$ be given, "
            r"and suppose $c$. Then, after considerable setup, short. \end{thm}"])
        cs = E.dedupe_restatements(E.extract_claims(text, E.theorem_registry(text)))
        by = {c.id.split("/")[-1]: c for c in cs}
        self.assertEqual(by["t:x_restated"].duplicate_of, "claim/t:x")

    def test_an_explicit_restatement_marker_still_links(self):
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{thm}\label{t1} Let $f$ be convex and bounded. "
            r"Then $A$ holds. \end{thm}",
            r"\begin{thm}[Restatement of Theorem 1]\label{t1r} Let $f$ be convex. "
            r"Then $A$ holds, and moreover $B$. \end{thm}"])
        cs = E.dedupe_restatements(E.extract_claims(text, E.theorem_registry(text)))
        self.assertTrue([c for c in cs if c.duplicate_of])

    def test_restatable_environment_is_understood(self):
        text = PREAMBLE + "\n" + "\n".join([
            r"\begin{restatable}[Main bound]{thm}{MainBound}\label{t1}",
            r"  Let $f$ be convex. Then $f$ is continuous.",
            r"\end{restatable}",
        ])
        cs = E.extract_claims(text, E.theorem_registry(text))
        self.assertEqual(cs[0].kind, "theorem")
        self.assertEqual(cs[0].title, "Main bound")
        self.assertEqual(cs[0].id, "claim/t1")


if __name__ == "__main__":
    unittest.main()
