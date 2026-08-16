"""Which claims to expand, in what order, and at what cost. Stdlib only.

A dozen theorems is a dozen subagents. `--plan-only` prints this and dispatches
nothing, which is the same pre-flight discipline `reviewing-paper-sources` phase 0
mandates before a gap sweep: finding out afterwards that the wrong proofs were
expanded is expensive in a way that reading a plan first is not.

Ordering is by **load-bearingness**, not by document order. A lemma the main
theorem's proof leans on is worth expanding before an isolated corollary, because
if the argument fails anywhere it most likely fails there.

Cost is estimated in *inference* steps rather than raw steps. A proof that is
thirty sentences of narration and two inferences is a short job, and counting
sentences would say the opposite.
"""
from . import fragment as _fragment

#: Claim kinds worth expanding. A definition asserts nothing to expand.
EXPANDABLE = ("theorem", "lemma", "proposition", "corollary", "claim", "fact")

_INFERENCE = ("chain-row", "display", "inline-assert", "prose-move")


def _dependents(ledger):
    """How many other proofs lean on each claim, via the reference graph.

    Falls back to matching the label against claim labels directly when the
    ledger's label map has no entry for it. Ordering degrades to document order
    when this cannot be resolved, and silently getting the order wrong is worse
    than the small cost of a second lookup.
    """
    by_label = {c.get("label"): c["id"] for c in ledger.get("claims", [])
                if c.get("label")}
    labels = ledger.get("refs", {}).get("labels", {})
    counts = {}
    for e in ledger.get("refs", {}).get("edges", []):
        target = (labels.get(e["label"], {}).get("target")
                  or by_label.get(e["label"]))
        if target and target != e.get("claim"):
            counts[target] = counts.get(target, 0) + 1
    return counts


def plan(ledger, claims=None, verdicts=None, only_flagged=False, level="grad-ml"):
    """One expansion request per provable claim that has a proof."""
    verdicts = verdicts or {}
    proofs_by_claim = {p["claim_id"]: p for p in ledger.get("proofs", [])
                       if p.get("claim_id")}
    steps_by_proof = {}
    for s in ledger.get("steps", []):
        steps_by_proof.setdefault(s.get("proof_id"), []).append(s)
    deps = _dependents(ledger)

    out = []
    for claim in ledger.get("claims", []):
        if claim.get("kind") not in EXPANDABLE:
            continue
        proof = proofs_by_claim.get(claim["id"])
        if proof is None:
            continue
        # Skip a restatement only when the original is *also* proved. A body
        # theorem restated in the appendix usually carries its proof on the
        # appendix copy alone, and skipping every duplicate then drops the
        # paper's headline results from the plan entirely.
        if claim.get("duplicate_of") in proofs_by_claim:
            continue
        if claims and not (claim["id"] in claims or claim.get("label") in claims):
            continue

        steps = sorted(steps_by_proof.get(proof["id"], []),
                       key=lambda s: s.get("ordinal") or 0)
        chosen = [s for s in steps if s["kind"] in _INFERENCE]
        if only_flagged:
            chosen = [s for s in chosen if _is_flagged(s, verdicts)]

        out.append({
            "claim_id": claim["id"], "proof_id": proof["id"],
            "label": claim.get("label"), "kind": claim.get("kind"),
            "number": claim.get("number"),
            "steps": len(steps),
            "inference_steps": sum(1 for s in steps if s["kind"] in _INFERENCE),
            "opaque_steps": sum(1 for s in steps
                                if s.get("checkable") == "opaque"),
            "step_ids": [s["id"] for s in chosen],
            "dependents": deps.get(claim["id"], 0),
            "level": level,
        })

    out.sort(key=lambda p: (-p["dependents"], -p["inference_steps"],
                            p["claim_id"]))
    return out


def _is_flagged(step, verdicts):
    """Worth expanding under `--only-flagged`: a real verdict, or a hedge."""
    v = verdicts.get(step["id"]) or {}
    if v.get("verdict") in ("CRITICAL", "MAJOR", "WEAK", "UNVERIFIED"):
        return True
    if (step.get("justification") or {}).get("hedges"):
        return True
    if any(c.get("status") == "unstated" for c in step.get("side_conditions") or []):
        return True
    return step.get("checkable") == "opaque"


def summarise(plan_rows):
    """One line per claim, for `--plan-only`."""
    lines = ["%-24s %-12s %5s steps %5s inferences %4s opaque  deps=%d"
             % (p["label"] or p["claim_id"], p["kind"], p["steps"],
                p["inference_steps"], p["opaque_steps"], p["dependents"])
             for p in plan_rows]
    lines.append("%d claim%s, %d inference steps to expand"
                 % (len(plan_rows), "" if len(plan_rows) == 1 else "s",
                    sum(len(p["step_ids"]) for p in plan_rows)))
    return "\n".join(lines)


def request_for(ledger, row, verdicts=None):
    """Build the subagent request for one planned claim."""
    from . import notation
    claims = {c["id"]: c for c in ledger["claims"]}
    proofs = {p["id"]: p for p in ledger["proofs"]}
    steps = [s for s in ledger["steps"] if s["id"] in set(row["step_ids"])]
    all_steps = [s for s in ledger["steps"] if s["proof_id"] == row["proof_id"]]
    # Narrowed to what this proof uses. Passing all 81 symbols of a monograph,
    # of which 67 read "not stated in the paper", is a page of context that
    # informs no row -- reported by both expanders that have run. `assemble.py`
    # already narrows the *rendered* table this way; the request did not.
    chosen = steps or all_steps
    used = {s for step in chosen for s in (step.get("symbols_used") or [])}
    frozen = notation.freeze(ledger)
    claim, proof = claims[row["claim_id"]], proofs[row["proof_id"]]
    blobs = [claim.get("statement_tex"), proof.get("body_tex")]
    blobs += [s.get("math_tex") for s in chosen] + [s.get("prose_tex") for s in chosen]
    return _fragment.request(
        claim=claim, proof=proof,
        steps=chosen,
        notation=dict(frozen,
                      symbols=notation.glossary(frozen, used or None),
                      macros=notation.macros_used(frozen, blobs)),
        context=_context(ledger, row),
        verdicts={k: v for k, v in (verdicts or {}).items()
                  if k in {s["id"] for s in all_steps}},
        level=row.get("level", "grad-ml"))


def _context(ledger, row):
    """Definitions, assumptions, results **and equations** this proof refers to.

    Equations were missing, and they are most of what a proof cites: an `\\eqref`
    resolves to no claim, so the old lookup dropped it. Reported independently by
    both expanders that have run -- on Bubeck the proof cites two equations by
    label, neither reached the request, and the subagent opened the source to
    read them before it could explain the step that uses them.

    Resolved against the equations' own `labels`, not through the reference
    graph: `refs` records an equation label with `target: None` by design, and
    teaching it to carry equation ids would change a structure two skills read.
    """
    labels = ledger.get("refs", {}).get("labels", {})
    eq_by_label = {}
    for eq in ledger.get("equations", []):
        for lab in (eq.get("labels") or []):
            eq_by_label.setdefault(lab, eq)
        for lab in (eq.get("row_labels") or {}).values():
            eq_by_label.setdefault(lab, eq)

    referenced, equations, seen = [], [], set()
    for e in ledger.get("refs", {}).get("edges", []):
        if e.get("from") != row["proof_id"] or e["label"] in seen:
            continue
        target = labels.get(e["label"], {}).get("target")
        for c in ledger["claims"]:
            if c["id"] == target:
                seen.add(e["label"])
                referenced.append({"label": e["label"], "local": True,
                                   "statement_tex": c.get("statement_tex")})
        eq = eq_by_label.get(e["label"])
        if eq is not None:
            seen.add(e["label"])
            equations.append({"label": e["label"], "id": eq.get("id"),
                              "env": eq.get("env"),
                              "tex": eq.get("expanded_tex") or eq.get("raw_tex")})
    return {
        "definitions": [c for c in ledger["claims"] if c.get("kind") == "definition"],
        "assumptions": [c for c in ledger["claims"] if c.get("kind") == "assumption"],
        "referenced_results": referenced,
        "referenced_equations": equations,
    }
