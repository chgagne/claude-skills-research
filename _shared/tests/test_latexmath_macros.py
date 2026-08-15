"""Scanner and macro table.

Every assertion here is a thing that must work before a single proof can be read.
Macro expansion is not a nicety: real ML sources define `\\encS`, `\\D`, `\\argmin`
and then write the whole appendix in terms of them, so an unexpanded ledger
records symbols that do not exist and misses the ones that do.
"""
import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from latexmath import tokenize as T  # noqa: E402
from latexmath import macros as M  # noqa: E402


class TestBalanced(unittest.TestCase):
    def test_extracts_a_nested_group(self):
        body, end = T.balanced(r"{a{b}c}tail", 0)
        self.assertEqual(body, "a{b}c")
        self.assertEqual(end, 7)

    def test_escaped_brace_does_not_close_the_group(self):
        body, _ = T.balanced(r"{a\}b}", 0)
        self.assertEqual(body, r"a\}b")

    def test_unbalanced_returns_none(self):
        self.assertEqual(T.balanced("{a", 0), (None, -1))


class TestEnvSpans(unittest.TestCase):
    def test_finds_an_environment_with_its_body(self):
        spans = T.find_env_spans(r"x \begin{proof} body \end{proof} y", ["proof"])
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].name, "proof")
        self.assertEqual(spans[0].body.strip(), "body")

    def test_optional_argument_is_captured_not_swallowed(self):
        spans = T.find_env_spans(r"\begin{proof}[Proof of Theorem 2] b \end{proof}",
                                 ["proof"])
        self.assertEqual(spans[0].arg, "Proof of Theorem 2")
        self.assertEqual(spans[0].body.strip(), "b")

    def test_nested_environments_of_the_same_name_pair_correctly(self):
        text = r"\begin{align}a\begin{align}b\end{align}c\end{align}"
        spans = T.find_env_spans(text, ["align"])
        self.assertEqual(len(spans), 1, "outer span only, not two half-open ones")
        self.assertIn(r"\begin{align}b\end{align}", spans[0].body)

    def test_commented_out_environments_are_absent(self):
        """The single most common source of phantom content in a real appendix."""
        text = "\n".join([
            r"% \begin{aligned}",
            r"%   \log p(x) &= \text{dead code}",
            r"% \end{aligned}",
            r"\begin{aligned} \log p(x) &= \text{live} \end{aligned}",
        ])
        spans = T.find_env_spans(text, ["aligned"])
        self.assertEqual(len(spans), 1)
        self.assertIn("live", spans[0].body)
        self.assertNotIn("dead code", spans[0].body)


class TestMathSpans(unittest.TestCase):
    def test_finds_inline_display_and_environment_math(self):
        text = r"a $x$ b \(y\) c \[z\] d \begin{equation}w\end{equation} e"
        got = [s.body for s in T.math_spans(text)]
        self.assertEqual(got, ["x", "y", "z", "w"])

    def test_escaped_dollar_is_not_math(self):
        self.assertEqual(T.math_spans(r"costs \$5 and \$7"), [])

    def test_verbatim_contents_are_never_math(self):
        text = r"\begin{verbatim} $not math$ \end{verbatim} $real$"
        got = [s.body for s in T.math_spans(text)]
        self.assertEqual(got, ["real"])

    def test_verb_command_is_protected(self):
        got = [s.body for s in T.math_spans(r"\verb|$fake$| and $real$")]
        self.assertEqual(got, ["real"])

    def test_masking_preserves_offsets(self):
        text = r"By $x = 1$ we conclude. Then $y$."
        masked = T.mask(text, T.math_spans(text))
        self.assertEqual(len(masked), len(text))
        self.assertNotIn("=", masked)
        self.assertIn("we conclude.", masked)


class TestMacroTable(unittest.TestCase):
    def test_zero_argument_macro_expands(self):
        t = M.MacroTable.from_text(r"\newcommand{\encS}{\mathrm{enc}_S}")
        out, unexpanded = t.expand(r"\encS(f)")
        self.assertEqual(out, r"\mathrm{enc}_S(f)")
        self.assertEqual(unexpanded, set())

    def test_expansion_does_not_match_a_longer_name(self):
        t = M.MacroTable.from_text(r"\newcommand{\enc}{E}")
        out, _ = t.expand(r"\encS \enc")
        self.assertEqual(out, r"\encS E", r"\encS is not \enc followed by S")

    def test_one_argument_macro_substitutes(self):
        t = M.MacroTable.from_text(r"\newcommand{\D}[1]{\mathrm{d}#1}")
        out, _ = t.expand(r"\D{x} + \D{y}")
        self.assertEqual(out, r"\mathrm{d}x + \mathrm{d}y")

    def test_repeated_parameter_is_substituted_everywhere(self):
        t = M.MacroTable.from_text(r"\newcommand{\sq}[1]{#1 \cdot #1}")
        out, _ = t.expand(r"\sq{a}")
        self.assertEqual(out, r"a \cdot a")

    def test_optional_argument_default_is_used(self):
        t = M.MacroTable.from_text(r"\newcommand{\norm}[2][2]{\|#2\|_{#1}}")
        self.assertEqual(t.expand(r"\norm{x}")[0], r"\|x\|_{2}")
        self.assertEqual(t.expand(r"\norm[1]{x}")[0], r"\|x\|_{1}")

    def test_declare_math_operator(self):
        t = M.MacroTable.from_text(r"\DeclareMathOperator{\argmin}{arg\,min}")
        self.assertEqual(t.expand(r"\argmin_\theta")[0],
                         r"\operatorname{arg\,min}_\theta")

    def test_declare_math_operator_star_takes_limits(self):
        t = M.MacroTable.from_text(r"\DeclareMathOperator*{\argmax}{arg\,max}")
        self.assertEqual(t.expand(r"\argmax")[0], r"\operatorname*{arg\,max}")

    def test_def_form_is_read(self):
        t = M.MacroTable.from_text(r"\def\R{\mathbb{R}}")
        self.assertEqual(t.expand(r"x \in \R")[0], r"x \in \mathbb{R}")

    def test_renewcommand_overrides(self):
        t = M.MacroTable.from_text(
            "\n".join([r"\newcommand{\eps}{\epsilon}",
                       r"\renewcommand{\eps}{\varepsilon}"]))
        self.assertEqual(t.expand(r"\eps")[0], r"\varepsilon")

    def test_nested_macros_expand_transitively(self):
        t = M.MacroTable.from_text(
            "\n".join([r"\newcommand{\R}{\mathbb{R}}",
                       r"\newcommand{\Rd}{\R^d}"]))
        self.assertEqual(t.expand(r"\Rd")[0], r"\mathbb{R}^d")

    def test_self_recursive_macro_terminates_and_is_reported(self):
        """A runaway expansion must degrade to a named finding, not hang."""
        t = M.MacroTable.from_text(r"\def\x{\x y}")
        out, unexpanded = t.expand(r"\x", depth=8)
        self.assertIn("x", unexpanded)
        self.assertLess(len(out), 200, "expansion must be bounded")

    def test_definitions_inside_comments_are_ignored(self):
        t = M.MacroTable.from_text(r"% \newcommand{\ghost}{G}")
        self.assertEqual(t.expand(r"\ghost")[0], r"\ghost")

    def test_reference_helpers_are_not_math_macros(self):
        """The checkpoint criterion: a ref helper must not pollute the symbol table."""
        t = M.MacroTable.from_text(
            "\n".join([r"\newcommand{\secref}[1]{Section~\ref{#1}}",
                       r"\newcommand{\encS}{\mathrm{enc}_S}"]))
        self.assertFalse(t.is_math_macro("secref"))
        self.assertTrue(t.is_math_macro("encS"))

    def test_from_sources_reads_a_document_and_its_inputs(self):
        import tempfile, os
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "defs.tex"), "w") as fh:
            fh.write(r"\newcommand{\fstar}{f^\star}")
        with open(os.path.join(d, "main.tex"), "w") as fh:
            fh.write("\\input{defs}\n\\begin{document}$\\fstar$\\end{document}")
        t = M.MacroTable.from_sources(os.path.join(d, "main.tex"))
        self.assertEqual(t.expand(r"\fstar")[0], r"f^\star")


if __name__ == "__main__":
    unittest.main()
