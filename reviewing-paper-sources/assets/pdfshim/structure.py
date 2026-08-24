"""Inventory of what is in the document and where.

This exists because of one recurring review defect: writing "the paper does not
report X" after a keyword search missed it. Greps fail for boring reasons — the
paper says `leave-one-dataset-out` and you searched `leave-one-out`; the caption
sits mid-line in a two-column extraction so `^Figure \\d` never matches; the
number you want is in the first paragraph of a section whose second paragraph
you already read. An inventory is read, not searched, and reading is what
catches these.
"""

from __future__ import annotations

import re

from .text import pages

# Captions are found ANYWHERE in the line, never anchored to line start.
# In a two-column extraction a caption routinely shares a line with body text
# from the adjacent column, so an anchored pattern silently misses it.
_CAPTION = re.compile(
    r"(Figure|Table|Algorithm)\s*([A-Z]?\.?\d+(?:\.\d+)*)\s*[:.]\s*(.{0,90})",
    re.S,
)

# A heading: a short line, title-ish, no terminal period, not a caption.
_HEADING = re.compile(r"^[ \t]*([A-Z][A-Za-z0-9 ,\-/&']{2,60})[ \t]*$")

_APPENDIX_START = re.compile(
    r"^\s*(Appendix|Supplementary\s+Material|Supplemental\s+Material|"
    r"Technical\s+Appendix|Supplementary\s+material\s+for)\b",
    re.I | re.M,
)

_REFS = re.compile(r"^\s*(References|REFERENCES|Bibliography)\s*$", re.M)

_STOPWORDS = {
    "Abstract", "Introduction", "Conclusion", "Conclusions", "Acknowledgments",
    "Acknowledgements", "References", "Anonymous submission",
}


def _clean(s: str) -> str:
    return " ".join(s.split())


def captions(page_texts: list[str]) -> list[tuple[int, str, str, str]]:
    """(page, kind, number, first words) for every caption in the document."""
    found = []
    for i, txt in enumerate(page_texts, start=1):
        for m in _CAPTION.finditer(txt):
            found.append((i, m.group(1), m.group(2), _clean(m.group(3))))
    return found


def headings(page_texts: list[str]) -> list[tuple[int, str]]:
    out = []
    for i, txt in enumerate(page_texts, start=1):
        for line in txt.split("\n"):
            m = _HEADING.match(line)
            if not m:
                continue
            h = _clean(m.group(1))
            if h in _STOPWORDS or len(h.split()) > 9:
                continue
            if _CAPTION.match(h):
                continue
            out.append((i, h))
    return out


def boundaries(page_texts: list[str]) -> dict:
    """Where the body ends, the references start, the appendix starts."""
    refs_pages, appendix_pages = [], []
    for i, txt in enumerate(page_texts, start=1):
        if _REFS.search(txt):
            refs_pages.append(i)
        if _APPENDIX_START.search(txt):
            appendix_pages.append(i)
    return {
        "pages": len(page_texts),
        "references_pages": refs_pages,
        "appendix_pages": appendix_pages,
        "body_ends": (min(refs_pages) - 1) if refs_pages else len(page_texts),
    }


def inventory(pdf: str) -> str:
    """A Markdown inventory. Read it end to end before writing any claim that
    the paper omits something."""
    page_texts = pages(pdf)
    b = boundaries(page_texts)
    caps = captions(page_texts)
    heads = headings(page_texts)

    lines: list[str] = []
    lines.append(f"# Structure inventory\n")
    lines.append(f"- Pages: **{b['pages']}**")
    lines.append(f"- Body appears to end on page **{b['body_ends']}**")
    lines.append(
        "- Reference list heading on page(s): "
        + (", ".join(map(str, b["references_pages"])) or "none found")
    )
    if len(b["references_pages"]) > 1:
        lines.append(
            "  - **More than one reference list.** Audit every one; a second list "
            "in the appendix commonly holds dataset or resource citations."
        )
    lines.append(
        "- Appendix/supplement heading on page(s): "
        + (", ".join(map(str, b["appendix_pages"])) or "none found")
    )

    lines.append("\n## First line of each page\n")
    for i, txt in enumerate(page_texts, start=1):
        first = next((l for l in txt.split("\n") if l.strip()), "")
        lines.append(f"- p{i}: {_clean(first)[:100]}")

    body_end = b["body_ends"]
    lines.append("\n## Captions\n")
    if not caps:
        lines.append("_None detected._")
    else:
        lines.append("| Page | Where | Label | Caption opens |")
        lines.append("|---|---|---|---|")
        for page, kind, num, head in caps:
            where = "body" if page <= body_end else "appendix"
            lines.append(f"| {page} | {where} | {kind} {num} | {head} |")
        body_labels = {f"{k} {n}" for p, k, n, _ in caps if p <= body_end}
        appx_labels = {f"{k} {n}" for p, k, n, _ in caps if p > body_end}
        lines.append(
            f"\n{len(body_labels)} distinct labels in the body, "
            f"{len(appx_labels)} in the appendix."
        )
        overlap = sorted(body_labels & appx_labels)
        if overlap:
            lines.append(
                "\n**Numbering restarts in the appendix** for: "
                + ", ".join(overlap)
                + ". A bare \"Table 1\" is therefore ambiguous; say which."
            )

    lines.append("\n## Candidate section headings\n")
    for page, h in heads:
        where = "body" if page <= body_end else "appendix"
        lines.append(f"- p{page} ({where}): {h}")

    lines.append(
        "\n---\n\n**Before writing that the paper omits something, read the "
        "appendix headings and captions above end to end.** Across four reviews, "
        "every false \"the paper does not report X\" would have been caught here."
    )
    return "\n".join(lines) + "\n"
