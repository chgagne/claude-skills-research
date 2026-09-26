# tests/test_markup.py
import unittest
from proofread.ledger import Row
from proofread.markup import wrap_cites, escape_comment, comment, replaced, deleted, render_edit, render_comment

def row(**kw):
    base = dict(id="W3", level="style", section="1", para=1, anchor="count vary",
                replacement="count varies", comment="W3: agreement", rationale="r",
                rule="defaults:agreement", confidence=0.9, status="kept")
    base.update(kw)
    return Row(**base)

class TestPrimitives(unittest.TestCase):
    def test_wrap_cites_multikey(self):
        self.assertEqual(wrap_cites(r"runs~\cite{a,b}."), r"runs~\mbox{\cite{a,b}}.")

    def test_wrap_cites_citep_with_option(self):
        self.assertIn(r"\mbox{\citep[p.~3]{a}}", wrap_cites(r"x \citep[p.~3]{a} y"))

    def test_comment_escapes_specials(self):
        out = escape_comment("50% of runs & x_i {unbalanced")
        self.assertEqual(out, r"50\% of runs \& x\_i \{unbalanced")

    def test_comment_escapes_superscript_and_tilde(self):
        # A bare ^ in a margin note is typeset inside todonotes' tikzpicture, where it
        # does not fail where it stands: the environment runs to \end{document}, and the
        # level bisect then blames whichever level happened to carry the row.
        out = escape_comment("L^S5 differs from L_full ~ here")
        self.assertNotIn("^", out)
        self.assertNotIn("~", out)
        self.assertIn(r"\textasciicircum{}", out)
        self.assertIn(r"\textasciitilde{}", out)

    def test_comment_escapes_backslash_commands(self):
        out = escape_comment(r"'of' should be '\citet{key}'")
        self.assertNotIn("\\citet", out)
        self.assertIn(r"\textbackslash{}citet\{key\}", out)

    def test_replaced_and_deleted_forms(self):
        self.assertEqual(replaced("new", "old"), r"\chreplaced[id=LG]{new}{old}")
        self.assertEqual(deleted("old"), r"\chdeleted[id=LG]{old}")
        self.assertEqual(comment("W1: x"), r"\chcomment[id=LG]{W1: x}")

class TestRows(unittest.TestCase):
    def test_style_row_puts_comment_before_replacement(self):
        out = render_edit(row())
        self.assertEqual(out, r"\chcomment[id=LG]{W3: agreement}\chreplaced[id=LG]{count varies}{count vary}")

    def test_mechanics_row_has_no_comment(self):
        out = render_edit(row(level="mechanics", comment="", rule=""))
        self.assertEqual(out, r"\chreplaced[id=LG]{count varies}{count vary}")

    def test_empty_replacement_is_deletion(self):
        out = render_edit(row(level="mechanics", comment="", rule="", replacement=""))
        self.assertEqual(out, r"\chdeleted[id=LG]{count vary}")

    def test_cites_inside_edit_are_wrapped(self):
        out = render_edit(row(level="mechanics", comment="", rule="",
                              anchor=r"runs \cite{a,b}", replacement=r"runs~\cite{a,b}"))
        self.assertEqual(out.count(r"\mbox{\cite{a,b}}"), 2)

    def test_render_comment_with_suffix(self):
        out = render_comment(row(level="flow", replacement=None, comment="W9: claim before evidence"), suffix="; see report")
        self.assertEqual(out, r"\chcomment[id=LG]{W9: claim before evidence; see report}")

    def test_comment_only_row_never_renders_edit(self):
        with self.assertRaises(ValueError):
            render_edit(row(level="flow", replacement=None, comment="W9: x"))
