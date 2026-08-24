"""Reconstruct a reviewable pseudo-source tree from a PDF.

Every tool in the review family assumes LaTeX sources. Given only a PDF, this
package produces the three artifacts the workflow actually needs:

  structure.md  an inventory of pages, headings and every figure/table caption,
                so "the paper does not report X" can be checked by reading
                rather than by grepping
  refs.bib      synthetic BibTeX for the reference list, which feeds
                verifying-bibliography unmodified
  body-flow.txt de-hyphenated, unwrapped prose, because pdftotext output is
                hard-wrapped and defeats multi-word search

Standard library plus poppler's pdftotext. No third-party imports.
"""

from .text import extract_text, flow, split_at_references
from .structure import inventory
from .refs import parse_reference_list, to_bibtex

__all__ = [
    "extract_text",
    "flow",
    "split_at_references",
    "inventory",
    "parse_reference_list",
    "to_bibtex",
]
