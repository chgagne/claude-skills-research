#!/usr/bin/env python3
"""arXiv / DBLP / Crossref helpers for related-work audits (stdlib only).

  sources.py arxiv QUERY... --work W [--sort relevance|submittedDate] [--limit 50]
        plain words are ANDed over all fields; "quoted phrases" kept; raw arXiv syntax
        (ti:, abs:, au:, AND/OR/ANDNOT) is passed through unchanged
  sources.py dblp QUERY... --work W [--limit 100]
        DBLP search API (title words, prefix match; falls back to the SPARQL endpoint)
  sources.py dblp-sparql WORD... --work W       titles containing ALL words (SPARQL endpoint)
  sources.py dblp-sparql --file q.rq            run your own SPARQL query, print TSV
  sources.py crossref QUERY... --work W [--from-year 2015]   journals/books outside CS
  sources.py published "Exact title"            is there a peer-reviewed version? (DBLP+Crossref+S2)
  sources.py bibtex ID... [--out missing.bib]   ID = DBLP:key | DOI:x | ARXIV:x | S2 paperId
"""
import argparse
import os
import re
import shlex
import sys
import urllib.parse
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from litlib import (PREPRINT_VENUE_RE, HTTPFailure, append_jsonl, clean_doi, fetch,  # noqa: E402
                    find_arxiv_id, info, log_query, make_rec, print_brief, title_sim, warn,
                    work_file)

ARXIV_API = "https://export.arxiv.org/api/query"
DBLP_API = "https://dblp.org/search/publ/api"
SPARQL = "https://sparql.dblp.org/sparql"
CROSSREF = "https://api.crossref.org/works"
NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
STOP = set("a an the of for and or in on to with by from at as is are via using towards toward "
           "into over under based its their our we new".split())


def emit(recs, a, source, query):
    if a.work:
        append_jsonl(work_file(a.work, "pool.jsonl"), recs)
        log_query(a.work, source, query, len(recs))
    print_brief(recs, a.show)
    info(f"{len(recs)} papers" + (" appended to pool" if a.work else " (not saved: no --work)"))


# ---------------------------------------------------------------- arXiv

def arxiv_query_string(q):
    if re.search(r"\b(ti|abs|au|all|cat|co|jr|id):", q):
        return q
    try:
        toks = shlex.split(q)
    except ValueError:
        toks = q.split()
    out = []
    for t in toks:
        if t.upper() in ("AND", "OR", "ANDNOT"):
            out.append(t.upper())
            continue
        if out and out[-1] not in ("AND", "OR", "ANDNOT"):
            out.append("AND")
        out.append(f'all:"{t}"' if " " in t else f"all:{t}")
    return " ".join(out)


def arxiv_search(q, limit=50, sort="relevance"):
    text = fetch(ARXIV_API, params={"search_query": arxiv_query_string(q), "start": 0,
                                    "max_results": limit, "sortBy": sort, "sortOrder": "descending"},
                 raw=True, min_interval=3.1, timeout=90)
    if not text:
        return []
    root = ET.fromstring(text)
    recs = []
    for i, e in enumerate(root.findall("a:entry", NS)):
        idurl = e.findtext("a:id", "", NS)
        if "api/errors" in idurl:
            warn(f"arXiv query error: {e.findtext('a:summary', '', NS)}")
            continue
        aid = re.sub(r"v\d+$", "", idurl.rsplit("/abs/", 1)[-1])
        pub = e.findtext("a:published", "", NS) or ""
        recs.append(make_rec(
            "arxiv", f"arxiv:{q}", rank=i + 1,
            title=" ".join(e.findtext("a:title", "", NS).split()),
            abstract=" ".join(e.findtext("a:summary", "", NS).split()),
            year=int(pub[:4]) if pub[:4].isdigit() else None, publicationDate=pub[:10] or None,
            venue=e.findtext("arxiv:journal_ref", None, NS) or "arXiv",
            externalIds={"ArXiv": aid, "DOI": clean_doi(e.findtext("arxiv:doi", None, NS))},
            authors=[x.findtext("a:name", "", NS) for x in e.findall("a:author", NS)]))
    return recs


def cmd_arxiv(a):
    q = " ".join(a.query)
    emit(arxiv_search(q, a.limit, a.sort), a, "arxiv", q)


# ---------------------------------------------------------------- DBLP

def dblp_api(q, limit=100):
    r = fetch(DBLP_API, params={"q": q, "format": "json", "h": min(limit, 1000)}, min_interval=1.5)
    hits = ((((r or {}).get("result") or {}).get("hits") or {}).get("hit")) or []
    recs = []
    for i, h in enumerate(hits):
        inf = h.get("info") or {}
        au = (inf.get("authors") or {}).get("author") or []
        au = [au] if isinstance(au, dict) else au
        names = [re.sub(r"\s+\d{4}$", "", x.get("text", "") if isinstance(x, dict) else str(x)) for x in au]
        ee = inf.get("ee")
        ee = " ".join(ee) if isinstance(ee, list) else (ee or "")
        venue = inf.get("venue")
        venue = ", ".join(venue) if isinstance(venue, list) else venue
        yr = str(inf.get("year", ""))
        recs.append(make_rec(
            "dblp", f"dblp:{q}", rank=i + 1, title=(inf.get("title") or "").rstrip("."),
            year=int(yr) if yr.isdigit() else None, venue=venue,
            publicationTypes=[inf["type"]] if inf.get("type") else None,
            externalIds={"DBLP": inf.get("key"), "DOI": clean_doi(inf.get("doi")),
                         "ArXiv": find_arxiv_id(ee)},
            authors=[n for n in names if n]))
    return recs


def sparql(query):
    r = fetch(SPARQL, params={"query": query}, accept="application/sparql-results+json",
              min_interval=1.0, timeout=180)
    return ((r or {}).get("results") or {}).get("bindings") or []


def sparql_title_query(words, limit, with_authors):
    flt = " && ".join('CONTAINS(LCASE(STR(?title)), "%s")' % w.replace('"', "").lower() for w in words)
    if with_authors:
        return f"""PREFIX dblp: <https://dblp.org/rdf/schema#>
SELECT ?pub ?title (SAMPLE(?y) AS ?year) (SAMPLE(?v) AS ?venue) (SAMPLE(?d) AS ?doi)
       (GROUP_CONCAT(DISTINCT ?name; SEPARATOR="|") AS ?authors) WHERE {{
  ?pub dblp:title ?title .
  FILTER({flt})
  OPTIONAL {{ ?pub dblp:yearOfPublication ?y }}
  OPTIONAL {{ ?pub dblp:publishedIn ?v }}
  OPTIONAL {{ ?pub dblp:doi ?d }}
  OPTIONAL {{ ?pub dblp:authoredBy ?a . ?a dblp:primaryCreatorName ?name }}
}} GROUP BY ?pub ?title LIMIT {limit}"""
    return f"""PREFIX dblp: <https://dblp.org/rdf/schema#>
SELECT ?pub ?title ?year ?venue WHERE {{
  ?pub dblp:title ?title .
  FILTER({flt})
  OPTIONAL {{ ?pub dblp:yearOfPublication ?year }}
  OPTIONAL {{ ?pub dblp:publishedIn ?venue }}
}} LIMIT {limit}"""


def dblp_sparql_titles(words, limit=200):
    try:
        rows = sparql(sparql_title_query(words, limit, True))
    except HTTPFailure as e:
        warn(f"SPARQL with authors failed ({e}); retrying simpler query")
        rows = sparql(sparql_title_query(words, limit, False))
    recs = []
    for i, b in enumerate(rows):
        v = {k: x.get("value") for k, x in b.items()}
        pub = v.get("pub", "")
        key = pub.split("/rec/", 1)[1] if "/rec/" in pub else None
        yr = (v.get("year") or "")[:4]
        recs.append(make_rec(
            "dblp", "dblp-sparql:" + " ".join(words), rank=i + 1, title=(v.get("title") or "").rstrip("."),
            year=int(yr) if yr.isdigit() else None, venue=v.get("venue"),
            externalIds={"DBLP": key, "DOI": clean_doi(v.get("doi"))},
            authors=[n for n in (v.get("authors") or "").split("|") if n]))
    return recs


def sig_words(q, n=5):
    ws = [w for w in re.findall(r"[A-Za-z0-9\-]+", q) if w.lower() not in STOP and len(w) > 2]
    return sorted(ws, key=len, reverse=True)[:n]


def cmd_dblp(a):
    q = " ".join(a.query)
    try:
        recs = dblp_api(q, a.limit)
    except HTTPFailure as e:
        warn(f"DBLP search API failed ({e}); using SPARQL title search")
        recs = dblp_sparql_titles(sig_words(q), a.limit)
    emit(recs, a, "dblp", q)


def cmd_dblp_sparql(a):
    if a.file:
        with open(a.file) as f:
            rows = sparql(f.read())
        if rows:
            cols = list(rows[0].keys())
            print("\t".join(cols))
            for b in rows:
                print("\t".join((b.get(c) or {}).get("value", "") for c in cols))
        info(f"{len(rows)} rows")
        return
    if not a.words:
        sys.exit("give title words or --file")
    emit(dblp_sparql_titles(a.words, a.limit), a, "dblp-sparql", " ".join(a.words))


# ---------------------------------------------------------------- Crossref

def crossref_search(q, rows=40, from_year=None):
    params = {"query.bibliographic": q, "rows": rows,
              "select": "DOI,title,author,issued,container-title,type,abstract,is-referenced-by-count"}
    if from_year:
        params["filter"] = f"from-pub-date:{from_year}"
    if os.environ.get("CROSSREF_MAILTO"):
        params["mailto"] = os.environ["CROSSREF_MAILTO"]
    r = fetch(CROSSREF, params=params, min_interval=1.0)
    items = (((r or {}).get("message") or {}).get("items")) or []
    recs = []
    for i, it in enumerate(items):
        dp = ((it.get("issued") or {}).get("date-parts") or [[None]])[0]
        abstract = re.sub(r"<[^>]+>", " ", it.get("abstract") or "")
        recs.append(make_rec(
            "crossref", f"crossref:{q}", rank=i + 1, title=" ".join((it.get("title") or [""])[0].split()),
            abstract=" ".join(abstract.split()) or None, year=dp[0] if dp else None,
            venue=(it.get("container-title") or [None])[0], citationCount=it.get("is-referenced-by-count"),
            publicationTypes=[it["type"]] if it.get("type") else None, externalIds={"DOI": it.get("DOI")},
            authors=[f"{x.get('given', '')} {x.get('family', '')}".strip() for x in it.get("author") or []]))
    return recs


def cmd_crossref(a):
    q = " ".join(a.query)
    emit(crossref_search(q, a.limit, a.from_year), a, "crossref", q)


# ---------------------------------------------------------------- published version / bibtex

def cmd_published(a):
    title = " ".join(a.title)
    hits = []
    try:
        hits += dblp_api(title, 30)
    except HTTPFailure as e:
        warn(f"DBLP API: {e}; trying SPARQL")
        try:
            hits += dblp_sparql_titles(sig_words(title, 4), 50)
        except HTTPFailure as e2:
            warn(f"DBLP SPARQL: {e2}")
    try:
        hits += crossref_search(title, 10)
    except HTTPFailure as e:
        warn(f"Crossref: {e}")
    try:
        import s2 as S2
        p, sim = S2.match_title(title)
        if p:
            hits.append(S2.to_rec(p, "s2", "match"))
    except HTTPFailure as e:
        warn(f"S2: {e}")
    good = [h for h in hits if h and title_sim(title, h.get("title")) >= 0.9]
    if not good:
        print("No version with a matching title found.")
        return
    published = []
    for h in good:
        ven = h.get("venue") or "?"
        pre = bool(PREPRINT_VENUE_RE.search(ven)) or ven == "?"
        if not pre:
            published.append(h)
        ids = " ".join(f"{k}:{v}" for k, v in (h.get("externalIds") or {}).items())
        print(f"[{h['_kind']}] {'preprint ' if pre else 'PUBLISHED'} {h.get('year')} | {ven} | "
              f"{h.get('publicationTypes') or ''} | {ids}")
    print("\nVerdict: " + ("peer-reviewed version exists - cite it (prefer its DBLP/DOI bibtex)"
                           if published else "only preprint versions found"))


def bibtex_from_meta(p):
    authors = [x.get("name") if isinstance(x, dict) else x for x in p.get("authors") or []]
    last = re.sub(r"[^A-Za-z]", "", authors[0].split()[-1] if authors else "anon").lower()
    first = next((w for w in re.findall(r"[A-Za-z]+", p.get("title") or "")
                  if w.lower() not in STOP), "paper").lower()
    venue = p.get("venue") or ""
    ext = p.get("externalIds") or {}
    types = p.get("publicationTypes") or []
    if "Conference" in types:
        typ, vf = "inproceedings", "booktitle"
    elif venue and not PREPRINT_VENUE_RE.search(venue):
        typ, vf = "article", "journal"
    else:
        typ, vf = "misc", "howpublished"
        venue = f"arXiv preprint arXiv:{ext['ArXiv']}" if ext.get("ArXiv") else venue
    fields = [("title", p.get("title")), ("author", " and ".join(authors)), ("year", p.get("year")),
              (vf, venue), ("doi", ext.get("DOI")), ("eprint", ext.get("ArXiv")),
              ("archivePrefix", "arXiv" if ext.get("ArXiv") else None)]
    body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields if v)
    return f"@{typ}{{{last}{p.get('year') or ''}{first},\n{body}\n}}\n"


def bibtex_for(ident):
    kind, _, val = ident.partition(":")
    kind = kind.upper()
    if kind == "DBLP":
        return fetch(f"https://dblp.org/rec/{val}.bib", raw=True, min_interval=1.0)
    if kind == "DOI":
        try:
            b = fetch(f"{CROSSREF}/{urllib.parse.quote(val, safe='/')}/transform/application/x-bibtex",
                      raw=True, min_interval=1.0)
            if b and b.strip().startswith("@"):
                return b
        except HTTPFailure:
            pass
        b = fetch(f"https://doi.org/{val}", accept="application/x-bibtex", raw=True, min_interval=1.0)
        return b if b and b.strip().startswith("@") else None
    if kind == "ARXIV":
        return bibtex_for(f"DOI:10.48550/arXiv.{val}")
    import s2 as S2  # S2 paperId (or any S2-style id): pick the best route from its external ids
    p = S2.batch([ident], S2.FIELDS)[0]
    if not p:
        return None
    ext = p.get("externalIds") or {}
    if ext.get("DBLP") and not str(ext["DBLP"]).startswith("journals/corr/"):
        b = bibtex_for("DBLP:" + ext["DBLP"])
        if b:
            return b
    if ext.get("DOI") and not str(ext["DOI"]).lower().startswith("10.48550"):
        b = bibtex_for("DOI:" + ext["DOI"])
        if b:
            return b
    return bibtex_from_meta(S2.to_rec(p, "bib", ""))


def cmd_bibtex(a):
    out = []
    for ident in a.ids:
        try:
            b = bibtex_for(ident)
        except HTTPFailure as e:
            warn(f"{ident}: {e}")
            b = None
        if not b:
            warn(f"no BibTeX for {ident}")
            continue
        out.append(f"% source id: {ident}\n{b.strip()}\n")
    text = "\n".join(out)
    print(text)
    if a.out and text:
        with open(a.out, "a", encoding="utf-8") as f:
            f.write(text + "\n")
        info(f"appended {len(out)} entries to {a.out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, limit):
        p = sub.add_parser(name)
        p.add_argument("--work")
        p.add_argument("--show", type=int, default=20)
        p.add_argument("--limit", type=int, default=limit)
        return p

    p = add("arxiv", 50)
    p.add_argument("query", nargs="+")
    p.add_argument("--sort", default="relevance", choices=["relevance", "submittedDate", "lastUpdatedDate"])
    p.set_defaults(fn=cmd_arxiv)
    p = add("dblp", 100)
    p.add_argument("query", nargs="+")
    p.set_defaults(fn=cmd_dblp)
    p = add("dblp-sparql", 200)
    p.add_argument("words", nargs="*")
    p.add_argument("--file")
    p.set_defaults(fn=cmd_dblp_sparql)
    p = add("crossref", 40)
    p.add_argument("query", nargs="+")
    p.add_argument("--from-year")
    p.set_defaults(fn=cmd_crossref)
    p = sub.add_parser("published")
    p.add_argument("title", nargs="+")
    p.set_defaults(fn=cmd_published)
    p = sub.add_parser("bibtex")
    p.add_argument("ids", nargs="+")
    p.add_argument("--out", help="append to this .bib file")
    p.set_defaults(fn=cmd_bibtex)

    a = ap.parse_args()
    try:
        a.fn(a)
    except HTTPFailure as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
