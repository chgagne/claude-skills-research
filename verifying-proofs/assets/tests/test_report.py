"""The report.

Two things it must never do: render `UNVERIFIED` as though it were a pass, and
imply completeness it did not achieve. The coverage histogram heads the document
for exactly that reason -- on a real paper "6 of 41 inference steps were
mechanically checkable" is not a caveat, it is the finding.
"""
import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))

from proofcheck import report as R  # noqa: E402


LEDGER = {
    "schema": "latexmath-ledger/1",
    "source": {"root": "/tmp/main.tex", "files": ["main.tex"]},
    "claims": [{"id": "claim/t1", "kind": "theorem", "label": "t1", "number": "1",
                "title": None, "statement_tex": "S", "duplicate_of": None,
                "hypotheses_diff": [], "source": {"start": 0, "end": 10}}],
    "proofs": [{"id": "proof/t1", "claim_id": "claim/t1", "attachment": "adjacent",
                "structure": {"is_induction": False, "base_case": {"verdict": "n/a"},
                              "cases": [], "hedges": [], "qed_present": True},
                "source": {"start": 0, "end": 10}}],
    "steps": [{"id": "proof/t1/s01", "proof_id": "proof/t1", "ordinal": 1,
               "kind": "chain-row", "checkable": "candidate", "opacity_reasons": [],
               "math_tex": "a | b = c", "prose_tex": "By Jensen,",
               "side_conditions": [], "symbols_used": ["a"], "case_path": [],
               "justification": {"kind": "named-result", "name": "jensen",
                                 "refs": [], "cites": [], "hedges": []},
               "content_hash": "h1", "source": {"file": "main.tex", "offset": 3}}],
    "symbols": [{"symbol": "a", "domain_hint": None,
                 "domain_provenance": "unknown", "domain_evidence": [],
                 "first_use": {"start": 1, "end": 2}, "occurrences": 1,
                 "defined_at": None, "role_hint": "scalar", "normalized": "a",
                 "scopes": []}],
    "equations": [],
    "refs": {"labels": {}, "edges": [], "dangling": [], "unused_labels": [],
             "forward_refs": [], "cycles": []},
    "coverage": {"claims": 1, "proofs": 1, "steps": 1,
                 "steps_by_kind": {"chain-row": 1}, "inference_steps": 1,
                 "checkable_candidates": 1, "opaque": 0, "structural": 0,
                 "opacity_histogram": {"asymptotic": 3},
                 "proof_text_captured_pct": 100.0, "macros_unexpandable": 0,
                 "symbols_with_unknown_domain": 1},
    "diagnostics": [], "macros_unexpandable": [],
}

VERDICTS = [{"step": "proof/t1/s01", "proof": "proof/t1", "severity": "UNVERIFIED",
             "detail": "not mechanisable: asymptotic", "confirmed": False,
             "counterexample": None, "engines": ["rational"],
             "scripts": ["checks/proof-t1-s01.py"]}]

FINDINGS = [{"kind": "side-condition-unstated", "severity": "MAJOR",
             "detail": "needs $1-\\gamma$ non-zero", "claim": "claim/t1",
             "proof": "proof/t1", "step": "proof/t1/s01", "evidence": "1-\\gamma",
             "script": None, "engine": None}]

CHECKERS = [{"name": "sympy", "available": True, "version": "1.12"},
            {"name": "z3", "available": False, "version": None}]


def md(**kw):
    kw.setdefault("ledger", LEDGER)
    kw.setdefault("verdicts", VERDICTS)
    kw.setdefault("findings", FINDINGS)
    kw.setdefault("checkers", CHECKERS)
    return R.markdown(**kw)


class TestHeader(unittest.TestCase):
    def test_the_coverage_histogram_heads_the_report(self):
        text = md()
        cov = text.index("Coverage")
        for later in ("Findings", "Per-step verdicts"):
            self.assertLess(cov, text.index(later),
                            "%s appeared before coverage" % later)

    def test_the_header_says_which_checkers_ran_and_which_did_not(self):
        text = md()
        self.assertIn("sympy", text)
        self.assertIn("1.12", text)
        self.assertIn("z3", text)
        self.assertRegex(text, r"z3[^\n]*(not installed|absent|unavailable)")

    def test_inference_steps_are_reported_against_checkable_ones(self):
        self.assertRegex(md(), r"1\s*(?:of|/)\s*1")

    def test_the_opacity_histogram_appears(self):
        self.assertIn("asymptotic", md())

    def test_unknown_domains_are_stated_as_a_limit_on_the_run(self):
        self.assertRegex(md().lower(), r"domain[^\n]*could not|could not[^\n]*domain")


class TestSeverityRendering(unittest.TestCase):
    def test_severities_are_ordered_worst_first(self):
        text = md(findings=[
            {"kind": "k1", "severity": "MINOR", "detail": "d", "claim": None,
             "proof": None, "step": None, "evidence": None, "script": None,
             "engine": None},
            {"kind": "k2", "severity": "CRITICAL", "detail": "d", "claim": None,
             "proof": None, "step": None, "evidence": None, "script": None,
             "engine": None}])
        self.assertLess(text.index("CRITICAL"), text.index("MINOR"))

    def test_each_severity_present_carries_its_blurb(self):
        self.assertIn("licence is missing", md())

    def test_unverified_is_never_rendered_as_a_pass(self):
        text = md().lower()
        self.assertNotIn("all steps verified", text)
        self.assertNotIn("no problems found", text)
        self.assertIn("finding, not a pass", text)

    def test_the_word_verified_is_not_claimed_for_sampling(self):
        text = R.markdown(
            ledger=LEDGER, checkers=CHECKERS, findings=[],
            verdicts=[dict(VERDICTS[0], severity="WEAK",
                           detail="NOT REFUTED -- 24 sample points")])
        self.assertNotIn("verified", text.lower().replace("unverified", ""))


class TestTables(unittest.TestCase):
    def test_pipes_in_mathematics_are_escaped(self):
        for line in md().splitlines():
            if line.startswith("|"):
                cells = line.split("|")[1:-1]
                for c in cells:
                    self.assertNotIn("| b", c, "an unescaped pipe broke a row")

    def test_every_verdict_cites_its_script(self):
        self.assertIn("checks/proof-t1-s01.py", md())

    def test_a_finding_names_its_claim_and_step(self):
        text = md()
        self.assertIn("claim/t1", text)
        self.assertIn("proof/t1/s01", text)


class TestCsv(unittest.TestCase):
    def test_columns_match_the_documented_order(self):
        rows = R.csv_rows(LEDGER, VERDICTS, FINDINGS)
        self.assertEqual(rows[0], ["claim", "proof", "step", "kind", "engine",
                                   "verdict", "severity", "detail", "script"])

    def test_one_row_per_step(self):
        rows = R.csv_rows(LEDGER, VERDICTS, FINDINGS)
        self.assertEqual(len(rows), 1 + len(LEDGER["steps"]) + len(FINDINGS))


class TestCheckerTable(unittest.TestCase):
    def test_a_run_needing_no_checker_says_so_rather_than_showing_an_empty_table(self):
        text = R.markdown(ledger=LEDGER, verdicts=[], findings=[], checkers=[])
        self.assertNotRegex(text, r"\| Checker \| Status \|\n\|---\|---\|\n\n")
        self.assertIn("no external checker", text.lower())


class TestEmptyRun(unittest.TestCase):
    def test_a_paper_with_no_proofs_says_so_rather_than_passing_it(self):
        empty = dict(LEDGER, claims=[], proofs=[], steps=[],
                     coverage=dict(LEDGER["coverage"], claims=0, proofs=0, steps=0,
                                   inference_steps=0, checkable_candidates=0))
        text = R.markdown(ledger=empty, verdicts=[], findings=[],
                          checkers=CHECKERS)
        self.assertIn("no proof", text.lower())


if __name__ == "__main__":
    unittest.main()
