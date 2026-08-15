"""The gap ledger. Stdlib only. The part that carries the finding.

**An expansion that cannot be completed is evidence against the derivation.** A
step nobody can justify explicitly is not a formatting problem; it is a hole in
the proof, and it leaves this skill as a row with a severity that feeds back into
the review.

The default view shows `SUBSTANTIVE` and above. Over-fragmenting a proof is the
main way a ledger becomes unreadable — dozens of rows that are really one
inference — and a reader who skims the ledger has lost the one thing the skill
produces that a PDF does not.

"No gaps" is **stated explicitly**, never implied by an empty section. An empty
section reads as "nothing was looked for".
"""

SEVERITIES = ("BLOCKING", "SUBSTANTIVE", "NOTATIONAL", "COSMETIC")

#: How a gap severity lands in a review that uses the proof-checking ladder.
REVIEW_SEVERITY = {"BLOCKING": "MAJOR", "SUBSTANTIVE": "MAJOR",
                   "NOTATIONAL": "MINOR", "COSMETIC": "MINOR"}

DEFAULT_MINIMUM = "SUBSTANTIVE"


def reportable(rows, all_gaps=False, minimum=DEFAULT_MINIMUM):
    """The gaps worth showing. `NOTATIONAL` and `COSMETIC` are held back by default."""
    if all_gaps:
        return sorted(rows, key=_order)
    cut = SEVERITIES.index(minimum)
    return sorted([g for g in rows if SEVERITIES.index(g["severity"]) <= cut],
                  key=_order)


def _order(gap):
    return (SEVERITIES.index(gap["severity"]), gap.get("step_id") or "")


def rollup(by_claim, all_gaps=False):
    """Counts across every expanded claim, plus a summary sentence."""
    counts = {s: 0 for s in SEVERITIES}
    total = 0
    per_claim = {}
    for claim, rows in by_claim.items():
        per_claim[claim] = {s: 0 for s in SEVERITIES}
        for g in rows:
            counts[g["severity"]] += 1
            per_claim[claim][g["severity"]] += 1
            total += 1
    return {"total": total, "by_severity": counts, "by_claim": per_claim,
            "summary": _summary(counts, total, len(by_claim))}


def _summary(counts, total, n_claims):
    if total == 0:
        return ("No gaps: every step of every expanded derivation was made "
                "explicit, with a stated licence. This is a claim about the "
                "expansion, not a proof that the theorems are true.")
    parts = []
    if counts["BLOCKING"]:
        parts.append(
            "**%d BLOCKING** -- %s could not be justified at all, and the "
            "derivation has a hole there until someone supplies what the ledger "
            "names" % (counts["BLOCKING"],
                       "a step" if counts["BLOCKING"] == 1 else "steps"))
    if counts["SUBSTANTIVE"]:
        parts.append("%d SUBSTANTIVE (justifiable only under an assumption the "
                     "paper never states)" % counts["SUBSTANTIVE"])
    if counts["NOTATIONAL"]:
        parts.append("%d NOTATIONAL" % counts["NOTATIONAL"])
    if counts["COSMETIC"]:
        parts.append("%d COSMETIC" % counts["COSMETIC"])
    return ("%d gap%s across %d expanded derivation%s: %s."
            % (total, "" if total == 1 else "s", n_claims,
               "" if n_claims == 1 else "s", "; ".join(parts)))


def as_findings(by_claim):
    """Gap rows as review findings, so they travel with the rest of the report."""
    out = []
    for claim, rows in by_claim.items():
        for g in rows:
            out.append({
                "kind": "derivation-gap",
                "severity": REVIEW_SEVERITY[g["severity"]],
                "gap_severity": g["severity"],
                "claim": g.get("claim_id") or claim,
                "step": g.get("step_id"),
                "detail": "%s. What would close it: %s"
                          % (g.get("what_is_missing"),
                             g.get("what_would_close_it") or "not stated"),
                "evidence": g.get("quote") or "",
                "proof": None, "script": None, "engine": None,
            })
    return sorted(out, key=lambda f: SEVERITIES.index(f["gap_severity"]))
