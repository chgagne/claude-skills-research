"""The subagent contract, and the guards that keep an expansion honest.

`licensed_by` being a closed set is the single most important rule in this skill.
The `expert-shorthand` register actively invites a plausible-sounding reason for a
step nobody checked, and a free-text justification field is exactly the affordance
that lets one through. Four shapes, one of which is the literal `not-established`.

Second most important: the expander may not write a mechanical verdict it did not
receive. With no checker results, every `checked` cell reads `not run`. Inventing
one would invert the purpose of the skill.
"""
import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))

from explain import fragment as F  # noqa: E402

ROW = {
    "step_id": "proof/thm:x/s07", "content_hash": "h7",
    "before_tex": r"\log \int q f", "after_tex": r"\int q \log f",
    "move": "apply-named-inequality:jensen",
    "licensed_by": {"kind": "named-result", "value": "jensen"},
    "breaks_if": r"the sum is infinite, or $q$ is not a density",
    "checked": {"verdict": "MAJOR", "engine": "sideconds",
                "script": "checks/proof-thm-x-s07.py"},
    "gloss": "Averaging a total is totalling the averages, for finitely many terms.",
    "expanded_into": [],
}

FRAG = {
    "request_id": "claim/thm:x", "contract": "explain-fragment/1",
    "tex_fragment": r"\stepblock{a}{b}{c}{d}{e}{f}",
    "rows": [ROW],
    "gaps": [{"step_id": "proof/thm:x/s11", "severity": "BLOCKING",
              "kind": "cannot-justify",
              "what_is_missing": r"the exchange of $\lim$ and $\sum$",
              "what_would_close_it": "a dominating summable bound",
              "quote": "Taking limits on both sides"}],
    "symbols_introduced": [], "macros_requested": [],
    "self_check": {"rows_cover_all_inference_steps": True, "unexplained_steps": 0,
                   "forbidden_tokens_present": False},
}

STEPS = {"proof/thm:x/s07": {"id": "proof/thm:x/s07", "content_hash": "h7",
                             "kind": "chain-row"},
         "proof/thm:x/s11": {"id": "proof/thm:x/s11", "content_hash": "h11",
                             "kind": "prose-move"}}

VERDICTS = {"proof/thm:x/s07": {"verdict": "MAJOR", "engine": "sideconds",
                                "script": "checks/proof-thm-x-s07.py"}}


def check(frag=None, steps=None, verdicts=None, **kw):
    return F.validate(frag or FRAG, steps or STEPS,
                      VERDICTS if verdicts is None else verdicts, **kw)


class TestLicensedBy(unittest.TestCase):
    def test_a_valid_shape_passes(self):
        self.assertEqual([p for p in check().problems if "licensed" in p], [])

    def test_free_text_is_refused(self):
        frag = _with_row(licensed_by="it is obvious from the definition")
        self.assertTrue([p for p in F.validate(frag, STEPS, VERDICTS).problems
                         if "licensed" in p])

    def test_an_unknown_kind_is_refused(self):
        frag = _with_row(licensed_by={"kind": "intuition", "value": "clear"})
        self.assertTrue([p for p in F.validate(frag, STEPS, VERDICTS).problems
                         if "licensed" in p])

    def test_all_four_shapes_are_accepted(self):
        for lb in ({"kind": "equation", "value": "eq:3"},
                   {"kind": "citation", "value": "vapnik1998"},
                   {"kind": "named-result", "value": "jensen"},
                   {"kind": "not-established", "value": ""}):
            frag = _with_row(licensed_by=lb)
            self.assertEqual(
                [p for p in F.validate(frag, STEPS, VERDICTS).problems
                 if "licensed" in p], [], "rejected %s" % lb["kind"])

    def test_not_established_is_a_first_class_answer(self):
        frag = _with_row(licensed_by={"kind": "not-established", "value": ""})
        r = F.validate(frag, STEPS, VERDICTS)
        self.assertTrue(r.ok)
        self.assertTrue(r.rows[0]["licensed_by"]["kind"] == "not-established")


class TestVerdictHonesty(unittest.TestCase):
    def test_with_no_verdicts_every_checked_cell_reads_not_run(self):
        r = F.validate(FRAG, STEPS, {})
        self.assertEqual(r.rows[0]["checked"]["verdict"], "not run")

    def test_a_verdict_the_expander_invented_is_refused(self):
        frag = _with_row(checked={"verdict": "SKIP", "engine": "symbolic",
                                  "script": "checks/made-up.py"})
        r = F.validate(frag, STEPS, VERDICTS)
        self.assertTrue([p for p in r.problems if "verdict" in p.lower()])

    def test_a_matching_verdict_is_kept(self):
        self.assertEqual(check().rows[0]["checked"]["engine"], "sideconds")


class TestContentHash(unittest.TestCase):
    def test_a_stale_hash_is_refused(self):
        frag = _with_row(content_hash="stale")
        r = F.validate(frag, STEPS, VERDICTS)
        self.assertFalse(r.ok)
        self.assertTrue([p for p in r.problems if "hash" in p.lower()])

    def test_a_missing_hash_is_refused(self):
        frag = _with_row(content_hash=None)
        self.assertFalse(F.validate(frag, STEPS, VERDICTS).ok)

    def test_an_unknown_step_is_refused(self):
        frag = _with_row(step_id="proof/thm:x/s99")
        self.assertFalse(F.validate(frag, STEPS, VERDICTS).ok)


class TestFragmentIsABodyNotADocument(unittest.TestCase):
    def test_usepackage_is_refused(self):
        for bad in (r"\usepackage{amsmath}", r"\documentclass{article}",
                    r"\begin{document}", r"\newcommand{\R}{\mathbb{R}}",
                    r"\renewcommand{\x}{y}", r"\def\z{1}"):
            frag = dict(FRAG, tex_fragment=bad + r"\stepblock{a}{b}{c}{d}{e}{f}")
            r = F.validate(frag, STEPS, VERDICTS)
            self.assertFalse(r.ok, "%s was allowed into a fragment" % bad)

    def test_macros_requested_is_the_sanctioned_channel(self):
        frag = dict(FRAG, macros_requested=[{"name": "qtil",
                                             "body": r"\tilde{q}",
                                             "why": "the normalised iterate"}])
        r = F.validate(frag, STEPS, VERDICTS)
        self.assertTrue(r.ok)
        self.assertEqual(r.macros_requested[0]["name"], "qtil")


class TestMoveVocabulary(unittest.TestCase):
    def test_a_known_move_passes_cleanly(self):
        self.assertEqual([p for p in check().problems if "move" in p.lower()], [])

    def test_an_off_vocabulary_move_is_flagged_not_dropped(self):
        frag = _with_row(move="hand-waving-manoeuvre")
        r = F.validate(frag, STEPS, VERDICTS)
        self.assertTrue(r.ok, "an unusual move is not a reason to lose the row")
        self.assertTrue([w for w in r.warnings if "vocabulary" in w.lower()])
        self.assertEqual(len(r.rows), 1)


class TestGaps(unittest.TestCase):
    def test_gap_severities_are_from_the_closed_set(self):
        self.assertEqual([p for p in check().problems if "severity" in p], [])

    def test_an_unknown_gap_severity_is_refused(self):
        frag = dict(FRAG, gaps=[dict(FRAG["gaps"][0], severity="CATASTROPHIC")])
        self.assertFalse(F.validate(frag, STEPS, VERDICTS).ok)

    def test_a_blocking_gap_must_say_what_would_close_it(self):
        frag = dict(FRAG, gaps=[dict(FRAG["gaps"][0], what_would_close_it="")])
        r = F.validate(frag, STEPS, VERDICTS)
        self.assertTrue([p for p in r.problems if "close" in p.lower()])


class TestContract(unittest.TestCase):
    def test_the_contract_version_is_checked(self):
        frag = dict(FRAG, contract="explain-fragment/99")
        self.assertFalse(F.validate(frag, STEPS, VERDICTS).ok)

    def test_a_fragment_with_no_rows_is_a_result_not_an_error(self):
        """A subagent that could not finish returns gaps and whatever it has."""
        frag = dict(FRAG, rows=[], tex_fragment="")
        r = F.validate(frag, STEPS, VERDICTS)
        self.assertTrue(r.ok)
        self.assertTrue(r.gaps)


def _with_row(**kw):
    return dict(FRAG, rows=[dict(ROW, **kw)])


class TestSilenceIsNoLongerAmbiguous(unittest.TestCase):
    """Four things the contract could not express, each found by an expander.

    All four cost a real subagent real work: two of them a lookup in the source,
    one a finding attached to the wrong single step, one a licence asserted
    before the text supplies it.
    """

    def test_a_gap_may_span_steps(self):
        frag = dict(FRAG, gaps=[{
            "step_ids": ["proof/thm:x/s07", "proof/thm:x/s11"],
            "severity": "SUBSTANTIVE", "kind": "k",
            "what_is_missing": "m", "what_would_close_it": "c"}])
        res = check(frag)
        self.assertTrue(res.ok, res.problems)
        self.assertEqual(res.gaps[0]["step_ids"],
                         ["proof/thm:x/s07", "proof/thm:x/s11"])

    def test_the_singular_form_still_validates_and_is_first(self):
        """Fragments written against the older shape must keep working."""
        res = check()
        self.assertTrue(res.ok, res.problems)
        self.assertEqual(res.gaps[0]["step_ids"], ["proof/thm:x/s11"])

    def test_a_gap_naming_a_step_outside_the_ledger_is_refused(self):
        frag = dict(FRAG, gaps=[{"step_ids": ["proof/thm:x/s99"],
                                 "severity": "COSMETIC", "kind": "k",
                                 "what_is_missing": "m"}])
        self.assertFalse(check(frag).ok)

    def test_a_licence_may_be_deferred_to_a_later_step(self):
        """The paper states the claim, then says why. Without this a row either
        asserts a licence the text has not yet given, or drops it."""
        rows = [dict(ROW, licensed_by={"kind": "local-result", "value": "lem:2",
                                       "deferred_to": "proof/thm:x/s11"})]
        res = check(dict(FRAG, rows=rows))
        self.assertTrue(res.ok, res.problems)

    def test_a_licence_deferred_to_nothing_is_refused(self):
        rows = [dict(ROW, licensed_by={"kind": "local-result", "value": "lem:2",
                                       "deferred_to": "proof/thm:x/s99"})]
        self.assertFalse(check(dict(FRAG, rows=rows)).ok)

    def test_the_request_names_the_steps_it_did_not_send(self):
        req = F.request(claim={"id": "claim/thm:x"}, proof={"id": "proof/thm:x"},
                        steps=[], notation={"macros": {}, "symbols": []},
                        context={}, verdicts={},
                        skipped_steps=[{"id": "proof/thm:x/s03",
                                        "kind": "narration",
                                        "why": "not an inference"}])
        self.assertEqual(req["skipped_steps"][0]["kind"], "narration")

    def test_a_request_with_nothing_skipped_still_has_the_key(self):
        req = F.request(claim={"id": "c"}, proof={"id": "p"}, steps=[],
                        notation={"macros": {}, "symbols": []}, context={},
                        verdicts={})
        self.assertEqual(req["skipped_steps"], [])


if __name__ == "__main__":
    unittest.main()
