import argparse
import os
import re
import sys
from .bibparse import parse_bib
from . import sources as sources_mod
from .sources import resolve
from .compare import check_entry
from .report import to_markdown, to_csv


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bibcheck",
                                 description="Verify .bib entries against academic records.")
    ap.add_argument("bib")
    ap.add_argument("--bbl", help="restrict to entries cited in this .bbl")
    ap.add_argument("--out", default=".", help="directory for report files")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    with open(a.bib, encoding="utf-8") as fh:
        entries = parse_bib(fh.read())
    total = len(entries)
    if a.bbl:
        with open(a.bbl, encoding="utf-8") as fh:
            cited = set(re.findall(r"\\bibitem\[.*?\]\{([^}]+)\}", fh.read(), re.S))
        entries = [e for e in entries if e.key in cited]

    findings = []
    for i, e in enumerate(entries, 1):
        if not a.quiet:
            print(f"[{i}/{len(entries)}] {e.key}", file=sys.stderr)
        findings.extend(check_entry(e, resolve(e)))

    os.makedirs(a.out, exist_ok=True)
    md = os.path.join(a.out, "bibcheck-report.md")
    cs = os.path.join(a.out, "bibdiff.csv")
    with open(md, "w", encoding="utf-8") as fh:
        fh.write(to_markdown(findings, total, len(entries)))
    with open(cs, "w", encoding="utf-8") as fh:
        fh.write(to_csv(findings))

    hard = sum(1 for f in findings if f.severity in ("CRITICAL", "MAJOR", "MINOR"))
    print(f"wrote {md} and {cs}")
    print(f"{hard} finding(s) needing attention across {len(entries)} entries")
    if sources_mod.SOURCE_FAILURES:
        detail = ", ".join(f"{h} ({n})" for h, n in
                           sorted(sources_mod.SOURCE_FAILURES.items()))
        print(f"WARNING: source coverage was degraded — unreachable after retries: "
              f"{detail}. Findings may be incomplete; re-run to fill the cache.",
              file=sys.stderr)
        if sources_mod.HOSTS_DISABLED:
            print(f"         Stopped querying after repeated failures: "
                  f"{', '.join(sorted(sources_mod.HOSTS_DISABLED))}. "
                  f"Wait for the rate limit to clear, then re-run.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
