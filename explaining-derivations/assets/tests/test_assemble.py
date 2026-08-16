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

    def test_an_undefined_control_sequence_is_reported_by_name(self):
        """`! Undefined control sequence.` alone sends the reader to a 900-line
        log to find one word. The token is on the following line."""
        log = ("Runaway argument?\n"
               "! Undefined control sequence.\n"
               "<argument> \\dd \n"
               "               m_t\n"
               "l.14 ...{\\dd m_t}\n")
        self.assertEqual(B._first_error(log),
                         "! Undefined control sequence.  (at \\dd)")

    def test_an_error_with_no_named_token_still_reports(self):
        self.assertEqual(B._first_error("! LaTeX Error: File `foo.sty' not found.\n"),
                         "! LaTeX Error: File `foo.sty' not found.")

    def test_no_error_in_a_clean_log(self):
        self.assertIsNone(B._first_error("Output written on thm-x.pdf (3 pages).\n"))


class TestRenderingEarnedByLookingAtPages(unittest.TestCase):
    """Every case here came from rendering a real expansion and reading it.

    None of them is catchable by asserting on the ledger: the fragment validated,
    the `.tex` was written, and four of the six produced a PDF. They are the
    reason `SKILL.md` says to look at the pages after any layout change.
    """

    def test_a_step_is_numbered_by_its_ledger_id_not_its_row_position(self):
        """Steps the checker skipped as narration never reach the expander, so
        row five can be step seven -- and the gap ledger keys on step ids."""
        self.assertEqual(A._step_number({"step_id": "proof/lem:x/s07"}, 5), "7")
        self.assertEqual(A._step_number({"step_id": None}, 5), "5")

    def test_a_verdict_with_no_engine_does_not_render_as_a_question_mark(self):
        cell = A._checked_cell({"verdict": "UNVERIFIED", "engine": None})
        self.assertNotIn("?", cell)
        self.assertIn("no engine could run", cell)

    def test_a_blocking_gap_and_a_substantive_one_do_not_look_the_same(self):
        """A SUBSTANTIVE gap sits beside a step that *was* expanded. Rendering it
        in the BLOCKING red under `could not be made explicit` contradicted the
        fully expanded block printed immediately above it."""
        blocking = A._gap_block(dict(GAPS[0], severity="BLOCKING"))
        substantive = A._gap_block(dict(GAPS[0], severity="SUBSTANTIVE"))
        self.assertTrue(blocking.startswith(r"\stepgap{"))
        self.assertTrue(substantive.startswith(r"\stepcaveat{"))

    def test_both_gap_macros_exist_in_the_frozen_preamble(self):
        text = pathlib.Path(A._TEMPLATES, "preamble.tex").read_text()
        self.assertIn(r"\newcommand{\stepgap}", text)
        self.assertIn(r"\newcommand{\stepcaveat}", text)

    def test_a_gap_names_its_step_by_number_not_by_its_full_id(self):
        """The full id is one unbreakable token. In a narrow table column it took
        half the width and pushed the last column 179pt past the right margin,
        where the text was clipped mid-word with a PDF produced anyway."""
        self.assertEqual(A._short_step("proof/lem:a_very_long_label/s07"), "Step 7")

    def test_the_gap_ledger_is_two_columns(self):
        """Four narrow columns overran on any gap carrying inline mathematics,
        which is most of them. One wide column removes the failure mode."""
        section = A._gap_section(GAPS)
        self.assertIn(r"p{0.17\textwidth} p{0.77\textwidth}", section)

    def test_a_conclusion_carrying_a_display_is_not_escaped_into_source(self):
        r"""Passing the clause through the prose escaper turned a displayed
        `align` into a paragraph of `\textbackslash{}sqrt\{...\}`."""
        got = A._clause("Then\n\\begin{align}\na &= b\n\\end{align}")
        self.assertNotIn(r"\textbackslash", got)

    def test_a_display_in_the_gloss_is_referred_to_rather_than_repeated(self):
        """The full statement is printed directly above the gloss, so repeating
        its displays set the same mathematics twice under two equation numbers."""
        got = A._clause(", the limit\n\\begin{align}\nm_t &\\to g_t\n\\end{align}")
        self.assertNotIn(r"\begin{align}", got)
        self.assertIn("the display in the statement above", got)
        self.assertFalse(got.startswith(","), "a split artefact left a bare comma")

    def test_an_accent_in_prose_survives_escaping(self):
        r"""`It\^o` and `Gr\"onwall` came back from a real expansion."""
        got = A._prose(r"via It\^o isometry plus Gr\"onwall")
        self.assertIn(r"It\^o", got)
        self.assertIn(r"Gr\"onwall", got)
        self.assertNotIn(r"\textbackslash", got)

    def test_prose_still_escapes_what_it_must(self):
        self.assertIn(r"\_", A._prose("a_b"))
        self.assertIn(r"\&", A._prose("a & b"))
        self.assertIn("$x^2$", A._prose("the term $x^2$ here"))

    def test_the_never_stated_note_is_made_once_not_per_row(self):
        table = A._notation_table(NOTATION)
        self.assertEqual(table.count("cannot be mechanically refuted")
                         + table.count("manufactures"), 1)


class TestNothingTheExpanderWritesIsSilentlyDiscarded(unittest.TestCase):
    """Two contract fields were validated and then thrown away.

    `tex_fragment` was checked for forbidden tokens, stored on `Result`, and
    never read by the assembler. `expanded_into` appeared nowhere in the code at
    all -- while `registers.md` instructs the expander at grad-ml that "a step
    that takes three moves to justify gets three sub-steps", and the validator
    accepted them. Both real dispatches filled the field in; on the second,
    roughly a page of what the expander wrote never reached the document.

    A spec that asks for work the code discards is worse than no spec.
    """

    def test_the_framing_paragraph_reaches_the_document(self):
        text = doc(tex_fragment="This lemma turns on one substitution.")
        self.assertIn("turns on one substitution", text)

    def test_sub_steps_reach_the_document(self):
        rows = [dict(ROWS[0], expanded_into=["Divide by $\\beta$.",
                                             "Collect the two terms."])]
        text = doc(rows=rows)
        self.assertIn("Divide by", text)
        self.assertIn("Collect the two terms", text)

    def test_a_step_with_no_sub_steps_renders_an_empty_ninth_argument(self):
        """The common case: a step that really is one move."""
        self.assertIn(r"\stepblock{", doc())

    def test_the_step_block_takes_nine_arguments(self):
        text = pathlib.Path(A._TEMPLATES, "preamble.tex").read_text()
        self.assertIn(r"\newcommand{\stepblock}[9]", text)


class TestLicenceKinds(unittest.TestCase):
    r"""A closed set that leaves out a common referent displaces free text
    somewhere worse rather than preventing it.

    Bubeck's gradient-mapping lemma turns on another lemma *of the same paper* --
    not an equation, not a bib key, not a move-vocabulary entry. The expander put
    the label in the `move` field, the only free-text-ish slot left.
    """

    def test_a_local_theorem_is_a_licence_kind(self):
        from explain import fragment as F
        self.assertIn("local-result", F.LICENCE_KINDS)

    def test_it_renders_as_a_result_of_this_paper(self):
        got = A._step_block(1, dict(ROWS[0], licensed_by={
            "kind": "local-result", "value": "lem:todonow"}))
        self.assertIn("lem:todonow", got)
        self.assertIn("this paper", got)

    def test_free_text_is_still_refused(self):
        from explain import fragment as F
        self.assertNotIn("free-text", F.LICENCE_KINDS)


class TestPreamblePackages(unittest.TestCase):
    """What the request may promise the subagent it can use.

    Read from the preamble rather than hard-coded: a list that drifts from the
    file it describes is a list that lies, and the cost of the lie is a document
    that dies on `Undefined control sequence` after the expansion is paid for.
    """

    def test_the_packages_are_read_from_the_frozen_preamble(self):
        got = N.preamble_packages()
        self.assertIn("amsmath", got)
        self.assertIn("amssymb", got)
        self.assertIn("mathtools", got)

    def test_a_package_with_options_is_read_without_them(self):
        with tempfile.NamedTemporaryFile("w", suffix=".tex", delete=False) as fh:
            fh.write("\\usepackage[margin=2.4cm]{geometry}\n"
                     "\\usepackage{amsmath,amssymb}\n"
                     "% \\usepackage{physics}\n")
            path = fh.name
        self.addCleanup(os.unlink, path)
        self.assertEqual(N.preamble_packages(path),
                         ["geometry", "amsmath", "amssymb"])

    def test_the_paper_may_load_packages_the_preamble_does_not(self):
        """The seam this exists for. `physics` gives the paper \\dd; the frozen
        preamble does not load it, and must not silently claim to."""
        self.assertNotIn("physics", N.preamble_packages())

    def test_a_missing_preamble_is_an_empty_list_not_a_crash(self):
        self.assertEqual(N.preamble_packages("/nonexistent/preamble.tex"), [])


if __name__ == "__main__":
    unittest.main()
