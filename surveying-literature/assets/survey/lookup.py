"""Confirm candidate titles against free bibliographic indexes.

A web search per candidate is the expensive way to check that a paper exists: each one
is a separate model call. Crossref and arXiv answer the same question for nothing. Each
title is looked up in both; a match gives the exact title, year, venue, DOI and arXiv id.
"""
import re

from scholarly.textnorm import norm_title

from . import traverse

ENGINES = {
    "crossref": lambda t: traverse._crossref_search(t, 5),
    "arxiv": lambda t: traverse._arxiv_search(t, 5),
}

_ARXIV_ID = re.compile(r"(\d{4}\.\d{4,5})")
# Crossref also registers supplementary files, titled after the article plus a file name
# ("..._supp1-3374889.pdf") under a component DOI (".../mm1"); they are not the article.
_COMPONENT = re.compile(r"\.(pdf|zip|docx?|mp4|csv)\b|_supp\d|/mm\d+$|\.s\d{3}$", re.I)


def _same(query, title):
    """2 for equal normalised titles, 1 when one is a prefix of the other on six or more
    words (published versions often add a subtitle the preprint lacks), else 0."""
    q, t = norm_title(query).split(), norm_title(title or "").split()
    if not q or not t:
        return 0
    if q == t:
        return 2
    n = min(len(q), len(t))
    return 1 if n >= 6 and q[:n] == t[:n] else 0


def _best(title, hits):
    ok = [h for h in hits if not _COMPONENT.search((h.get("title") or "") + " " + (h.get("doi") or ""))]
    scored = [(_same(title, h.get("title")), i, h) for i, h in enumerate(ok)]
    scored = [s for s in scored if s[0]]
    return max(scored, key=lambda s: (s[0], -s[1]))[2] if scored else None


def resolve(title):
    out = {"query": title, "found": False, "title": None, "year": None, "venue": None,
           "doi": None, "arxiv": None, "first_author": None, "sources": []}
    for name, search in ENGINES.items():
        try:
            hits = search(title) or []
        except Exception:
            continue
        h = _best(title, hits)
        if h is None:
            continue
        out["found"] = True
        out["sources"].append(name)
        if name == "arxiv":
            m = _ARXIV_ID.search(h.get("id") or "")
            out["arxiv"] = out["arxiv"] or (m.group(1) if m else None)
        else:
            out["doi"] = out["doi"] or h.get("doi")
            out["venue"] = h.get("venue") or out["venue"]
        out["title"] = out["title"] or h.get("title")
        out["year"] = out["year"] or h.get("year")
        out["first_author"] = out["first_author"] or ((h.get("authors") or [None])[0])
        out["venue"] = out["venue"] or h.get("venue")
    return out


def resolve_all(titles):
    return [resolve(t) for t in titles]


def render(results):
    lines = []
    for r in results:
        if not r["found"]:
            lines.append(f"NOT FOUND | {r['query']}")
            continue
        ids = "; ".join(x for x in (r["doi"] and f"doi:{r['doi']}", r["arxiv"] and f"arXiv:{r['arxiv']}") if x)
        lines.append(f"FOUND | {r['title']} | {r['first_author'] or '?'} | {r['year'] or '?'} | "
                     f"{r['venue'] or '?'} | {ids}")
    return "\n".join(lines)
