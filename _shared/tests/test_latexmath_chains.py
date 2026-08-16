"""Multi-row display reconstruction.

Nearly all mechanically checkable content in a paper lives in `align` rows, and
almost none of it is written as a self-contained equation. Row 3 of a chain says
`&= \\int q(z)\\ldots` and means "the thing on the previous line equals this".
Reconstructing both readings -- adjacent and anchored -- is what turns a display
into checkable claims.
"""
import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from latexmath import chains as C  # noqa: E402

CHAIN = r"""\begin{align}
  \log p(x) &= \log \int q(z) \frac{p(x,z)}{q(z)} dz \label{eq:a} \\
            &\ge \int q(z) \log \frac{p(x,z)}{q(z)} dz \label{eq:b} \\
            &= \mathbb{E}_q[\log p(x,z)] - \mathbb{E}_q[\log q(z)] \nonumber \\
            &= \mathcal{L}(q)
\end{align}"""


class TestRowSplitting(unittest.TestCase):
    def test_four_rows(self):
        eq = C.parse_display(CHAIN)
        self.assertEqual(eq.env, "align")
        self.assertEqual(len(eq.rows), 4)

    def test_row_labels_are_per_row_not_per_display(self):
        eq = C.parse_display(CHAIN)
        self.assertEqual(eq.row_labels, {1: "eq:a", 2: "eq:b"})
        self.assertEqual(eq.labels, ["eq:a", "eq:b"])

    def test_nonumber_rows_are_unnumbered_but_still_rows(self):
        eq = C.parse_display(CHAIN)
        self.assertEqual(eq.numbered_rows, [1, 2, 4])
        self.assertEqual(eq.notag_rows, [3])
        self.assertEqual(len(eq.rows), 4, "an unnumbered row is still a step")

    def test_optional_spacing_argument_on_the_separator(self):
        eq = C.parse_display(r"\begin{align} a &= b \\[2ex] &= c \end{align}")
        self.assertEqual(len(eq.rows), 2)

    def test_nested_environment_rows_do_not_split_the_outer_display(self):
        eq = C.parse_display(
            r"\begin{align} f(x) &= \begin{cases} 1 \\ 0 \end{cases} \\ &= g(x)"
            r"\end{align}")
        self.assertEqual(len(eq.rows), 2)

    def test_starred_environment_is_recorded(self):
        eq = C.parse_display(r"\begin{align*} a &= b \end{align*}")
        self.assertTrue(eq.starred)
        self.assertEqual(eq.numbered_rows, [])


class TestClaimForms(unittest.TestCase):
    def setUp(self):
        self.claims = C.rows_to_claims(C.parse_display(CHAIN))

    def test_first_row_is_split_at_its_own_relation(self):
        first = self.claims[0]
        self.assertEqual(first["relation"], "=")
        self.assertIn(r"\log p(x)", first["claim_forms"][0]["lhs_tex"])
        self.assertIn(r"\log \int", first["claim_forms"][0]["rhs_tex"])

    def test_continuation_row_carries_the_previous_right_hand_side(self):
        adjacent = self.claims[1]["claim_forms"][0]
        self.assertEqual(adjacent["form"], "adjacent")
        self.assertEqual(adjacent["relation"], r"\ge")
        self.assertIn(r"\log \int", adjacent["lhs_tex"],
                      "the left side of row 2 is the right side of row 1")

    def test_continuation_row_also_carries_the_anchor(self):
        anchored = [f for f in self.claims[1]["claim_forms"]
                    if f["form"] == "anchored"][0]
        self.assertIn(r"\log p(x)", anchored["lhs_tex"])
        self.assertEqual(anchored["relation"], r"\ge")

    def test_equality_after_an_inequality_composes_to_the_inequality(self):
        anchored = [f for f in self.claims[3]["claim_forms"]
                    if f["form"] == "anchored"][0]
        self.assertEqual(anchored["relation"], r"\ge",
                         "log p(x) >= L(q), not log p(x) = L(q)")

    def test_incomparable_relations_produce_no_anchored_form(self):
        """`a <= b >= c` says nothing about a and c, so no anchored claim is made."""
        cl = C.rows_to_claims(C.parse_display(
            r"\begin{align} a &\le b \\ &\ge c \end{align}"))
        forms = [f["form"] for f in cl[1]["claim_forms"]]
        self.assertIn("adjacent", forms)
        self.assertNotIn("anchored", forms)

    def test_carried_flag_distinguishes_the_two_kinds_of_row(self):
        self.assertFalse(self.claims[0]["carried"])
        self.assertTrue(self.claims[1]["carried"])


class TestRelationChains(unittest.TestCase):
    def test_a_row_with_two_relations_splits_into_two_claims(self):
        cl = C.rows_to_claims(C.parse_display(
            r"\begin{equation} a \le b = c \end{equation}"))
        self.assertEqual(len(cl), 2)
        self.assertEqual(cl[0]["relation"], r"\le")
        self.assertEqual(cl[1]["relation"], "=")
        self.assertEqual(cl[0]["derived_from"], "relation-chain")
        self.assertEqual(cl[0]["row"], cl[1]["row"], "same source row")

    def test_a_relation_inside_a_fraction_does_not_split(self):
        cl = C.rows_to_claims(C.parse_display(
            r"\begin{equation} x = \frac{\sum_{i = 1}^n a_i}{n} \end{equation}"))
        self.assertEqual(len(cl), 1)

    def test_a_relation_inside_text_does_not_split(self):
        cl = C.rows_to_claims(C.parse_display(
            r"\begin{equation} x = y \quad \text{if $a = b$} \end{equation}"))
        self.assertEqual(len(cl), 1)

    def test_leq_is_not_matched_inside_a_longer_command(self):
        cl = C.rows_to_claims(C.parse_display(
            r"\begin{equation} a \leftarrow b \end{equation}"))
        self.assertEqual(cl, [], "no relation, so no claim -- not a bogus one")


class TestCommaSeparatedDefinitions(unittest.TestCase):
    """Observed on a real paper: several definitions packed into one row.

    `C_0 = \\{c_{i0}\\}, O_0 = \\{o_{i0}\\}` is two independent statements. Read as
    a transitive chain it yields the left-hand side `\\{c_{i0}\\}, O_0`, which is
    not an expression at all -- and handing that to a checker manufactures a
    finding about something the paper never claimed.
    """

    def test_two_definitions_on_one_row_are_independent_claims(self):
        cl = C.rows_to_claims(C.parse_display(
            r"\begin{align} C_0 &= \{c_{i0}\}_{i=1}^{B}, O_0 = \{o_{i0}\}_{i=1}^{B}"
            r"\end{align}"))
        self.assertEqual(len(cl), 2)
        self.assertEqual(cl[0]["claim_forms"][0]["lhs_tex"], "C_0")
        self.assertEqual(cl[1]["claim_forms"][0]["lhs_tex"], "O_0")
        self.assertEqual(cl[1]["derived_from"], "comma-list")
        self.assertNotIn("anchored", [f["form"] for f in cl[1]["claim_forms"]],
                         "an independent definition anchors to nothing")

    def test_a_comma_inside_parentheses_is_not_a_boundary(self):
        cl = C.rows_to_claims(C.parse_display(
            r"\begin{equation} f(x, y) = z \end{equation}"))
        self.assertEqual(len(cl), 1)
        self.assertEqual(cl[0]["claim_forms"][0]["lhs_tex"], "f(x, y)")

    def test_a_comma_list_without_a_second_relation_is_not_a_boundary(self):
        cl = C.rows_to_claims(C.parse_display(
            r"\begin{equation} S = 1, 2, \ldots, n \end{equation}"))
        self.assertEqual(len(cl), 1)
        self.assertIn(r"\ldots", cl[0]["claim_forms"][0]["rhs_tex"])

    def test_a_genuine_chain_is_still_chained(self):
        cl = C.rows_to_claims(C.parse_display(
            r"\begin{equation} a \le b = c \end{equation}"))
        self.assertEqual(cl[0]["derived_from"], "relation-chain")


class TestAngleBrackets(unittest.TestCase):
    """Measured on arXiv:1806.07572, which writes inner products as `<a,b>`.

    Read as relations, the `<` and `>` truncate the right-hand side: the step
    `\\partial_t W = \\frac{1}{\\sqrt{n}}<\\alpha, d>` came out as
    `\\partial_t W = \\frac{1}{\\sqrt{n}}`, which is a different claim from the
    one in the paper -- and checking it would report on something the authors
    never wrote.
    """

    def test_an_angle_bracket_inner_product_is_not_two_relations(self):
        cl = C.rows_to_claims(C.parse_display(
            r"\begin{equation} \partial_t W = \frac{1}{\sqrt{n}}"
            r"<\alpha^{(\ell)}, d_t^{(\ell+1)}>_{p} \end{equation}"))
        self.assertEqual(len(cl), 1)
        rhs = cl[0]["claim_forms"][0]["rhs_tex"]
        self.assertIn(r"\alpha", rhs, "the inner product was cut off the claim")
        self.assertIn("d_t", rhs)

    def test_a_genuine_strict_inequality_still_splits(self):
        cl = C.rows_to_claims(C.parse_display(r"\begin{equation} x < 1 \end{equation}"))
        self.assertEqual(len(cl), 1)
        self.assertEqual(cl[0]["relation"], "<")

    def test_a_genuine_greater_than_still_splits(self):
        cl = C.rows_to_claims(C.parse_display(r"\begin{equation} n > 0 \end{equation}"))
        self.assertEqual(cl[0]["relation"], ">")

    def test_a_chained_inequality_still_splits(self):
        cl = C.rows_to_claims(C.parse_display(
            r"\begin{equation} 0 < x < 1 \end{equation}"))
        self.assertEqual(len(cl), 2)

    def test_langle_rangle_form_is_unaffected(self):
        cl = C.rows_to_claims(C.parse_display(
            r"\begin{equation} y = \langle a, b \rangle \end{equation}"))
        self.assertEqual(len(cl), 1)
        self.assertIn(r"\langle", cl[0]["claim_forms"][0]["rhs_tex"])


class TestIntertext(unittest.TestCase):
    def test_intertext_attaches_to_the_following_row(self):
        """The justification for the most important row must not fall on the floor."""
        eq = C.parse_display(
            r"\begin{align} a &= b \\ \intertext{where we used Lemma 2}"
            r" &= c \end{align}")
        self.assertEqual(len(eq.rows), 2)
        self.assertEqual(len(eq.intertext), 1)
        self.assertEqual(eq.intertext[0]["after_row"], 1)
        self.assertIn("Lemma 2", eq.intertext[0]["tex"])
        self.assertNotIn("intertext", eq.rows[1].tex)

    def test_shortintertext_is_understood(self):
        eq = C.parse_display(
            r"\begin{align} a &= b \\ \shortintertext{so} &= c \end{align}")
        self.assertEqual(len(eq.intertext), 1)


class TestAContinuationRowIsNotANewClaim(unittest.TestCase):
    r"""`align` breaks a long right-hand side across `\\` and opens the next line
    with `&+ ...`. That is the same expression continued, not a new one.

    Rows with no top-level relation were skipped, which left the previous row's
    right-hand side truncated -- and the next carried row then compared a partial
    expression against a partial expression, which is a claim the paper never
    made.

    Measured on Adam's Theorem 4.1: the truncated pair is **false** (slack
    -0.121) at a point where the full display is **true** (+0.087). A translator
    handed that row would have produced a counterexample against correct
    mathematics. It was caught because a subagent checked the row against its
    source instead of trusting it.
    """

    DISPLAY = ("\\begin{align*}\n"
               "x =& a \\\\\n"
               "&+ b + c \\\\\n"
               "\\le& d \\\\\n"
               "&+ e\n"
               "\\end{align*}")

    def _claims(self):
        eq = C.parse_display(self.DISPLAY, eid="eq/1")
        return C.rows_to_claims(eq)

    def test_the_continuation_extends_the_row_above(self):
        first = self._claims()[0]
        rhs = first["claim_forms"][0]["rhs_tex"]
        self.assertIn("a", rhs)
        self.assertIn("b", rhs, "the continuation was dropped")
        self.assertIn("c", rhs)

    def test_the_carried_row_inherits_the_whole_left_hand_side(self):
        carried = [c for c in self._claims() if c["carried"]]
        self.assertTrue(carried, "no carried row was produced")
        lhs = carried[0]["claim_forms"][0]["lhs_tex"]
        for term in ("a", "b", "c"):
            self.assertIn(term, lhs,
                          "the carried row compares a partial expression")

    def test_the_carried_rows_own_continuation_is_kept_too(self):
        carried = [c for c in self._claims() if c["carried"]]
        rhs = carried[0]["claim_forms"][0]["rhs_tex"]
        self.assertIn("d", rhs)
        self.assertIn("e", rhs)

    def test_a_row_with_a_relation_is_still_its_own_claim(self):
        eq = C.parse_display("\\begin{align*}\nx =& a \\\\\ny =& b\n\\end{align*}",
                             eid="eq/2")
        self.assertEqual(len(C.rows_to_claims(eq)), 2)


if __name__ == "__main__":
    unittest.main()
