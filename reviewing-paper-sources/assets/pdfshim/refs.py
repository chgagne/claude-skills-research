"""Reference list -> synthetic BibTeX.

The output feeds `verifying-bibliography`'s run-bibcheck.py unmodified. That
checker resolves entries by title search, so **title fidelity is the field that
has to be right**; authors, year and venue are carried through for the audit
table and for the checker's field comparison.

Reference lists come in three shapes that differ in both how entries are
delimited and where the year sits:

    numbered   [1] Given Family, Given Family. Title. In Venue, 2021. 6, 7
    initials   Family, G., Family, G., et al. Title. In Venue, pp. 1-9, 2016.
    year-first Family, G.; Family, G. 2022. Title. In Venue, 1-9.
               Given Family, and Given Family. 2019. Title. Venue.

Getting this wrong silently returns a handful of entries out of fifty, which
looks like a short bibliography rather than a broken parse. `style()` reports
what it detected so the count can be sanity-checked against the page.
"""

from __future__ import annotations

import re
import unicodedata

_NUMBERED = re.compile(r"^\s*\[(\d{1,3})\]\s*")
# Family, G.  /  Family, Given  /  van der Berg, G.
_INITIALS_START = re.compile(
    r"^\s*(?:(?:van|von|de|della|del|da|di|der|ten|ter)\s+)*"
    r"[A-ZÀ-ÞŠŽ][\w'’\-]+(?:\s+[A-ZÀ-ÞŠŽ][\w'’\-]+)?,\s+"
    r"[A-ZÀ-ÞŠŽ]\.(?:\s*-?\s*[A-ZÀ-ÞŠŽ]\.)*(?=[\s,;])",
    re.U,
)
_CAP_START = re.compile(r"^\s*[A-ZÀ-ÞŠŽ]", re.U)

# One "Family, G." / "Family, G.-H." / "van Berg, G." unit, plus its separator.
_NAME_UNIT = (
    r"(?:(?:van|von|de|della|del|da|di|der|ten|ter)\s+)*"
    r"[A-ZÀ-ÞŠŽ][\w'’\-]+(?:\s+[A-ZÀ-ÞŠŽ][\w'’\-]+)?,\s*"
    r"[A-ZÀ-ÞŠŽ]\.(?:\s*-?\s*[A-ZÀ-ÞŠŽ]\.)*"
)
# The whole author block of an "initials" entry: repeated units, optional
# "and" before the last, optional trailing "et al."  Anchored at the start.
_AUTHOR_BLOCK = re.compile(
    r"^\s*(?:(?:and\s+)?" + _NAME_UNIT + r"\s*(?:,\s*|\s+and\s+|;\s*)?)+"
    r"(?:(?:and\s+)?et\s*~?al\.?)?",
    re.U,
)

_YEAR_ANY = re.compile(r"(?<!\d)((?:19|20|21)\d{2})([a-z]?)(?!\d)")
_YEAR_TAIL = re.compile(r"(?<!\d)((?:19|20|21)\d{2})([a-z]?)\.?\s*$")
_ARXIV = re.compile(r"arXiv[:\s]*(\d{4}\.\d{4,5})", re.I)
_DOI = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)")
_PAGES = re.compile(r"(?:pp?\.\s*)?(\d+)\s*[-–—]{1,2}\s*(\d+)")
# Trailing back-references to citing pages, e.g. "In CVPR, 2021. 6, 7, 8, 11"
_BACKREFS = re.compile(r"\.\s*\d+(?:\s*,\s*\d+)*\s*$")


def _norm(s: str) -> str:
    return " ".join(s.replace("­", "").split())


def style(refs_text: str) -> str:
    """'numbered' | 'initials' | 'plain'."""
    lines = [l for l in refs_text.split("\n") if l.strip()]
    if sum(bool(_NUMBERED.match(l)) for l in lines) >= 3:
        return "numbered"
    if sum(bool(_INITIALS_START.match(l)) for l in lines) >= 3:
        return "initials"
    return "plain"


def split_entries(refs_text: str, kind: str | None = None) -> list[str]:
    """Group wrapped lines into whole entries."""
    kind = kind or style(refs_text)
    lines = [l.rstrip() for l in refs_text.split("\n") if l.strip()]
    entries: list[list[str]] = []

    for line in lines:
        if kind == "numbered":
            new = bool(_NUMBERED.match(line))
        elif kind == "initials":
            new = bool(_INITIALS_START.match(line))
        else:
            # Hanging indent is lost in extraction, so use completeness: a new
            # entry can only start once the current one already carries a year.
            cur = " ".join(entries[-1]) if entries else ""
            new = bool(_CAP_START.match(line)) and bool(_YEAR_ANY.search(cur))
        if new or not entries:
            entries.append([line])
        else:
            entries[-1].append(line)

    out = []
    for chunk in entries:
        joined = " ".join(chunk)
        joined = _NUMBERED.sub("", joined)
        joined = re.sub(r"-\s+(?=[a-z])", "", joined)   # rejoin split words
        joined = _BACKREFS.sub(".", joined)             # drop citing-page lists
        cleaned = _norm(joined)
        if len(cleaned) > 25:
            out.append(cleaned)
    return out


def _segments(entry: str) -> list[str]:
    """Split on sentence-ending periods, ignoring initials and abbreviations."""
    segs, start = [], 0
    for m in re.finditer(r"\.(?:\s+|$)", entry):
        before = entry[start:m.start()]
        whole = entry[:m.start()]
        if re.search(r"(?:^|\s)[A-ZÀ-ÞŠŽ]$", whole):        # an initial
            continue
        if re.search(r"\b(?:et al|vs|eds?|Jr|Sr|St|approx|Inc|Ltd|no|vol)$",
                     whole, re.I):
            continue
        segs.append(before.strip())
        start = m.end()
    tail = entry[start:].strip()
    if tail:
        segs.append(tail)
    return [s for s in segs if s]


def _split_initials_entry(entry: str) -> tuple[str, str] | None:
    """(authors, rest) for the 'initials' style, where the author list ends in
    an initial and a sentence splitter cannot tell "Levine, S. Learning..."
    (end of authors) from "Ku, W.-S., and Nguyen, A." (middle of the list)."""
    m = _AUTHOR_BLOCK.match(entry)
    if not m or m.end() < 6:
        return None
    authors = entry[: m.end()].strip().rstrip(",;").strip()
    rest = entry[m.end():].lstrip(" ,;.")
    if not rest or authors.count(",") == 0:
        return None
    return authors, rest


def parse_entry(entry: str, kind: str = "") -> dict | None:
    if kind == "initials":
        split = _split_initials_entry(entry)
        if split:
            authors, rest = split
            lead_year = re.match(r"\s*((?:19|20|21)\d{2})([a-z]?)\.\s*", rest)
            forced_year = forced_suffix = ""
            if lead_year:
                forced_year, forced_suffix = lead_year.group(1), lead_year.group(2)
                rest = rest[lead_year.end():]
            segs = _segments(rest)
            if segs:
                title = segs[0]
                venue = " ".join(segs[1:])
                year = suffix = ""
                ym = None
                for ym in _YEAR_ANY.finditer(entry[len(authors):]):
                    pass
                if ym:
                    year, suffix = ym.group(1), ym.group(2)
                if forced_year:
                    year, suffix = forced_year, forced_suffix
                rec = {
                    "authors": _norm(authors), "year": year, "suffix": suffix,
                    "title": _norm(title).rstrip("."),
                    "venue": _norm(venue).rstrip("."), "raw": entry,
                }
                return _decorate(rec, entry)

    segs = _segments(entry)
    if len(segs) < 2:
        return None

    year = suffix = ""
    # Shape A: authors end with the year  ("...; and Liang, J. 2022")
    m = _YEAR_TAIL.search(segs[0])
    if m and len(segs) >= 2:
        authors = segs[0][: m.start()].strip().rstrip(",;").strip()
        year, suffix = m.group(1), m.group(2)
        title, venue = segs[1], " ".join(segs[2:])
    # Shape B: the year is its own segment  ("Agirre, ... . 2007. Title.")
    elif re.fullmatch(r"(?:19|20|21)\d{2}[a-z]?", segs[1].strip()):
        authors = segs[0]
        ym = _YEAR_ANY.search(segs[1])
        year, suffix = ym.group(1), ym.group(2)
        title, venue = (segs[2] if len(segs) > 2 else ""), " ".join(segs[3:])
    # Shape C: the year sits at the end, in the venue
    else:
        authors, title, venue = segs[0], segs[1], " ".join(segs[2:])
        ym = None
        for ym in _YEAR_ANY.finditer(entry):
            pass
        if ym:
            year, suffix = ym.group(1), ym.group(2)

    if not title:
        return None
    rec = {
        "authors": _norm(authors),
        "year": year,
        "suffix": suffix,
        "title": _norm(title).rstrip("."),
        "venue": _norm(venue).rstrip("."),
        "raw": entry,
    }
    return _decorate(rec, entry)


# A title that is really a name list: mostly capitalised words, commas, "and".
_LOOKS_LIKE_NAMES = re.compile(
    r"^(?:[A-ZÀ-ÞŠŽ][\w'’\-]*\.?\s*){0,3}(?:,|\band\b)", re.U
)


def _confidence(rec: dict) -> str:
    """'ok' | 'low'. Low-confidence rows are the ones to transcribe by hand.

    Reference parsing from a text layer is heuristic; the failure that matters
    is a wrong title, because the checker then reports a real entry as
    unfindable. These signals catch most wrong titles.
    """
    t = rec["title"]
    if not rec["year"]:
        return "low"
    if len(t) < 12 or len(t.split()) < 3:
        return "low"
    if _LOOKS_LIKE_NAMES.match(t) and sum(
        w[:1].isupper() for w in t.split()
    ) > len(t.split()) * 0.6:
        return "low"
    if t.lower().startswith(("in ", "proceedings of the ", "arxiv preprint",
                             "advances in neural")):
        return "low"
    return "ok"


def _decorate(rec: dict, entry: str) -> dict:
    if (m := _ARXIV.search(entry)):
        rec["arxiv"] = m.group(1)
    if (m := _DOI.search(entry)):
        rec["doi"] = m.group(1).rstrip(".")
    if (m := _PAGES.search(rec["venue"])):
        rec["pages"] = f"{m.group(1)}--{m.group(2)}"
    rec["confidence"] = _confidence(rec)
    return rec


def parse_reference_list(refs_text: str) -> list[dict]:
    kind = style(refs_text)
    out = []
    for entry in split_entries(refs_text, kind):
        rec = parse_entry(entry, kind)
        if rec and len(rec["title"]) > 5:
            rec["style"] = kind
            out.append(rec)
    return out


def _key(rec: dict, taken: set[str]) -> str:
    first = re.split(r"[,;]", rec["authors"])[0]
    first = first.split()[-1] if first.split() else "anon"
    first = unicodedata.normalize("NFKD", first)
    first = "".join(c for c in first if c.isascii() and c.isalnum()).lower()
    base = f"{first or 'anon'}{rec['year'] or 'nd'}{rec['suffix']}"
    key, n = base, 2
    while key in taken:
        key, n = f"{base}{chr(96 + n)}", n + 1
    taken.add(key)
    return key


_NAME_UNIT_RE = re.compile(_NAME_UNIT, re.U)


def bibtex_authors(authors: str) -> str:
    """Convert a printed author list into BibTeX's `and`-separated form.

    Emitting the printed string verbatim makes the bibliography checker parse
    the whole list as a single author and report every co-author as missing --
    a defect manufactured by the shim, indistinguishable in a report from a
    real one. Two shapes have to be handled: "Family, G., Family, G." where the
    comma is part of the name, and "Given Family, Given Family" where it is the
    separator.
    """
    a = re.sub(r"\bet\s*~?al\.?", "", authors).strip().rstrip(",;").strip()
    if not a:
        return ""
    units = [m.group(0).strip().rstrip(",;").strip()
             for m in _NAME_UNIT_RE.finditer(a)]
    joined = " ".join(units)
    # Trust the unit split only when it accounts for most of the string;
    # otherwise the list is "Given Family, Given Family" and commas separate.
    if units and len(joined) >= 0.6 * len(a):
        return " and ".join(units)
    parts = re.split(r",|\band\b|;", a)
    return " and ".join(p.strip() for p in parts if p.strip())


def _escape(s: str) -> str:
    return s.replace("{", "").replace("}", "").replace("\\", "")


def to_bibtex(records: list[dict]) -> str:
    taken: set[str] = set()
    chunks = [
        "% Synthetic BibTeX reconstructed from a PDF reference list.",
        "% Transcribed, not authoritative: verify anything the checker flags",
        "% against the publisher record before reporting it as a defect.",
        "",
    ]
    for rec in records:
        key = _key(rec, taken)
        venue = rec["venue"]
        venue = re.sub(r",?\s*(?:pp?\.?\s*)?\d+\s*[-–—]{1,2}\s*\d+\.?", "", venue)
        venue = re.sub(r",?\s*(?:19|20|21)\d{2}[a-z]?\.?\s*$", "", venue)
        venue = re.sub(r"^In\s+", "", venue).strip().rstrip(",.").strip()
        kind = "article" if re.search(
            r"\bJournal\b|\bTransactions\b|\barXiv\b|\bNature\b|\bScience\b|"
            r"\bProceedings of the [A-Z]", venue, re.I) else "inproceedings"
        field = "journal" if kind == "article" else "booktitle"
        lines = [f"@{kind}{{{key},",
                 f"  author = {{{_escape(bibtex_authors(rec['authors']))}}},",
                 f"  title = {{{_escape(rec['title'])}}},"]
        if venue:
            lines.append(f"  {field} = {{{_escape(venue)}}},")
        if "pages" in rec:
            lines.append(f"  pages = {{{rec['pages']}}},")
        if "doi" in rec:
            lines.append(f"  doi = {{{rec['doi']}}},")
        if "arxiv" in rec:
            lines.append(f"  eprint = {{{rec['arxiv']}}},")
        lines.append(f"  year = {{{rec['year'] or '0000'}}}")
        lines.append("}")
        chunks.append("\n".join(lines))
    return "\n".join(chunks) + "\n"
