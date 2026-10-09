#!/usr/bin/env python3
"""Semantic Scholar helper for related-work audits (stdlib only).

Key: $S2_API_KEY or ~/.config/scholarly/s2_key. Requests are throttled to ~1/s (keyed limit)
and retried on 429/5xx. With --work W, returned papers are appended to W/pool.jsonl, tagged
with how they were found; searches are also logged to W/queries.tsv.

  s2.py resolve-bib --work W [--set KEY=ID ...]   map .bib entries to S2 papers -> W/cited.jsonl
  s2.py search QUERY... --work W [--year 2015-] [--bulk [--sort citationCount:desc]]
  s2.py refs  [IDS...] [--keys k1,k2] [--all-cited] --work W    references of seeds
  s2.py cites [IDS...] [--keys k1,k2] --work W [--skip-over 3000]  papers citing seeds
  s2.py recommend [IDS...] [--keys k1,k2] [--neg IDS] --work W
  s2.py author-search "First Last"                disambiguate (prints ids + sample papers)
  s2.py author-papers AUTHOR_ID... --work W
  s2.py match "Exact title"... [--work W --tag web]  verify a paper you heard of; adds it
  s2.py paper ID...                               full record: abstract, tldr, ids, OA pdf

IDs: S2 paperId, DOI:10.x/y, ARXIV:2101.00001, CorpusId:123, DBLP:conf/x/Y20, ACL:..., URL:...
"""
import argparse
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from litlib import (HTTPFailure, append_jsonl, fetch, info, load_json, log_query,  # noqa: E402
                    make_rec, print_brief, read_jsonl, short_authors, title_sim, warn,
                    work_file, write_jsonl)

GRAPH = "https://api.semanticscholar.org/graph/v1"
RECS = "https://api.semanticscholar.org/recommendations/v1"
FIELDS = ("paperId,externalIds,title,abstract,year,venue,publicationVenue,authors,"
          "citationCount,publicationTypes,publicationDate")
DETAIL_FIELDS = FIELDS + ",tldr,referenceCount,url,openAccessPdf"
KEY_FILE = os.path.expanduser("~/.config/scholarly/s2_key")
_key = None


def api_key():
    global _key
    if _key is None:
        _key = os.environ.get("S2_API_KEY", "").strip()
        if not _key:
            try:
                with open(KEY_FILE) as f:
                    _key = f.read().strip()
            except OSError:
                warn(f"no S2 API key ({KEY_FILE}); unauthenticated calls are slow and often 429")
    return _key


def s2(path, params=None, body=None, base=GRAPH):
    key = api_key()
    interval = float(os.environ.get("S2_MIN_INTERVAL", "1.05" if key else "3.5"))
    return fetch(base + path, params=params, body=body,
                 headers={"x-api-key": key} if key else None,
                 min_interval=interval, retries=7)


def qid(pid):
    return urllib.parse.quote(pid, safe=":/")


def to_rec(p, kind, tag, seed=None, rank=None):
    if not p or not (p.get("paperId") or p.get("title")):
        return None
    venue = p.get("venue") or (p.get("publicationVenue") or {}).get("name")
    return make_rec(kind, tag, seed=seed, rank=rank, paperId=p.get("paperId"),
                    title=p.get("title"), abstract=p.get("abstract"), year=p.get("year"),
                    venue=venue, citationCount=p.get("citationCount"),
                    publicationTypes=p.get("publicationTypes"),
                    publicationDate=p.get("publicationDate"), externalIds=p.get("externalIds"),
                    authors=[a.get("name") for a in (p.get("authors") or []) if a.get("name")])


def emit(recs, args, source=None, query=None):
    recs = [r for r in recs if r]
    if args.work:
        append_jsonl(work_file(args.work, "pool.jsonl"), recs)
        if query is not None:
            log_query(args.work, source, query, len(recs))
    print_brief(recs, args.show)
    where = f" appended to {work_file(args.work, 'pool.jsonl')}" if args.work else " (not saved: no --work)"
    info(f"{len(recs)} papers{where}")


def batch(ids, fields=FIELDS):
    out = []
    for i in range(0, len(ids), 400):
        chunk = ids[i:i + 400]
        r = s2("/paper/batch", {"fields": fields}, body={"ids": chunk})
        out.extend(r if isinstance(r, list) else [None] * len(chunk))
    return out


def match_title(title):
    try:
        r = s2("/paper/search/match", {"query": title[:300], "fields": FIELDS})
    except HTTPFailure as e:
        if e.code == 400:
            return None, 0.0
        raise
    data = (r or {}).get("data") or []
    if not data:
        return None, 0.0
    return data[0], title_sim(title, data[0].get("title"))


def to_paper_id(i):
    if len(i) == 40 and ":" not in i:
        return i, None
    p = s2(f"/paper/{qid(i)}", {"fields": "paperId,title,citationCount"})
    if not p:
        warn(f"paper {i} not found on S2")
        return None, None
    return p["paperId"], p.get("citationCount")


def resolve_seeds(args):
    """-> list of (paperId, label, citationCount|None) from IDS, --keys and --all-cited."""
    seeds = []
    cited = read_jsonl(work_file(args.work, "cited.jsonl")) if args.work else []
    by_key = {c["key"]: c for c in cited}
    for k in [k.strip() for k in (getattr(args, "keys", None) or "").split(",") if k.strip()]:
        c = by_key.get(k)
        if not c:
            warn(f"bib key {k!r} not in cited.jsonl (run resolve-bib first?)")
        elif not c.get("paperId"):
            warn(f"bib key {k!r} is not resolved to an S2 paper (fix with resolve-bib --set)")
        else:
            seeds.append((c["paperId"], k, c.get("citationCount")))
    if getattr(args, "all_cited", False):
        seeds += [(c["paperId"], c["key"], c.get("citationCount"))
                  for c in cited if c.get("cited") and c.get("paperId")]
    for i in getattr(args, "ids", None) or []:
        pid, cc = to_paper_id(i)
        if pid:
            seeds.append((pid, i, cc))
    out, seen = [], set()
    for s in seeds:
        if s[0] not in seen:
            seen.add(s[0])
            out.append(s)
    return out


# ---------------------------------------------------------------- commands

def cmd_search(a):
    query = " ".join(a.query)
    papers = []
    if a.bulk:
        params = {"query": query, "fields": FIELDS, "year": a.year, "sort": a.sort,
                  "fieldsOfStudy": a.fos}
        while len(papers) < a.limit:
            r = s2("/paper/search/bulk", params) or {}
            data = r.get("data") or []
            papers.extend(data)
            if not r.get("token") or not data:
                break
            params["token"] = r["token"]
    else:
        off = 0
        while off < min(a.limit, 1000):
            lim = min(100, a.limit - off, 1000 - off)
            r = s2("/paper/search", {"query": query, "fields": FIELDS, "limit": lim,
                                     "offset": off, "year": a.year, "fieldsOfStudy": a.fos}) or {}
            data = r.get("data") or []
            papers.extend(data)
            if len(data) < lim:
                break
            off += lim
    papers = papers[:a.limit]
    src = "s2bulk" if a.bulk else "s2"
    recs = [to_rec(p, "search", f"{src}:{query}", rank=i + 1) for i, p in enumerate(papers)]
    emit(recs, a, source=src, query=query)


def edge_list(pid, which, maxn):
    field = "citedPaper" if which == "references" else "citingPaper"
    out, off = [], 0
    while off < maxn:
        lim = min(500, maxn - off)
        r = s2(f"/paper/{qid(pid)}/{which}", {"fields": FIELDS, "limit": lim, "offset": off})
        if not r:
            break
        data = r.get("data") or []
        out.extend(d[field] for d in data if d.get(field) and d[field].get("paperId"))
        if not data or r.get("next") is None:
            break
        off = r["next"]
    return out


def cmd_edges(a, which):
    kind = "refs" if which == "references" else "cites"
    seeds = resolve_seeds(a)
    if not seeds:
        sys.exit("no seeds: give S2 ids, --keys k1,k2 (bib keys from cited.jsonl) or --all-cited")
    total = []
    for pid, label, cc in seeds:
        if which == "citations":
            if cc is None:
                cc = (s2(f"/paper/{qid(pid)}", {"fields": "citationCount"}) or {}).get("citationCount")
            if cc and cc > a.skip_over and not a.force:
                warn(f"skip citations of {label}: {cc} > --skip-over {a.skip_over} "
                     "(too generic to be informative; --force to override)")
                continue
        recs = []
        for p in edge_list(pid, which, a.max):
            r = to_rec(p, kind, f"{kind}:{label}", seed=pid)
            if r:
                r["_seedLabel"] = label
                recs.append(r)
        info(f"{label}: {len(recs)} {which}")
        total.extend(recs)
    emit(total, a)


def cmd_recommend(a):
    seeds = resolve_seeds(a)
    pos = [s[0] for s in seeds]
    neg = [p for p in (to_paper_id(i)[0] for i in (a.neg or [])) if p]
    if not pos:
        sys.exit("no positive seeds")
    tag = "rec:" + (a.tag or ",".join(s[1] for s in seeds))[:120]
    body = {"positivePaperIds": pos, "negativePaperIds": neg}
    try:
        r = s2("/papers/", {"fields": FIELDS, "limit": a.limit}, body=body, base=RECS)
    except HTTPFailure as e:
        if e.code != 400:
            raise
        r = s2("/papers/", {"fields": "paperId,title,abstract,year,venue,authors,citationCount,externalIds",
                            "limit": a.limit}, body=body, base=RECS)
    papers = (r or {}).get("recommendedPapers") or []
    emit([to_rec(p, "rec", tag, rank=i + 1) for i, p in enumerate(papers)], a, source="s2rec", query=tag)


def cmd_author_search(a):
    name = " ".join(a.name)
    try:
        r = s2("/author/search", {"query": name, "limit": 10, "fields":
                                  "name,affiliations,paperCount,citationCount,hIndex,papers.title,papers.year"})
    except HTTPFailure:
        r = s2("/author/search", {"query": name, "limit": 10,
                                  "fields": "name,affiliations,paperCount,citationCount,hIndex"})
    for au in (r or {}).get("data") or []:
        print(f"{au.get('authorId')}  {au.get('name')}  | {', '.join(au.get('affiliations') or []) or '-'}"
              f" | papers {au.get('paperCount')} | h {au.get('hIndex')}")
        ps = sorted(au.get("papers") or [], key=lambda p: -(p.get("year") or 0))[:6]
        for p in ps:
            print(f"      [{p.get('year')}] {p.get('title')}")


def cmd_author_papers(a):
    total = []
    for aid in a.ids:
        off, n = 0, 0
        while off < a.max:
            r = s2(f"/author/{aid}/papers", {"fields": FIELDS, "limit": min(500, a.max - off), "offset": off})
            if not r:
                break
            data = r.get("data") or []
            total += [to_rec(p, "author", f"author:{a.label or aid}") for p in data]
            n += len(data)
            if not data or r.get("next") is None:
                break
            off = r["next"]
        info(f"author {aid}: {n} papers")
    emit(total, a)


def cmd_match(a):
    recs = []
    for t in a.titles:
        p, sim = match_title(t)
        if not p:
            print(f"NOT FOUND: {t}")
            continue
        ok = sim >= 0.85 or a.force
        print(f"{'OK  ' if ok else 'WEAK'} sim={sim:.2f}  [{p.get('year')}] {p.get('title')}  "
              f"({p.get('venue') or '?'}; {p.get('citationCount')} cites)  {p.get('paperId')}")
        if ok:
            recs.append(to_rec(p, "manual", f"manual:{a.tag}"))
    if a.work and recs:
        append_jsonl(work_file(a.work, "pool.jsonl"), [r for r in recs if r])
        info(f"{len(recs)} added to pool")


def cmd_paper(a):
    papers = batch(list(a.ids), DETAIL_FIELDS)
    if a.json:
        print(json.dumps(papers, indent=1, ensure_ascii=False))
        return
    for i, p in zip(a.ids, papers):
        if not p:
            print(f"== {i}: not found\n")
            continue
        ext = p.get("externalIds") or {}
        print(f"== {p.get('title')}")
        print(f"   {short_authors([x.get('name') for x in p.get('authors') or []], 8)}")
        print(f"   {p.get('year')} | {p.get('venue') or '?'} | types {p.get('publicationTypes')} | "
              f"date {p.get('publicationDate')} | cites {p.get('citationCount')} | refs {p.get('referenceCount')}")
        print(f"   S2 {p.get('paperId')} | " + " | ".join(f"{k} {v}" for k, v in ext.items()))
        if (p.get("openAccessPdf") or {}).get("url"):
            print(f"   PDF {p['openAccessPdf']['url']}")
        if (p.get("tldr") or {}).get("text"):
            print(f"   TLDR {p['tldr']['text']}")
        print(f"   ABSTRACT {p.get('abstract') or '(none on S2; try arXiv/WebFetch)'}\n")


def cmd_resolve_bib(a):
    draft = load_json(work_file(a.work, "draft.json"))
    entries = draft["bib"]
    by_key = {e["key"]: e for e in entries}
    found, how = {}, {}
    want = []
    for e in entries:
        if e.get("doi"):
            want.append((e["key"], "DOI:" + e["doi"], "doi"))
        if e.get("arxiv"):
            want.append((e["key"], "ARXIV:" + e["arxiv"], "arxiv"))
    for (key, _, method), p in zip(want, batch([w[1] for w in want]) if want else []):
        if p and key not in found:
            e = by_key[key]
            if e.get("title") and title_sim(e["title"], p.get("title")) < 0.5:
                warn(f"{key}: {method} gives a different-looking title {p.get('title')!r} "
                     f"(bib: {e['title']!r}); kept - verify")
            found[key], how[key] = p, method
    todo = [e for e in entries if e["key"] not in found and len(e.get("title") or "") > 8]
    info(f"title-matching {len(todo)} entries (~{len(todo)}s) ...")
    for e in todo:
        p, sim = match_title(e["title"])
        if p and sim >= 0.85:
            found[e["key"]], how[e["key"]] = p, f"title {sim:.2f}"
        elif p:
            how[e["key"]] = f"weak {sim:.2f}: {p.get('title')} [{p.get('paperId')}]"
    for spec in a.set or []:
        key, _, pid = spec.partition("=")
        if key not in by_key:
            warn(f"--set: no bib key {key!r}")
            continue
        p = batch([pid])[0]
        if p:
            found[key], how[key] = p, "manual"
        else:
            warn(f"--set: {pid} not found")

    out, weak, unresolved, hints = [], [], [], []
    for e in entries:
        k = e["key"]
        r = {"key": k, "cited": e.get("cited", False), "bib_title": e.get("title"),
             "bib_year": e.get("year"), "bib_venue": e.get("venue"), "method": how.get(k, "unresolved")}
        p = found.get(k)
        if p:
            rec = to_rec(p, "cited", "")
            r.update({x: rec.get(x) for x in ("paperId", "title", "year", "venue", "citationCount",
                                              "externalIds", "publicationTypes", "authors")})
            bv = (e.get("venue") or "").lower()
            if (("arxiv" in bv or "corr" in bv or (not bv and e.get("arxiv")))
                    and r.get("venue") and "arxiv" not in r["venue"].lower()):
                r["published_version_hint"] = r["venue"]
                hints.append(f"{k}: bib cites preprint; S2 venue is {r['venue']}")
        elif how.get(k, "").startswith("weak"):
            weak.append(f"{k}: bib '{e.get('title')}' ~ {how[k]}")
        else:
            unresolved.append(f"{k}: {e.get('title') or '(no title)'}")
        out.append(r)
    write_jsonl(work_file(a.work, "cited.jsonl"), out)
    n_cited = sum(1 for r in out if r["cited"])
    n_res = sum(1 for r in out if r["cited"] and r.get("paperId"))
    print(f"Resolved {sum(1 for r in out if r.get('paperId'))}/{len(out)} bib entries "
          f"({n_res}/{n_cited} of the cited ones) -> {work_file(a.work, 'cited.jsonl')}")
    if weak:
        print("\nWeak title matches (not accepted; use --set KEY=PAPERID if correct):")
        print("\n".join("  " + w for w in weak))
    if unresolved:
        print("\nUnresolved (books, web pages, or very new work are normal here):")
        print("\n".join("  " + u for u in unresolved))
    if hints:
        print("\nCited as preprint but apparently published (mention in report notes):")
        print("\n".join("  " + h for h in hints))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, show=0):
        p = sub.add_parser(name)
        p.add_argument("--work", help="audit work dir (results appended to WORK/pool.jsonl)")
        p.add_argument("--show", type=int, default=show, help="print first N results")
        return p

    p = add("search", 20)
    p.add_argument("query", nargs="+")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--year", help="e.g. 2015-  or 2018-2022")
    p.add_argument("--fos", help="fieldsOfStudy filter, e.g. 'Computer Science'")
    p.add_argument("--bulk", action="store_true",
                   help="bulk endpoint: boolean syntax (+ | - \"phrase\" prefix*), unranked unless --sort")
    p.add_argument("--sort", help="bulk only, e.g. citationCount:desc or publicationDate:desc")
    p.set_defaults(fn=cmd_search)

    for name, which in (("refs", "references"), ("cites", "citations")):
        p = add(name)
        p.add_argument("ids", nargs="*")
        p.add_argument("--keys", help="comma-separated bib keys (needs resolve-bib)")
        p.add_argument("--all-cited", action="store_true", help="every resolved cited entry")
        p.add_argument("--max", type=int, default=1000, help="max papers per seed")
        p.add_argument("--skip-over", type=int, default=3000,
                       help="cites: skip seeds with more citations than this")
        p.add_argument("--force", action="store_true")
        p.set_defaults(fn=lambda a, w=which: cmd_edges(a, w))

    p = add("recommend", 20)
    p.add_argument("ids", nargs="*")
    p.add_argument("--keys")
    p.add_argument("--neg", nargs="*", help="negative example ids")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--tag")
    p.set_defaults(fn=cmd_recommend)

    p = sub.add_parser("author-search")
    p.add_argument("name", nargs="+")
    p.set_defaults(fn=cmd_author_search)

    p = add("author-papers")
    p.add_argument("ids", nargs="+")
    p.add_argument("--label", help="readable tag, e.g. the author's name")
    p.add_argument("--max", type=int, default=1000)
    p.set_defaults(fn=cmd_author_papers)

    p = add("match")
    p.add_argument("titles", nargs="+")
    p.add_argument("--tag", default="memory/web")
    p.add_argument("--force", action="store_true", help="accept weak matches")
    p.set_defaults(fn=cmd_match)

    p = sub.add_parser("paper")
    p.add_argument("ids", nargs="+")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_paper)

    p = sub.add_parser("resolve-bib")
    p.add_argument("--work", required=True)
    p.add_argument("--set", action="append", metavar="KEY=ID", help="force a mapping (repeatable)")
    p.set_defaults(fn=cmd_resolve_bib)

    a = ap.parse_args()
    try:
        a.fn(a)
    except HTTPFailure as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
