"""Resolve a paper reference to a verified identity.

Everything downstream quotes this paper's text back at a reviewer, so resolving
the wrong paper is worse than resolving nothing. A title query is accepted only
when the retrieved record's title actually matches -- the rule the bibliography
work needed three separate times before it stuck.
"""
import json
import os
import re
import sys
import urllib.parse
from dataclasses import dataclass, field

_SHARED = os.path.expanduser("~/.claude/skills/_shared")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from scholarly.retrieval import (fetch_arxiv, fetch_crossref,  # noqa: E402
                                 get_json, s2_api_key, search_dblp)
from scholarly.textnorm import norm_title  # noqa: E402

_DOI = re.compile(r"(?:^|doi\.org/)(10\.\d{4,}/\S+)", re.I)
_ARXIV = re.compile(r"(?:arxiv[:/]|abs/)?(\d{4}\.\d{4,5})(?:v\d+)?$", re.I)


@dataclass
class PaperRef:
    title: str = ""
    authors: list = field(default_factory=list)
    year: int = None
    venue: str = ""
    doi: str = None
    arxiv_id: str = None
    s2_id: str = None
    source: str = ""


def _from_record(rec, **extra):
    if rec is None:
        return None
    return PaperRef(title=rec.title, authors=list(rec.authors or []),
                    year=rec.year, venue=rec.venue or "", doi=rec.doi,
                    source=rec.source, **extra)


def _by_doi(doi):
    return _from_record(fetch_crossref(doi))


def _by_arxiv(arxiv_id):
    ref = _from_record(fetch_arxiv(arxiv_id))
    if ref:
        ref.arxiv_id = arxiv_id
    return ref


def _s2_match(title):
    """S2 title match, keeping the external ids the shared Record drops.

    The arXiv id matters more than it looks: it is what lets the full-text
    ladder fetch LaTeX source instead of parsing a PDF, and appendices -- where
    training scale and seed counts live -- only survive that route.
    """
    url = ("https://api.semanticscholar.org/graph/v1/paper/search/match?"
           "fields=title,year,venue,externalIds,authors&query="
           + urllib.parse.quote(title))
    key = s2_api_key()
    d = get_json(url, {"x-api-key": key} if key else None)
    data = (d or {}).get("data") or []
    if not data:
        return None
    p = data[0]
    ext = p.get("externalIds") or {}
    return PaperRef(
        title=p.get("title") or "",
        authors=[a.get("name") for a in (p.get("authors") or []) if a.get("name")],
        year=p.get("year"), venue=p.get("venue") or "",
        doi=ext.get("DOI"), arxiv_id=ext.get("ArXiv"),
        s2_id=p.get("paperId"), source="s2")


def _by_title(title):
    ref = _s2_match(title)
    if ref:
        return ref
    rec = search_dblp(title)
    return _from_record(rec) if rec else None


def resolve(query):
    """Accept a DOI, an arXiv id, a URL to either, or a title."""
    q = (query or "").strip()
    if not q:
        return None

    m = _DOI.search(q)
    if m:
        return _by_doi(m.group(1).rstrip(".,;"))

    m = _ARXIV.search(q)
    if m and not q.lower().startswith("10."):
        return _by_arxiv(m.group(1))

    ref = _by_title(q)
    if ref is None:
        return None
    # Identity before use: a near-miss title must never be quoted as this paper.
    if norm_title(ref.title) != norm_title(q):
        return None
    return ref


def from_candidates(path, grades=("THREAT",)):
    """Take a shortlist straight from a gap sweep's candidates.json."""
    try:
        with open(path, encoding="utf-8") as fh:
            rows = json.load(fh)
    except (OSError, ValueError):
        return []

    out = []
    for row in rows:
        if row.get("grade") not in grades:
            continue
        ref = None
        if row.get("doi"):
            ref = _by_doi(row["doi"])
        if ref is None and row.get("title"):
            ref = _by_title(row["title"])
        if ref is None and row.get("title"):
            # Keep what the sweep already knew rather than dropping the paper.
            ref = PaperRef(title=row["title"], year=row.get("year"),
                           venue=row.get("venue", ""), doi=row.get("doi"),
                           authors=list(row.get("authors") or []),
                           source="candidates.json")
        if ref:
            out.append(ref)
    return out
