"""The index across every expanded derivation. Stdlib only.

The PDFs are what a reader opens; this is what a *reviewer* reads. It leads with
the gap roll-up, because the gap ledger is the part that carries a finding and the
prose is the part that carries the explanation.
"""
import json
import os

from . import gaps as _gaps


def index(rows, by_claim_gaps, meta, all_gaps=False):
    """`index.md`: one line per derivation, gap roll-up first."""
    roll = _gaps.rollup(by_claim_gaps, all_gaps=all_gaps)
    out = ["# Expanded derivations\n",
           "Source: `%s`  " % meta.get("source_file", "?"),
           "Register: `%s`  " % meta.get("level", "grad-ml"),
           "Verdicts: %s\n" % ("from `verifying-proofs`"
                               if meta.get("has_verdicts")
                               else "**none supplied** — every *Checked* cell in "
                                    "every document reads *not run*"),
           "## Gap ledger\n",
           roll["summary"] + "\n"]

    if roll["total"]:
        out += ["| Derivation | " + " | ".join(_gaps.SEVERITIES) + " |",
                "|---" * (len(_gaps.SEVERITIES) + 1) + "|"]
        for claim, counts in sorted(roll["by_claim"].items()):
            out.append("| `%s` | %s |" % (
                claim, " | ".join(str(counts[s]) for s in _gaps.SEVERITIES)))
        out.append("")

    out.append("## Documents\n")
    if not rows:
        out.append("No derivations were expanded.\n")
    else:
        out += ["| Claim | Steps expanded | Gaps | PDF |", "|---|---|---|---|"]
        for r in rows:
            n_gaps = len(by_claim_gaps.get(r["claim_id"], []))
            pdf = r.get("pdf") or "**not built**"
            out.append("| `%s` | %d of %d | %d | %s |"
                       % (r["claim_id"], r.get("rows_written", 0),
                          r.get("inference_steps", 0), n_gaps,
                          os.path.basename(pdf) if r.get("pdf") else pdf))
        out.append("")

    failed = [r for r in rows if not r.get("ok")]
    if failed:
        out.append("## Derivations that could not be expanded\n")
        for r in failed:
            out.append("- `%s` — %s" % (r["claim_id"],
                                        r.get("detail") or "no reason recorded"))
        out.append("")
        out.append("**An expansion that could not be completed is evidence about "
                   "the derivation**, not merely a failed run. Each of the above "
                   "has a document stating what was reached and what was not.\n")

    out.append("## What this does not establish\n")
    out.append("- An expanded step is a step someone could justify, not a step "
               "proved correct. Where a mechanical verdict exists it is shown; "
               "where it does not, the cell says *not run*.")
    out.append("- A derivation with no gaps has been made explicit. That is a "
               "statement about the expansion, not a proof of the theorem.\n")
    return "\n".join(out)


def write(outdir, rows, by_claim_gaps, meta, all_gaps=False):
    os.makedirs(outdir, exist_ok=True)
    text = index(rows, by_claim_gaps, meta, all_gaps)
    with open(os.path.join(outdir, "index.md"), "w", encoding="utf-8") as fh:
        fh.write(text)
    with open(os.path.join(outdir, "gaps.json"), "w", encoding="utf-8") as fh:
        json.dump({"rollup": _gaps.rollup(by_claim_gaps, all_gaps),
                   "by_claim": by_claim_gaps,
                   "findings": _gaps.as_findings(by_claim_gaps)}, fh, indent=1)
    return text
