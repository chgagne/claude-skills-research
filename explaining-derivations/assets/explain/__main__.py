"""CLI. Stdlib only.

    python3 ~/.claude/skills/explaining-derivations/assets/run-explain.py main.tex \
        --out derivations/ --level grad-ml

This tool prepares and assembles; it does not write the explanations. Expansion is
a per-theorem subagent job, and the dispatching skill drives it — see
`reference/subagent-contract.md`. Run `--plan-only` first: a dozen theorems is a
dozen subagents, and finding out afterwards that the wrong ones were expanded is
expensive in a way that reading a plan first is not.

Exit codes: `0` clean, `1` usage or input error, **`2` degraded** — latexmk
absent, a fragment refused, or a derivation that could not be expanded.
"""
import argparse
import json
import os
import sys

from . import assemble, build, fragment, gaps, ledger_io, notation, report, triage

LEVELS = ("undergrad", "grad-ml", "expert-shorthand")


def build_parser():
    p = argparse.ArgumentParser(
        prog="run-explain.py",
        description="Expand a paper's derivations into standalone documents "
                    "that make every step explicit, and record every step that "
                    "could not be made explicit.")
    p.add_argument("main_tex", help="root .tex of the document")
    p.add_argument("--out", default="derivations",
                   help="output directory (default: derivations)")
    p.add_argument("--level", default="grad-ml", choices=LEVELS,
                   help="register (default: grad-ml)")
    p.add_argument("--claims", default="",
                   help="comma-separated claim labels to restrict to")
    p.add_argument("--verdicts", default=None,
                   help="proofsteps.csv from verifying-proofs (or a JSON object "
                        "keyed by step id); not proof-ledger.json, which is the "
                        "step ledger rather than the result")
    p.add_argument("--fragments", default=None,
                   help="directory of returned explain-fragment/1 JSON files")
    p.add_argument("--plan-only", action="store_true",
                   help="print the dispatch plan and expand nothing")
    p.add_argument("--only-flagged", action="store_true",
                   help="expand only steps with a verdict or a hedge, rather "
                        "than every inference step")
    p.add_argument("--all-gaps", action="store_true",
                   help="show NOTATIONAL and COSMETIC gaps too")
    p.add_argument("--no-pdf", action="store_true", help="write .tex, skip latexmk")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not os.path.exists(args.main_tex):
        sys.stderr.write("no such file: %s\n" % args.main_tex)
        return 1

    try:
        led = ledger_io.build(args.main_tex)
    except (OSError, ValueError) as exc:
        sys.stderr.write("could not build a ledger: %s\n" % exc)
        return 1

    try:
        verdicts = ledger_io.load_verdicts(args.verdicts)
    except (OSError, ValueError) as exc:
        sys.stderr.write("could not read --verdicts: %s\n" % exc)
        return 1
    wanted = {c.strip() for c in args.claims.split(",") if c.strip()}
    plan = triage.plan(led, claims=wanted, verdicts=verdicts,
                       only_flagged=args.only_flagged, level=args.level)

    if not plan:
        sys.stderr.write("no claim in this document has a proof to expand\n")
        return 1

    if args.plan_only:
        sys.stdout.write(triage.summarise(plan) + "\n")
        sys.stderr.write("--plan-only: nothing was expanded and no subagent was "
                         "dispatched.\n")
        return 0

    os.makedirs(args.out, exist_ok=True)
    frozen = notation.freeze(led)
    requests_dir = os.path.join(args.out, "requests")
    os.makedirs(requests_dir, exist_ok=True)
    for row in plan:
        req = triage.request_for(led, row, verdicts)
        with open(os.path.join(requests_dir, "%s.json" % _slug(row["claim_id"])),
                  "w", encoding="utf-8") as fh:
            json.dump(req, fh, indent=1)

    frags = ledger_io.load_fragments(args.fragments)
    if not frags:
        sys.stderr.write(
            "%d expansion request%s written to %s. Dispatch one subagent per "
            "request (see reference/subagent-contract.md), then rerun with "
            "--fragments pointing at their returned JSON.\n"
            % (len(plan), "" if len(plan) == 1 else "s", requests_dir))
        return 2

    return _assemble_all(args, led, plan, frozen, verdicts, frags)


def _assemble_all(args, led, plan, frozen, verdicts, frags):
    steps = {s["id"]: s for s in led["steps"]}
    claims = {c["id"]: c for c in led["claims"]}
    by_claim_gaps, rows_out, degraded = {}, [], False

    collisions = notation.collisions(frags, frozen)
    for c in collisions:
        by_claim_gaps.setdefault(c.get("claim_id") or "(notation)", []).append(c)
        degraded = True

    by_request = {f.get("request_id"): f for f in frags}
    for row in plan:
        cid = row["claim_id"]
        frag = by_request.get(cid)
        if frag is None:
            sys.stderr.write("no fragment returned for %s\n" % cid)
            by_claim_gaps.setdefault(cid, []).append({
                "step_id": None, "claim_id": cid, "severity": "BLOCKING",
                "kind": "not-attempted",
                "what_is_missing": "the whole expansion; no fragment was returned",
                "what_would_close_it": "dispatch a subagent for this claim",
                "quote": ""})
            degraded = True
            result = fragment.Result(ok=False, rows=[], gaps=[])
        else:
            result = fragment.validate(frag, steps, verdicts, args.level)
            for p in result.problems:
                sys.stderr.write("%s: %s\n" % (cid, p))
            for w in result.warnings:
                sys.stderr.write("%s: warning: %s\n" % (cid, w))
            if not result.ok:
                degraded = True

        claim_gaps = list(result.gaps)
        for g in claim_gaps:
            g.setdefault("claim_id", cid)
        by_claim_gaps.setdefault(cid, []).extend(claim_gaps)

        used = {s for r in result.rows for s in
                steps.get(r["step_id"], {}).get("symbols_used", [])}
        doc_notation = dict(frozen,
                            symbols=notation.glossary(frozen, used or None))
        text = assemble.document(
            claim=claims[cid], rows=result.rows if result.ok else [],
            gaps=by_claim_gaps.get(cid, []), notation=doc_notation,
            tex_fragment=result.tex_fragment or "",
            meta={"source_file": os.path.basename(args.main_tex),
                  "ledger_hash": led["schema"], "level": args.level,
                  "paper": os.path.basename(os.path.dirname(
                      os.path.abspath(args.main_tex)))},
            all_gaps=args.all_gaps)
        name = _slug(row["label"] or cid)
        path = assemble.write_document(args.out, name, text)

        entry = {"claim_id": cid, "tex": path, "pdf": None,
                 "rows_written": len(result.rows) if result.ok else 0,
                 "inference_steps": row["inference_steps"], "ok": result.ok,
                 "detail": "; ".join(result.problems) or None}
        if not args.no_pdf:
            b = build.build_pdf(path)
            entry["pdf"] = b["pdf"]
            if b["degraded"]:
                degraded = True
                sys.stderr.write("%s: %s\n" % (name, b["detail"]))
            for w in b["warnings"]:
                sys.stderr.write("%s: %s\n" % (name, w))
        rows_out.append(entry)

    report.write(args.out, rows_out, by_claim_gaps,
                 {"source_file": args.main_tex, "level": args.level,
                  "has_verdicts": bool(verdicts)}, args.all_gaps)

    roll = gaps.rollup(by_claim_gaps, args.all_gaps)
    sys.stderr.write("%s\n" % roll["summary"])
    return 2 if degraded else 0


def _slug(text):
    import re
    return re.sub(r"[^A-Za-z0-9]+", "-", str(text)).strip("-")


if __name__ == "__main__":
    raise SystemExit(main())
