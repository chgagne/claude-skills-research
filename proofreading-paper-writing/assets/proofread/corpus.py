"""Assemble the style corpora: arXiv sources for field papers and an author's prior papers."""
import json, os, pathlib, re, sys, urllib.parse

_SHARED = os.path.expanduser("~/.claude/skills/_shared")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)
from scholarly.retrieval import get_bytes, get_json, s2_api_key, arxiv_id_of  # noqa: E402
from scholarly.bibtex import parse_bib                                           # noqa: E402
from scholarly.eprint import tex_from_eprint                                     # noqa: E402

_S2 = "https://api.semanticscholar.org/graph/v1/"


def fetch_arxiv_source(arxiv_id, dest_root):
    dest = pathlib.Path(dest_root) / arxiv_id.replace("/", "_")
    if (dest / "source.tex").exists():
        return dest
    blob = get_bytes(f"https://arxiv.org/e-print/{urllib.parse.quote(arxiv_id)}")
    tex = tex_from_eprint(blob)
    if not tex.strip():
        return None
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "source.tex").write_text(tex, encoding="utf-8")
    (dest / "meta.json").write_text(json.dumps({"arxiv_id": arxiv_id, "kind": "arxiv-latex"}), encoding="utf-8")
    return dest


def author_papers(name, limit=5):
    key = s2_api_key()
    if not key:
        return []
    hdr = {"x-api-key": key}
    hit = get_json(_S2 + "author/search?query=" + urllib.parse.quote(name) + "&fields=authorId,name,paperCount", hdr)
    data = (hit or {}).get("data") or []
    if not data:
        return []
    aid = data[0]["authorId"]
    papers = get_json(_S2 + f"author/{aid}/papers?fields=title,year,venue,citationCount,externalIds&limit=100", hdr)
    rows = []
    for p in (papers or {}).get("data") or []:
        rows.append({"title": p.get("title", ""), "year": p.get("year"), "venue": p.get("venue", ""),
                     "arxiv_id": (p.get("externalIds") or {}).get("ArXiv"), "citations": p.get("citationCount", 0)})
    rows.sort(key=lambda r: (-(r["citations"] or 0), -(r["year"] or 0)))
    return rows[:limit]


def propose_field_corpus(bib_text, venues, k=8):
    pats = [re.compile(re.escape(v), re.I) for v in venues]
    out = []
    for e in parse_bib(bib_text):
        venue = e.fields.get("booktitle") or e.fields.get("journal") or ""
        if not any(p.search(venue) for p in pats):
            continue
        aid = arxiv_id_of(e)
        if not aid:
            continue
        out.append({"key": e.key, "title": e.fields.get("title", ""), "venue": venue, "arxiv_id": aid})
    return out[:k]
