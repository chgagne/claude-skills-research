"""CLI. Stdlib only.

    python3 ~/.claude/skills/verifying-proofs/assets/run-proofcheck.py main.tex \
        --out review-assets/

Exit codes follow the sibling skills: `0` clean run, `1` usage or input error,
**`2` degraded coverage** -- a checker was missing, a ledger dropped proof text,
or an engine could not run. A `2` means "nothing wrong was found in a degraded
run", which is a different sentence from "the proofs are correct", and the report
says so in those words.
"""
import argparse
import os
import sys

from . import compose, ledger_io, report, sandbox, stubs
from latexmath import named as _named

ENGINE_ORDER = ("sideconds", "rational", "symbolic", "named", "gradient", "smt")
DEFAULT_ENGINES = ("sideconds",)

#: Engines that need an external checker, and which one.
ENGINE_CHECKER = {"symbolic": "sympy", "smt": "z3"}


def build_parser():
    p = argparse.ArgumentParser(
        prog="run-proofcheck.py",
        description="Check the mathematical development of a paper, and say "
                    "plainly what could not be checked.")
    p.add_argument("main_tex", help="root .tex of the document")
    p.add_argument("--out", default="review-assets",
                   help="output directory (default: review-assets)")
    p.add_argument("--claims", default="",
                   help="comma-separated claim labels to restrict to")
    p.add_argument("--symbols", default=None,
                   help="JSON object of symbol -> domain, supplied by the reader")
    p.add_argument("--engines", default=",".join(DEFAULT_ENGINES),
                   help="comma-separated subset of: " + ", ".join(ENGINE_ORDER))
    p.add_argument("--trials", type=int, default=24,
                   help="sample points for the randomized engine")
    p.add_argument("--step-timeout", type=int, default=sandbox.DEFAULT_TIMEOUT)
    p.add_argument("--budget-seconds", type=int, default=300)
    p.add_argument("--emit-stubs-only", action="store_true",
                   help="write every check script and run nothing, so you can "
                        "read what would run first")
    p.add_argument("--ledger-only", action="store_true",
                   help="write proof-ledger.json and stop")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not os.path.exists(args.main_tex):
        sys.stderr.write("no such file: %s\n" % args.main_tex)
        return 1
    os.makedirs(args.out, exist_ok=True)

    try:
        led = ledger_io.build(args.main_tex, args.symbols)
    except (OSError, ValueError) as exc:
        sys.stderr.write("could not build a ledger: %s\n" % exc)
        return 1
    led = ledger_io.select_claims(
        led, {c.strip() for c in args.claims.split(",") if c.strip()})
    ledger_io.save(led, os.path.join(args.out, "proof-ledger.json"))
    if args.ledger_only:
        _summarise(led, [], [])
        return 0

    engines = [e.strip() for e in args.engines.split(",") if e.strip()]
    unknown = [e for e in engines if e not in ENGINE_ORDER]
    if unknown:
        sys.stderr.write("unknown engine(s): %s\n" % ", ".join(unknown))
        return 1

    checkers, degraded = [], False
    for name in sorted({ENGINE_CHECKER[e] for e in engines if e in ENGINE_CHECKER}):
        c = sandbox.probe(name)
        checkers.append(c.as_dict())
        if not c.available:
            degraded = True
            sys.stderr.write("%s\n" % c.install_hint)

    findings = compose.structural_findings(led)

    # Engines beyond `sideconds` work through generated scripts: the tool writes
    # one per checkable step, the agent fills in `build()`, and a rerun collects
    # the verdicts. An unfilled script reports `untranslatable`, which composes
    # to UNVERIFIED -- so a run that translated nothing reports nothing checked.
    # `named` is template matching over the ledger, not a generated script: it
    # reads the result a step invokes by name and looks for that result's
    # hypotheses. Its output is a side condition, so it joins the same severity
    # path as `sideconds` rather than inventing a second one.
    if "named" in engines:
        named_found = 0
        for step in led["steps"]:
            got = _named.conditions(step, {s["symbol"]: s for s in led["symbols"]})
            if got:
                step.setdefault("side_conditions", []).extend(got)
                named_found += len(got)
        sys.stderr.write("named: %d hypothesis check%s over %d step%s invoking a "
                         "named result\n"
                         % (named_found, "" if named_found == 1 else "s",
                            sum(1 for s in led["steps"]
                                if (s.get("justification") or {}).get("kind")
                                == "named-result"),
                            "" if named_found == 1 else "s"))

    by_step = {}
    script_engines = [e for e in engines if e not in ("sideconds", "named")]
    if script_engines:
        try:
            written = stubs.write_stubs(led, args.out, tuple(script_engines),
                                        args.trials)
        except ValueError as exc:
            sys.stderr.write("%s\n" % exc)
            return 1
        sys.stderr.write("%d check script%s in %s, for %s\n"
                         % (len(written), "" if len(written) == 1 else "s",
                            os.path.join(args.out, "checks"),
                            ", ".join(script_engines)))
        if args.emit_stubs_only:
            sys.stderr.write("--emit-stubs-only: nothing was executed. Fill in "
                             "build() in each script, then rerun without the "
                             "flag.\n")
        else:
            for r in stubs.collect(args.out, args.step_timeout,
                                   args.budget_seconds):
                if r.get("step_id"):
                    by_step.setdefault(r["step_id"], []).append(r)
            if any(r[0].get("outcome") == "untranslatable"
                   for r in by_step.values()):
                degraded = True

    symbols = {s["symbol"]: s for s in led["symbols"]}
    verdicts = []
    for step in led["steps"]:
        verdicts.append(compose.compose_step(
            step, by_step.get(step["id"], []),
            compose.domains_known_for(step, symbols),
            compose.unknown_domain_symbols(step, symbols)))

    text = report.markdown(led, verdicts, findings, checkers, args)
    with open(os.path.join(args.out, "proofcheck-report.md"), "w",
              encoding="utf-8") as fh:
        fh.write(text)
    report.write_csv(os.path.join(args.out, "proofsteps.csv"),
                     report.csv_rows(led, verdicts, findings))

    if led["coverage"]["proof_text_captured_pct"] < 90.0 and led["coverage"]["proofs"]:
        degraded = True
        sys.stderr.write(
            "only %.1f%% of proof text was segmented; these verdicts describe a "
            "different document\n" % led["coverage"]["proof_text_captured_pct"])

    _summarise(led, findings, verdicts)
    return 2 if degraded else 0


def _summarise(led, findings, verdicts):
    cov = led["coverage"]
    sys.stderr.write(
        "%d claims, %d proofs, %d steps (%d inferences); "
        "%d mechanically checkable, %d opaque\n"
        % (cov["claims"], cov["proofs"], cov["steps"], cov["inference_steps"],
           cov["checkable_candidates"], cov["opaque"]))
    if findings:
        counts = {}
        for f in findings:
            counts[f["severity"]] = counts.get(f["severity"], 0) + 1
        sys.stderr.write("findings: %s\n" % ", ".join(
            "%s %d" % (s, counts[s]) for s in compose.SEVERITIES if s in counts))
    del verdicts


if __name__ == "__main__":
    raise SystemExit(main())
