"""Shared helpers for the self-surveying-literature scripts (Python 3 standard library only)."""
import http.client as httpclient
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher

UA = "self-surveying-literature/1.0 (related-work audit)"
REC_FIELDS = ("paperId", "title", "abstract", "year", "venue", "citationCount",
              "publicationTypes", "publicationDate", "externalIds", "authors")
PREPRINT_VENUE_RE = re.compile(
    r"arxiv|\bcorr\b|biorxiv|medrxiv|ssrn|preprint|research square|techrxiv|chemrxiv|psyarxiv",
    re.I)


def warn(msg):
    print(f"[warn] {msg}", file=sys.stderr, flush=True)


def info(msg):
    print(msg, file=sys.stderr, flush=True)


class HTTPFailure(RuntimeError):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


_last_call = {}


def fetch(url, params=None, headers=None, body=None, accept=None, raw=False,
          retries=5, timeout=60, min_interval=0.0):
    """GET (or POST JSON `body`) with per-host throttling and retries on 429/5xx/network errors.

    Returns parsed JSON (or text if raw=True), or None on 404. Raises HTTPFailure otherwise.
    """
    if params:
        params = {k: v for k, v in params.items() if v is not None}
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    hdrs = {"User-Agent": UA}
    if accept:
        hdrs["Accept"] = accept
    if headers:
        hdrs.update(headers)
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    host = urllib.parse.urlparse(url).netloc
    delay = 2.0
    for attempt in range(retries):
        wait = min_interval - (time.time() - _last_call.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        _last_call[host] = time.time()
        req = urllib.request.Request(url, data=data, headers=hdrs,
                                     method="POST" if data is not None else "GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                text = resp.read().decode("utf-8", "replace")
            return text if raw else json.loads(text)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                ra = e.headers.get("Retry-After") if e.headers else None
                sleep = float(ra) if ra and ra.isdigit() else delay
                warn(f"HTTP {e.code} from {host}; retrying in {sleep:.0f}s")
                time.sleep(sleep)
                delay = min(delay * 2, 60)
                continue
            try:
                detail = e.read().decode("utf-8", "replace")[:400]
            except Exception:
                detail = ""
            raise HTTPFailure(e.code, f"HTTP {e.code} for {url[:300]}: {detail}")
        except (OSError, ValueError, httpclient.HTTPException) as e:
            if attempt < retries - 1:
                warn(f"{type(e).__name__} from {host}: {e}; retrying in {delay:.0f}s")
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            raise HTTPFailure(None, f"request failed for {url[:300]}: {e}")
    raise HTTPFailure(None, f"request failed for {url[:300]}")


# ---------------------------------------------------------------- files

def work_file(work, name):
    os.makedirs(work, exist_ok=True)
    return os.path.join(work, name)


def read_jsonl(path):
    out = []
    if not path or not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                warn(f"skipping malformed line in {path}")
    return out


def append_jsonl(path, recs):
    with open(path, "a", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_jsonl(path, recs):
    with open(path, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def log_query(work, source, query, n):
    with open(work_file(work, "queries.tsv"), "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M')}\t{source}\t{query}\t{n}\n")


# ---------------------------------------------------------------- text / ids

def norm_title(t):
    t = unicodedata.normalize("NFKD", t or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"\\[A-Za-z]+", " ", t)
    t = re.sub(r"[^a-z0-9]+", " ", t.lower())
    return " ".join(t.split())


def title_sim(a, b):
    na, nb = norm_title(a), norm_title(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


def identifiers(r):
    """Keys under which two records are considered the same paper."""
    out = []
    if r.get("paperId"):
        out.append("s2:" + r["paperId"])
    ext = r.get("externalIds") or {}
    if ext.get("DOI"):
        out.append("doi:" + str(ext["DOI"]).lower())
    if ext.get("ArXiv"):
        out.append("arxiv:" + str(ext["ArXiv"]).lower())
    if ext.get("DBLP"):
        out.append("dblp:" + str(ext["DBLP"]))
    nt = norm_title(r.get("title"))
    if len(nt) >= 25 and nt.count(" ") >= 3:
        out.append("t:" + nt)
    return out


def find_arxiv_id(text, bare_ok=False):
    """Extract an arXiv id from free text (requires the word 'arxiv' unless bare_ok)."""
    if not text:
        return None
    if not bare_ok and "arxiv" not in text.lower():
        return None
    m = re.search(r"(?<![\d.])(\d{4}\.\d{4,5})(?:v\d+)?(?!\d)", text)
    if m:
        return m.group(1)
    m = re.search(r"\b([a-z][a-z\-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?\b", text, re.I)
    return m.group(1) if m else None


def clean_doi(d):
    if not d:
        return None
    d = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", str(d).strip(), flags=re.I)
    m = re.search(r"10\.\d{4,9}/\S+", d)
    return m.group(0).rstrip(".,;}") if m else None


_ACCENT_RE = re.compile(
    r"\\(?:[`'^\"~=.]\s*\{?|[uvHtcdbkr](?:\s*\{|\s+))\s*\\?([A-Za-z])\s*\}?")
_SPECIAL = {"ss": "ss", "o": "o", "O": "O", "l": "l", "L": "L", "ae": "ae", "AE": "AE",
            "oe": "oe", "OE": "OE", "aa": "a", "AA": "A", "i": "i", "j": "j"}


def tex_to_text(s):
    """Rough LaTeX -> plain text for short strings such as titles and author lists."""
    if not s:
        return ""
    s = _ACCENT_RE.sub(r"\1", s)
    s = re.sub(r"\\(ss|o|O|l|L|ae|AE|oe|OE|aa|AA|i|j)(?![A-Za-z])",
               lambda m: _SPECIAL[m.group(1)], s)
    s = re.sub(r"\\([&%$#_])", r"\1", s)
    s = re.sub(r"\\[A-Za-z]+\*?", " ", s)
    s = s.replace("{", "").replace("}", "").replace("~", " ").replace("$", "")
    s = s.replace("\\", " ")
    return " ".join(s.split())


# ---------------------------------------------------------------- records

def make_rec(kind, tag, seed=None, rank=None, **f):
    """Common candidate-record shape used by every source."""
    r = {k: f.get(k) for k in REC_FIELDS}
    r["externalIds"] = {k: v for k, v in (r["externalIds"] or {}).items() if v}
    r["authors"] = r["authors"] or []
    r["_kind"] = kind
    r["_tag"] = tag
    if seed:
        r["_seed"] = seed
    if rank is not None:
        r["_rank"] = rank
    return r


def short_authors(authors, n=3):
    a = [x for x in (authors or []) if x]
    return ", ".join(a[:n]) + (" et al." if len(a) > n else "")


def print_brief(recs, n):
    for r in recs[:n]:
        ext = r.get("externalIds") or {}
        ident = r.get("paperId") or (f"ARXIV:{ext['ArXiv']}" if ext.get("ArXiv") else "") \
            or (f"DOI:{ext['DOI']}" if ext.get("DOI") else "") \
            or (f"DBLP:{ext['DBLP']}" if ext.get("DBLP") else "")
        cc = r.get("citationCount")
        extra = f"; {cc} cites" if cc is not None else ""
        print(f"{str(r.get('_rank', '-')):>3}. [{r.get('year') or '----'}] {r.get('title')}"
              f"  ({r.get('venue') or '?'}{extra})  {ident}")
