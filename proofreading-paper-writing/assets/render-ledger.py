#!/usr/bin/env python3
"""Render a writing ledger into LG track-change markup plus a writing report.

Stdlib only. Never writes to a file named main.tex. See SKILL.md for the workflow.
"""
import argparse, datetime, os, pathlib, sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))

from proofread.ledger import load_ledger, dump_ledger          # noqa: E402
from proofread.preamble import ensure_changes                   # noqa: E402
from proofread.apply import apply_ledger                        # noqa: E402
from proofread.report import RunHeader, write_report            # noqa: E402
from proofread.build import render_with_bisect, latexmk_available  # noqa: E402

PREAMBLE = _HERE.parent.parent / "reviewing-paper-sources" / "assets" / "changes-preamble.tex"


def parse(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--tex", required=True, help="main-annotated.tex to layer onto, or main.tex to start from")
    ap.add_argument("--out", required=True, help="output tex; must not be main.tex")
    ap.add_argument("--report", required=True)
    ap.add_argument("--paper", default="main.tex")
    ap.add_argument("--mode", default="A")
    ap.add_argument("--field-profile"); ap.add_argument("--author-profile")
    ap.add_argument("--run-rule", action="append", default=[])
    ap.add_argument("--forbid-ulem", action="store_true")
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--scratch", help="build directory; default <out dir>/.lg-build")
    ap.add_argument("--preamble", default=str(PREAMBLE))
    return ap.parse_args(argv)


def main(argv=None):
    a = parse(argv)
    if os.path.basename(a.out) == "main.tex":
        print("refusing to write main.tex; use main-annotated.tex", file=sys.stderr)
        return 1
    try:
        rows = load_ledger(a.ledger)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    with open(a.tex, encoding="utf-8") as fh:
        tex = fh.read()
    with open(a.preamble, encoding="utf-8") as fh:
        preamble = "".join(l for l in fh if not l.lstrip().startswith("%"))
    base = ensure_changes(tex, preamble, forbid_ulem=a.forbid_ulem)

    out_dir = os.path.dirname(os.path.abspath(a.out))
    builds, dropped = {"markup": None, "final": None}, []
    rc = 0
    if a.no_build:
        applied = apply_ledger(base, rows)
        final_tex = applied.tex
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(final_tex)
    elif not latexmk_available():
        print("latexmk not found: writing markup without building. Do not install anything; ask the user.", file=sys.stderr)
        applied = apply_ledger(base, rows)
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(applied.tex)
        rc = 2
    else:
        scratch = a.scratch or os.path.join(out_dir, ".lg-build")
        final_tex, builds, dropped = render_with_bisect(base, rows, out_dir, os.path.basename(a.out), scratch)
        if dropped or not builds.get("final"):
            rc = 2
    header = RunHeader(paper=a.paper, mode=a.mode, date=datetime.date.today().isoformat(),
                       field_profile=a.field_profile, author_profile=a.author_profile,
                       run_rules=a.run_rule, dropped_levels=dropped, builds=builds)
    write_report(rows, header, a.report)
    dump_ledger(rows, a.ledger)
    n = lambda s: sum(1 for r in rows if r.status == s)
    print(f"applied {n('applied')}, degraded {n('degraded')}, unanchored {n('unanchored')}, cut {n('cut')}; "
          f"markup {builds.get('markup')}; final {builds.get('final')}; dropped: {', '.join(dropped) or 'none'}")
    if builds.get("markup") is False:
        print("markup build failed even with no rows applied; log tail:\n" + builds.get("markup_log", ""), file=sys.stderr)
        return 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
