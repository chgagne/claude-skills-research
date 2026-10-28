#!/usr/bin/env python3
"""Confirm candidate titles against Crossref and arXiv, free, in one call.

    python3 ~/.claude/skills/surveying-literature/assets/lookup-titles.py --memory memory.txt candidates.txt

One title per line in each file: memory.txt is the step-2 list of the closest work you can name
from memory (at least 10 titles), candidates.txt the titles the searches showed. Prints one line
per distinct title, memory first, tagged [M], [S] or [M+S]: FOUND with the exact title, first
author, year, venue and DOI/arXiv id, or NOT FOUND. `--json` prints the records instead.
"""
import argparse
import json
import pathlib
import sys

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
    a = ap.parse_args(argv)
    memory = _lines(a.memory)
    if len(memory) < MIN_MEMORY:
        print(f"memory list has {len(memory)} titles; write at least {MIN_MEMORY} closest prior works "
              "you can name from memory (step 2), then rerun", file=sys.stderr)
        return 2
    merged = lookup.merge(memory, _lines(a.file))
    res = lookup.resolve_all([t for t, _ in merged], tags=[s for _, s in merged])
    print(json.dumps(res, indent=1, ensure_ascii=False) if a.json else lookup.render(res))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
