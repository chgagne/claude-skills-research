#!/usr/bin/env python3
"""Fetch style-corpus sources into a private cache. Prints what it fetched; never writes into the skill repo."""
import argparse, json, pathlib, sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE)); sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))
from proofread.corpus import fetch_arxiv_source, author_papers, propose_field_corpus  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dest", required=True, help="sources cache root, e.g. ~/Claude/style-profiles/sources")
    ap.add_argument("--arxiv", nargs="*", default=[])
    ap.add_argument("--author"); ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--propose", help="a .bib file to mine for field-corpus candidates")
    ap.add_argument("--venue", action="append", default=[])
    a = ap.parse_args(argv)
    dest = pathlib.Path(a.dest).expanduser()
    if a.propose:
        cands = propose_field_corpus(pathlib.Path(a.propose).read_text(encoding="utf-8", errors="replace"), a.venue or ["ICLR", "NeurIPS", "ICML"])
        print(json.dumps(cands, indent=1))
    if a.author:
        print(json.dumps(author_papers(a.author, a.limit), indent=1))
    rc = 0
    for aid in a.arxiv:
        p = fetch_arxiv_source(aid, dest)
        print(f"{aid}: {'cached at ' + str(p) if p else 'NO LATEX SOURCE (use PDF fallback via pdfshim)'}")
        rc = rc or (0 if p else 2)
    return rc


if __name__ == "__main__":
    sys.exit(main())
