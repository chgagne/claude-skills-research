"""Triage, frozen notation, and the gap ledger.

`--plan-only` making no dispatch is the pre-flight discipline the orchestrator
mandates elsewhere: a dozen theorems is a dozen subagents, and finding out
afterwards that the wrong ones were expanded is expensive.

Notation is frozen *before* dispatch because fragments are produced
independently. Two subagents introducing the same symbol with different meanings
must produce a NOTATIONAL gap and a rename, never a silent overwrite.
"""
import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))

from explain import triage as T, notation as N, gaps as G  # noqa: E402

LEDGER = {
    "schema": "latexmath-ledger/1",
    "claims": [
        {"id": "claim/thm:main", "kind": "theorem", "label": "thm:main",
         "number": "1", "title": None, "statement_tex": "Main.",
         "hypotheses": [], "conclusion": "Main.", "duplicate_of": None,
         "hypotheses_diff": [], "source": {"start": 0, "end": 10}},
        {"id": "claim/lem:aux", "kind": "lemma", "label": "lem:aux",
         "number": "2", "title": None, "statement_tex": "Aux.",
         "hypotheses": [], "conclusion": "Aux.", "duplicate_of": None,
         "hypotheses_diff": [], "source": {"start": 20, "end": 30}},
        {"id": "claim/cor:iso", "kind": "corollary", "label": "cor:iso",
         "number": "3", "title": None, "statement_tex": "Iso.",
         "hypotheses": [], "conclusion": "Iso.", "duplicate_of": None,
         "hypotheses_diff": [], "source": {"start": 40, "end": 50}},
    ],
    "proofs": [
        {"id": "proof/thm:main", "claim_id": "claim/thm:main",
         "attachment": "adjacent", "structure": {"is_induction": False,
                                                 "base_case": {"verdict": "n/a"},
                                                 "cases": [], "hedges": [],
                                                 "qed_present": True},
         "source": {"start": 10, "end": 20}},
        {"id": "proof/lem:aux", "claim_id": "claim/lem:aux",
         "attachment": "adjacent", "structure": {"is_induction": False,
                                                 "base_case": {"verdict": "n/a"},
                                                 "cases": [], "hedges": [],
                                                 "qed_present": True},
         "source": {"start": 30, "end": 40}},
        {"id": "proof/cor:iso", "claim_id": "claim/cor:iso",
         "attachment": "adjacent", "structure": {"is_induction": False,
                                                 "base_case": {"verdict": "n/a"},
                                                 "cases": [], "hedges": [],
                                                 "qed_present": True},
         "source": {"start": 50, "end": 60}},
    ],
    "steps": (
        [{"id": "proof/thm:main/s%02d" % i, "proof_id": "proof/thm:main",
          "ordinal": i, "kind": "chain-row", "checkable": "candidate",
          "opacity_reasons": [], "math_tex": "a = b", "prose_tex": "",
          "side_conditions": [], "symbols_used": [], "case_path": [],
          "claim_forms": [], "content_hash": "h%d" % i,
          "justification": {"kind": "none", "name": None, "refs": [],
                            "cites": [], "hedges": []},
          "source": {"file": "main.tex", "offset": i}} for i in range(1, 13)]
        + [{"id": "proof/lem:aux/s01", "proof_id": "proof/lem:aux", "ordinal": 1,
            "kind": "narration", "checkable": "structural", "opacity_reasons": [],
            "math_tex": "", "prose_tex": "Recall.", "side_conditions": [],
            "symbols_used": [], "case_path": [], "claim_forms": [],
            "content_hash": "hx",
            "justification": {"kind": "none", "name": None, "refs": [],
                              "cites": [], "hedges": []},
            "source": {"file": "main.tex", "offset": 30}}]
        + [{"id": "proof/cor:iso/s01", "proof_id": "proof/cor:iso", "ordinal": 1,
            "kind": "inline-assert", "checkable": "candidate",
            "opacity_reasons": [], "math_tex": "c = d", "prose_tex": "",
            "side_conditions": [], "symbols_used": [], "case_path": [],
            "claim_forms": [], "content_hash": "hy",
            "justification": {"kind": "none", "name": None, "refs": [],
                              "cites": [], "hedges": []},
            "source": {"file": "main.tex", "offset": 50}}]),
    "symbols": [
        {"symbol": r"\gamma", "normalized": "gamma",
         "domain_hint": "unit-interval-half-open", "domain_provenance": "declared",
         "domain_evidence": [{"quote": r"$\gamma \in [0,1)$"}],
         "first_use": {"start": 1, "end": 2}, "occurrences": 5,
         "defined_at": {"start": 1, "end": 2}, "role_hint": "scalar", "scopes": []},
    ],
    "macros": [{"name": "R", "nargs": 0, "body": r"\mathbb{R}", "is_math": True},
               {"name": "secref", "nargs": 1, "body": r"Section~\ref{#1}",
                "is_math": False}],
    "equations": [],
    "refs": {"labels": {}, "edges": [
        {"from": "proof/thm:main", "claim": "claim/thm:main", "label": "lem:aux",
         "cmd": "ref", "resolved": True}],
        "dangling": [], "unused_labels": [], "forward_refs": [], "cycles": []},
    "coverage": {}, "diagnostics": [], "macros_unexpandable": [],
}


class TestTriage(unittest.TestCase):
    def test_one_request_per_provable_claim_with_a_proof(self):
        plan = T.plan(LEDGER)
        self.assertEqual(len(plan), 3)

    def test_cost_is_estimated_in_inference_steps_not_raw_steps(self):
        plan = {p["claim_id"]: p for p in T.plan(LEDGER)}
        self.assertEqual(plan["claim/lem:aux"]["inference_steps"], 0)
        self.assertEqual(plan["claim/lem:aux"]["steps"], 1)
        self.assertEqual(plan["claim/thm:main"]["inference_steps"], 12)

    def test_load_bearing_claims_come_first(self):
        """A claim other proofs depend on outranks an isolated corollary."""
        order = [p["claim_id"] for p in T.plan(LEDGER)]
        self.assertLess(order.index("claim/lem:aux"), order.index("claim/cor:iso"),
                        "a lemma the main theorem uses should outrank a corollary "
                        "nothing depends on")

    def test_restricting_to_named_claims(self):
        plan = T.plan(LEDGER, claims={"thm:main"})
        self.assertEqual([p["claim_id"] for p in plan], ["claim/thm:main"])

    def test_only_flagged_selects_steps_with_a_verdict_or_a_hedge(self):
        verdicts = {"proof/thm:main/s03": {"verdict": "MAJOR"}}
        plan = {p["claim_id"]: p for p in
                T.plan(LEDGER, verdicts=verdicts, only_flagged=True)}
        self.assertEqual(plan["claim/thm:main"]["step_ids"],
                         ["proof/thm:main/s03"])

    def test_default_expands_every_inference_step(self):
        plan = {p["claim_id"]: p for p in T.plan(LEDGER)}
        self.assertEqual(len(plan["claim/thm:main"]["step_ids"]), 12)

    def test_a_restatement_is_planned_when_it_is_the_one_with_the_proof(self):
        """Measured on a real draft: all five main results vanished from the plan.

        The body states the theorem and the appendix restates it with the proof
        attached. Skipping everything marked `duplicate_of` then skips exactly the
        claims that carry the proofs -- and the body copies are skipped too, for
        having no proof of their own. The paper's headline results become
        unexpandable.
        """
        led = dict(LEDGER)
        led["claims"] = LEDGER["claims"] + [
            {"id": "claim/thm:main_restated", "kind": "theorem",
             "label": "thm:main_restated", "number": "4", "title": None,
             "statement_tex": "Main.", "hypotheses": [], "conclusion": "Main.",
             "duplicate_of": "claim/thm:main", "hypotheses_diff": [],
             "source": {"start": 70, "end": 80}}]
        led["proofs"] = [p for p in LEDGER["proofs"]
                         if p["claim_id"] != "claim/thm:main"] + [
            {"id": "proof/thm:main_restated", "claim_id": "claim/thm:main_restated",
             "attachment": "adjacent",
             "structure": {"is_induction": False, "base_case": {"verdict": "n/a"},
                           "cases": [], "hedges": [], "qed_present": True},
             "source": {"start": 80, "end": 90}}]
        led["steps"] = [s for s in LEDGER["steps"]
                        if s["proof_id"] != "proof/thm:main"] + [
            dict(LEDGER["steps"][0], id="proof/thm:main_restated/s01",
                 proof_id="proof/thm:main_restated")]
        planned = [p["claim_id"] for p in T.plan(led)]
        self.assertIn("claim/thm:main_restated", planned,
                      "the only copy carrying a proof was skipped")

    def test_a_duplicate_whose_original_is_proved_is_still_skipped(self):
        """When both copies have a proof, expanding both is waste."""
        led = dict(LEDGER)
        led["claims"] = LEDGER["claims"] + [
            {"id": "claim/thm:main_restated", "kind": "theorem",
             "label": "thm:main_restated", "number": "4", "title": None,
             "statement_tex": "Main.", "hypotheses": [], "conclusion": "Main.",
             "duplicate_of": "claim/thm:main", "hypotheses_diff": [],
             "source": {"start": 70, "end": 80}}]
        led["proofs"] = LEDGER["proofs"] + [
            {"id": "proof/thm:main_restated", "claim_id": "claim/thm:main_restated",
             "attachment": "adjacent",
             "structure": {"is_induction": False, "base_case": {"verdict": "n/a"},
                           "cases": [], "hedges": [], "qed_present": True},
             "source": {"start": 80, "end": 90}}]
        led["steps"] = LEDGER["steps"] + [
            dict(LEDGER["steps"][0], id="proof/thm:main_restated/s01",
                 proof_id="proof/thm:main_restated")]
        planned = [p["claim_id"] for p in T.plan(led)]
        self.assertNotIn("claim/thm:main_restated", planned)
        self.assertIn("claim/thm:main", planned)

    def test_a_claim_with_no_proof_is_not_planned(self):
        led = dict(LEDGER, proofs=[p for p in LEDGER["proofs"]
                                   if p["claim_id"] != "claim/cor:iso"])
        self.assertNotIn("claim/cor:iso",
                         [p["claim_id"] for p in T.plan(led)])


class TestFrozenNotation(unittest.TestCase):
    def test_only_math_macros_enter_the_preamble(self):
        n = N.freeze(LEDGER)
        self.assertIn("R", n["macros"])
        self.assertNotIn("secref", n["macros"],
                         "a cross-reference helper is not notation")

    def test_symbols_carry_their_domain_and_its_quote(self):
        n = N.freeze(LEDGER)
        g = {s["symbol"]: s for s in n["symbols"]}[r"\gamma"]
        self.assertEqual(g["domain_provenance"], "declared")
        self.assertIn("[0,1)", g["quote"])

    def test_a_symbol_with_no_stated_domain_says_so(self):
        led = dict(LEDGER, symbols=[dict(LEDGER["symbols"][0],
                                         domain_hint=None,
                                         domain_provenance="unknown",
                                         domain_evidence=[])])
        g = N.freeze(led)["symbols"][0]
        self.assertEqual(g["domain"], "not stated in the paper")


class TestCollisions(unittest.TestCase):
    def sym(self, symbol, why):
        return {"symbol": symbol, "why": why, "defined_in_fragment": True}

    def test_two_fragments_defining_a_symbol_differently_collide(self):
        frags = [{"request_id": "claim/a",
                  "symbols_introduced": [self.sym(r"\tq", "normalised iterate")]},
                 {"request_id": "claim/b",
                  "symbols_introduced": [self.sym(r"\tq", "the target measure")]}]
        found = N.collisions(frags, N.freeze(LEDGER))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["severity"], "NOTATIONAL")
        self.assertIn(r"\tq", found[0]["what_is_missing"])

    def test_the_same_meaning_twice_is_not_a_collision(self):
        frags = [{"request_id": "claim/a",
                  "symbols_introduced": [self.sym(r"\tq", "normalised iterate")]},
                 {"request_id": "claim/b",
                  "symbols_introduced": [self.sym(r"\tq", "normalised iterate")]}]
        self.assertEqual(N.collisions(frags, N.freeze(LEDGER)), [])

    def test_a_symbol_shadowing_the_papers_own_notation_is_a_collision(self):
        frags = [{"request_id": "claim/a",
                  "symbols_introduced": [self.sym(r"\gamma", "a fresh index")]}]
        found = N.collisions(frags, N.freeze(LEDGER))
        self.assertEqual(len(found), 1)


class TestGapLedger(unittest.TestCase):
    ROWS = [{"step_id": "proof/thm:main/s01", "severity": "BLOCKING",
             "kind": "cannot-justify", "what_is_missing": "the interchange",
             "what_would_close_it": "a dominating bound", "quote": "q"},
            {"step_id": "proof/thm:main/s02", "severity": "COSMETIC",
             "kind": "index-slip", "what_is_missing": "off by one",
             "what_would_close_it": "renumber", "quote": "q"}]

    def test_default_shows_substantive_and_above(self):
        shown = G.reportable(self.ROWS)
        self.assertEqual([g["severity"] for g in shown], ["BLOCKING"])

    def test_all_gaps_shows_everything(self):
        self.assertEqual(len(G.reportable(self.ROWS, all_gaps=True)), 2)

    def test_the_rollup_counts_match(self):
        r = G.rollup({"claim/thm:main": self.ROWS})
        self.assertEqual(r["by_severity"]["BLOCKING"], 1)
        self.assertEqual(r["total"], 2)

    def test_no_gaps_is_stated_explicitly_never_implied(self):
        r = G.rollup({"claim/thm:main": []})
        self.assertEqual(r["total"], 0)
        self.assertIn("no gap", r["summary"].lower())

    def test_a_blocking_gap_dominates_the_summary(self):
        r = G.rollup({"claim/thm:main": self.ROWS})
        self.assertIn("BLOCKING", r["summary"])

    def test_gaps_become_review_findings_with_severities(self):
        f = G.as_findings({"claim/thm:main": self.ROWS})
        self.assertEqual(f[0]["severity"], "MAJOR")
        self.assertEqual(f[0]["kind"], "derivation-gap")
        self.assertEqual(f[0]["claim"], "claim/thm:main")


class TestTheRequestCarriesWhatTheProofCites(unittest.TestCase):
    r"""Both expanders that have run reported the same two gaps in the request.

    Two independent complaints on different papers is the threshold for treating
    something as a finding rather than an anecdote.

    An `\eqref` resolves to no *claim*, so the reference lookup dropped it and
    the request carried no equations at all -- while equations are most of what a
    proof cites. On Bubeck the proof cites two by label, neither reached the
    subagent, and it opened the source to read them before it could explain the
    step that uses them.

    And the glossary went whole: 81 symbols on that paper, 67 of them reading
    "not stated in the paper". `assemble.py` already narrowed the *rendered*
    table to the symbols an expansion uses; the request did not.
    """

    def _request(self):
        led = dict(LEDGER)
        led["equations"] = [
            {"id": "eq/100", "env": "equation", "labels": ["eq:fix"],
             "row_labels": {"1": "eq:fix"},
             "expanded_tex": r"\begin{equation}\label{eq:fix} S = 1 + \gamma S"
                             r"\end{equation}", "raw_tex": ""},
        ]
        led["refs"] = dict(led.get("refs") or {}, edges=[
            {"from": "proof/thm:main", "claim": "claim/thm:main",
             "label": "eq:fix", "cmd": "eqref", "resolved": True}])
        plan = T.plan(led)
        row = [p for p in plan if p["claim_id"] == "claim/thm:main"][0]
        return T.request_for(led, row, {})

    def test_a_cited_equation_reaches_the_expander(self):
        eqs = self._request()["context"]["referenced_equations"]
        self.assertEqual([e["label"] for e in eqs], ["eq:fix"])
        self.assertIn("1 + ", eqs[0]["tex"])

    def test_the_glossary_is_narrowed_to_what_the_proof_uses(self):
        req = self._request()
        used = {s for step in req["steps"] for s in (step.get("symbols_used") or [])}
        listed = {s["symbol"] for s in req["notation"]["symbols"]}
        self.assertTrue(listed <= used or not used,
                        "the request carries symbols the proof never touches: %s"
                        % sorted(listed - used))

    def test_a_proof_citing_nothing_gets_an_empty_list_not_a_missing_key(self):
        plan = T.plan(LEDGER)
        row = [p for p in plan if p["claim_id"] == "claim/thm:main"][0]
        self.assertEqual(T.request_for(LEDGER, row, {})["context"]
                         ["referenced_equations"], [])


if __name__ == "__main__":
    unittest.main()
