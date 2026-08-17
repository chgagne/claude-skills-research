"""Engine verdicts -> a per-step severity, and the findings that need no engine.

The severity ladder mirrors `verifying-bibliography`'s shape with meanings
adapted to proofs. Two of its rungs are the ones that matter:

- **`MAJOR` is a missing licence, not a wrong step.** The algebra can be right
  and the theorem still unproved -- a side condition nobody assumed, a limit
  interchanged without justification, a restatement that quietly drops a
  hypothesis. Most real findings live here.
- **`UNVERIFIED` is a finding, not a pass.** A dense cluster of it in one proof
  *is* the headline, and the report must never let it read as a clean bill.

- **`LOCAL` is a refutation that did not travel.** Measured on two validated
  papers: a line printed with `\\lambda T` where the algebra gives `\\lambda^T`,
  and a stated threshold looser than the inequality it is supposed to license.
  Both are real -- checked by hand, refuted by two independent translations --
  and neither touches the result. Reported as `CRITICAL` they read as "this
  theorem is wrong", which they do not support.

Three composition rules exist to stop the tool reporting its own limitations as
the paper's mistakes, and they are asserted directly in `test_compose.py`:

1. A symbol whose domain nobody stated can never produce a refutation.
2. A translation that is not `faithful` caps the severity at `WEAK`.
3. Engines that disagree yield `UNVERIFIED` -- never `CRITICAL`.

A fourth, in `apply_supersession`, demotes rather than suppresses, and is
deliberately the narrowest rule that fits the evidence: see its docstring.

The structural half of this module needs no external checker at all, and on real
papers it is where nearly all of the usable output comes from.
"""
import re

#: Ordered worst-first, as the sibling skills order theirs.
SEVERITIES = ("CRITICAL", "MAJOR", "LOCAL", "MINOR", "WEAK", "UNVERIFIED", "SKIP")

SEVERITY_BLURB = {
    "CRITICAL": "A reproduced counterexample under a faithful translation inside "
                "the stated domain, or a structural break in the argument. "
                "**Says the step as written is false; it does not say the theorem "
                "is.** Whether the refutation reaches the result depends on how the "
                "step is used downstream, which no engine here answers -- on one "
                "validated paper a step overstated a tolerance about fivefold and "
                "the result still held, because downstream it was only ever used "
                "well inside the supported range.",
    "MAJOR": "Not refuted, but the licence is missing: the algebra can be right "
             "and the theorem still unproved.",
    "LOCAL": "Refuted where it stands, and the refutation was not observed to "
             "travel: this is not the last row of its chain, and **every** row "
             "after it was independently confirmed. This does not say the result "
             "is safe -- only how far the failure was seen to reach.",
    "MINOR": "Impedes checking rather than threatening the argument.",
    "WEAK": "Checked only by sampling, or under a translation that was not "
            "faithful. **Not verified.**",
    "UNVERIFIED": "Could not be mechanised. **A finding, not a pass** -- a "
                  "cluster of these in one proof is the headline.",
    "SKIP": "Not an inference, or confirmed symbolically.",
}

#: Only these engines may ever *confirm*. Everything else can only fail to refute.
CONFIRMING_ENGINES = {"symbolic": ("=",), "smt": ("<", ">", "\\le", "\\ge")}

_FAITHFUL = "faithful"


def is_pass(severity):
    """`WEAK` and `UNVERIFIED` are not clean bills of health."""
    return severity == "SKIP"


def worst(severities):
    for s in SEVERITIES:
        if s in severities:
            return s
    return "SKIP"


def _finding(kind, severity, detail, **extra):
    out = {"kind": kind, "severity": severity, "detail": detail,
           "claim": None, "step": None, "proof": None, "evidence": None,
           "script": None, "engine": None}
    out.update(extra)
    return out


# --------------------------------------------------------------------------
# Engine 0: everything reachable without a computer algebra system.
# --------------------------------------------------------------------------

def structural_findings(ledger):
    """Findings that need no external checker.

    On three real papers this is where the usable output was, so it runs first
    and it runs even when every checker is absent.
    """
    out = []
    out += _induction_findings(ledger)
    out += _cycle_findings(ledger)
    out += _restatement_findings(ledger)
    out += _reference_findings(ledger)
    out += _diagnostic_findings(ledger)
    out += _side_condition_findings(ledger)
    out += _hedge_findings(ledger)
    return sorted(out, key=lambda f: SEVERITIES.index(f["severity"]))


def _induction_findings(ledger):
    out = []
    for p in ledger.get("proofs", []):
        st = p.get("structure") or {}
        if not st.get("is_induction"):
            continue
        bc = st.get("base_case") or {}
        verdict = bc.get("verdict")
        if verdict == "not-found":
            out.append(_finding(
                "induction-no-base-case", "CRITICAL",
                "induction on $%s$ with no base case: %s"
                % (bc.get("variable"), bc.get("evidence")),
                proof=p["id"], claim=p.get("claim_id")))
        elif verdict == "unknown":
            # Measured on arXiv:1806.07572, where hard-coding the induction
            # variable made this a CRITICAL on 4 of 4 correct proofs.
            out.append(_finding(
                "induction-base-case-unclear", "UNVERIFIED",
                "induction whose variable is never named, so the base case could "
                "not be located; check by hand",
                proof=p["id"], claim=p.get("claim_id")))
    return out


def _cycle_findings(ledger):
    return [_finding("claim-cycle", "CRITICAL",
                     "circular dependency: " + " -> ".join(c),
                     claim=c[0])
            for c in ledger.get("refs", {}).get("cycles", [])]


def _restatement_findings(ledger):
    out = []
    for c in ledger.get("claims", []):
        if c.get("duplicate_of") and c.get("hypotheses_diff"):
            out.append(_finding(
                "restatement-hypothesis-drift", "MAJOR",
                "restatement of %s differs in its hypotheses: %s"
                % (c["duplicate_of"], ", ".join(c["hypotheses_diff"])),
                claim=c["id"], evidence=c.get("statement_tex")))
    return out


def _reference_findings(ledger):
    return [_finding("dangling-ref", "MINOR",
                     "\\%s{%s} resolves to nothing" % (d["cmd"], d["label"]),
                     proof=d.get("from"))
            for d in ledger.get("refs", {}).get("dangling", [])]


def _diagnostic_findings(ledger):
    out = []
    for d in ledger.get("diagnostics", []):
        if d.get("code") == "orphan-proof":
            out.append(_finding("orphan-proof", "MINOR", d.get("message", "")))
        elif d.get("code") == "low-text-capture":
            out.append(_finding("low-text-capture", "CRITICAL", d.get("message", "")))
    return out


def _side_condition_findings(ledger):
    """One obligation per proof, not one per row.

    A chain dividing by the same quantity in four consecutive rows owes one
    non-vanishing condition. Four is what makes a report unreadable, and on a real
    paper the raw count was 94 against 3 distinct obligations.
    """
    seen, out = set(), []
    for s in ledger.get("steps", []):
        proof = s.get("proof_id")
        for c in s.get("side_conditions", []):
            status = c.get("status")
            if status == "established":
                continue
            key = (proof, c["kind"], re.sub(r"\s+", "", c.get("expr_tex") or ""))
            if key in seen:
                continue
            seen.add(key)
            if status == "unstated":
                out.append(_finding(
                    "side-condition-unstated", "MAJOR",
                    "%s: the step needs $%s$ to be admissible and nothing "
                    "establishes it" % (c["kind"], c.get("expr_tex")),
                    proof=proof, step=s["id"], evidence=c.get("expr_tex")))
            else:
                out.append(_finding(
                    "side-condition-undetermined", "UNVERIFIED",
                    "%s on $%s$: no domain could be read for it, so no claim is "
                    "made either way" % (c["kind"], c.get("expr_tex")),
                    proof=proof, step=s["id"], evidence=c.get("expr_tex")))
    return out


def _hedge_findings(ledger):
    """A hedge is only a finding on a step nothing else could check.

    "Clearly" over an inference the tool verified is a style note, not a defect.
    """
    out = []
    for s in ledger.get("steps", []):
        j = s.get("justification") or {}
        hedges = j.get("hedges") or []
        if not hedges:
            continue
        if s.get("checkable") != "opaque" and j.get("kind") != "none":
            continue
        if s.get("checkable") == "structural":
            continue
        out.append(_finding(
            "hedged-step", "MINOR",
            "%s on a step that could not be checked" % ", ".join(hedges),
            proof=s.get("proof_id"), step=s["id"],
            evidence=(s.get("prose_tex") or "")[:160]))
    return out


# --------------------------------------------------------------------------
# Composing engine results for one step.
# --------------------------------------------------------------------------

def compose_step(step, results, domains_known=True, unknown_symbols=None):
    """One step's verdict from whatever engines managed to say something."""
    if step.get("checkable") == "structural":
        return _verdict("SKIP", "not an inference", step)

    results = [r for r in (results or []) if r]
    refuted = [r for r in results if r.get("outcome") == "refuted"]
    confirmed = [r for r in results
                 if r.get("outcome") == "confirmed"
                 and r.get("engine") in CONFIRMING_ENGINES]
    not_refuted = [r for r in results if r.get("outcome") == "not-refuted"]

    if refuted and confirmed:
        return _verdict("UNVERIFIED",
                        "engines disagree: %s refuted and %s confirmed it"
                        % (refuted[0].get("engine"), confirmed[0].get("engine")),
                        step, results=results)

    if refuted:
        r = refuted[0]
        if not domains_known:
            # Suppressing the *claim* is right -- the failing point may lie
            # outside what the paper meant. Burying the *event* is not: measured
            # on Adam (arXiv:1412.6980v8) Lemma 10.4, an exact refutation of a
            # genuinely wrong step was reported as an ordinary UNVERIFIED among
            # nineteen others. A blocked decisive check is the single most
            # actionable thing this tool can hand a reviewer.
            names = list(unknown_symbols or step.get("symbols_used") or [])
            faithful = r.get("translation_confidence", _FAITHFUL) == _FAITHFUL
            if not faithful:
                return _verdict("UNVERIFIED",
                                "a check failed under a %s translation and the "
                                "domains are unknown; nothing is concluded"
                                % r.get("translation_confidence"),
                                step, results=results)
            return _verdict(
                "MAJOR",
                "a faithful check FAILED on this step, but no counterexample is "
                "claimed because the paper never states a domain for %s. Supply "
                "them with --symbols and rerun: this is one step away from being "
                "decisive. The check said: %s"
                % (", ".join("$%s$" % n for n in names) or "one of its symbols",
                   r.get("detail") or "no detail"),
                step, results=results, kind="refutation-blocked-by-unknown-domain",
                symbols_to_supply=names)
        if r.get("translation_confidence", _FAITHFUL) != _FAITHFUL:
            return _verdict("WEAK",
                            "refuted under a %s translation, which is not enough "
                            "to claim an error: %s"
                            % (r.get("translation_confidence"), r.get("detail")),
                            step, results=results)
        return _verdict("CRITICAL", r.get("detail") or "counterexample found",
                        step, results=results,
                        counterexample=r.get("counterexample"))

    if confirmed:
        r = confirmed[0]
        if r.get("translation_confidence", _FAITHFUL) != _FAITHFUL:
            # A confirmation under an idealised translation is exactly as
            # untrustworthy as a refutation under one. The gate was asymmetric
            # until a real draft produced a "confirmed" step whose script had
            # substituted the lemma's own assumption and simplified to `p = p`.
            return _verdict("WEAK",
                            "confirmed only under a %s translation, which says "
                            "more about the model than about the step: %s"
                            % (r.get("translation_confidence"), r.get("detail")),
                            step, results=results)
        return _verdict("SKIP", r.get("detail") or "confirmed symbolically",
                        step, results=results, confirmed=True)

    if not_refuted:
        r = not_refuted[0]
        trials = r.get("trials")
        return _verdict(
            "WEAK",
            "NOT REFUTED -- %s sample points, which is evidence and not proof"
            % (trials if trials is not None else "several"),
            step, results=results)

    reasons = step.get("opacity_reasons") or []
    if reasons:
        return _verdict("UNVERIFIED",
                        "not mechanisable: %s" % ", ".join(reasons),
                        step, results=results)
    if results:
        return _verdict("UNVERIFIED",
                        results[0].get("detail") or "no engine returned a verdict",
                        step, results=results)
    return _verdict("UNVERIFIED", "no engine was able to run on this step", step)


def chain_rows_after(step, steps):
    r"""The steps that come after `step` in the same displayed chain.

    There is no chain id in the ledger -- a chain is recorded per step as
    `row` of `of_rows` -- so membership is reconstructed by walking a proof's
    steps in order and starting a new chain wherever the row counter restarts.
    Two rows can both read `7/7` and belong to different chains, which is
    exactly what `lemma:error_bound` does, so grouping on `of_rows` alone would
    be wrong.

    A step with no integer `row` is not in a chain and gets an empty list. That
    matters: `row` and `of_rows` are both `None` for a standalone display, and
    `None == None` would otherwise read as "last row".
    """
    ch = step.get("chain") or {}
    row, of_rows = ch.get("row"), ch.get("of_rows")
    if not isinstance(row, int) or not isinstance(of_rows, int):
        return []
    if row >= of_rows:
        return []                       # nothing comes after the last row

    same_proof = [s for s in steps if s.get("proof_id") == step.get("proof_id")]
    ids = [s.get("id") for s in same_proof]
    if step.get("id") not in ids:
        return []

    # Walk forward only. The chain ends at the first step whose row counter does
    # not continue upward -- either it restarted (a new chain) or it is not a
    # chain row at all.
    rest, prev = [], row
    for s in same_proof[ids.index(step.get("id")) + 1:]:
        r = (s.get("chain") or {}).get("row")
        if not isinstance(r, int) or r <= prev:
            break
        rest.append(s)
        prev = r
    return rest


def apply_supersession(verdicts, steps):
    r"""Demote a `CRITICAL` to `LOCAL` when the refutation did not travel.

    **The rule, stated narrowly on purpose.** A refuted step is demoted only if
    it is a chain row that is *not* the last one, and *every* row after it in
    that same chain was independently confirmed. Anything else -- an unchecked
    later row, a later row that only failed to be refuted, a refutation on the
    last row, a refutation outside any chain -- leaves the `CRITICAL` alone.

    **An unchecked row is not a confirmation.** This is the whole safety
    property. Every genuine finding this pipeline has produced sits on a last
    row or outside a chain, so the rule cannot reach them; but if that ever
    stops being true, the thing that must not happen is a real defect demoted
    because nobody looked at what came after it. Silence is not supersession.

    **What a demotion does and does not claim.** It says the failure was not
    observed to reach past this row. It does not say the chain's conclusion
    follows -- a broken link is still a broken link, and confirming the links
    after it does not repair the chain. The severity is a statement about
    reach, which is why it is `LOCAL` and not `IMMATERIAL`.

    Returns the number of demotions, and rewrites in place.
    """
    confirmed = {v["step"] for v in verdicts if v.get("confirmed")}
    by_id = {s["id"]: s for s in steps}
    demoted = 0
    for v in verdicts:
        if v.get("severity") != "CRITICAL":
            continue
        step = by_id.get(v.get("step"))
        if step is None:
            continue
        after = chain_rows_after(step, steps)
        if not after or not all(s["id"] in confirmed for s in after):
            continue
        names = ", ".join(s["id"].rsplit("/", 1)[-1] for s in after)
        v["severity"] = "LOCAL"
        v["superseded_by"] = [s["id"] for s in after]
        v["detail"] = (
            "%s -- but the refutation was not observed to travel: every later "
            "row of this chain (%s) was independently confirmed. The chain's "
            "conclusion is not thereby established; this records only how far "
            "the failure was seen to reach."
            % (v.get("detail") or "counterexample found", names))
        demoted += 1
    return demoted


def _verdict(severity, detail, step, results=None, **extra):
    out = {"step": step.get("id"), "proof": step.get("proof_id"),
           "severity": severity, "detail": detail, "confirmed": False,
           "counterexample": None, "kind": None, "symbols_to_supply": None,
           "engines": [r.get("engine") for r in results or []],
           "scripts": [r.get("script") for r in (results or []) if r.get("script")]}
    out.update(extra)
    return out


def unknown_domain_symbols(step, symbols_by_name):
    """Symbols this step leans on whose domain the paper never states."""
    out = []
    for name in step.get("symbols_used") or []:
        s = symbols_by_name.get(name)
        if s is None or s.get("domain_provenance") == "unknown":
            out.append(name)
    return out


def domains_known_for(step, symbols_by_name):
    """Do we know the domain of every symbol this step leans on?

    False makes a refutation impossible. This is the single rule that keeps
    "counterexample at $x = -11/5$" off a report about a step that plainly meant
    $x > 0$.
    """
    for name in step.get("symbols_used") or []:
        s = symbols_by_name.get(name)
        if s is None or s.get("domain_provenance") == "unknown":
            return False
    return True
