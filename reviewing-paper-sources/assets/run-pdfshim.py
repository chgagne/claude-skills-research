#!/usr/bin/env python3
"""Reconstruct a reviewable pseudo-source tree from a PDF.

    python3 run-pdfshim.py paper.pdf --out review-assets/

Writes:
    structure.md    page/heading/caption inventory  (read this first)
    refs.bib        synthetic BibTeX for verifying-bibliography
    body-flow.txt   unwrapped prose, main body
    body-raw.txt    raw prose, main body
    appendix-flow.txt / appendix-raw.txt   when an appendix is detected

Standard library plus poppler's pdftotext.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdfshim import (  # noqa: E402
    extract_text,
    flow,
    inventory,
    parse_reference_list,
    to_bibtex,
)
from pdfshim.structure import boundaries  # noqa: E402
from pdfshim.text import PdftotextMissing, pages, reference_sections  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(prog="pdfshim")
    ap.add_argument("pdf")
    ap.add_argument("--out", default="review-assets")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    try:
        page_texts = pages(args.pdf)
    except PdftotextMissing as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    os.makedirs(args.out, exist_ok=True)

    def write(name: str, content: str) -> str:
        path = os.path.join(args.out, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path

    b = boundaries(page_texts)
    body_end = b["body_ends"]

    write("structure.md", inventory(args.pdf))

    body = "\n".join(page_texts[:body_end])
    write("body-raw.txt", body)
    write("body-flow.txt", flow(body))

    if body_end < len(page_texts):
        appx = "\n".join(page_texts[body_end:])
        write("appendix-raw.txt", appx)
        write("appendix-flow.txt", flow(appx))

    full = "\n".join(page_texts)
    sections = reference_sections(full)
    records: list[dict] = []
    for sec in sections:
        records.extend(parse_reference_list(sec))
    write("refs.bib", to_bibtex(records))

    low = [r for r in records if r.get("confidence") == "low"]
    if low:
        lines = [
            "# Reference entries needing manual transcription\n",
            "Parsed from a text layer, and these rows did not parse cleanly: the",
            "title is probably wrong. A wrong title makes the bibliography checker",
            "report a real reference as unfindable, which looks exactly like a",
            "fabricated citation. Transcribe these from the rendered page before",
            "reporting anything about them.\n",
        ]
        for r in low:
            lines.append(f"- **parsed title:** {r['title'][:110]}")
            lines.append(f"  - raw: {r['raw'][:240]}")
        write("refs-low-confidence.md", "\n".join(lines) + "\n")

    if not args.quiet:
        print(f"pages: {b['pages']}  body ends: p{body_end}")
        if len(sections) > 1:
            print(f"reference lists found: {len(sections)}  (audit every one)")
        n_low = sum(1 for r in records if r.get("confidence") == "low")
        print(f"reference entries parsed: {len(records)} "
              f"({n_low} low-confidence)")
        if n_low:
            print(f"  -> {args.out}/refs-low-confidence.md: transcribe these by hand")
        print("  Sanity-check the count against the printed list before trusting it.")
        print(f"wrote {args.out}/structure.md, refs.bib, body-*.txt")
        print("Read structure.md end to end before claiming the paper omits anything.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
