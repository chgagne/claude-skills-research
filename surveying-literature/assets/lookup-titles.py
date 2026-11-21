#!/usr/bin/env python3
"""Confirm candidate titles against Crossref and arXiv, free, in one call.

    python3 ~/.claude/skills/surveying-literature/assets/lookup-titles.py --memory memory.txt candidates.txt

One title per line in each file: memory.txt is the step-2 list of the closest work you can name
from memory (at least 10 titles), candidates.txt the titles the searches showed. Prints one line
per distinct title, memory first, tagged [M], [S] or [M+S]: FOUND with the exact title, first
author, year, venue and DOI/arXiv id, or NOT FOUND. Each line prints as soon as its title is
checked; titles left when the time budget (--budget, 240 s) runs out print NOT CHECKED, so a slow
Crossref or arXiv costs the tail of the list, not the whole step. `--json` prints the records instead.
"""
import argparse
import json
import pathlib
import sys
import time

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))

from survey import lookup  # noqa: E402

MIN_MEMORY = 10


def _lines(path):
    return [l.strip() for l in pathlib.Path(path).read_text().splitlines() if l.strip()]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="candidate titles from the searches, one per line")
    ap.add_argument("--memory", required=True,
                    help=f"the step-2 list: titles you can name from memory, one per line (>= {MIN_MEMORY})")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--budget", type=float, default=240,
                    help="seconds before the remaining titles are printed NOT CHECKED (default 240)")
    a = ap.parse_args(argv)
    memory = _lines(a.memory)
    if len(memory) < MIN_MEMORY:
        print(f"memory list has {len(memory)} titles; write at least {MIN_MEMORY} closest prior works "
              "you can name from memory (step 2), then rerun", file=sys.stderr)
        return 2
    merged = lookup.merge(memory, _lines(a.file))
    # One line per title, flushed as it resolves: B5 lost a whole run when a slow API kept the
    # buffered output empty past the agent's Bash limit.
    start, res, skipped = time.monotonic(), [], 0
    for title, tag in merged:
        if skipped or time.monotonic() - start > a.budget:
            r = {"query": title, "found": False, "not_checked": True, "source": tag}
            skipped += 1
        else:
            r = lookup.resolve(title); r["source"] = tag
        res.append(r)
        if not a.json:
            print(lookup.render([r]), flush=True)
    if a.json:
        print(json.dumps(res, indent=1, ensure_ascii=False))
    elif skipped:
        print(f"time budget of {a.budget:.0f} s reached: {skipped} titles NOT CHECKED; rerun with those "
              "titles only to check them", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
