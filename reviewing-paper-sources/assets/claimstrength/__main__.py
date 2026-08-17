"""CLI: read a paper's sources, pair abstract assertions against results."""
import argparse
import os
import sys

from scholarly.latex import read_sources, split_sections

from .claims import abstract_text, pair, results_bodies, sentences
from .report import render


def main(argv=None):
    ap = argparse.ArgumentParser(prog="claimstrength")
    ap.add_argument("paper_dir")
    ap.add_argument("--main", default="main.tex")
    ap.add_argument("--out", default=None)
    ap.add_argument("--min-shared", type=int, default=3)
    args = ap.parse_args(argv)

    main_path = os.path.join(args.paper_dir, args.main)
    if not os.path.exists(main_path):
        print(f"no such file: {main_path}", file=sys.stderr)
        return 1

    full = read_sources(main_path)
    degraded = []

    abstract = abstract_text(full)
    if not abstract:
        degraded.append("no abstract environment found")

    bodies = results_bodies(split_sections(full))
    if not bodies:
        degraded.append("no results/evaluation/experiments section found")

    results_sents = []
    for _, body in bodies:
        results_sents += sentences(body)

    pairings = pair(sentences(abstract), results_sents, args.min_shared)
    text = render(pairings, degraded)

    if args.out:
        os.makedirs(args.out, exist_ok=True)
        path = os.path.join(args.out, "claim-strength.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(path)
    else:
        print(text)

    return 2 if degraded else 0
