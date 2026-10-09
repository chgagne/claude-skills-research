#!/usr/bin/env python3
"""Merge, de-duplicate, filter and rank the candidate pool of a related-work audit.

  pool.py rank --work W [--after 2026-05-15] [--md-top 150]
      W/pool.jsonl -> W/candidates.json + W/shortlist.md. Merges versions of the same paper
      (S2 id / DOI / arXiv id / DBLP key / title), drops papers the draft already cites (using
      W/cited.jsonl and the .bib, incl. fuzzy titles), flags .bib entries that are never \\cite'd,
      the draft itself, and (with --after) papers dated after the draft's cutoff.
  pool.py coupling --work W [--top 200]
      Fetches reference lists of the top-ranked candidates and measures bibliographic coupling
      with the draft's own citations (close prior work cites the same papers). Re-ranks.
  pool.py show --work W [--start 0] [--top 30] [--ids 3,17,PAPERID] [--status candidate]
      Prints candidates (signals, ids, abstract) for triage.

The score only orders reading; it is not a verdict. Signals in shortlist/show:
  q3#2      hit by 3 distinct queries (best rank 2)       refd-by4  in reference lists of 4 seeds
  cites5    cites 5 seed papers (forward citation hits)   rec       S2 recommendation
  auth      from an author's publication list             manual    added by hand (match)
  cpl9/40   9 of its 40 references are cited by the draft sim.31  TF-IDF similarity to draft
"""
import argparse
import math
import os
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from litlib import (PREPRINT_VENUE_RE, REC_FIELDS, identifiers, info, load_json,  # noqa: E402
                    norm_title, read_jsonl, short_authors, title_sim, warn, work_file, write_json)

SEARCH_KINDS = {"search", "arxiv", "dblp", "crossref", "manual"}
ACTIVE = ("candidate", "in-bib-uncited")
STOP = set("""a an the of for and or in on to with by from at as is are was were be been being this
that these those it its we our us their they them which who whom whose what when where how why can
could may might will would shall should do does did not no nor than then there here via using use
used based towards toward into onto over under between among within without about across after
before during through per vs versus et al also such both each more most other some only same so very
paper propose proposed proposes show shows shown present presents result results approach approaches
method methods work works study studies new novel problem problems task tasks model models data
existing however while thus well first two one three large small high low different further""".split())


# ---------------------------------------------------------------- similarity

def stem(w):
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("s") and not w.endswith(("ss", "us", "is")):
        return w[:-1]
    return w


def tokens(text):
    text = re.sub(r"\[(?:CITE|EQ)[^\]]*\]", " ", text or "")
    words = [stem(w) for w in re.findall(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", text.lower())
             if w not in STOP and len(w) > 2]
    return words + [x + "_" + y for x, y in zip(words, words[1:])]


def tfidf_sims(profile, docs):
    counts = [Counter(tokens(d)) for d in docs]
    pc = Counter(tokens(profile))
    df = Counter()
    for c in counts + [pc]:
        df.update(c.keys())
    n = len(counts) + 1

    def vec(c):
        v = {t: (1 + math.log(tf)) * (math.log((n + 1) / (df[t] + 1)) + 1) for t, tf in c.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    pv = vec(pc)
    return [sum(pv.get(t, 0.0) * x for t, x in vec(c).items()) for c in counts]


# ---------------------------------------------------------------- merging

def cluster(records):
    parent = list(range(len(records)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    first = {}
    for i, r in enumerate(records):
        for ident in identifiers(r):
            if ident in first:
                ra, rb = find(i), find(first[ident])
                if ra != rb:
                    parent[ra] = rb
            else:
                first[ident] = i
    groups = defaultdict(list)
    for i, r in enumerate(records):
        groups[find(i)].append(r)
    return list(groups.values())


def merge(group):
    s2recs = [r for r in group if r.get("paperId")]
    base = s2recs[0] if s2recs else group[0]
    m = {k: base.get(k) for k in REC_FIELDS}
    ext = {}
    for r in group:
        for k, v in (r.get("externalIds") or {}).items():
            if v and k not in ext:
                ext[k] = v
        for k in ("paperId", "title", "year", "publicationDate", "publicationTypes"):
            if not m.get(k) and r.get(k):
                m[k] = r[k]
        if r.get("abstract") and len(r["abstract"]) > len(m.get("abstract") or ""):
            m["abstract"] = r["abstract"]
        if r.get("citationCount") is not None:
            m["citationCount"] = max(m.get("citationCount") or 0, r["citationCount"])
        if len(r.get("authors") or []) > len(m.get("authors") or []):
            m["authors"] = r["authors"]
    m["externalIds"] = ext
    venues = [r.get("venue") for r in group if r.get("venue")]
    reviewed = [v for v in venues if not PREPRINT_VENUE_RE.search(v)]
    m["venue"] = reviewed[0] if reviewed else (venues[0] if venues else None)
    m["preprintOnly"] = not reviewed
    return m


def signals(group, key_of):
    def lab(r):
        return key_of.get(r.get("_seed")) or r.get("_seedLabel") or r.get("_seed") or "?"

    q = sorted({r.get("_tag") or "?" for r in group if r.get("_kind") in SEARCH_KINDS})
    ranks = [r["_rank"] for r in group if r.get("_kind") in SEARCH_KINDS and isinstance(r.get("_rank"), int)]
    return {"queries": q, "n_queries": len(q), "best_rank": min(ranks) if ranks else None,
            "refs_of": sorted({lab(r) for r in group if r.get("_kind") == "refs"}),
            "cites_seeds": sorted({lab(r) for r in group if r.get("_kind") == "cites"}),
            "rec": sorted({r.get("_tag") or "?" for r in group if r.get("_kind") == "rec"}),
            "author": sorted({r.get("_tag") or "?" for r in group if r.get("_kind") == "author"}),
            "manual": any(r.get("_kind") == "manual" for r in group)}


class CitedIndex:
    """What the draft already has: resolved bib entries plus raw .bib metadata."""

    def __init__(self, cited_rows, draft):
        self.ids, self.titles = {}, []
        for c in cited_rows:
            self._add(c["key"], bool(c.get("cited")), c.get("paperId"), c.get("externalIds") or {},
                      [c.get("title"), c.get("bib_title")])
        for b in draft.get("bib", []):
            self._add(b["key"], bool(b.get("cited")), None, {"DOI": b.get("doi"), "ArXiv": b.get("arxiv")},
                      [b.get("title")])

    def _add(self, key, cited, pid, ext, titles):
        idents = identifiers({"paperId": pid, "externalIds": ext})
        for t in titles:
            nt = norm_title(t)
            if len(nt) >= 12:
                idents.append("t:" + nt)
                self.titles.append((nt, set(nt.split()), key, cited))
        for ident in idents:
            if ident not in self.ids or (cited and not self.ids[ident][1]):
                self.ids[ident] = (key, cited)

    def lookup(self, m):
        best = None
        for ident in identifiers(m):
            hit = self.ids.get(ident)
            if hit and (best is None or (hit[1] and not best[1])):
                best = hit
        if best and best[1]:
            return best
        nt = norm_title(m.get("title"))
        toks = set(nt.split())
        if not toks:
            return best
        for t, tt, key, cited in self.titles:
            if len(toks & tt) / len(toks | tt) < 0.5:
                continue
            if (t == nt or SequenceMatcher(None, t, nt).ratio() >= 0.92) and (best is None or (cited and not best[1])):
                best = (key, cited)
        return best


def score(sig):
    s = 4.0 * sig.get("simn", 0.0)
    s += 1.2 * math.log2(1 + sig["n_queries"])
    if sig.get("best_rank") and sig["best_rank"] <= 10:
        s += 0.6
    s += 0.6 * math.log2(1 + len(sig["refs_of"])) + 1.0 * math.log2(1 + len(sig["cites_seeds"]))
    s += 0.8 * min(len(sig["rec"]), 2) + 0.5 * min(len(sig["author"]), 1) + (1.0 if sig["manual"] else 0)
    cp = sig.get("coupling")
    if cp and cp["n_refs"] > 0:
        s += min(4.0, 12.0 * cp["salton"])
    return s


def sigstr(s):
    parts = []
    if s.get("n_queries"):
        parts.append(f"q{s['n_queries']}" + (f"#{s['best_rank']}" if s.get("best_rank") else ""))
    if s.get("refs_of"):
        parts.append(f"refd-by{len(s['refs_of'])}")
    if s.get("cites_seeds"):
        parts.append(f"cites{len(s['cites_seeds'])}")
    if s.get("rec"):
        parts.append("rec" + (str(len(s["rec"])) if len(s["rec"]) > 1 else ""))
    if s.get("author"):
        parts.append("auth")
    if s.get("manual"):
        parts.append("manual")
    if s.get("coupling"):
        parts.append(f"cpl{s['coupling']['overlap']}/{s['coupling']['n_refs']}")
    if s.get("sim") is not None:
        parts.append(f"sim{s['sim']:.2f}".replace("0.", "."))
    return " ".join(parts)


def post_cutoff(c, after):
    if not after:
        return None
    d = c.get("publicationDate")
    if d:
        return True if d[:len(after)] > after else None
    if c.get("year"):
        y = str(c["year"])
        if y > after[:4]:
            return True
        if y == after[:4] and len(after) > 4:
            return "maybe"
    return None


# ---------------------------------------------------------------- commands

def do_rank(work, after=None, md_top=150):
    pool = read_jsonl(work_file(work, "pool.jsonl"))
    if not pool:
        sys.exit("W/pool.jsonl is empty: run searches first")
    dpath = work_file(work, "draft.json")
    draft = load_json(dpath) if os.path.exists(dpath) else {}
    cited_rows = read_jsonl(work_file(work, "cited.jsonl"))
    if not cited_rows:
        warn("no cited.jsonl: already-cited papers are only filtered by .bib metadata (run s2.py resolve-bib)")
    idx = CitedIndex(cited_rows, draft)
    key_of = {c["paperId"]: c["key"] for c in cited_rows if c.get("paperId")}
    cited_ids = {c["paperId"] for c in cited_rows if c.get("paperId") and c.get("cited")}
    cpath = work_file(work, "coupling.json")
    coupling = load_json(cpath) if os.path.exists(cpath) else {}
    dtitle = draft.get("title") or ""

    cands = []
    for g in cluster(pool):
        m = merge(g)
        hit = idx.lookup(m)
        if dtitle and title_sim(dtitle, m.get("title")) >= 0.85:
            m["status"] = "self"
        elif hit:
            m["status"] = "cited" if hit[1] else "in-bib-uncited"
            m["bibKey"] = hit[0]
        else:
            m["status"] = "candidate"
        sig = signals(g, key_of)
        refs = coupling.get(m.get("paperId") or "", [])
        if refs:
            shared = sorted(set(refs) & cited_ids)
            sig["coupling"] = {"overlap": len(shared), "n_refs": len(set(refs)),
                               "salton": round(len(shared) / math.sqrt(len(set(refs)) * max(1, len(cited_ids))), 3),
                               "shared": [key_of.get(x, x) for x in shared]}
        m["signals"] = sig
        pc = post_cutoff(m, after)
        if pc:
            m["postCutoff"] = pc
        cands.append(m)

    active = [c for c in cands if c["status"] in ACTIVE]
    profile = " ".join([dtitle, dtitle, draft.get("abstract") or ""]
                       + [x["sentence"] for x in draft.get("novelty_claims", [])])
    if profile.strip() and active:
        sims = tfidf_sims(profile, [f"{c.get('title') or ''} {c.get('title') or ''} {c.get('abstract') or ''}"
                                    for c in active])
        mx = max(sims) or 1.0
        for c, s in zip(active, sims):
            c["signals"]["sim"] = round(s, 3)
            c["signals"]["simn"] = s / mx
    for c in cands:
        c["score"] = round(score(c["signals"]), 2) if c["status"] in ACTIVE else None
    active.sort(key=lambda c: -c["score"])
    for i, c in enumerate(active):
        c["rank"] = i + 1
    rest = [c for c in cands if c["status"] not in ACTIVE]
    write_json(work_file(work, "candidates.json"), active + rest)

    L = ["| # | score | year | venue | cites | signals | title | id |", "|---|---|---|---|---|---|---|---|"]
    for c in active[:md_top]:
        flag = (" [in .bib, uncited]" if c["status"] == "in-bib-uncited" else "") + \
               (" [after cutoff]" if c.get("postCutoff") is True else " [cutoff?]" if c.get("postCutoff") else "")
        ven = (c.get("venue") or "?")[:30] + (" (preprint)" if c.get("preprintOnly") else "")
        title = (c.get("title") or "").replace("|", "/")
        L.append(f"| {c['rank']} | {c['score']} | {c.get('year') or ''} | {ven} | {c.get('citationCount') or 0} | "
                 f"{sigstr(c['signals'])} | {title}{flag} | {c.get('paperId') or ''} |")
    with open(work_file(work, "shortlist.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    st = Counter(c["status"] for c in cands)
    kinds = Counter(r.get("_kind") for r in pool)
    n_cited = sum(1 for c in cited_rows if c.get("cited")) or len(draft.get("cited_keys", []))
    found = {c.get("bibKey") for c in cands if c["status"] == "cited"
             and (c["signals"]["n_queries"] or c["signals"]["rec"])}
    print(f"pool records: {len(pool)} ({', '.join(f'{k}:{v}' for k, v in kinds.most_common())})")
    print(f"unique papers: {len(cands)} -> {st['candidate']} candidates, {st['in-bib-uncited']} in .bib but "
          f"uncited, {st['cited']} already cited, {st['self']} = the draft itself")
    if n_cited:
        print(f"recall proxy: searches/recommendations re-found {len(found)}/{n_cited} of the draft's own "
              f"citations ({100 * len(found) / n_cited:.0f}%)")
    print(f"coupling computed for {sum(1 for c in active if c['signals'].get('coupling'))} candidates")
    print(f"wrote {work_file(work, 'candidates.json')} and {work_file(work, 'shortlist.md')} (top {md_top})")


def cmd_rank(a):
    do_rank(a.work, a.after, a.md_top)


def cmd_coupling(a):
    import s2 as S2
    cpath = work_file(a.work, "candidates.json")
    if not os.path.exists(cpath):
        sys.exit("run pool.py rank first")
    cands = load_json(cpath)
    cache_path = work_file(a.work, "coupling.json")
    cache = load_json(cache_path) if os.path.exists(cache_path) else {}
    top = [c for c in cands if c["status"] in ACTIVE][:a.top]
    todo = [c["paperId"] for c in top if c.get("paperId") and c["paperId"] not in cache]
    info(f"fetching reference lists for {len(todo)} candidates (~{len(todo)}s)")
    for i, pid in enumerate(todo):
        try:
            r = S2.s2(f"/paper/{pid}/references", {"fields": "paperId", "limit": 1000}) or {}
        except Exception as e:  # keep going; one bad record should not stop the batch
            warn(f"{pid}: {e}")
            continue
        cache[pid] = [d["citedPaper"]["paperId"] for d in r.get("data") or []
                      if d.get("citedPaper") and d["citedPaper"].get("paperId")]
        if i % 25 == 24:
            write_json(cache_path, cache)
    write_json(cache_path, cache)
    do_rank(a.work, a.after, a.md_top)


def cmd_show(a):
    cands = load_json(work_file(a.work, "candidates.json"))
    if a.ids:
        want = [x.strip() for x in a.ids.split(",") if x.strip()]
        by_rank = {str(c.get("rank")): c for c in cands if c.get("rank")}
        by_id = {}
        for c in cands:
            for ident in [c.get("paperId")] + [str(v) for v in (c.get("externalIds") or {}).values()]:
                if ident:
                    by_id[ident.lower()] = c
        sel = [by_rank.get(w) or by_id.get(w.lower().split(":", 1)[-1]) for w in want]
        for w, c in zip(want, sel):
            if not c:
                warn(f"{w}: not in candidates.json")
        sel = [c for c in sel if c]
    else:
        statuses = a.status.split(",") if a.status else list(ACTIVE)
        sel = [c for c in cands if c["status"] in statuses]
        if a.min_sim is not None:
            sel = [c for c in sel if (c["signals"].get("sim") or 0) >= a.min_sim]
        sel = sel[a.start:a.start + a.top]
    for c in sel:
        s = c["signals"]
        ext = c.get("externalIds") or {}
        flags = [c["status"]] + (["bib:" + c["bibKey"]] if c.get("bibKey") else []) \
            + (["PREPRINT-ONLY"] if c.get("preprintOnly") else []) \
            + ([f"post-cutoff:{c['postCutoff']}"] if c.get("postCutoff") else [])
        print(f"#{c.get('rank', '-')}  score {c.get('score')}  [{' '.join(flags)}]  {c.get('year')}  "
              f"{c.get('venue') or '?'}  ({c.get('citationCount') or 0} cites)  {c.get('publicationTypes') or ''}")
        print(f"   {c.get('title')}")
        print(f"   {short_authors(c.get('authors'), 6)}")
        det = [sigstr(s)]
        if s.get("cites_seeds"):
            det.append("cites: " + ", ".join(s["cites_seeds"][:8]))
        if s.get("refs_of"):
            det.append("referenced by: " + ", ".join(s["refs_of"][:8]))
        if s.get("coupling"):
            det.append("shares refs: " + ", ".join(s["coupling"]["shared"][:10]))
        if s.get("queries"):
            det.append("queries: " + " || ".join(q.split(":", 1)[-1] for q in s["queries"][:4]))
        print("   " + " | ".join(det))
        print(f"   S2 {c.get('paperId') or '-'} | " + " | ".join(f"{k} {v}" for k, v in ext.items()
                                                                  if k in ("DOI", "ArXiv", "DBLP")))
        ab = c.get("abstract") or "(no abstract: use s2.py paper / arXiv)"
        if a.chars and len(ab) > a.chars:
            ab = ab[:a.chars] + " ..."
        print(f"   {ab}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("rank", cmd_rank), ("coupling", cmd_coupling)):
        p = sub.add_parser(name)
        p.add_argument("--work", required=True)
        p.add_argument("--after", help="draft cutoff date YYYY[-MM[-DD]]; later papers are flagged")
        p.add_argument("--md-top", type=int, default=150)
        if name == "coupling":
            p.add_argument("--top", type=int, default=200)
        p.set_defaults(fn=fn)
    p = sub.add_parser("show")
    p.add_argument("--work", required=True)
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--top", type=int, default=30)
    p.add_argument("--ids", help="comma list of ranks, S2 ids, DOIs or arXiv ids")
    p.add_argument("--status", help="comma list: candidate,in-bib-uncited,cited,self")
    p.add_argument("--min-sim", type=float)
    p.add_argument("--chars", type=int, default=700, help="abstract truncation (0 = full)")
    p.set_defaults(fn=cmd_show)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
