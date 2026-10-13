#!/usr/bin/env python3
"""Confirm candidate titles against Crossref and arXiv, free, in one call.

    python3 ~/.claude/skills/surveying-literature/assets/lookup-titles.py candidates.txt

One title per line. Prints one line per title: FOUND with the exact title, first author,
year, venue and DOI/arXiv id, or NOT FOUND. `--json` prints the records instead.
"""
import argparse
import json
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))

from survey import lookup  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="one candidate title per line")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    titles = [l.strip() for l in pathlib.Path(a.file).read_text().splitlines() if l.strip()]
    res = lookup.resolve_all(titles)
    print(json.dumps(res, indent=1, ensure_ascii=False) if a.json else lookup.render(res))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
