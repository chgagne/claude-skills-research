r"""Two independent translations of the same steps, and the rule that a
`CRITICAL` requires both of them to refute.

Every other guard in this skill protects against the tool's own limitations being
reported as the paper's mistakes. Agent-authored translation adds a new way to
fail -- a model that quietly drops a term produces a counterexample against
correct mathematics -- and no amount of reading the round-trip display scales.
Two independent translations do: if a refutation is an artefact of how one agent
read the LaTeX, the other agent is unlikely to read it the same wrong way.

**One refutes and the other does not is not a weaker finding.** It is
`UNVERIFIED`, for the same reason composition rule 3 says engines that disagree
yield `UNVERIFIED` rather than a finding. This extends that rule from engines to
translations.

The agreement rate is the number to publish. It is the measured false-positive
control, and if it is low the problem is the contract, not the mathematics.

Measured before this was folded in: 94% aggregate agreement over 126 steps on 10
papers, above 80% on every paper. The same 18 Adam steps scored 28% through SymPy
translations and 94% through Z3 ones -- the engine the translator is writing for
changes the agreement rate far more than the translator does.
"""
import json
import os
import re
import shutil
from dataclasses import dataclass

from . import compose, stubs


@dataclass
class Row:
    step_id: str
    outcome_a: str
    outcome_b: str
    agree: bool
    severity: str
    detail: str = ""


def _slug(step_id):
    return re.sub(r"[^A-Za-z0-9]+", "-", step_id).strip("-")


def fill_stub(text, entry):
    """Replace a stub's placeholder `build()` and its three honesty fields.

    A translation that returned no `build` becomes `Untranslatable`, never an
    empty model: absence must not run as a confirmation.
    """
    head = text[:text.index("STEP_ID = ")]
    consts = text[text.index("STEP_ID = "):text.index('if __name__ == "__main__":')]
    main = text[text.index('if __name__ == "__main__":'):]
    # Drop the stub's placeholder `build()` rather than leaving it above the real
    # one. Python would take the later definition and the script would still run
    # correctly -- which is how this survived three stages unnoticed -- but these
    # scripts exist to be read, and a reader auditing one should not meet
    # `raise Untranslatable("fill me in")` above the translation that actually ran.
    cut = consts.find("def build(")
    if cut != -1:
        consts = consts[:cut]
    consts = re.sub(r"^IGNORED_SYMBOLS = .*$",
                    "IGNORED_SYMBOLS = %r" % (entry.get("ignored_symbols") or []),
                    consts, flags=re.M)
    consts = re.sub(r"^TRANSLATION_CONFIDENCE = .*$",
                    "TRANSLATION_CONFIDENCE = %r"
                    % (entry.get("translation_confidence") or "approximate"),
                    consts, flags=re.M)
    consts = re.sub(r"^TRANSLATION_NOTES = .*$",
                    "TRANSLATION_NOTES = %r" % (entry.get("translation_notes") or ""),
                    consts, flags=re.M)
    body = entry.get("build") or '    raise Untranslatable("no translation returned")'
    return head + consts + "\n\ndef build():\n" + body.rstrip() + "\n\n\n" + main


def stage(checks, out, translations, engine="symbolic"):
    """Write one filled copy of each emitted script this translation covers."""
    if os.path.exists(out):
        shutil.rmtree(out)
    staged_dir = os.path.join(out, "checks")
    os.makedirs(staged_dir)
    n = 0
    for sid, entry in translations.items():
        name = "%s.%s.py" % (_slug(sid), engine)
        src = os.path.join(checks, name)
        if not os.path.exists(src):
            continue
        with open(src, encoding="utf-8") as fh:
            text = fh.read()
        with open(os.path.join(staged_dir, name), "w", encoding="utf-8") as fh:
            fh.write(fill_stub(text, entry))
        n += 1
    return n


def run(outdir, timeout=60, budget=600):
    """Run one staged translation's scripts, keyed by step id."""
    got = {}
    for r in stubs.collect(outdir, timeout, budget):
        if r.get("step_id"):
            got[r["step_id"]] = r
    return got


def adjudicate(steps, symbols, ra, rb):
    """Merge two translations' results. Returns (rows, summary).

    Coverage is the **intersection**: a step only one translation produced a
    result for has no second opinion, so it is named in the summary rather than
    folded in on one vote.
    """
    shared = sorted(set(ra) & set(rb))
    rows, agree, both_refuted, both_confirmed = [], 0, [], []
    for sid in shared:
        oa, ob = ra[sid]["outcome"], rb[sid]["outcome"]
        same = oa == ob
        agree += same
        step = steps.get(sid, {"id": sid})
        known = compose.domains_known_for(step, symbols)
        unknown = compose.unknown_domain_symbols(step, symbols)
        if oa == ob == "refuted":
            both_refuted.append(sid)
            v = compose.compose_step(step, [ra[sid], rb[sid]], known, unknown)
        elif "refuted" in (oa, ob):
            v = {"severity": "UNVERIFIED",
                 "detail": "the two translations disagree (%s vs %s), so nothing "
                           "is concluded either way" % (oa, ob)}
        else:
            if oa == ob == "confirmed":
                both_confirmed.append(sid)
            v = compose.compose_step(step, [ra[sid]], known, unknown)
        rows.append(Row(sid, oa, ob, same, v["severity"], v.get("detail", "")))

    summary = {
        "n": len(shared),
        "agreement": agree,
        "agreement_pct": round(100.0 * agree / max(1, len(shared)), 1),
        "both_refuted": both_refuted,
        "both_confirmed": both_confirmed,
        "critical": [r.step_id for r in rows if r.severity == "CRITICAL"],
        "only_a": sorted(set(ra) - set(rb)),
        "only_b": sorted(set(rb) - set(ra)),
    }
    return rows, summary


def render(rows, summary):
    """The agreement table, coverage first."""
    out = ["# Two-translation agreement", "",
           "%d steps were run by both translations; %d by only one "
           "(named below and not folded in — one vote is not a second opinion)."
           % (summary["n"], len(summary["only_a"]) + len(summary["only_b"])), "",
           "**Agreement on outcome: %d of %d (%.0f%%).** This is the false-positive "
           "control. Below about 80%% the contract is the problem, not the "
           "mathematics." % (summary["agreement"], summary["n"],
                             summary["agreement_pct"]), "",
           "| Step | A | B | Agree | Verdict |", "|---|---|---|---|---|"]
    for r in rows:
        out.append("| `%s` | %s | %s | %s | %s |"
                   % (r.step_id.split("/", 1)[-1], r.outcome_a, r.outcome_b,
                      "yes" if r.agree else "**NO**", r.severity))
    out += ["", "`CRITICAL` after the two-agree rule: **%d**%s"
            % (len(summary["critical"]),
               (" — " + ", ".join("`%s`" % s.split("/", 1)[-1]
                                       for s in summary["critical"]))
               if summary["critical"] else "")]
    if summary["only_a"] or summary["only_b"]:
        out += ["", "Covered by only one translation: A=%s B=%s"
                % (summary["only_a"] or "none", summary["only_b"] or "none")]
    return "\n".join(out) + "\n"


def write(outdir, rows, summary):
    """Persist the agreement table and its json beside the other artifacts."""
    os.makedirs(outdir, exist_ok=True)
    md = os.path.join(outdir, "two-translation-agreement.md")
    with open(md, "w", encoding="utf-8") as fh:
        fh.write(render(rows, summary))
    js = os.path.join(outdir, "agreement.json")
    with open(js, "w", encoding="utf-8") as fh:
        json.dump({"summary": summary,
                   "rows": [r.__dict__ for r in rows]}, fh, indent=1)
    return md, js
