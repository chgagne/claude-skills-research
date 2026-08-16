r"""The `--symbols` template.

A symbol whose domain the paper never states can never produce a counterexample.
That rule is the foundation of the severity ladder and it is not negotiable, so
`--symbols` is what converts this skill from a hygiene checker into a correctness
checker -- and until this existed, nothing in the tool helped anyone write one.
On a 2692-step monograph, 63 of 88 symbols had no readable domain.

The ordering is the design. Sorting by occurrence count is the obvious choice and
the wrong one: a symbol used 900 times in steps that are already settled is worth
less than one used twice in the denominator of a bound. Rows are ordered by how
many *unmet side conditions* the symbol stands in, which is what supplying it
actually buys.
"""
import unittest, sys, pathlib, tempfile, os
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))

from proofcheck import ledger_io  # noqa: E402

PAPER = r"""\documentclass{article}
\usepackage{amsmath}
\newtheorem{thm}{Theorem}
\begin{document}
\begin{thm}\label{t:x} The bound holds. \end{thm}
\begin{proof}
Let $\eta > 0$ be the step size. Then
\begin{align}
A &= \frac{u}{w} \\
  &= \frac{u}{w} + \log v + \frac{1}{w}.
\end{align}
\end{proof}
\end{document}
"""


def build(text=PAPER):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "main.tex")
    with open(p, "w") as fh:
        fh.write(text)
    return ledger_io.build(p)


class TestTemplate(unittest.TestCase):
    def setUp(self):
        self.table, self.notes = ledger_io.symbols_template(build())

    def test_the_table_is_directly_usable_as_symbols(self):
        """It must round-trip: fill in values, pass it back, no restructuring."""
        self.assertTrue(all(v == "" for v in self.table.values()))
        self.assertTrue(all(isinstance(k, str) for k in self.table))

    def test_a_symbol_with_a_declared_domain_is_not_offered(self):
        """A domain the paper stated is not the reader's to override here.
        Inviting that produces the wrong-domain-recorded-as-declared failure that
        false-alarm classes 14, 17 and 18 are all instances of."""
        self.assertNotIn(r"\eta", self.table)

    def test_a_blocking_symbol_is_offered(self):
        self.assertIn("w", self.table)

    def test_symbols_are_ordered_by_what_they_unblock(self):
        """`w` stands in three unmet obligations, `v` in one."""
        names = list(self.table)
        self.assertLess(names.index("w"), names.index("v"),
                        "ordered by occurrence rather than by what it unblocks")

    def test_the_notes_say_which_obligation_each_symbol_stands_in(self):
        self.assertIn("nonzero-denominator", self.notes)
        self.assertIn("log-argument-positive", self.notes)

    def test_the_notes_list_the_legal_values(self):
        """A value outside the list is refused, so the list has to be in reach."""
        self.assertIn("probability-distribution", self.notes)
        self.assertIn("unit-interval-half-open", self.notes)

    def test_a_paper_with_nothing_blocked_says_so(self):
        clean = PAPER.replace(r"A &= \frac{u}{w} \\", r"A &= u \\").replace(
            r"  &= \frac{u}{w} + \log v + \frac{1}{w}.", r"  &= u + 1.")
        table, notes = ledger_io.symbols_template(build(clean))
        self.assertIn("nothing", notes.lower())


if __name__ == "__main__":
    unittest.main()
