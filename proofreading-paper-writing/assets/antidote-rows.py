#!/usr/bin/env python3
"""Append an Antidote pass to the writing ledger as mechanics rows.

Diffs the original tex against a copy the user corrected in Antidote, appends the safe
word-level fixes to the ledger (ids from the next free block of 100), and writes every
refused change, with its reason, to a review file. The corrected copy is never rendered.
Stdlib only. See SKILL.md, step 3b.
"""
import argparse, pathlib, re, sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from proofread.antidote import antidote_rows                    # noqa: E402
from proofread.ledger import load_ledger, dump_ledger           # noqa: E402


def parse(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--orig", required=True, help="the tex the renderer will edit (main.tex)")
    ap.add_argument("--corrected", required=True, help="the copy saved from Antidote")
    ap.add_argument("--ledger", required=True, help="writing-ledger.jsonl; created if missing")
    ap.add_argument("--review", required=True, help="markdown list of refused changes")
    ap.add_argument("--start", type=int, help="first id number; default the next block of 100")
    return ap.parse_args(argv)


def next_block(rows):
    nums = [int(r.id[1:]) for r in rows]
    return (max(nums) // 100 + 1) * 100 if nums else 1


def write_review(path, rejected, corrected):
    # edits inside LaTeX comments never reach the PDF; count them, don't list them
    in_comment = sum(x["reason"] == "inside a LaTeX comment" for x in rejected)
    rejected = [x for x in rejected if x["reason"] != "inside a LaTeX comment"]
    lines = [f"# Antidote changes not turned into rows ({len(rejected)})", "",
             f"Corrected copy: `{corrected}`. Each item is a change Antidote made that the",
             "script refused. Restore nothing from the copy; if the fix itself is right,",
             "write it as a ledger row by hand (a `style` row needs a rule).", ""]
    if in_comment:
        lines += [f"{in_comment} edits inside LaTeX comments ignored.", ""]
    for x in rejected:
        lines += [f"- line {x['line']}: {x['reason']}",
                  f"  - before: `{' '.join(x['before'].split())}`",
                  f"  - after: `{' '.join(x['after'].split())}`"]
    pathlib.Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    a = parse(argv)
    orig = pathlib.Path(a.orig).read_text(encoding="utf-8")
    corrected = pathlib.Path(a.corrected).read_text(encoding="utf-8")
    ledger = pathlib.Path(a.ledger)
    existing = load_ledger(ledger) if ledger.exists() else []
    start = a.start if a.start is not None else next_block(existing)
    rows, rejected = antidote_rows(orig, corrected, start, existing)
    dump_ledger(existing + rows, ledger)
    write_review(a.review, rejected, a.corrected)
    unescaped = sum("unescaped %" in x["reason"] for x in rejected)
    print(f"antidote: {len(rows)} rows appended (W{start}-), {len(rejected)} refused -> {a.review}"
          + (f"; {unescaped} unescaped % in the corrected copy" if unescaped else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
