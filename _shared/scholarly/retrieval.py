"""The only network boundary for every scholarly skill. Stdlib only."""
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from .textnorm import strip_dblp_suffix

def _contact():
    """Contact address for the API "polite pools", or "" when unset.

    Crossref and OpenAlex give faster, more reliable service to requests that
    identify a contact address, and arXiv asks for one. It is optional
    everywhere: without it the code still works, just in the anonymous pool.

    Set SCHOLARLY_MAILTO, or write the address to ~/.config/scholarly/mailto.
    """
    value = os.environ.get("SCHOLARLY_MAILTO", "").strip()
    if value:
        return value
    try:
        with open(os.path.expanduser("~/.config/scholarly/mailto"),
                  encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


MAILTO = _contact()
UA = "scholarly/0.1 (+https://github.com/chgagne/claude-skills-research)"
if MAILTO:
    UA = f"scholarly/0.1 (mailto:{MAILTO})"


def _mailto_param(prefix="&"):
    """'&mailto=...' when a contact is configured, otherwise nothing."""
    return f"{prefix}mailto={MAILTO}" if MAILTO else ""
def default_cache_dir():
    return os.path.expanduser("~/.cache/scholarly")


_CACHE_DIR = default_cache_dir()
_last_hit = {}


def set_cache_dir(path):
    global _CACHE_DIR
    _CACHE_DIR = path


@dataclass
class Record:
    title: str = ""
    authors: list = field(default_factory=list)
    venue: str = ""
    year: int = None
    volume: str = None
    issue: str = None
    pages: str = None
    doi: str = None
    source: str = ""
    strong: bool = False


# DBLP drops connections under a 1 req/s burst (RemoteDisconnected, sporadic
# 500s). Semantic Scholar grants 1 req/s on an API key -- stay just above the
# line so clock jitter cannot put two requests inside the same second. arXiv
# asks for 3s between requests and answers 429 for a long while once annoyed.
_HOST_DELAY = {"dblp.org": 2.5, "api.semanticscholar.org": 1.1,
               "export.arxiv.org": 3.0}
_DEFAULT_DELAY = 1.0
_RETRIES = 3
_TIMEOUT = 15
# Longest Retry-After worth waiting for. Beyond this the host is unavailable for
# this run (OpenAlex signals an exhausted daily budget with ~21 hours).
_MAX_RETRY_AFTER = 30

# Hosts that failed even after retries, so a run can report that its source
# coverage was degraded rather than silently returning fewer findings.
SOURCE_FAILURES = {}

# Circuit breaker. Retrying is right for one flaky request and catastrophic for
# a host that is down: 3 attempts x 15s timeout x every entry turns a 5-minute
# run into a 6-hour one. After this many consecutive failures, stop asking.
_BREAKER_THRESHOLD = 3
_consecutive_failures = {}
HOSTS_DISABLED = set()


def reset_breaker():
    _consecutive_failures.clear()
    HOSTS_DISABLED.clear()
    SOURCE_FAILURES.clear()


def _throttle(host, seconds=None):
    if seconds is None:
        seconds = _HOST_DELAY.get(host, _DEFAULT_DELAY)
    now = time.time()
    wait = _last_hit.get(host, 0) + seconds - now
    if wait > 0:
        time.sleep(wait)
    _last_hit[host] = time.time()


def _raw_get(url, extra_headers=None):
    headers = {"User-Agent": UA}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return resp.read()


S2_KEY_FILE = os.path.expanduser("~/.config/scholarly/s2_key")


def s2_api_key():
    """Key from the environment, else from a 0600 key file. Never logged."""
    key = os.environ.get("S2_API_KEY", "").strip()
    if key:
        return key
    try:
        with open(S2_KEY_FILE, encoding="utf-8") as fh:
            return fh.read().strip() or None
    except OSError:
        return None


def _get_with_retry(url, host, extra_headers=None):
    """Retry transient failures with backoff. A 404/410 is definitive and re-raised."""
    delay = 1.0
    for attempt in range(_RETRIES):
        try:
            return _raw_get(url, extra_headers)
        except urllib.error.HTTPError as exc:
            if exc.code in (404, 410):
                raise
            if exc.code == 429:
                # Honour the server's guidance, but only within reason. OpenAlex
                # answers an exhausted daily budget with Retry-After: 77547 --
                # 21.5 hours. Sleeping that is indistinguishable from a hang, so
                # anything beyond the cap means "unavailable for this run": open
                # the circuit immediately rather than waiting.
                try:
                    wait = float(exc.headers.get("Retry-After") or 0)
                except (TypeError, ValueError):
                    wait = 0.0
                if wait > _MAX_RETRY_AFTER:
                    HOSTS_DISABLED.add(host)
                    SOURCE_FAILURES[host] = SOURCE_FAILURES.get(host, 0) + 1
                    raise
                delay = max(delay, wait)
            last = exc
        except Exception as exc:
            last = exc
        if attempt < _RETRIES - 1:
            time.sleep(delay)
            delay *= 2
    SOURCE_FAILURES[host] = SOURCE_FAILURES.get(host, 0) + 1
    raise last


def _cache_path(url):
    os.makedirs(_CACHE_DIR, exist_ok=True)
    return os.path.join(_CACHE_DIR, hashlib.sha256(url.encode()).hexdigest() + ".cache")


def get_bytes(url, extra_headers=None):
    """Fetch with an on-disk cache.

    A definitive negative (404/410) is cached as an empty file so an unresolvable
    DOI is not re-requested on every run. Transient failures (timeouts, 5xx) are
    not cached, so an outage does not poison the cache permanently.
    """
    p = _cache_path(url)
    if os.path.exists(p):
        with open(p, "rb") as fh:
            return fh.read() or None
    host = urllib.parse.urlparse(url).netloc
    if host in HOSTS_DISABLED:          # circuit open: fail fast, do not wait
        return None
    _throttle(host)
    try:
        data = _get_with_retry(url, host, extra_headers)
    except urllib.error.HTTPError as exc:
        if exc.code in (404, 410):
            # Definitive: the host is healthy, this record simply is not there.
            _consecutive_failures[host] = 0
            with open(p, "wb") as fh:
                fh.write(b"")
        else:
            _trip(host)
        return None
    except Exception:
        _trip(host)
        return None
    _consecutive_failures[host] = 0
    with open(p, "wb") as fh:
        fh.write(data)
    return data


def _trip(host):
    n = _consecutive_failures.get(host, 0) + 1
    _consecutive_failures[host] = n
    if n >= _BREAKER_THRESHOLD:
        HOSTS_DISABLED.add(host)


def get_json(url, extra_headers=None):
    data = get_bytes(url, extra_headers)
    if not data:
        return None
    try:
        return json.loads(data)
    except ValueError:
        return None


def _crossref_to_record(m):
    yr = None
    dp = (m.get("issued") or {}).get("date-parts") or [[]]
    if dp and dp[0]:
        yr = dp[0][0]
    ct = m.get("container-title") or [""]
    return Record(
        title=(m.get("title") or [""])[0],
        authors=[" ".join(x for x in [a.get("given"), a.get("family")] if x)
                 for a in m.get("author", [])],
        venue=ct[0] if ct else "",
        year=yr, volume=m.get("volume"), issue=m.get("issue"),
        pages=m.get("page"), doi=m.get("DOI"),
        source="crossref", strong=True)


def fetch_crossref(doi):
    d = get_json("https://api.crossref.org/works/" +
                 urllib.parse.quote(doi) + _mailto_param("?"))
    if not d or "message" not in d:
        return None
    return _crossref_to_record(d["message"])


def fetch_acl(doi):
    """ACL Anthology DOIs resolve through Crossref; tag the source for reporting."""
    r = fetch_crossref(doi)
    if r:
        r.source = "acl/crossref"
    return r


def fetch_arxiv(arxiv_id):
    data = get_bytes("http://export.arxiv.org/api/query?id_list=" +
                     urllib.parse.quote(arxiv_id))
    if not data:
        return None
    ns = {"a": "http://www.w3.org/2005/Atom"}
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return None
    e = root.find("a:entry", ns)
    if e is None:
        return None
    pub = (e.findtext("a:published", "", ns) or "")[:4]
    return Record(
        title=" ".join((e.findtext("a:title", "", ns) or "").split()),
        authors=[a.findtext("a:name", "", ns) for a in e.findall("a:author", ns)],
        venue="arXiv", year=int(pub) if pub.isdigit() else None,
        source="arxiv", strong=True)


def _dblp_to_record(hit):
    info = hit.get("info", {})
    au = info.get("authors", {}).get("author", [])
    if isinstance(au, dict):
        au = [au]
    return Record(
        title=(info.get("title") or "").rstrip("."),
        authors=[strip_dblp_suffix(a.get("text", "")) for a in au],
        venue=info.get("venue", ""),
        year=int(info["year"]) if str(info.get("year", "")).isdigit() else None,
        volume=info.get("volume"), issue=info.get("number"),
        pages=info.get("pages"), doi=info.get("doi"),
        source="dblp", strong=False)


def search_dblp(title):
    d = get_json("https://dblp.org/search/publ/api?format=json&h=5&q=" +
                 urllib.parse.quote(title))
    try:
        hits = d["result"]["hits"].get("hit", [])
    except (TypeError, KeyError):
        return None
    return _dblp_to_record(hits[0]) if hits else None


def search_openalex(title):
    d = get_json("https://api.openalex.org/works?per-page=1"
                 + _mailto_param() + "&filter=title.search:"
                 + urllib.parse.quote(title))
    results = (d or {}).get("results") or []
    if not results:
        return None
    w = results[0]
    loc = (w.get("primary_location") or {}).get("source") or {}
    return Record(
        title=w.get("title") or "",
        authors=[a["author"]["display_name"] for a in w.get("authorships", [])],
        venue=loc.get("display_name", ""), year=w.get("publication_year"),
        doi=(w.get("doi") or "").replace("https://doi.org/", "") or None,
        source="openalex", strong=False)


def search_s2(title):
    key = s2_api_key()
    if not key:
        return None
    url = ("https://api.semanticscholar.org/graph/v1/paper/search/match?"
           "fields=title,authors,year,venue,externalIds&query=" +
           urllib.parse.quote(title))
    # The key is sent as a header, so it never enters the cache key or any URL
    # that gets written to disk or printed.
    d = get_json(url, {"x-api-key": key})
    data = (d or {}).get("data") or []
    if not data:
        return None
    w = data[0]
    ext = w.get("externalIds") or {}
    return Record(title=w.get("title", ""),
                  authors=[a.get("name", "") for a in w.get("authors", [])],
                  venue=w.get("venue", ""), year=w.get("year"),
                  doi=ext.get("DOI"),
                  source="s2", strong=False)


_PREPRINT_VENUE = re.compile(r"^corr\b|arxiv|preprint|biorxiv|ssrn", re.I)


def is_preprint(rec):
    """True when a record describes a preprint rather than a venue of record."""
    return rec.source == "arxiv" or bool(_PREPRINT_VENUE.search(rec.venue or ""))


_ARXIV_RE = re.compile(r"(\d{4}\.\d{4,5})(v\d+)?")
_ARXIV_DOI_RE = re.compile(r"^10\.48550/arxiv\.(\d{4}\.\d{4,5})", re.I)


def arxiv_id_from_doi(doi):
    """arXiv DOIs (10.48550/*) are registered with DataCite and are absent from
    Crossref, so resolving one there yields a spurious 'does not resolve'."""
    m = _ARXIV_DOI_RE.match((doi or "").strip())
    return m.group(1) if m else None


def arxiv_id_of(entry):
    for f in ("eprint", "arxiv", "archiveprefix", "url", "note", "journal"):
        v = entry.fields.get(f, "")
        m = _ARXIV_RE.search(v)
        if m:
            return m.group(1)
    return None


def resolve(entry):
    """Run the ladder. Return every record found, strongest first."""
    out = []
    doi = entry.fields.get("doi", "").strip()
    doi_arxiv = arxiv_id_from_doi(doi)
    if doi and not doi_arxiv:
        r = fetch_acl(doi) if doi.startswith("10.18653/") else fetch_crossref(doi)
        if r:
            out.append(r)
        else:
            out.append(Record(source="crossref", strong=True, title="",
                              venue="__DOI_UNRESOLVED__"))
    aid = doi_arxiv or arxiv_id_of(entry)
    if aid:
        r = fetch_arxiv(aid)
        if r:
            out.append(r)
    # Title searches only add value when no stable identifier resolved the entry.
    # Once Crossref/ACL has answered, that record is authoritative and the weak
    # rungs cost four requests to four free APIs for no extra information.
    #
    # A *preprint* record is the exception: an arXiv hit does not tell us whether
    # the work was later published, and a bibliography must cite the venue of
    # record. So keep searching when all we have is a preprint.
    if any(r.strong and r.venue != "__DOI_UNRESOLVED__" and not is_preprint(r)
           for r in out):
        return out

    title = entry.fields.get("title", "")
    if title:
        for fn in (search_dblp, search_openalex, search_s2):
            r = fn(title)
            if r:
                out.append(r)
    return out


def url_ok(url):
    try:
        _throttle(urllib.parse.urlparse(url).netloc)
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return True, resp.status
    except Exception as exc:
        return False, getattr(exc, "code", None)
