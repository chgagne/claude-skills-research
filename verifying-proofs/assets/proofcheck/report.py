"""Markdown report and CSV. Stdlib only.

The coverage histogram heads the document, before any finding. On a real paper
"54 of 138 inference steps were mechanically checkable" is not a caveat to bury
at the end -- it is frequently the most important thing the run learned, and a
report that leads with three findings and hides the coverage invites the reader
to believe the other 135 steps were checked and passed.

The report never prints "verified" for a sampling result. `NOT REFUTED at 24
sample points` is what happened, and the wording is load-bearing in the same way
`WEAK` and `UNVERIFIED` are in `verifying-bibliography`.
"""
import csv
import io
import re

from .compose import SEVERITIES, SEVERITY_BLURB


def _esc(text, limit=None):
    """Table-cell safe. An unescaped pipe silently eats the rest of the row."""
    s = re.sub(r"\s+", " ", str(text if text is not None else "")).strip()
    s = s.replace("|", "\\|")
    if limit and len(s) > limit:
        s = s[:limit - 1] + "…"
    return s


def _code(text, limit=None):
    s = _esc(text, limit)
    return "`%s`" % s if s else ""


def markdown(ledger, verdicts, findings, checkers, args=None):
    cov = ledger.get("coverage", {})
    out = []
    a = out.append

    a("# Proof check\n")
    src = ledger.get("source", {})
    a("Source: `%s` (%d file%s)  "
      % (src.get("root", "?"), len(src.get("files", [])),
         "" if len(src.get("files", [])) == 1 else "s"))
    a("Ledger schema: `%s`\n" % ledger.get("schema"))

    a("## Coverage\n")
    a("**What was actually checked.** Read this before the findings: a step that "
      "no engine could reach is neither right nor wrong here, and the count of "
      "those is part of the result.\n")
    a("| | |")
    a("|---|---|")
    a("| Claims / proofs | %d / %d |" % (cov.get("claims", 0), cov.get("proofs", 0)))
    a("| Steps | %d, of which %d are inferences |"
      % (cov.get("steps", 0), cov.get("inference_steps", 0)))
    a("| Mechanically checkable | **%d of %d** inference steps |"
      % (cov.get("checkable_candidates", 0), cov.get("inference_steps", 0)))
    a("| Opaque / structural | %d / %d |"
      % (cov.get("opaque", 0), cov.get("structural", 0)))
    a("| Proof text segmented | %.1f%% |" % cov.get("proof_text_captured_pct", 0.0))
    unknown = cov.get("symbols_with_unknown_domain", 0)
    total_syms = len(ledger.get("symbols", []))
    a("| Symbols whose domain could not be read | %d of %d |" % (unknown, total_syms))
    a("")

    if unknown:
        a("> The domain of %d symbol%s could not be read from the paper. **No "
          "counterexample is ever reported against a symbol whose domain is "
          "unknown**, so those steps can fail a check without producing a "
          "finding. Supplying `--symbols` narrows this.\n"
          % (unknown, "" if unknown == 1 else "s"))

    hist = cov.get("opacity_histogram") or {}
    if hist:
        a("**Why steps could not be mechanised**\n")
        a("| Reason | Steps |")
        a("|---|---|")
        for k, v in hist.items():
            a("| `%s` | %d |" % (_esc(k), v))
        a("")

    a("## Checkers\n")
    if not checkers:
        a("This run required **no external checker**: every finding below came "
          "from the structure of the argument and the text of the paper. Engines "
          "that need SymPy or Z3 were not requested.\n")
    else:
        a("| Checker | Status |")
        a("|---|---|")
    for c in checkers or []:
        if c["available"]:
            a("| `%s` | available, version %s |" % (c["name"], _esc(c["version"])))
        else:
            a("| `%s` | **not installed** -- steps routed to it are `UNVERIFIED` |"
              % c["name"])
    a("")

    a("## Findings\n")
    if not ledger.get("proofs"):
        a("**No proof environments were found in this document.** Nothing was "
          "checked. This is a statement about the source, not a clean bill: a "
          "paper whose arguments are written as running prose rather than "
          "`\\begin{proof}` is outside what this tool can read.\n")
    elif not findings:
        a("No structural findings. This is *not* a statement that the proofs are "
          "correct -- see Coverage above for how much of the argument any engine "
          "was able to reach.\n")
    else:
        present = [s for s in SEVERITIES
                   if any(f["severity"] == s for f in findings)]
        for sev in present:
            rows = [f for f in findings if f["severity"] == sev]
            a("### %s (%d)\n" % (sev, len(rows)))
            a("*%s*\n" % SEVERITY_BLURB[sev])
            a("| Kind | Claim | Where | Detail |")
            a("|---|---|---|---|")
            for f in rows:
                where = f.get("step") or f.get("proof") or ""
                claim = f.get("claim") or _claim_of(ledger, f.get("proof")) or ""
                a("| `%s` | %s | %s | %s |"
                  % (_esc(f["kind"]), _code(claim), _code(where),
                     _esc(f["detail"], 220)))
            a("")

    a("## Per-step verdicts\n")
    if not verdicts:
        a("No step-level checks were run.\n")
    else:
        a("| Step | Kind | Severity | Detail | Script |")
        a("|---|---|---|---|---|")
        steps = {s["id"]: s for s in ledger.get("steps", [])}
        order = {s: i for i, s in enumerate(SEVERITIES)}
        for v in sorted(verdicts, key=lambda v: order.get(v["severity"], 99)):
            st = steps.get(v["step"], {})
            scripts = ", ".join(_code(s) for s in v.get("scripts") or []) or "--"
            a("| %s | %s | `%s` | %s | %s |"
              % (_code(v["step"]), _esc(st.get("kind", "")), v["severity"],
                 _esc(v["detail"], 200), scripts))
        a("")
        a("`WEAK` and `UNVERIFIED` are **not** passes. `WEAK` means a sampling "
          "check did not refute the step, which is evidence and not proof. "
          "`UNVERIFIED` means no engine could reach it at all -- a **finding, "
          "not a pass**, and a cluster of them inside one proof is the headline "
          "of this report.\n")

    a("## What this run cannot tell you\n")
    a("- It can refute a step and it can name a missing licence. It can almost "
      "never certify that a theorem is true.")
    a("- Steps marked `UNVERIFIED` were not examined by any engine. A cluster of "
      "them inside one proof is itself the finding.")
    a("- A `SKIP` on a narration step means the step asserts nothing, not that "
      "the surrounding argument was checked.\n")
    return "\n".join(out)


def _claim_of(ledger, proof_id):
    for p in ledger.get("proofs", []):
        if p["id"] == proof_id:
            return p.get("claim_id")
    return None


def csv_rows(ledger, verdicts, findings):
    """Machine-readable rows: one per step, then one per structural finding."""
    rows = [["claim", "proof", "step", "kind", "engine", "verdict", "severity",
             "detail", "script"]]
    steps = {s["id"]: s for s in ledger.get("steps", [])}
    proofs = {p["id"]: p for p in ledger.get("proofs", [])}
    byid = {v["step"]: v for v in verdicts}
    for s in ledger.get("steps", []):
        v = byid.get(s["id"], {})
        pr = proofs.get(s.get("proof_id"), {})
        rows.append([
            pr.get("claim_id") or "", s.get("proof_id") or "", s["id"],
            s.get("kind", ""), ",".join(v.get("engines") or []),
            "confirmed" if v.get("confirmed") else (v.get("severity") or ""),
            v.get("severity") or "", (v.get("detail") or "").replace("\n", " "),
            ";".join(v.get("scripts") or [])])
    for f in findings:
        rows.append([f.get("claim") or "", f.get("proof") or "",
                     f.get("step") or "", f["kind"], f.get("engine") or "",
                     "finding", f["severity"],
                     (f.get("detail") or "").replace("\n", " "),
                     f.get("script") or ""])
    return rows


def write_csv(path, rows):
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(buf.getvalue())
    return path
