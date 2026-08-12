"""Expand outward from what the draft cites, three ways.

Backward (what the cited papers cite), forward (what cites them) and OpenAlex's
own related-works edge. A paper reached from several directions at once is far
more likely to matter than one reached from a single hop, so *how* a candidate
was found is recorded and used for ranking.

Every network call goes through scholarly.retrieval, which carries the
throttling, retry, negative caching and circuit breaker that Stage 1 needed.
Do not call urllib directly from here.
"""
import os
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

_SHARED = os.path.expanduser("~/.claude/skills/_shared")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from scholarly.retrieval import (_mailto_param, get_bytes,  # noqa: E402
                                 get_json,
                                 s2_api_key, _dblp_to_record)
from scholarly.textnorm import norm_title  # noqa: E402

_OA = "https://api.openalex.org/works"
_FIELDS = "id,title,display_name,publication_year,cited_by_count,doi,primary_location"


@dataclass
class Candidate:
    title: str
    authors: list = field(default_factory=list)
    year: int = None
    venue: str = ""
    doi: str = None
    paths: list = field(default_factory=list)
    # None means "no engine reported a count", which is not the same as zero.
    # arXiv and DBLP never report one; scoring their silence as zero demotes
    # recent parallel work.
    cited_by_count: int = None
    # Reference ids, when the engine supplies them. Used for bibliographic
    # coupling in field-map mode; empty means "unknown", not "cites nothing".
    referenced: set = field(default_factory=set)


def _work_to_dict(w):
    loc = (w.get("primary_location") or {}).get("source") or {}
    return {
        "id": w.get("id"),
        "title": w.get("title") or w.get("display_name"),
        "year": w.get("publication_year"),
        "cited_by_count": w.get("cited_by_count") or 0,
        "doi": (w.get("doi") or "").replace("https://doi.org/", "") or None,
        "venue": loc.get("display_name", ""),
        "authors": [a["author"]["display_name"]
                    for a in (w.get("authorships") or [])
                    if a.get("author", {}).get("display_name")],
    }


def _resolve_work(title):
    """Find the OpenAlex work whose title matches; None when it does not."""
    d = get_json(f"{_OA}?per-page=1{_mailto_param()}&select={_FIELDS},authorships"
                 f"&filter=title.search:{urllib.parse.quote(title)}")
    results = (d or {}).get("results") or []
    if not results:
        return None
    w = _work_to_dict(results[0])
    # Identity before use: OpenAlex answers title searches with near misses.
    if norm_title(w["title"] or "") != norm_title(title):
        return None
    return w


def _fetch_ids(ids, limit):
    """Batch-fetch works by OpenAlex id (their filter ORs on |)."""
    out = []
    ids = [i.rsplit("/", 1)[-1] for i in ids if i][:limit]
    for i in range(0, len(ids), 25):
        chunk = "|".join(ids[i:i + 25])
        d = get_json(f"{_OA}?per-page=25{_mailto_param()}"
                     f"&select={_FIELDS},authorships&filter=openalex_id:{chunk}")
        out.extend(_work_to_dict(w) for w in (d or {}).get("results") or [])
    return out


def _oa_refs(title, limit):
    w = _resolve_work(title)
    if not w:
        return []
    d = get_json(f"{_OA}/{w['id'].rsplit('/', 1)[-1]}{_mailto_param('?')}"
                 f"&select=referenced_works")
    return _fetch_ids((d or {}).get("referenced_works") or [], limit)


def _oa_citers(title, limit):
    w = _resolve_work(title)
    if not w:
        return []
    d = get_json(f"{_OA}?per-page={min(limit, 50)}{_mailto_param()}"
                 f"&select={_FIELDS},authorships"
                 f"&sort=cited_by_count:desc"
                 f"&filter=cites:{w['id'].rsplit('/', 1)[-1]}")
    return [_work_to_dict(x) for x in (d or {}).get("results") or []]


def _oa_related(title, limit):
    w = _resolve_work(title)
    if not w:
        return []
    d = get_json(f"{_OA}/{w['id'].rsplit('/', 1)[-1]}{_mailto_param('?')}"
                 f"&select=related_works")
    return _fetch_ids((d or {}).get("related_works") or [], limit)


# ---------------------------------------------------------------- Semantic Scholar
# Fallback so a single index being rate-limited cannot empty the whole sweep.

_S2 = "https://api.semanticscholar.org/graph/v1"
_S2_FIELDS = "title,year,venue,citationCount,externalIds,authors"


def _s2_headers():
    key = s2_api_key()
    return {"x-api-key": key} if key else None


def _s2_papers(payload, wrapper=None):
    """Map an S2 response to the same dict shape the OpenAlex path produces."""
    rows = (payload or {}).get("data") or (payload or {}).get("recommendedPapers") or []
    out = []
    for row in rows:
        p = row.get(wrapper) if wrapper and isinstance(row, dict) else row
        if not p or not p.get("title"):
            continue
        ext = p.get("externalIds") or {}
        out.append({
            "id": p.get("paperId"),
            "title": p.get("title"),
            "year": p.get("year"),
            "cited_by_count": p.get("citationCount") or 0,
            "doi": ext.get("DOI"),
            "venue": p.get("venue") or "",
            "authors": [a.get("name") for a in (p.get("authors") or []) if a.get("name")],
        })
    return out


def _s2_resolve(title):
    d = get_json(f"{_S2}/paper/search/match?fields=title&query="
                 + urllib.parse.quote(title), _s2_headers())
    data = (d or {}).get("data") or []
    if not data:
        return None
    if norm_title(data[0].get("title") or "") != norm_title(title):
        return None                       # identity before use, as everywhere
    return data[0].get("paperId")


def _s2_refs(title, limit):
    pid = _s2_resolve(title)
    if not pid:
        return []
    d = get_json(f"{_S2}/paper/{pid}/references?limit={min(limit, 100)}"
                 f"&fields={_S2_FIELDS}", _s2_headers())
    return _s2_papers(d, "citedPaper")


def _s2_citers(title, limit):
    pid = _s2_resolve(title)
    if not pid:
        return []
    d = get_json(f"{_S2}/paper/{pid}/citations?limit={min(limit, 100)}"
                 f"&fields={_S2_FIELDS}", _s2_headers())
    return _s2_papers(d, "citingPaper")


def _s2_related(title, limit):
    pid = _s2_resolve(title)
    if not pid:
        return []
    d = get_json(f"https://api.semanticscholar.org/recommendations/v1/papers/"
                 f"forpaper/{pid}?limit={min(limit, 100)}&fields={_S2_FIELDS}",
                 _s2_headers())
    return _s2_papers(d)


def _oa_search(query, limit):
    d = get_json(f"{_OA}?per-page={min(limit, 50)}{_mailto_param()}"
                 f"&select={_FIELDS},authorships&sort=relevance_score:desc"
                 f"&search={urllib.parse.quote(query)}")
    return [_work_to_dict(w) for w in (d or {}).get("results") or []]


def _s2_search(query, limit):
    d = get_json(f"{_S2}/paper/search?limit={min(limit, 100)}&fields={_S2_FIELDS}"
                 f"&query={urllib.parse.quote(query)}", _s2_headers())
    return _s2_papers(d)


# Source order. Semantic Scholar leads because OpenAlex moved to a paid budget:
# each search or filter query costs $0.001 against a small daily allowance, and
# once it is spent every request 429s until midnight UTC. An API key gives S2
# 1 req/s with no budget, so it is the dependable spine; OpenAlex remains a
# genuinely useful second opinion while budget lasts.
# ------------------------------------------------------------------ arXiv search
def _parse_arxiv_atom(data):
    ns = {"a": "http://www.w3.org/2005/Atom"}
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return []
    out = []
    for e in root.findall("a:entry", ns):
        title = " ".join((e.findtext("a:title", "", ns) or "").split())
        if not title:
            continue
        pub = (e.findtext("a:published", "", ns) or "")[:4]
        out.append({
            "id": e.findtext("a:id", "", ns),
            "title": title,
            "year": int(pub) if pub.isdigit() else None,
            "cited_by_count": None,       # arXiv publishes no citation counts
            "doi": None,
            "venue": "arXiv",
            "authors": [a.findtext("a:name", "", ns)
                        for a in e.findall("a:author", ns)],
        })
    return out


def _arxiv_search(query, limit):
    data = get_bytes("http://export.arxiv.org/api/query?sortBy=relevance"
                     f"&max_results={min(limit, 50)}&search_query="
                     + urllib.parse.quote(f'all:"{query}"'))
    return _parse_arxiv_atom(data) if data else []


# --------------------------------------------------------------- Crossref search
def _crossref_to_dicts(payload):
    items = ((payload or {}).get("message") or {}).get("items") or []
    out = []
    for m in items:
        title = (m.get("title") or [""])[0]
        if not title:
            continue
        dp = (m.get("issued") or {}).get("date-parts") or [[]]
        year = dp[0][0] if dp and dp[0] else None
        ct = m.get("container-title") or [""]
        out.append({
            "id": m.get("DOI"),
            "title": title,
            "year": year,
            "cited_by_count": m.get("is-referenced-by-count") or 0,
            "doi": m.get("DOI"),
            "venue": ct[0] if ct else "",
            "authors": [" ".join(x for x in [a.get("given"), a.get("family")] if x)
                        for a in m.get("author", [])],
        })
    return out


def _crossref_search(query, limit):
    d = get_json(f"https://api.crossref.org/works?rows={min(limit, 50)}"
                 f"{_mailto_param()}&select=title,author,issued,container-title,DOI,"
                 f"is-referenced-by-count"
                 f"&query.bibliographic={urllib.parse.quote(query)}")
    return _crossref_to_dicts(d)


# ------------------------------------------------------------------ DBLP search
def _dblp_search(query, limit):
    d = get_json(f"https://dblp.org/search/publ/api?format=json&h={min(limit, 50)}"
                 f"&q={urllib.parse.quote(query)}")
    try:
        hits = d["result"]["hits"].get("hit", [])
    except (TypeError, KeyError):
        return []
    out = []
    for h in hits:
        rec = _dblp_to_record(h)
        if not rec.title:
            continue
        out.append({"id": rec.doi, "title": rec.title, "year": rec.year,
                    "cited_by_count": None,  # DBLP reports no counts
                    "doi": rec.doi, "venue": rec.venue,
                    "authors": rec.authors})
    return out


# Keyword lookup is a search problem. S2 and OpenAlex are citation-graph APIs
# whose relevance ranking is idiosyncratic -- OpenAlex puts Chat2VIS fifth for
# "natural language visualization" while S2 does not return it in twenty. arXiv,
# Crossref and DBLP are different retrieval systems with different recall, and
# querying all of them is how a topically central paper stops slipping through.
_TOPICAL_ENGINES = [
    ("s2", lambda q, n: _s2_search(q, n)),
    ("openalex", lambda q, n: _oa_search(q, n)),
    ("arxiv", lambda q, n: _arxiv_search(q, n)),
    ("crossref", lambda q, n: _crossref_search(q, n)),
    ("dblp", lambda q, n: _dblp_search(q, n)),
]


def _lookup_topical(query, limit):
    """Union every engine. One being down or rate-limited must not blind the rest."""
    out, seen = [], set()
    for name, fn in _TOPICAL_ENGINES:
        try:
            results = fn(query, limit) or []
        except Exception:
            continue
        for r in results:
            key = norm_title(r.get("title") or "")
            if key and key not in seen:
                seen.add(key)
                out.append(r)
    return out


def _lookup_refs(title, limit):
    return _s2_refs(title, limit) or _oa_refs(title, limit)


def _lookup_citers(title, limit):
    return _s2_citers(title, limit) or _oa_citers(title, limit)


def _lookup_related(title, limit):
    return _s2_related(title, limit) or _oa_related(title, limit)


def _add(store, rec, path, cited_norm):
    title = (rec.get("title") or "").strip()
    if not title:
        return
    key = norm_title(title)
    if not key or key in cited_norm:
        return                                  # the draft already cites it
    c = store.get(key)
    if c is None:
        c = Candidate(title=title, authors=rec.get("authors") or [],
                      year=rec.get("year"), venue=rec.get("venue") or "",
                      doi=rec.get("doi"),
                      cited_by_count=rec.get("cited_by_count"),
                      referenced=set(rec.get("referenced") or ()))
        store[key] = c
    else:
        # A later engine may know a count the first one did not.
        incoming = rec.get("cited_by_count")
        if incoming is not None:
            c.cited_by_count = (incoming if c.cited_by_count is None
                                else max(c.cited_by_count, incoming))
        c.referenced |= set(rec.get("referenced") or ())
    if path not in c.paths:
        c.paths.append(path)


# Seed titles no index could resolve. Anonymous artifacts, blog posts and
# workshop papers legitimately land here; a long list means the sweep explored
# far less of the graph than the bibliography size suggests, and the report must
# say so rather than implying full coverage.
UNRESOLVED_SEEDS = []


_IDEAL_ANGLE_WORDS = 3
# Two phrases this similar are the same concept, not two queries.
_CONCEPT_OVERLAP = 0.5


def _pick_angles(angles, limit):
    """One query per concept, plus a broader variant of each.

    Three constraints learned the hard way:

    * Longest-first is wrong. "natural language visualization code" returns
      almost nothing where the 3-word form puts Chat2VIS in the top five.
    * Closest-to-three alone is wrong too: every slot fills with 3-grams and the
      sweep never asks a broader question. LLM4Vis is titled "Explainable
      Visualization *Recommendation*" -- a draft saying "explainable
      visualization authoring" reaches it only via "explainable visualization".
    * Overlapping slices of one sentence are not twelve queries. "execution
      verified", "execution verified multiagent" and "execution verified
      multiagent pipelines" all ask the same thing.

    So: pick distinct concepts first, nearest to three words, skipping any
    phrase that is a subset or superset of one already chosen. Then spend the
    remaining budget broadening each concept to its two-word prefix.
    """
    unique = list(dict.fromkeys(a for a in angles if a.split()))
    order = {a: i for i, a in enumerate(unique)}
    ranked = sorted(unique,
                    key=lambda a: (abs(len(a.split()) - _IDEAL_ANGLE_WORDS),
                                   order[a]))

    # Reserve part of the budget for broadening, or primaries eat it all and the
    # sweep only ever asks narrow questions.
    primary_limit = max(1, (limit * 2) // 3)
    picked, picked_sets = [], []
    for a in ranked:
        if len(picked) >= primary_limit:
            break
        words = set(a.split())
        # Sliding windows over one sentence overlap heavily without either
        # containing the other ("execution verified multiagent" vs "verified
        # multiagent pipelines"), so compare by Jaccard, not by subset.
        if any(len(words & s) / len(words | s) >= _CONCEPT_OVERLAP
               for s in picked_sets):
            continue            # same concept, said slightly differently
        picked.append(a)
        picked_sets.append(words)

    # Broaden: a two-word prefix of each concept, which is what reaches papers
    # whose vocabulary differs in the third word.
    for a in list(picked):
        if len(picked) >= limit:
            break
        parts = a.split()
        if len(parts) < 3:
            continue
        broader = " ".join(parts[:2])
        if broader not in picked:
            picked.append(broader)
    return picked[:limit]


def expand(seed, max_per_seed=25, max_angles=8):
    """Return {normalised title: Candidate} for everything the draft misses.

    Two complementary strategies. Citation-graph traversal finds intellectual
    ancestors and descendants of what the draft cites. Topical search on the
    contribution angles finds *parallel* work, which the graph cannot reach when
    the related-work section is thin -- and a thin related-work section is
    exactly the defect being looked for.
    """
    cited_norm = {norm_title(t) for t in seed.cited_titles}
    store = {}
    UNRESOLVED_SEEDS.clear()

    for title in seed.cited_titles:
        found = 0
        for fn, label in ((_lookup_refs, "backward"),
                          (_lookup_citers, "forward"),
                          (_lookup_related, "related")):
            for rec in fn(title, max_per_seed) or []:
                found += 1
                _add(store, rec, f"{label}:{title}", cited_norm)
        if found == 0:
            UNRESOLVED_SEEDS.append(title)

    for angle in _pick_angles(list(seed.angles or []), max_angles):
        for rec in _lookup_topical(angle, max_per_seed) or []:
            _add(store, rec, f"topical:{angle}", cited_norm)

    return store
