"""Assembly and the PDF build.

`latexmk` missing must leave the `.tex` written and exit 2. Losing the document
because a build tool is absent would discard the expensive part of the work — the
expansion — to preserve the cheap part.
"""
import unittest, sys, pathlib, tempfile, os, shutil
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))

from explain import assemble as A, build as B, notation as N  # noqa: E402

NOTATION = {"macros": {"R": {"nargs": 0, "body": r"\mathbb{R}"}},
            "symbols": [{"symbol": r"\gamma", "normalized": "gamma",
                         "domain": "unit-interval-half-open",
                         "domain_provenance": "declared",
                         "quote": r"$\gamma \in [0,1)$", "role": "scalar",
                         "occurrences": 5},
                        {"symbol": "w", "normalized": "w",
                         "domain": "not stated in the paper",
                         "domain_provenance": "unknown", "quote": "",
                         "role": "scalar", "occurrences": 2}]}

CLAIM = {"id": "claim/thm:x", "kind": "theorem", "label": "thm:x", "number": "1",
         "title": "A bound", "statement_tex": r"For all $\gamma$, $S = 1/(1-\gamma)$.",
         "hypotheses": [r"$\gamma \in [0,1)$"], "conclusion": r"$S = 1/(1-\gamma)$",
         "split_method": "then"}

ROWS = [{"step_id": "proof/thm:x/s01", "content_hash": "h1",
         "before_tex": r"S", "after_tex": r"1 + \gamma S",
         "move": "substitute-definition",
         "licensed_by": {"kind": "equation", "value": "eq:fix"},
         "breaks_if": "the series does not converge",
         "checked": {"verdict": "WEAK", "engine": "rational",
                     "script": "checks/a.py"},
         "gloss": "Peel off the first term.", "expanded_into": []},
        {"step_id": "proof/thm:x/s02", "content_hash": "h2",
         "before_tex": r"1 + \gamma S", "after_tex": r"\frac{1}{1-\gamma}",
         "move": "algebraic-rearrangement",
         "licensed_by": {"kind": "not-established", "value": ""},
         "breaks_if": r"$\gamma = 1$",
         "checked": {"verdict": "not run", "engine": None, "script": None},
         "gloss": "Solve for S.", "expanded_into": []}]

GAPS = [{"step_id": "proof/thm:x/s03", "severity": "BLOCKING",
         "kind": "cannot-justify", "what_is_missing": "the limit interchange",
         "what_would_close_it": "a dominating bound", "quote": "Taking limits"}]


def doc(**kw):
    kw.setdefault("claim", CLAIM)
    kw.setdefault("rows", ROWS)
    kw.setdefault("gaps", GAPS)
    kw.setdefault("notation", NOTATION)
    kw.setdefault("meta", {"source_file": "main.tex", "ledger_hash": "abc",
                           "level": "grad-ml", "paper": "Some paper"})
    return A.document(**kw)


class TestDocument(unittest.TestCase):
    def test_it_is_a_complete_latex_document(self):
        t = doc()
        self.assertIn(r"\documentclass", t)
        self.assertIn(r"\begin{document}", t)
        self.assertIn(r"\end{document}", t)

    def test_no_placeholder_survives(self):
        t = doc()
        import re
        self.assertEqual(re.findall(r"@@[A-Z]+@@", t), [],
                         "a template placeholder was never substituted")

    def test_every_row_becomes_a_step_block(self):
        self.assertEqual(doc().count(r"\stepblock"), len(ROWS))

    def test_a_blocking_gap_is_rendered_inline_as_well_as_in_the_ledger(self):
        t = doc()
        self.assertIn(r"\stepgap", t)
        self.assertIn("limit interchange", t)

    def test_not_run_is_rendered_as_not_run_never_as_a_pass(self):
        t = doc()
        self.assertIn("not run", t)
        self.assertNotIn("verified", t.lower().replace("unverified", ""))

    def test_the_notation_table_quotes_declared_domains(self):
        self.assertIn(r"[0,1)", doc())

    def test_an_unstated_domain_is_shown_as_unstated(self):
        self.assertIn("not stated in the paper", doc())

    def test_the_provenance_footer_names_the_register_and_the_source(self):
        t = doc()
        self.assertIn("grad-ml", t)
        self.assertIn("main.tex", t)

    def test_no_gaps_is_stated_explicitly(self):
        t = doc(gaps=[])
        self.assertIn("No gaps", t)

    def test_a_document_with_no_rows_says_it_could_not_be_expanded(self):
        t = doc(rows=[])
        self.assertIn("could not be expanded", t)

    def test_special_characters_in_prose_are_escaped(self):
        t = doc(rows=[dict(ROWS[0], gloss="100% of the mass & the rest")])
        self.assertIn(r"100\%", t)
        self.assertIn(r"\&", t)

    def test_mathematics_is_not_escaped(self):
        self.assertIn(r"\frac{1}{1-\gamma}", doc())


class TestBuild(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp()

    def write(self):
        os.makedirs(self.out, exist_ok=True)
        path = os.path.join(self.out, "thm-x.tex")
        with open(path, "w") as fh:
            fh.write(doc())
        return path

    def test_the_preamble_is_copied_next_to_the_document(self):
        A.write_document(self.out, "thm-x", doc())
        self.assertTrue(os.path.exists(os.path.join(self.out, "preamble.tex")),
                        "the artifact must still build after the skill is gone")

    def test_a_missing_latexmk_leaves_the_tex_and_reports_degraded(self):
        path = self.write()
        r = B.build_pdf(path, latexmk="definitely-not-a-real-binary")
        self.assertFalse(r["ok"])
        self.assertTrue(r["degraded"])
        self.assertTrue(os.path.exists(path), "the .tex must survive")
        self.assertIn("ask the user", r["detail"].lower())

    @unittest.skipUnless(shutil.which("latexmk"), "latexmk not installed")
    def test_a_real_build_produces_a_pdf(self):
        A.write_document(self.out, "thm-x", doc())
        r = B.build_pdf(os.path.join(self.out, "thm-x.tex"))
        self.assertTrue(r["ok"], r.get("detail"))
        self.assertTrue(os.path.exists(r["pdf"]))


if __name__ == "__main__":
    unittest.main()
