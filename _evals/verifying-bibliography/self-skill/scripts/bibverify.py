#!/usr/bin/env python3
"""
bibverify.py - check BibTeX entries against the published record.

Looks every entry up in Crossref, doi.org (content negotiation + Handle API),
arXiv, DBLP, OpenAlex, Semantic Scholar, bioRxiv and Open Library, then reports
fabricated / non-existent references, wrong titles, authors, DOIs, venues,
volumes, pages and years, retractions, and arXiv/bioRxiv preprints that have a
published version. Python 3 standard library only.

Subcommands
  check  REFS.bib [--cited-in main.tex ...] [--keys k1,k2] [--out report.json]
                  [--md report.md] [--workers 4] [--no-cache]
  lookup (--doi DOI | --arxiv ID | --title TITLE [--author SURNAME])
  bibtex (--doi DOI | --arxiv ID | --dblp DBLP_KEY)

Environment (all optional)
  BIBVERIFY_MAILTO   contact address for the Crossref/OpenAlex "polite pool"
  BIBVERIFY_CACHE    cache directory (default ~/.cache/bibverify)
  S2_API_KEY         Semantic Scholar API key (higher rate limit)
  OPENALEX_API_KEY   OpenAlex API key
"""

import argparse
import concurrent.futures
import difflib
import hashlib
import html
import http.client
import json
import os
import re
import sys
import threading
import time
import traceback
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CACHE_DIR = os.environ.get("BIBVERIFY_CACHE") or os.path.join(
    os.path.expanduser("~"), ".cache", "bibverify")
MAILTO = os.environ.get("BIBVERIFY_MAILTO", "").strip()
S2_KEY = os.environ.get("S2_API_KEY", "").strip()
OPENALEX_KEY = os.environ.get("OPENALEX_API_KEY", "").strip()
UA = "bibverify/1.0 (self-verifying-bibliography skill; python-urllib)"
if MAILTO:
    UA += " mailto:" + MAILTO
USE_CACHE = True

# Minimum seconds between two requests to the same host.
HOST_INTERVAL = {
    "export.arxiv.org": 3.1,
    "arxiv.org": 1.0,
    "api.semanticscholar.org": 1.2,
    "dblp.org": 1.0,
    "api.crossref.org": 0.25,
    "api.openalex.org": 0.15,
    "doi.org": 0.3,
    "api.biorxiv.org": 0.5,
    "openlibrary.org": 0.5,
}

# ---------------------------------------------------------------------------
# HTTP with per-host throttling, retries and an on-disk cache
# ---------------------------------------------------------------------------

_locks = {}
_last = {}
_meta_lock = threading.Lock()


def _throttle(host):
    with _meta_lock:
        lock = _locks.setdefault(host, threading.Lock())
    with lock:
        wait = _last.get(host, 0.0) + HOST_INTERVAL.get(host, 0.5) - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[host] = time.time()


def _cache_path(url, accept):
    h = hashlib.sha256((accept + " " + url).encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, h[:2], h + ".json")


def http_get(url, accept="application/json", headers=None, tries=4):
    """Return (status, text). status is None when the network failed."""
    path = _cache_path(url, accept)
    if USE_CACHE:
        try:
            with open(path, encoding="utf-8") as fh:
                d = json.load(fh)
            return d["status"], d["body"]
        except (OSError, ValueError, KeyError):
            pass
    host = urllib.parse.urlsplit(url).hostname or ""
    hdrs = {"User-Agent": UA, "Accept": accept}
    if headers:
        hdrs.update(headers)
    status, body = None, ""
    for attempt in range(tries):
        _throttle(host)
        req = urllib.request.Request(url, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                status = resp.status
                body = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            status = e.code
            try:
                body = e.read().decode("utf-8", "replace")
            except Exception:
                body = ""
            if status == 429 or status >= 500:
                retry = (e.headers.get("Retry-After", "") if e.headers else "") or ""
                delay = float(retry) if retry.strip().isdigit() else 2.0 * (2 ** attempt)
                time.sleep(min(delay, 60))
                continue
        except (OSError, http.client.HTTPException) as e:
            status, body = None, "network error: %s" % e
            time.sleep(min(2.0 * (2 ** attempt), 30))
            continue
        break
    if USE_CACHE and status in (200, 404, 410):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = "%s.%d.%d.tmp" % (path, os.getpid(), threading.get_ident())
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({"url": url, "status": status, "body": body}, fh)
            os.replace(tmp, path)
        except OSError:
            pass
    return status, body


def get_json(url, headers=None, tries=4):
    status, body = http_get(url, "application/json", headers, tries)
    try:
        return status, (json.loads(body) if body else None)
    except ValueError:
        return status, None


def q(s):
    return urllib.parse.quote(s, safe="/")


# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------

FOLD_MAP = str.maketrans({
    "ø": "o", "Ø": "O", "ł": "l", "Ł": "L", "æ": "ae", "Æ": "AE", "œ": "oe",
    "Œ": "OE", "ß": "ss", "đ": "d", "Đ": "D", "ð": "d", "Ð": "D", "þ": "th",
    "Þ": "Th", "ı": "i", "ŀ": "l",
})
_ACC_SYM = r"""[`'^"~=.]"""
_SPECIAL = {"ss": "ss", "ae": "ae", "AE": "AE", "oe": "oe", "OE": "OE",
            "aa": "a", "AA": "A", "o": "o", "O": "O", "l": "l", "L": "L",
            "i": "i", "j": "j"}


def latex_to_text(s):
    """Strip LaTeX markup from a BibTeX value (accents are reduced to the base letter)."""
    if not s:
        return ""
    s = str(s).replace("\\\\", " ")
    for a, b in (("\\&", "&"), ("\\%", "%"), ("\\_", "_"), ("\\$", "$"),
                 ("\\#", "#"), ("\\{", "{"), ("\\}", "}"),
                 ("\\LaTeX", "LaTeX"), ("\\TeX", "TeX")):
        s = s.replace(a, b)
    s = re.sub(r"\\" + _ACC_SYM + r"\s*\{\s*\\?([A-Za-z])\s*\}", r"\1", s)
    s = re.sub(r"\\" + _ACC_SYM + r"\s*\\?([A-Za-z])", r"\1", s)
    s = re.sub(r"\\[uvHcdbtkr]\s*\{\s*\\?([A-Za-z])\s*\}", r"\1", s)
    s = re.sub(r"\\[uvHcdbtkr]\s+([A-Za-z])", r"\1", s)
    s = re.sub(r"\\(ss|ae|AE|oe|OE|aa|AA|o|O|l|L|i|j)(?![A-Za-z])\s*",
               lambda m: _SPECIAL[m.group(1)], s)
    s = re.sub(r"\\[A-Za-z]+\*?", "", s)
    s = s.replace("{", "").replace("}", "").replace("$", "").replace("~", " ")
    s = s.replace("``", '"').replace("''", '"')
    return " ".join(s.split())


def clean(s):
    """Human-readable form of an API string (drops JATS/HTML tags)."""
    if not s:
        return ""
    s = re.sub(r"</?[A-Za-z][^>]*>", "", str(s))
    return " ".join(html.unescape(s).split())


def fold(s, markup=False):
    """Aggressive normalisation for comparisons: ascii, lowercase, alnum words."""
    if not s:
        return ""
    s = str(s)
    if markup:
        s = html.unescape(re.sub(r"</?[A-Za-z][^>]*>", "", s))
    s = latex_to_text(s)
    s = unicodedata.normalize("NFKD", s.translate(FOLD_MAP))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


# ---------------------------------------------------------------------------
# BibTeX parsing
# ---------------------------------------------------------------------------

MONTHS = {m: m.capitalize() for m in
          ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")}
ENTRY_RE = re.compile(r"@\s*([A-Za-z]+)\s*([{(])")
FIELD_RE = re.compile(r"([A-Za-z0-9_\-:.+/]+)\s*=")
TOKEN_RE = re.compile(r"[^\s,#})]+")


def _skip_ws(s, i):
    while i < len(s) and s[i].isspace():
        i += 1
    return i


def _read_braced(s, i):
    depth, j = 0, i
    while j < len(s):
        c = s[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    return s[i + 1:], len(s)


def _read_quoted(s, i):
    depth, j = 0, i + 1
    while j < len(s):
        c = s[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif c == '"' and depth == 0:
            return s[i + 1:j], j + 1
        j += 1
    return s[i + 1:], len(s)


def _read_value(s, i, strings):
    parts = []
    while True:
        i = _skip_ws(s, i)
        if i >= len(s):
            break
        c = s[i]
        if c == "{":
            v, i = _read_braced(s, i)
        elif c == '"':
            v, i = _read_quoted(s, i)
        else:
            m = TOKEN_RE.match(s, i)
            if not m:
                break
            tok, i = m.group(0), m.end()
            v = tok if tok.isdigit() else strings.get(tok.lower(), tok)
        parts.append(v)
        i = _skip_ws(s, i)
        if i < len(s) and s[i] == "#":
            i += 1
            continue
        break
    return "".join(parts), i


def parse_bibtex(text):
    strings = dict(MONTHS)
    entries, pos = [], 0
    while True:
        m = ENTRY_RE.search(text, pos)
        if not m:
            break
        etype = m.group(1).lower()
        if m.group(2) == "{":
            body, end = _read_braced(text, m.end() - 1)
        else:
            depth, j = 0, m.end()
            while j < len(text):
                c = text[j]
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                elif c == ")" and depth == 0:
                    break
                j += 1
            body, end = text[m.end():j], j + 1
        line = text.count("\n", 0, m.start()) + 1
        pos = end
        if etype in ("comment", "preamble"):
            continue
        if etype == "string":
            b = body.strip()
            fm = FIELD_RE.match(b)
            if fm:
                val, _ = _read_value(b, fm.end(), strings)
                strings[fm.group(1).lower()] = val
            continue
        comma = body.find(",")
        key = (body if comma < 0 else body[:comma]).strip()
        rest = "" if comma < 0 else body[comma + 1:]
        fields, i = {}, 0
        while True:
            i = _skip_ws(rest, i)
            while i < len(rest) and rest[i] == ",":
                i = _skip_ws(rest, i + 1)
            fm = FIELD_RE.match(rest, i)
            if not fm:
                break
            name = fm.group(1).lower()
            val, i = _read_value(rest, fm.end(), strings)
            fields.setdefault(name, val)
        entries.append({"type": etype, "key": key, "fields": fields, "line": line})
    return entries


CITE_RE = re.compile(
    r"\\(?:[A-Za-z]*cite[A-Za-z]*|citation|nocite)\*?\s*(?:\[[^\]]*\]\s*){0,2}\{([^}]*)\}")


def cited_keys(paths):
    keys = set()
    for p in paths:
        with open(p, encoding="utf-8", errors="replace") as fh:
            txt = fh.read()
        if p.endswith(".tex"):
            txt = re.sub(r"(?<!\\)%.*", "", txt)
        for m in CITE_RE.finditer(txt):
            keys.update(k.strip() for k in m.group(1).split(",") if k.strip())
    return keys


# ---------------------------------------------------------------------------
# Field helpers
# ---------------------------------------------------------------------------

PREPRINT_DOI_RE = re.compile(
    r"10\.48550/|10\.1101/(\d{4}\.\d{2}\.\d{2}\.)?\d{6,}(v\d+)?$|10\.2139/ssrn|"
    r"10\.21203/rs\.|10\.20944/preprints|10\.26434/chemrxiv|10\.31234/osf|"
    r"10\.31219/osf|10\.31235/osf|10\.36227/techrxiv|10\.22541/au\.", re.I)
PREPRINT_VENUE_RE = re.compile(
    r"arxiv|\bcorr\b|biorxiv|medrxiv|ssrn|chemrxiv|techrxiv|psyarxiv|"
    r"research\s*square|\bpreprints?\b", re.I)
NEW_ARXIV = re.compile(r"(?<!\d)(\d{4}\.\d{4,5})(?:v\d+)?(?!\d)")
OLD_ARXIV = re.compile(r"\b(?!abs/)([a-z][a-z\-]*(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?\b")
UNVERIFIABLE_TYPES = {
    "misc", "online", "electronic", "www", "webpage", "software", "dataset",
    "manual", "techreport", "report", "phdthesis", "mastersthesis", "thesis",
    "patent", "standard", "unpublished", "booklet", "proceedings", "periodical",
}


def is_preprint_doi(d):
    return bool(d) and bool(PREPRINT_DOI_RE.match(d))


def norm_doi(s):
    if not s:
        return ""
    s = s.replace("\\_", "_").replace("{", "").replace("}", "").strip()
    s = urllib.parse.unquote(s)
    m = re.search(r"10\.\d{4,9}/\S+", s)
    return m.group(0).rstrip(".,;").lower() if m else ""


def doi_from_url(u):
    m = re.search(r"(?:doi\.org/|/doi/(?:abs/|full/|pdf/|epdf/)?)(10\.\d{4,9}/[^\s?#]+)", u or "", re.I)
    return norm_doi(m.group(1)) if m else ""


def extract_arxiv(f):
    texts = []
    ep = (f.get("eprint") or f.get("arxivid") or "").strip()
    kind = (f.get("archiveprefix", "") + " " + f.get("eprinttype", "")).lower()
    if ep and ("arxiv" in kind or not kind.strip()):
        texts.append(ep)
    for k in ("journal", "journaltitle", "volume", "note", "howpublished", "url",
              "doi", "booktitle", "publisher", "number"):
        v = f.get(k, "")
        if v and re.search(r"arxiv|corr|abs/", v, re.I):
            texts.append(v)
    for t in texts:
        t = t.replace("\\_", "_")
        m = NEW_ARXIV.search(t)
        if m:
            return m.group(1)
        m = OLD_ARXIV.search(t)
        if m:
            return m.group(1)
    return ""


def arxiv_id_year(aid):
    m = re.match(r"(\d{2})\d{2}\.\d{4,5}$", aid)
    if m:
        return 2000 + int(m.group(1))
    m = re.search(r"/(\d{2})\d{5}$", aid)
    if m:
        yy = int(m.group(1))
        return 1900 + yy if yy >= 91 else 2000 + yy
    return None


def arxiv_id_problem(aid):
    m = re.match(r"(\d{2})(\d{2})\.(\d{4,5})$", aid)
    if not m:
        return ""
    yy, mm, num = int(m.group(1)), int(m.group(2)), m.group(3)
    now = time.localtime()
    if not 1 <= mm <= 12:
        return "arXiv id %s has an invalid month (%02d)." % (aid, mm)
    if (yy, mm) < (7, 4):
        return "arXiv id %s predates the YYMM.NNNN scheme (April 2007)." % aid
    if len(num) == 5 and (yy, mm) < (15, 1):
        return "arXiv id %s: 5-digit numbers only exist from 1501 onward." % aid
    if len(num) == 4 and (yy, mm) >= (15, 1):
        return "arXiv id %s: ids from 1501 onward have 5 digits." % aid
    if (2000 + yy, mm) > (now.tm_year, now.tm_mon):
        return "arXiv id %s is in the future." % aid
    return ""


def cites_preprint(e, doi, arxiv_id):
    f = e["fields"]
    venue = " ".join(f.get(k, "") for k in ("journal", "journaltitle", "booktitle", "publisher",
                                              "howpublished", "institution", "series"))
    if PREPRINT_VENUE_RE.search(venue):
        return True
    if is_preprint_doi(doi):
        return True
    has_venue = f.get("journal") or f.get("journaltitle") or f.get("booktitle")
    if arxiv_id and not has_venue:
        return True
    if not has_venue and PREPRINT_VENUE_RE.search(f.get("note", "")):
        return True
    return False


def bib_year(f):
    for k in ("year", "date"):
        m = re.search(r"(1[5-9]\d\d|20\d\d)", f.get(k, "") or "")
        if m:
            return int(m.group(1))
    return None


def bib_venue(f):
    return f.get("journal") or f.get("journaltitle") or f.get("booktitle") or ""


# ---------------------------------------------------------------------------
# Names
# ---------------------------------------------------------------------------

PARTICLES = {"van", "von", "der", "den", "de", "del", "della", "di", "da", "du",
             "la", "le", "dos", "das", "ten", "ter", "bin", "al", "el"}
SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}
_AND = re.compile(r"\s+and\s+", re.I)


def _split_top(s, sep):
    out, depth, cur = [], 0, []
    for c in s:
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        if depth == 0 and (c.isspace() if sep == " " else c == sep):
            out.append("".join(cur))
            cur = []
        else:
            cur.append(c)
    out.append("".join(cur))
    if sep == " ":
        return [x.strip() for x in out if x.strip()]
    return [x.strip() for x in out]


def split_names(s):
    out, depth, start, i = [], 0, 0, 0
    while i < len(s):
        c = s[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif depth == 0 and c.isspace():
            m = _AND.match(s, i)
            if m:
                out.append(s[start:i])
                i = m.end()
                start = i
                continue
        i += 1
    out.append(s[start:])
    return [x.strip() for x in out if x.strip()]


def parse_bib_name(raw):
    parts = _split_top(raw, ",")
    if len(parts) >= 2:
        family = parts[0]
        given = parts[-1] if len(parts) == 2 else parts[2]
    else:
        words = _split_top(raw, " ")
        if len(words) <= 1:
            family, given = raw, ""
        else:
            k = len(words) - 1
            for idx in range(1, len(words) - 1):
                if words[idx][:1].islower():
                    k = idx
                    break
            family, given = " ".join(words[k:]), " ".join(words[:k])
    return {"family": latex_to_text(family), "given": latex_to_text(given)}


def bib_author_list(s):
    authors, truncated = [], False
    for n in split_names(" ".join((s or "").split())):
        if re.search(r"\bet\s*al\b", n, re.I):
            truncated = True
            n = re.sub(r"\bet\s*al\b\.?", "", n, flags=re.I).strip(" ,")
        if fold(n) in ("others", ""):
            if fold(n) == "others":
                truncated = True
            continue
        authors.append(parse_bib_name(n))
    return authors, truncated


def name_from_full(full):
    full = re.sub(r"\s+\d{4}$", "", (full or "").strip())  # DBLP homonym suffix
    w = full.split()
    if w and fold(w[-1]) in SUFFIXES and len(w) > 2:
        w = w[:-1]
    if not w:
        return {"family": "", "given": ""}
    if len(w) == 1:
        return {"family": w[0], "given": ""}
    k = len(w) - 1
    while k > 1 and w[k - 1].lower() in PARTICLES:
        k -= 1
    return {"family": " ".join(w[k:]), "given": " ".join(w[:k])}


def name_key(family, given=""):
    fam = [t for t in fold(family).split() if t not in SUFFIXES] or fold(family).split()
    toks = {t for t in fold("%s %s" % (given, family)).split() if len(t) > 1}
    disp = ("%s, %s" % (family, given)).strip().strip(",").strip()
    return {"key": fam[-1] if fam else "", "tokens": toks, "display": disp}


def name_kind(b, r):
    if not b["key"] or not r["key"]:
        return None
    if b["key"] == r["key"]:
        return "exact"
    if r["key"] in b["tokens"] or b["key"] in r["tokens"]:
        return "format"
    if len(b["key"]) > 3 and len(r["key"]) > 3 and \
            difflib.SequenceMatcher(None, b["key"], r["key"]).ratio() >= 0.8:
        return "spelling"
    return None


def align(B, R):
    m, used = [None] * len(B), set()
    for kinds in (("exact",), ("format", "spelling")):
        for i, b in enumerate(B):
            if m[i] is not None:
                continue
            for j in sorted(range(len(R)), key=lambda j: abs(j - i)):
                if j in used:
                    continue
                k = name_kind(b, R[j])
                if k in kinds:
                    m[i] = (j, k)
                    used.add(j)
                    break
    return m


def _keys(authors):
    return [name_key(a["family"], a["given"]) for a in authors]


def author_overlap(bib_authors, rec_authors):
    if not bib_authors or not rec_authors:
        return None
    m = align(_keys(bib_authors), _keys(rec_authors))
    return sum(1 for x in m if x) / float(len(bib_authors))


def author_findings(bib_authors, truncated, rec_authors):
    B, R = _keys(bib_authors), _keys(rec_authors)
    if not B or not R:
        return []
    out = []
    m = align(B, R)
    used = {x[0] for x in m if x}
    extra = [B[i]["display"] for i, x in enumerate(m) if x is None]
    missing = [R[j]["display"] for j in range(len(R)) if j not in used]
    if extra:
        out.append(("error", "author_not_in_record",
                    "Author(s) in bib but not in record: " + "; ".join(extra)))
    if missing and not truncated:
        sev = "warning" if len(R) > 30 and len(B) <= 5 else "error"
        out.append((sev, "author_missing", "%d author(s) in record missing from bib: %s%s" % (
            len(missing), "; ".join(missing[:10]), " ..." if len(missing) > 10 else "")))
    if m[0] is None or m[0][0] != 0:
        out.append(("error", "first_author", "First author is '%s' in bib but '%s' in record."
                    % (B[0]["display"], R[0]["display"])))
    pos = [x[0] for x in m if x]
    if pos != sorted(pos):
        out.append(("error", "author_order", "Author order differs from the record."))
    elif truncated and pos != list(range(len(pos))):
        out.append(("warning", "author_truncation",
                    "Truncated list ('and others') does not start with the record's leading authors."))
    sp = ["'%s' (bib) vs '%s' (record)" % (B[i]["display"], R[x[0]]["display"])
          for i, x in enumerate(m) if x and x[1] == "spelling"]
    if sp:
        out.append(("warning", "author_spelling", "Name spelling differs: " + "; ".join(sp)))
    return out


def fmt_authors(authors, n=None):
    names = [("%s %s" % (a.get("given", ""), a.get("family", ""))).strip() for a in authors]
    if n and len(names) > n:
        return ", ".join(names[:n]) + " et al. (%d authors)" % len(names)
    return ", ".join(names)


# ---------------------------------------------------------------------------
# Records (normalised metadata from any source)
# ---------------------------------------------------------------------------

SOURCE_PRIORITY = {"crossref": 0, "doi.org": 1, "dblp": 2, "openalex": 3, "s2": 4,
                   "openlibrary": 5, "arxiv": 6}


def mkrec(source, **kw):
    r = {"source": source, "title": "", "main_title": "", "authors": [], "year": None,
         "years": [], "venue": "", "venue_alts": [], "volume": "", "number": "",
         "pages": "", "pages_is_article_number": False, "doi": "", "arxiv": "",
         "type": "", "preprint": False, "url": "", "link": "", "retracted": False,
         "published_doi": "", "journal_ref": "", "publisher": "", "dblp_key": ""}
    r.update(kw)
    ys = []
    for y in [r["year"]] + list(r["years"]):
        try:
            if y:
                ys.append(int(y))
        except (TypeError, ValueError):
            pass
    r["years"] = sorted(set(ys))
    if r["year"] is not None:
        try:
            r["year"] = int(r["year"])
        except (TypeError, ValueError):
            r["year"] = None
    for k in ("volume", "number", "pages"):
        r[k] = "" if r[k] is None else str(r[k]).strip()
    return r


def by_priority(recs):
    return sorted(recs, key=lambda r: (SOURCE_PRIORITY.get(r["source"], 9),
                                       -r.get("_title_sim", 0.0)))


def summarize(r):
    d = {"source": r["source"], "title": clean(r["title"]),
         "authors": fmt_authors(r["authors"], 8), "year": r["year"],
         "venue": clean(r["venue"]), "volume": r["volume"], "number": r["number"],
         "pages": r["pages"], "doi": r["doi"], "arxiv": r["arxiv"],
         "url": r["link"] or r["url"], "type": r["type"], "preprint": r["preprint"]}
    if r.get("journal_ref"):
        d["journal_ref"] = r["journal_ref"]
    if "_title_sim" in r:
        d["title_similarity"] = round(r["_title_sim"], 3)
    if r.get("_author_overlap") is not None:
        d["author_overlap"] = round(r["_author_overlap"], 3)
    return {k: v for k, v in d.items() if v not in ("", None, [])}


def cite_line(r):
    bits = ['"%s"' % clean(r["title"]), fmt_authors(r["authors"], 3)]
    v = clean(r["venue"])
    if v:
        bits.append(v + (" " + r["volume"] if r["volume"] else ""))
    if r["pages"]:
        bits.append("pp. " + r["pages"])
    if r["year"]:
        bits.append(str(r["year"]))
    if r["doi"]:
        bits.append("doi:" + r["doi"])
    elif r["link"] or r["url"]:
        bits.append(r["link"] or r["url"])
    bits.append("[%s]" % r["source"])
    return ", ".join(b for b in bits if b)


def suggestion(r):
    s = {"source": r["source"], "title": clean(r["title"])}
    if r["authors"]:
        s["author"] = " and ".join(
            ("%s, %s" % (a["family"], a["given"])).strip().strip(",").strip() for a in r["authors"])
    if r["year"]:
        s["year"] = r["year"]
    if r["venue"]:
        s["venue"] = clean(r["venue"])
    for k in ("volume", "number", "pages", "doi"):
        if r[k]:
            s[k] = r[k]
    if r["pages_is_article_number"]:
        s["pages_note"] = "pages value is an article number"
    if r["arxiv"]:
        s["eprint"] = r["arxiv"]
    if r.get("dblp_key"):
        s["dblp_key"] = r["dblp_key"]
    return s


# --- Crossref -----------------------------------------------------------------

def _cr_year(m, k):
    try:
        return int(m[k]["date-parts"][0][0])
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def from_crossref(m):
    title = " ".join(m.get("title") or [])
    sub = m.get("subtitle") or []
    authors = []
    for a in (m.get("author") or m.get("editor") or []):
        if a.get("family"):
            authors.append({"family": a["family"], "given": a.get("given", "")})
        elif a.get("name"):
            authors.append({"family": a["name"], "given": ""})
    years = [_cr_year(m, k) for k in ("published-print", "published-online", "issued", "published")]
    year = _cr_year(m, "issued") or next((y for y in years if y), None)
    venues = list(m.get("container-title") or [])
    alts = venues[1:] + list(m.get("short-container-title") or [])
    ev = m.get("event")
    if isinstance(ev, dict):
        alts += [x for x in (ev.get("name"), ev.get("acronym")) if x]
    pages, artnum = m.get("page") or "", m.get("article-number") or ""
    retracted = bool(re.match(r"\s*(retracted|withdrawn)\b", title, re.I))
    for u in (m.get("updated-by") or []):
        if isinstance(u, dict) and ("retract" in str(u.get("type", "")).lower()
                                    or "withdraw" in str(u.get("type", "")).lower()):
            retracted = True
    pub_doi = ""
    for rel in ((m.get("relation") or {}).get("is-preprint-of") or []):
        if isinstance(rel, dict) and rel.get("id-type") == "doi":
            pub_doi = norm_doi(rel.get("id", ""))
            break
    typ = m.get("type", "")
    return mkrec("crossref", title=title + (": " + sub[0] if sub else ""), main_title=title,
                 authors=authors, year=year, years=years, venue=venues[0] if venues else "",
                 venue_alts=alts, volume=m.get("volume", ""), number=m.get("issue", ""),
                 pages=pages or artnum, pages_is_article_number=bool(artnum and not pages),
                 doi=(m.get("DOI") or "").lower(), type=typ,
                 preprint=(typ == "posted-content" or is_preprint_doi((m.get("DOI") or "").lower())),
                 url=m.get("URL", ""), retracted=retracted, published_doi=pub_doi,
                 publisher=m.get("publisher", ""))


def _cr_params(p):
    if MAILTO:
        p["mailto"] = MAILTO
    return urllib.parse.urlencode(p)


def crossref_search(title, author="", rows=5):
    query = latex_to_text(title) + (" " + latex_to_text(author) if author else "")
    st, d = get_json("https://api.crossref.org/works?" + _cr_params(
        {"query.bibliographic": query, "rows": rows}))
    items = (((d or {}).get("message") or {}).get("items") or []) if st == 200 else []
    return [from_crossref(it) for it in items]


def from_csl(m):
    title = m.get("title") or ""
    if isinstance(title, list):
        title = " ".join(title)
    ct = m.get("container-title") or ""
    if isinstance(ct, list):
        ct = ct[0] if ct else ""
    authors = []
    for a in (m.get("author") or m.get("editor") or []):
        if a.get("family"):
            authors.append({"family": a["family"], "given": a.get("given", "")})
        elif a.get("literal"):
            authors.append(name_from_full(a["literal"]))
    year = None
    for k in ("issued", "published-print", "published-online", "created"):
        try:
            year = int(m[k]["date-parts"][0][0])
            break
        except (KeyError, IndexError, TypeError, ValueError):
            continue
    doi = (m.get("DOI") or "").lower()
    pub = m.get("publisher") or ""
    pre = (is_preprint_doi(doi) or m.get("type") == "posted-content"
           or fold(pub) in ("arxiv", "biorxiv", "medrxiv", "ssrn", "research square"))
    return mkrec("doi.org", title=title, authors=authors, year=year, venue=ct,
                 volume=m.get("volume") or "", number=m.get("issue") or "",
                 pages=m.get("page") or "", doi=doi, type=m.get("type") or "",
                 preprint=pre, url=m.get("URL") or "", publisher=pub)


def resolve_doi(doi):
    """Return (record|None, state); state in ok, not_found, no_metadata, unknown."""
    st, d = get_json("https://api.crossref.org/works/" + q(doi) +
                     ("?" + _cr_params({}) if MAILTO else ""))
    if st == 200 and isinstance(d, dict) and d.get("message"):
        return from_crossref(d["message"]), "ok"
    st2, body = http_get("https://doi.org/" + q(doi),
                         accept="application/vnd.citationstyles.csl+json")
    if st2 == 200:
        try:
            m = json.loads(body)
            if isinstance(m, dict) and m.get("title"):
                return from_csl(m), "ok"
        except ValueError:
            pass
    st3, d3 = get_json("https://doi.org/api/handles/" + q(doi))
    code = d3.get("responseCode") if isinstance(d3, dict) else None
    if code == 1:
        return None, "no_metadata"
    if code == 100 or st3 == 404:
        return None, "not_found"
    return None, "unknown"


# --- arXiv --------------------------------------------------------------------

ATOM = "{http://www.w3.org/2005/Atom}"
ARXNS = "{http://arxiv.org/schemas/atom}"


def parse_arxiv_feed(xml_text):
    out = {}
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return out
    for ent in root.findall(ATOM + "entry"):
        idurl = (ent.findtext(ATOM + "id") or "").strip()
        m = re.search(r"arxiv\.org/abs/(.+?)(v\d+)?$", idurl)
        if not m:
            continue
        aid = m.group(1)
        title = " ".join((ent.findtext(ATOM + "title") or "").split())
        if not title or title == "Error":
            continue
        authors = [name_from_full(a.findtext(ATOM + "name") or "") for a in ent.findall(ATOM + "author")]
        pub = ent.findtext(ATOM + "published") or ""
        upd = ent.findtext(ATOM + "updated") or ""
        y1 = int(pub[:4]) if pub[:4].isdigit() else None
        y2 = int(upd[:4]) if upd[:4].isdigit() else None
        out[aid] = mkrec("arxiv", title=title, authors=authors, year=y1, years=[y1, y2],
                         venue="arXiv", arxiv=aid, preprint=True,
                         url="https://arxiv.org/abs/" + aid,
                         doi="10.48550/arxiv." + aid.lower(),
                         published_doi=norm_doi(ent.findtext(ARXNS + "doi") or ""),
                         journal_ref=" ".join((ent.findtext(ARXNS + "journal_ref") or "").split()))
    return out


def arxiv_fetch(ids):
    out, ids = {}, [i for i in ids if i]
    for k in range(0, len(ids), 40):
        batch = ids[k:k + 40]
        url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
            {"id_list": ",".join(batch), "max_results": len(batch)})
        st, body = http_get(url, accept="application/atom+xml")
        if st == 200:
            out.update(parse_arxiv_feed(body))
    return out


def arxiv_abs(aid):
    """Fallback: read the citation_* meta tags of the abs page. Returns (rec, state)."""
    st, body = http_get("https://arxiv.org/abs/" + aid, accept="text/html")
    if st in (404, 410):
        return None, "not_found"
    if st != 200:
        return None, "unknown"
    metas = re.findall(r'<meta\s+name="citation_([a-z_]+)"\s+content="([^"]*)"', body)
    title = next((html.unescape(v) for k, v in metas if k == "title"), "")
    if not title:
        return None, "unknown"
    authors = []
    for k, v in metas:
        if k == "author":
            v = html.unescape(v)
            if "," in v:
                fam, giv = v.split(",", 1)
                authors.append({"family": fam.strip(), "given": giv.strip()})
            else:
                authors.append(name_from_full(v))
    dates = [v for k, v in metas if k in ("date", "online_date")]
    years = [int(d[:4]) for d in dates if d[:4].isdigit()]
    return mkrec("arxiv", title=title, authors=authors, year=min(years) if years else None,
                 years=years, venue="arXiv", arxiv=aid, preprint=True,
                 url="https://arxiv.org/abs/" + aid, doi="10.48550/arxiv." + aid.lower()), "ok"


def arxiv_search(title, n=5):
    stop = {"a", "an", "the", "of", "and", "or", "for", "in", "on", "to", "with", "via", "by", "is", "are"}
    words = [w for w in fold(title).split() if w not in stop][:10]
    if not words:
        return []
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": " AND ".join("ti:" + w for w in words), "max_results": n})
    st, body = http_get(url, accept="application/atom+xml")
    return list(parse_arxiv_feed(body).values()) if st == 200 else []


# --- DBLP ---------------------------------------------------------------------

def _dblp_query(qs, h):
    st, d = get_json("https://dblp.org/search/publ/api?" + urllib.parse.urlencode(
        {"q": qs, "format": "json", "h": h}))
    if st != 200 or not isinstance(d, dict):
        return []
    return (((d.get("result") or {}).get("hits") or {}).get("hit")) or []


def dblp_search(title, h=6):
    words = fold(title).split()
    hits = _dblp_query(" ".join(words[:14]), h)
    if not hits and len(words) > 6:
        hits = _dblp_query(" ".join(sorted(words, key=len, reverse=True)[:6]), h)
    recs = []
    for hit in hits:
        info = hit.get("info") or {}
        au = (info.get("authors") or {}).get("author") or []
        if isinstance(au, dict):
            au = [au]
        authors = [name_from_full(a.get("text", "") if isinstance(a, dict) else str(a)) for a in au]
        venue = info.get("venue") or ""
        if isinstance(venue, list):
            venue = " / ".join(venue)
        vol = str(info.get("volume") or "")
        is_corr = fold(venue) in ("corr", "arxiv") or vol.startswith("abs/")
        ee = info.get("ee") or ""
        if isinstance(ee, list):
            ee = ee[0] if ee else ""
        recs.append(mkrec("dblp", title=html.unescape(info.get("title") or "").rstrip("."),
                          authors=authors, year=info.get("year"), venue=venue,
                          volume="" if is_corr else vol, number=info.get("number") or "",
                          pages=info.get("pages") or "", doi=(info.get("doi") or "").lower(),
                          type=info.get("type") or "", preprint=is_corr,
                          arxiv=vol[4:] if vol.startswith("abs/") else "",
                          url=info.get("url") or "", link=ee, dblp_key=info.get("key") or ""))
    return recs


# --- OpenAlex -----------------------------------------------------------------

def _oa_url(path, params=None):
    p = dict(params or {})
    if MAILTO:
        p["mailto"] = MAILTO
    if OPENALEX_KEY:
        p["api_key"] = OPENALEX_KEY
    return "https://api.openalex.org/" + path + ("?" + urllib.parse.urlencode(p) if p else "")


def from_openalex(w):
    if not isinstance(w, dict) or not (w.get("display_name") or w.get("title")):
        return None
    authors = [name_from_full(((a.get("author") or {}).get("display_name")) or a.get("raw_author_name") or "")
               for a in (w.get("authorships") or [])]
    src = ((w.get("primary_location") or {}).get("source")) or {}
    b = w.get("biblio") or {}
    fp, lp = b.get("first_page") or "", b.get("last_page") or ""
    pages = fp + ("--" + lp if lp and lp != fp else "")
    doi = norm_doi(w.get("doi") or "")
    typ = w.get("type") or ""
    alts = [((loc.get("source") or {}).get("display_name") or "") for loc in (w.get("locations") or [])]
    return mkrec("openalex", title=w.get("display_name") or w.get("title"), authors=authors,
                 year=w.get("publication_year"), venue=src.get("display_name") or "",
                 venue_alts=[a for a in alts if a], volume=b.get("volume") or "",
                 number=b.get("issue") or "", pages=pages, doi=doi, type=typ,
                 preprint=(typ == "preprint" or src.get("type") == "repository" or is_preprint_doi(doi)),
                 retracted=bool(w.get("is_retracted")), url=w.get("id") or "")


def openalex_by_doi(doi):
    st, d = get_json(_oa_url("works/doi:" + q(doi)))
    return from_openalex(d) if st == 200 else None


def openalex_search(title, n=5):
    st, d = get_json(_oa_url("works", {"filter": "title.search:" + fold(title), "per-page": n}))
    if st != 200 or not isinstance(d, dict):
        return []
    return [r for r in (from_openalex(w) for w in d.get("results") or []) if r]


# --- Semantic Scholar -----------------------------------------------------------

S2_FIELDS = "title,authors,year,venue,publicationVenue,externalIds,journal,publicationDate,url"


def from_s2(p):
    if not isinstance(p, dict) or not p.get("title"):
        return None
    ext = p.get("externalIds") or {}
    j = p.get("journal") or {}
    pv = p.get("publicationVenue") or {}
    venue = p.get("venue") or pv.get("name") or j.get("name") or ""
    doi = (ext.get("DOI") or "").lower()
    pre_venue = fold(venue) in ("", "arxiv", "arxiv org", "corr", "biorxiv", "medrxiv", "ssrn")
    vol = str(j.get("volume") or "")
    if vol.lower().startswith("abs/"):
        vol = ""
    alts = [x for x in [j.get("name"), pv.get("name")] + list(pv.get("alternate_names") or []) if x]
    return mkrec("s2", title=p["title"],
                 authors=[name_from_full(a.get("name") or "") for a in (p.get("authors") or [])],
                 year=p.get("year"), venue=venue, venue_alts=alts, volume=vol,
                 pages=(j.get("pages") or "").strip(), doi=doi, arxiv=ext.get("ArXiv") or "",
                 preprint=pre_venue and (not doi or is_preprint_doi(doi)),
                 url=p.get("url") or "")


def _s2_get(path, params):
    url = "https://api.semanticscholar.org/graph/v1/" + path + "?" + urllib.parse.urlencode(params)
    return get_json(url, headers={"x-api-key": S2_KEY} if S2_KEY else None, tries=3)


def s2_paper(pid):
    st, d = _s2_get("paper/" + urllib.parse.quote(pid, safe=":/"), {"fields": S2_FIELDS})
    return from_s2(d) if st == 200 else None


def s2_match(title):
    st, d = _s2_get("paper/search/match", {"query": latex_to_text(title), "fields": S2_FIELDS})
    if st != 200 or not isinstance(d, dict) or not d.get("data"):
        return None
    return from_s2(d["data"][0])


# --- bioRxiv / medRxiv, Open Library ----------------------------------------------

def biorxiv_published(doi):
    for server in ("biorxiv", "medrxiv"):
        st, d = get_json("https://api.biorxiv.org/details/%s/%s" % (server, doi))
        coll = (d or {}).get("collection") or [] if isinstance(d, dict) else []
        if coll:
            pub = str(coll[-1].get("published") or "")
            return norm_doi(pub) if pub and pub.upper() != "NA" else ""
    return ""


def openlibrary_search(title, author=""):
    p = {"title": fold(title), "limit": 5,
         "fields": "title,subtitle,author_name,first_publish_year,publish_year,publisher,key"}
    if author:
        p["author"] = fold(author)
    st, d = get_json("https://openlibrary.org/search.json?" + urllib.parse.urlencode(p))
    if st != 200 or not isinstance(d, dict):
        return []
    recs = []
    for doc in d.get("docs") or []:
        t = doc.get("title") or ""
        if doc.get("subtitle"):
            t += ": " + doc["subtitle"]
        recs.append(mkrec("openlibrary", title=t, main_title=doc.get("title") or "",
                          authors=[name_from_full(a) for a in doc.get("author_name") or []],
                          year=doc.get("first_publish_year"), years=doc.get("publish_year") or [],
                          venue="", publisher="; ".join((doc.get("publisher") or [])[:3]),
                          type="book", url="https://openlibrary.org" + (doc.get("key") or "")))
    return recs


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def _sim(a, b):
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a.replace(" ", "") == b.replace(" ", ""):
        return 0.99
    r = difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    if len(short.split()) >= 4 and long_.startswith(short):
        r = max(r, 0.92)  # subtitle present on one side only
    return r


def title_sim(bib_title, rec):
    a = fold(bib_title)
    cands = {rec["title"], rec.get("main_title") or rec["title"]}
    return max(_sim(a, fold(t, markup=True)) for t in cands)


def same_work(title, bib_authors, rec, lenient=False):
    ts = title_sim(title, rec)
    ao = author_overlap(bib_authors, rec["authors"])
    if lenient:  # identifier given in the entry: only reject clear mismatches
        ok = ts >= 0.75 or (ts >= 0.45 and (ao or 0) >= 0.5)
    elif ao is None:
        ok = ts >= 0.93
    else:
        ok = ((ts >= 0.9 and ao >= 0.3) or (ts >= 0.8 and ao >= 0.6)
              or (ts >= 0.97 and len(fold(title).split()) >= 6))
    return ok, ts, ao


VSTOP = {"of", "the", "and", "on", "in", "for", "at", "a", "an", "to", "with"}
GENERIC_ACR = {"ieee", "acm", "cvf", "siam", "lncs", "pmlr", "usa", "uk", "proc", "ccis",
               "ifip", "springer", "elsevier", "press"}
VENUE_ALIASES = [
    ("neurips", "nips", "neural information processing systems"),
    ("icml", "international conference on machine learning"),
    ("iclr", "international conference on learning representations"),
    ("cvpr", "computer vision and pattern recognition"),
    ("iccv", "international conference on computer vision"),
    ("eccv", "european conference on computer vision"),
    ("aistats", "artificial intelligence and statistics"),
    ("uai", "uncertainty in artificial intelligence"),
    ("colt", "conference on learning theory"),
    ("jmlr", "journal of machine learning research", "j mach learn res"),
    ("tmlr", "transactions on machine learning research"),
    ("tpami", "pami", "pattern analysis and machine intelligence"),
    ("ijcv", "international journal of computer vision"),
    ("aaai", "aaai conference on artificial intelligence"),
    ("ijcai", "international joint conference on artificial intelligence"),
    ("acl", "annual meeting of the association for computational linguistics"),
    ("naacl", "north american chapter of the association for computational linguistics"),
    ("eacl", "european chapter of the association for computational linguistics"),
    ("emnlp", "empirical methods in natural language processing"),
    ("coling", "international conference on computational linguistics"),
    ("tacl", "transactions of the association for computational linguistics"),
    ("kdd", "knowledge discovery and data mining"),
    ("www", "the web conference", "world wide web conference"),
    ("sigir", "research and development in information retrieval"),
    ("chi", "human factors in computing systems"),
    ("icra", "international conference on robotics and automation"),
    ("iros", "intelligent robots and systems"),
    ("corl", "conference on robot learning"),
    ("rss", "robotics science and systems"),
    ("miccai", "medical image computing and computer assisted intervention"),
    ("icassp", "acoustics speech and signal processing"),
    ("pnas", "proceedings of the national academy of sciences"),
    ("stoc", "symposium on theory of computing"),
    ("focs", "foundations of computer science"),
    ("soda", "symposium on discrete algorithms"),
    ("osdi", "operating systems design and implementation"),
    ("sosp", "symposium on operating systems principles"),
    ("nsdi", "networked systems design and implementation"),
    ("ccs", "computer and communications security"),
    ("pldi", "programming language design and implementation"),
    ("popl", "principles of programming languages"),
    ("icse", "international conference on software engineering"),
    ("wacv", "winter conference on applications of computer vision"),
    ("bmvc", "british machine vision conference"),
    ("lrec", "language resources and evaluation"),
]


def _vwords(s):
    return [w for w in fold(s, markup=True).split()
            if w not in VSTOP and not re.fullmatch(r"\d+(st|nd|rd|th)?", w)]


def _is_subseq(a, b):
    it = iter(b)
    return all(c in it for c in a)


def _abbr(a, b):
    return a == b or (a[0] == b[0] and _is_subseq(a, b))


def _alias_groups(s):
    fs = " " + fold(s, markup=True) + " "
    return {i for i, g in enumerate(VENUE_ALIASES) if any(" " + a + " " in fs for a in g)}


def _acronyms(s):
    found = re.findall(r"\b[A-Z][A-Za-z]*[A-Z][A-Za-z]*\b", latex_to_text(clean(s)))
    return {fold(x) for x in found if fold(x) not in GENERIC_ACR and len(fold(x)) >= 2}


def venue_jaccard(a, b):
    A, B = set(_vwords(a)), set(_vwords(b))
    return len(A & B) / float(len(A | B)) if A and B else 0.0


def venue_match(bv, rv):
    A, B = _vwords(bv), _vwords(rv)
    if not A or not B:
        return False
    if A == B or "".join(A) == "".join(B):
        return True
    if len(A) == len(B) and (all(_abbr(x, y) for x, y in zip(A, B))
                             or all(_abbr(y, x) for x, y in zip(A, B))):
        return True
    sa, sb = set(A), set(B)
    if len(sa & sb) / float(len(sa | sb)) >= 0.6:
        return True
    if len(sa) >= 3 and sa <= sb or len(sb) >= 3 and sb <= sa:
        return True
    if _alias_groups(bv) & _alias_groups(rv):
        return True
    ini_a, ini_b = "".join(w[0] for w in A), "".join(w[0] for w in B)
    for ac in _acronyms(bv):
        if ac in sb or (len(ac) >= 3 and ac in ini_b):
            return True
    for ac in _acronyms(rv):
        if ac in sa or (len(ac) >= 3 and ac in ini_a):
            return True
    return False


def page_parts(p):
    parts = [x for x in re.split(r"\s*[-\u2010-\u2015]+\s*", latex_to_text(p).strip()) if x]

    def n(x):
        return re.sub(r"^[a-z]+", "", re.sub(r"[^0-9a-z]", "", x.lower()))
    first = n(parts[0]) if parts else ""
    last = n(parts[-1]) if len(parts) > 1 else ""
    if last.isdigit() and first.isdigit() and len(last) < len(first):
        last = first[:len(first) - len(last)] + last  # 1234--45 means 1234--1245
    return first, last


def _norm_vol(v):
    d = re.sub(r"\D", "", latex_to_text(v))
    return d or fold(v)


def compare_fields(e, recs, bib_authors, truncated, add, cites_pre, doi, identity_only=False):
    f = e["fields"]
    title = f.get("title", "")
    recs = by_priority(recs)

    best = max(recs, key=lambda r: (round(title_sim(title, r), 3), -SOURCE_PRIORITY.get(r["source"], 9)))
    ts = title_sim(title, best)
    if ts < 0.9:
        add("error", "title_mismatch", 'Title differs from the record: "%s" [%s]' % (clean(best["title"]), best["source"]))
    elif ts < 0.985:
        add("warning", "title_differs", 'Title differs slightly from the record: "%s" [%s]' % (clean(best["title"]), best["source"]))

    if bib_authors:
        chosen = None
        for r in recs:
            if not r["authors"]:
                continue
            af = author_findings(bib_authors, truncated, r["authors"])
            score = (sum(1 for x in af if x[0] == "error"), len(af))
            if chosen is None or score < chosen[0]:
                chosen = (score, af, r)
        if chosen and chosen[1]:
            for sev, code, msg in chosen[1]:
                add(sev, code, msg)
            add("info", "record_authors", "%s lists: %s" % (chosen[2]["source"], fmt_authors(chosen[2]["authors"], 25)))
    else:
        add("warning", "no_authors", "Entry has no author/editor field.")

    if any(r.get("retracted") for r in recs):
        add("error", "retracted", "The record is marked as retracted/withdrawn.")

    if identity_only:
        return

    by = bib_year(f)
    years = sorted({y for r in recs for y in r["years"]})
    if years:
        if by is None:
            add("warning", "no_year", "Entry has no year; record says %s." % "/".join(map(str, years)))
        elif by not in years:
            dist = min(abs(by - y) for y in years)
            add("warning" if dist == 1 else "error", "year_mismatch",
                "Year %d does not match the record (%s)." % (by, "/".join(map(str, years))))

    bv = bib_venue(f)
    if bv and not cites_pre:
        rvs = [v for r in recs for v in [r["venue"]] + r["venue_alts"] if v]
        if rvs and not any(venue_match(bv, v) for v in rvs):
            jac = max(venue_jaccard(bv, v) for v in rvs)
            strong = e["type"] == "article" and any(
                r["source"] in ("crossref", "doi.org") and r["type"] == "journal-article" for r in recs)
            add("error" if strong and jac < 0.2 else "warning", "venue_mismatch",
                'Venue "%s" does not match the record ("%s").' % (latex_to_text(bv), '" / "'.join(
                    sorted({clean(v) for v in rvs})[:4])))

    def simple(bkey, rkey, sev, code, label):
        bvv = f.get(bkey, "")
        vals = [r[rkey] for r in recs if r.get(rkey)]
        if not bvv or not vals:
            return
        nb = _norm_vol(bvv)
        if nb and not any(_norm_vol(v) == nb for v in vals):
            add(sev, code, '%s "%s" does not match the record (%s).' % (
                label, latex_to_text(bvv), ", ".join(sorted(set(vals)))))

    simple("volume", "volume", "error" if e["type"] == "article" else "warning", "volume_mismatch", "Volume")
    simple("number", "number", "warning", "number_mismatch", "Number/issue")

    bp = f.get("pages", "")
    rps = [(r["pages"], r["pages_is_article_number"]) for r in recs if r["pages"]]
    if bp and rps:
        bf, bl = page_parts(bp)
        if bf and not any(page_parts(p)[0] == bf for p, _ in rps):
            add("warning" if all(a for _, a in rps) else "error", "pages_mismatch",
                'Pages "%s" do not match the record (%s).' % (latex_to_text(bp), ", ".join(sorted({p for p, _ in rps}))))
        elif bl and not any(page_parts(p)[1] in ("", bl) for p, _ in rps):
            add("warning", "last_page_mismatch",
                'Last page of "%s" differs from the record (%s).' % (latex_to_text(bp), ", ".join(sorted({p for p, _ in rps}))))

    if not cites_pre and not doi:
        d = next((r["doi"] for r in recs if r["doi"] and not is_preprint_doi(r["doi"])), "")
        if d:
            add("info", "doi_available", "Record has DOI %s (entry has none)." % d)


# ---------------------------------------------------------------------------
# Checking one entry
# ---------------------------------------------------------------------------

def finalize(res):
    codes = {x["code"] for x in res["findings"]}
    errs = [x for x in res["findings"] if x["severity"] == "error"]
    warns = [x for x in res["findings"] if x["severity"] == "warning"]
    if "not_found" in codes:
        s = "not_found"
    elif codes & {"doi_not_found", "doi_mismatch", "arxiv_not_found", "arxiv_mismatch", "arxiv_id_malformed"}:
        s = "bad_identifier"
    elif "retracted" in codes:
        s = "retracted"
    elif any(x["code"] != "preprint_has_published_version" for x in errs):
        s = "mismatch"
    elif "preprint_has_published_version" in codes:
        s = "preprint_published"
    elif codes & {"unverified", "no_title"}:
        s = "unverified"
    elif warns:
        s = "review"
    else:
        s = "ok"
    res["status"] = s
    if s == "ok":
        res["suggest"] = None
    return res


def check_entry(e, arxiv_recs):
    f = e["fields"]
    title = f.get("title", "")
    res = {"key": e["key"], "type": e["type"], "line": e["line"], "title": latex_to_text(title),
           "status": "ok", "findings": [], "matched": [], "near_misses": [],
           "published_version": None, "suggest": None}

    def add(sev, code, msg):
        res["findings"].append({"severity": sev, "code": code, "msg": msg})

    bib_authors, truncated = bib_author_list(f.get("author") or f.get("editor") or "")
    first_fam = bib_authors[0]["family"] if bib_authors else ""
    doi = norm_doi(f.get("doi", "")) or doi_from_url(f.get("url", ""))
    arx = extract_arxiv(f)
    pre = cites_preprint(e, doi, arx)
    by = bib_year(f)
    res.update({"doi": doi, "arxiv": arx, "cites_preprint": pre})

    if not fold(title):
        add("warning", "no_title", "Entry has no title; verify manually.")
        return finalize(res)

    same, rejected, seen = [], [], set()

    def consider(rec, linked=False, lenient=False):
        if not rec:
            return False
        ident = (rec["source"], rec["doi"] or rec["arxiv"] or rec["dblp_key"] or rec["url"] or fold(rec["title"]))
        if ident in seen:
            return False
        seen.add(ident)
        rec = dict(rec)
        ok, ts, ao = same_work(title, bib_authors, rec, lenient)
        rec["_title_sim"], rec["_author_overlap"] = ts, ao
        if ok or linked:
            same.append(rec)
            return True
        rejected.append(rec)
        return False

    # 1. The DOI given in the entry.
    if doi and not doi.startswith("10.48550/"):
        rec, state = resolve_doi(doi)
        if state == "not_found":
            add("error", "doi_not_found", "DOI %s is not registered at doi.org." % doi)
        elif state == "unknown":
            add("warning", "doi_unchecked", "Could not resolve DOI %s (network/agency problem); open https://doi.org/%s." % (doi, doi))
        elif state == "no_metadata":
            add("info", "doi_no_metadata", "DOI %s exists but no metadata was returned; check https://doi.org/%s." % (doi, doi))
        elif rec and not consider(rec, lenient=True):
            add("error", "doi_mismatch", 'DOI %s belongs to a different work: "%s" (%s, %s).' % (
                doi, clean(rec["title"]), fmt_authors(rec["authors"], 3), rec["year"]))

    # 2. The arXiv identifier given in the entry.
    if arx:
        problem = arxiv_id_problem(arx)
        if problem:
            add("error", "arxiv_id_malformed", problem)
        rec, state = (arxiv_recs[arx], "ok") if arx in arxiv_recs else arxiv_abs(arx)
        if state == "not_found":
            add("error", "arxiv_not_found", "arXiv:%s does not exist." % arx)
        elif state == "unknown" and not problem:
            add("warning", "arxiv_unchecked", "Could not fetch arXiv:%s; open https://arxiv.org/abs/%s." % (arx, arx))
        elif rec and not consider(rec, lenient=True):
            add("error", "arxiv_mismatch", 'arXiv:%s is a different paper: "%s" (%s).' % (
                arx, clean(rec["title"]), fmt_authors(rec["authors"], 3)))
        idy = arxiv_id_year(arx)
        if pre and by and idy and by < idy:
            add("error", "year_before_arxiv", "Year %d is earlier than the arXiv submission (%s => %d)." % (by, arx, idy))

    # 3. For preprints: identifier-level links to the published version.
    if pre:
        linked = set()
        for r in list(same):
            if r["published_doi"] and not is_preprint_doi(r["published_doi"]):
                linked.add(r["published_doi"])
            if r.get("journal_ref"):
                res["journal_ref"] = r["journal_ref"]
        if arx:
            s2 = s2_paper("ARXIV:" + arx)
            if s2:
                if s2["doi"] and not is_preprint_doi(s2["doi"]):
                    linked.add(s2["doi"])
                elif not s2["preprint"]:
                    consider(s2, linked=True)
        if doi.startswith("10.1101/"):
            p = biorxiv_published(doi)
            if p:
                linked.add(p)
        for d in sorted(linked):
            rec, _ = resolve_doi(d)
            if rec:
                rec["preprint"] = False
                consider(rec, linked=True)

    # 4. Bibliographic search.
    if not any(not r["preprint"] for r in same):
        if pre and not arx:
            for rec in arxiv_search(title):
                consider(rec)
        for rec in crossref_search(title, first_fam):
            consider(rec)
        for rec in dblp_search(title):
            consider(rec)
    if not same:
        for rec in openalex_search(title):
            consider(rec)
    if not same:
        consider(s2_match(title))
    if not same and not (pre and not arx):
        for rec in arxiv_search(title):
            consider(rec)
    if not same and e["type"] == "book":
        for rec in openlibrary_search(title, first_fam):
            consider(rec)

    pubs = by_priority([r for r in same if not r["preprint"]])

    # 5. Retraction status / corroboration from OpenAlex for published works.
    if not pre and pubs:
        pub_doi = next((r["doi"] for r in pubs if r["doi"] and not is_preprint_doi(r["doi"])), "")
        if pub_doi and not any(r["source"] == "openalex" for r in same):
            oa = openalex_by_doi(pub_doi)
            if oa:
                oa["preprint"] = False
                consider(oa, linked=True)
                pubs = by_priority([r for r in same if not r["preprint"]])
    pres = by_priority([r for r in same if r["preprint"]])
    res["matched"] = [summarize(r) for r in (pubs + pres)[:6]]

    if not same:
        near = sorted(rejected, key=lambda r: -r["_title_sim"])[:3]
        res["near_misses"] = [summarize(r) for r in near if r["_title_sim"] >= 0.5]
        if pre or arx or doi or e["type"] not in UNVERIFIABLE_TYPES:
            add("error", "not_found", "No matching record in Crossref, DBLP, OpenAlex, Semantic Scholar or arXiv%s. "
                "Possibly fabricated - verify manually." % (" (closest candidates listed)" if res["near_misses"] else ""))
        else:
            add("warning", "unverified", "@%s entry not found in scholarly indexes; verify manually." % e["type"])
        return finalize(res)

    venue = bib_venue(f)
    if pre:
        if pres:
            compare_fields(e, pres, bib_authors, truncated, add, True, doi)
        else:
            compare_fields(e, pubs, bib_authors, truncated, add, True, doi, identity_only=True)
        if pubs:
            res["published_version"] = summarize(pubs[0])
            res["suggest"] = suggestion(pubs[0])
            add("error", "preprint_has_published_version",
                "Cited as a preprint, but a published version exists: " + cite_line(pubs[0]))
        else:
            if res.get("journal_ref"):
                add("warning", "preprint_journal_ref",
                    'arXiv journal_ref says "%s" - a published version probably exists; locate it.' % res["journal_ref"])
            res["suggest"] = suggestion(pres[0])
    elif pubs:
        compare_fields(e, pubs, bib_authors, truncated, add, False, doi)
        res["suggest"] = suggestion(pubs[0])
    elif venue:
        compare_fields(e, pres, bib_authors, truncated, add, True, doi, identity_only=True)
        add("warning", "venue_unconfirmed", 'Only a preprint was found (%s); the claimed venue "%s" could not be confirmed.'
            % (cite_line(pres[0]), latex_to_text(venue)))
        res["suggest"] = suggestion(pres[0])
    else:
        compare_fields(e, pres, bib_authors, truncated, add, True, doi)
        res["suggest"] = suggestion(pres[0])
    return finalize(res)


def safe_check(e, arxiv_recs):
    try:
        return check_entry(e, arxiv_recs)
    except Exception as ex:  # keep going; report the entry for manual checking
        return {"key": e["key"], "type": e["type"], "line": e["line"],
                "title": latex_to_text(e["fields"].get("title", "")), "status": "error",
                "findings": [{"severity": "error", "code": "internal_error",
                              "msg": "%s: %s" % (type(ex).__name__, ex),
                              "trace": traceback.format_exc(limit=4)}],
                "matched": [], "near_misses": [], "published_version": None, "suggest": None}


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

ORDER = ["not_found", "bad_identifier", "retracted", "mismatch", "preprint_published",
         "review", "unverified", "error", "ok"]
STATUS_HELP = {
    "not_found": "No matching record anywhere - possible fabrication; verify manually.",
    "bad_identifier": "DOI/arXiv id unregistered, malformed, or pointing to a different work.",
    "retracted": "The cited work has been retracted or withdrawn.",
    "mismatch": "Fields contradict the published record.",
    "preprint_published": "Preprint cited although a published version exists.",
    "review": "Minor differences or unconfirmed claims - check and decide.",
    "unverified": "Not checkable through scholarly APIs - verify manually.",
    "error": "Script error on this entry - verify manually.",
    "ok": "Matches the record.",
}
SEV = {"error": "ERROR", "warning": "warn", "info": "info"}


def render_md(results, bibpath, dupes, missing_keys):
    counts = {s: sum(1 for r in results if r["status"] == s) for s in ORDER}
    out = ["# Bibliography verification: %s" % bibpath, "",
           "Checked %d entries on %s." % (len(results), time.strftime("%Y-%m-%d")), "",
           "| status | count | meaning |", "|---|---|---|"]
    for s in ORDER:
        if counts[s]:
            out.append("| %s | %d | %s |" % (s, counts[s], STATUS_HELP[s]))
    out.append("")
    if missing_keys:
        out += ["**Cited but not defined in the .bib:** " + ", ".join(sorted(missing_keys)), ""]
    if dupes:
        out.append("**Possible duplicate entries:** " + "; ".join(", ".join(g) for g in dupes))
        out.append("")
    for s in ORDER[:-1]:
        group = [r for r in results if r["status"] == s]
        if not group:
            continue
        out += ["## %s (%d)" % (s, len(group)), ""]
        for r in group:
            out.append("### `%s`  (line %s, @%s)" % (r["key"], r["line"], r["type"]))
            out.append("- bib title: %s" % r["title"])
            for x in r["findings"]:
                out.append("- **%s** `%s` %s" % (SEV.get(x["severity"], x["severity"]), x["code"], x["msg"]))
            for m in r.get("near_misses") or []:
                out.append("- closest candidate (sim %.2f): \"%s\" - %s, %s, %s %s" % (
                    m.get("title_similarity", 0), m.get("title", ""), m.get("authors", ""),
                    m.get("venue", ""), m.get("year", ""), m.get("doi") or m.get("url", "")))
            ev = ["%s: %s" % (m["source"], m.get("doi") or m.get("url") or m.get("arxiv", "")) for m in r.get("matched") or []]
            if ev:
                out.append("- evidence: " + "; ".join(ev[:5]))
            if r.get("suggest"):
                out.append("- record values: `%s`" % json.dumps(r["suggest"], ensure_ascii=False))
            out.append("")
    ok = [r["key"] for r in results if r["status"] == "ok"]
    if ok:
        out += ["## ok (%d)" % len(ok), "", ", ".join(ok), ""]
    return "\n".join(out)


def find_duplicates(entries):
    by = {}
    for e in entries:
        d = norm_doi(e["fields"].get("doi", ""))
        t = fold(e["fields"].get("title", ""))
        if d:
            by.setdefault("doi:" + d, set()).add(e["key"])
        if len(t) > 20:
            by.setdefault("title:" + t, set()).add(e["key"])
    groups = {frozenset(v) for v in by.values() if len(v) > 1}
    return sorted(sorted(g) for g in groups)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def run_check(args):
    with open(args.bib, encoding="utf-8", errors="replace") as fh:
        entries = parse_bibtex(fh.read())
    all_keys = {e["key"] for e in entries}
    missing_keys = set()
    if args.cited_in:
        keys = cited_keys(args.cited_in)
        if "*" not in keys:
            missing_keys = keys - all_keys
            entries = [e for e in entries if e["key"] in keys]
    if args.keys:
        wanted = {k.strip() for k in args.keys.split(",") if k.strip()}
        entries = [e for e in entries if e["key"] in wanted]
    print("Parsed %d entries to check from %s" % (len(entries), args.bib), file=sys.stderr, flush=True)

    ids = sorted({extract_arxiv(e["fields"]) for e in entries} - {""})
    ids_ok = [i for i in ids if not arxiv_id_problem(i)]
    arxiv_recs = arxiv_fetch(ids_ok) if ids_ok else {}

    results = [None] * len(entries)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = {ex.submit(safe_check, e, arxiv_recs): i for i, e in enumerate(entries)}
        for n, fut in enumerate(concurrent.futures.as_completed(futs), 1):
            i = futs[fut]
            results[i] = fut.result()
            print("[%d/%d] %s: %s" % (n, len(entries), results[i]["key"], results[i]["status"]),
                  file=sys.stderr, flush=True)

    dupes = find_duplicates(entries)
    report = {"bib": os.path.abspath(args.bib), "date": time.strftime("%Y-%m-%d"),
              "counts": {s: sum(1 for r in results if r["status"] == s) for s in ORDER},
              "cited_but_undefined": sorted(missing_keys), "duplicates": dupes,
              "entries": results}
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    md = render_md(results, args.bib, dupes, missing_keys)
    with open(args.md, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    print("\nJSON report: %s\nMarkdown report: %s" % (args.out, args.md))


def run_lookup(args):
    out = {}
    if args.doi:
        d = norm_doi(args.doi)
        rec, state = resolve_doi(d)
        out["doi"] = {"doi": d, "state": state, "record": summarize(rec) if rec else None}
        oa = openalex_by_doi(d)
        if oa:
            out["openalex"] = dict(summarize(oa), retracted=oa["retracted"])
    if args.arxiv:
        aid = re.sub(r"v\d+$", "", re.sub(r"^arxiv:", "", args.arxiv.strip(), flags=re.I))
        recs = arxiv_fetch([aid])
        rec, state = (recs[aid], "ok") if aid in recs else arxiv_abs(aid)
        out["arxiv"] = {"id": aid, "state": state, "record": summarize(rec) if rec else None}
        if rec:
            out["arxiv"]["published_doi"] = rec["published_doi"]
        s2 = s2_paper("ARXIV:" + aid)
        out["semantic_scholar"] = summarize(s2) if s2 else None
    if args.title:
        bib_authors = [parse_bib_name(args.author)] if args.author else []

        def score(recs):
            rows = []
            for r in recs:
                if not r:
                    continue
                ok, ts, ao = same_work(args.title, bib_authors, r)
                r["_title_sim"], r["_author_overlap"] = ts, ao
                rows.append(summarize(r))
            return sorted(rows, key=lambda x: -x.get("title_similarity", 0))
        out["crossref"] = score(crossref_search(args.title, args.author or ""))
        out["dblp"] = score(dblp_search(args.title))
        out["openalex"] = score(openalex_search(args.title))
        out["arxiv"] = score(arxiv_search(args.title))
        out["semantic_scholar"] = score([s2_match(args.title)])
    print(json.dumps(out, indent=2, ensure_ascii=False))


def run_bibtex(args):
    if args.doi:
        st, body = http_get("https://doi.org/" + q(norm_doi(args.doi)), accept="application/x-bibtex")
    elif args.arxiv:
        st, body = http_get("https://arxiv.org/bibtex/" + args.arxiv.strip(), accept="text/plain")
    else:
        st, body = http_get("https://dblp.org/rec/%s.bib" % args.dblp.strip(), accept="text/plain")
    if st != 200:
        print("Failed (HTTP %s): %s" % (st, body[:300]), file=sys.stderr)
        sys.exit(1)
    print(body.strip())


def main():
    global USE_CACHE
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="verify every entry of a .bib file")
    c.add_argument("bib")
    c.add_argument("--cited-in", nargs="+", metavar="FILE",
                   help=".tex/.aux files; only check keys cited there")
    c.add_argument("--keys", help="comma-separated keys to check")
    c.add_argument("--out", default="bibverify_report.json")
    c.add_argument("--md", default="bibverify_report.md")
    c.add_argument("--workers", type=int, default=4)
    c.add_argument("--no-cache", action="store_true")
    lk = sub.add_parser("lookup", help="show what each source says about one work")
    lk.add_argument("--doi")
    lk.add_argument("--arxiv")
    lk.add_argument("--title")
    lk.add_argument("--author", help="first author's surname (improves ranking)")
    lk.add_argument("--no-cache", action="store_true")
    bt = sub.add_parser("bibtex", help="print the BibTeX provided by the registry")
    g = bt.add_mutually_exclusive_group(required=True)
    g.add_argument("--doi")
    g.add_argument("--arxiv")
    g.add_argument("--dblp", help="DBLP key, e.g. conf/cvpr/HeZRS16")
    bt.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()
    USE_CACHE = not args.no_cache
    if args.cmd == "check":
        run_check(args)
    elif args.cmd == "lookup":
        if not (args.doi or args.arxiv or args.title):
            ap.error("lookup needs --doi, --arxiv or --title")
        run_lookup(args)
    else:
        run_bibtex(args)


if __name__ == "__main__":
    main()
