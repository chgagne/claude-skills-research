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
from .textnorm import norm_title, strip_dblp_suffix

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


# dblp.org disallows every robot (robots.txt ends "User-agent: * / Disallow: /")
# and answers scripts with a proof-of-work page, so it is never contacted; DBLP
# is read through sparql.dblp.org, whose robots.txt allows /sparql with
# "Crawl-delay: 10". Semantic Scholar grants 1 req/s on an API key -- stay just
# above the line so clock jitter cannot put two requests inside the same second.
# arXiv asks for 3s between requests and answers 429 for a long while once annoyed.
_HOST_DELAY = {"sparql.dblp.org": 10.0, "api.semanticscholar.org": 1.1,
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


# A DBLP SPARQL scan takes 6-12 s on the server before the first byte.
_HOST_TIMEOUT = {"sparql.dblp.org": 60}


def _raw_get(url, extra_headers=None):
    headers = {"User-Agent": UA}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    timeout = _HOST_TIMEOUT.get(urllib.parse.urlparse(url).netloc, _TIMEOUT)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


S2_KEY_FILE = os.path.expanduser("~/.config/scholarly/s2_key")


def s2_api_key():
    """Key from the environment, else from a 0600 key file. Never logged.

    EVAL_S2_API_KEY is read too: `claude plugin eval` gives each run a fresh HOME
    and passes only EVAL_* variables, so neither S2_API_KEY nor the key file arrives.
    """
    for var in ("S2_API_KEY", "EVAL_S2_API_KEY"):
        key = os.environ.get(var, "").strip()
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


ENGINE_HOSTS = {"openalex": "api.openalex.org", "s2": "api.semanticscholar.org",
                "dblp": "sparql.dblp.org", "crossref": "api.crossref.org",
                "arxiv": "export.arxiv.org"}


def disabled_engines():
    """Engines switched off by SCHOLARLY_DISABLE (or EVAL_SCHOLARLY_DISABLE, which
    is what an eval sandbox can pass), comma-separated. A measured run uses this to
    give every arm the same sources; an unknown name is an error, not a no-op."""
    names = set()
    for var in ("SCHOLARLY_DISABLE", "EVAL_SCHOLARLY_DISABLE"):
        names |= {n.strip().lower() for n in os.environ.get(var, "").split(",") if n.strip()}
    unknown = names - set(ENGINE_HOSTS)
    if unknown:
        raise ValueError(f"unknown engine(s) in SCHOLARLY_DISABLE: {', '.join(sorted(unknown))}; "
                         f"known: {', '.join(sorted(ENGINE_HOSTS))}")
    return names


def get_bytes(url, extra_headers=None):
    """Fetch with an on-disk cache.

    A definitive negative (404/410) is cached as an empty file so an unresolvable
    DOI is not re-requested on every run. Transient failures (timeouts, 5xx) are
    not cached, so an outage does not poison the cache permanently.
    """
    host = urllib.parse.urlparse(url).netloc
    # Switched off on purpose: no request, no cache read (a cached answer would
    # give one arm a source the others lack), and no failure count.
    if host in {ENGINE_HOSTS[n] for n in disabled_engines()}:
        return None
    p = _cache_path(url)
    if os.path.exists(p):
        with open(p, "rb") as fh:
            return fh.read() or None
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
    """JSON from url, or None.

    A body that does not parse is a failure, not an answer: a bot-challenge or
    error page served with status 200 would otherwise be cached and replayed as
    "no record" on every later run, and the run would not report degraded
    coverage. Such a body is evicted, refetched once if it came from the cache,
    and otherwise counted against the host.
    """
    p = _cache_path(url)
    from_cache = os.path.exists(p)
    for _ in range(2 if from_cache else 1):
        data = get_bytes(url, extra_headers)
        if not data:
            return None
        try:
            return json.loads(data)
        except ValueError:
            if os.path.exists(p):
                os.remove(p)
    host = urllib.parse.urlparse(url).netloc
    SOURCE_FAILURES[host] = SOURCE_FAILURES.get(host, 0) + 1
    _trip(host)
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


DBLP_SPARQL = "https://sparql.dblp.org/sparql"
_DBLP_CHUNK = 20          # titles per query: the regex scan costs ~7 s whatever the count
_DBLP_PREFIX_WORDS = 6
_DBLP_POOL = {}           # publication URI -> Record, from every query this run
_DBLP_ASKED = set()       # normalised titles already queried
_LATEX_CMD = re.compile(r"\\[a-zA-Z]+\*?")


def reset_dblp():
    _DBLP_POOL.clear()
    _DBLP_ASKED.clear()


def _title_words(title):
    return norm_title(_LATEX_CMD.sub(" ", title or "")).split()


def _sparql(query):
    url = DBLP_SPARQL + "?query=" + urllib.parse.quote(query)
    d = get_json(url, {"Accept": "application/sparql-results+json"})
    try:
        return d["results"]["bindings"]
    except (TypeError, KeyError):
        return None


_DBLP_SELECT = """PREFIX dblp: <https://dblp.org/rdf/schema#>
SELECT ?p ?t ?type ?venue ?year ?doi ?pages ?volume ?number ?ord ?name WHERE {
  %s
  ?p dblp:title ?t .
  ?p a ?type . FILTER(?type != dblp:Publication)
  OPTIONAL { ?p dblp:publishedIn ?venue }
  OPTIONAL { ?p dblp:yearOfPublication ?year }
  OPTIONAL { ?p dblp:doi ?doi }
  OPTIONAL { ?p dblp:pagination ?pages }
  OPTIONAL { ?p dblp:publicationVolume ?volume }
  OPTIONAL { ?p dblp:publicationNumber ?number }
  OPTIONAL { ?p dblp:hasSignature ?s . ?s a dblp:AuthorSignature ;
             dblp:signatureOrdinal ?ord ; dblp:signatureDblpName ?name }
}"""


def _rows_to_records(rows):
    """One SPARQL row per (publication, author signature) -> Records, authors in order."""
    pubs = {}
    for b in rows or []:
        v = {k: x.get("value") for k, x in b.items()}
        uri = v.get("p")
        if not uri:
            continue
        e = pubs.setdefault(uri, {"v": v, "au": {}})
        if v.get("name") and str(v.get("ord", "")).isdigit():
            e["au"][int(v["ord"])] = strip_dblp_suffix(v["name"])
    out = []
    for uri, e in pubs.items():
        v = e["v"]
        year = v.get("year")
        out.append(Record(
            title=(v.get("t") or "").strip().rstrip("."),
            authors=[e["au"][k] for k in sorted(e["au"])],
            venue=v.get("venue") or "",
            year=int(year) if str(year or "").isdigit() else None,
            volume=v.get("volume"), issue=v.get("number"), pages=v.get("pages"),
            doi=(v.get("doi") or "").replace("https://doi.org/", "").replace("http://dx.doi.org/", "") or None,
            source="dblp", strong=False))
        _DBLP_POOL[uri] = out[-1]
    return out


def _title_pattern(title):
    words = _title_words(title)[:_DBLP_PREFIX_WORDS]
    return "[^a-z0-9]+".join(words) if words else None


def _title_query(alternatives):
    return _DBLP_SELECT % ('?p dblp:title ?t0 . FILTER(REGEX(?t0, "^(?:%s)", "i"))'
                           % "|".join(alternatives))


def dblp_records(title):
    """Every DBLP record whose title starts like `title` (one SPARQL scan)."""
    pat = _title_pattern(title)
    return _rows_to_records(_sparql(_title_query([pat]))) if pat else []


def prefetch_dblp(titles):
    """Query many titles in as few scans as possible; later searches hit the pool."""
    todo = []
    for t in titles:
        key = " ".join(_title_words(t))
        pat = _title_pattern(t)
        if key and pat and key not in _DBLP_ASKED:
            _DBLP_ASKED.add(key)
            todo.append(pat)
    todo = list(dict.fromkeys(todo))
    for i in range(0, len(todo), _DBLP_CHUNK):
        _rows_to_records(_sparql(_title_query(todo[i:i + _DBLP_CHUNK])))


def _same_work(query_words, rec):
    """Titles match, or one is a prefix of the other (arXiv titles often drop a
    subtitle the published version adds), on at least four words."""
    r = _title_words(rec.title)
    q = query_words
    n = min(len(q), len(r))
    return n >= 4 and q[:n] == r[:n] or q == r


def search_dblp(title):
    """Best DBLP record for a title: the published version when one exists."""
    words = _title_words(title)
    if not words:
        return None
    if " ".join(words) not in _DBLP_ASKED:
        prefetch_dblp([title])
    hits = [r for r in _DBLP_POOL.values() if _same_work(words, r)]
    if not hits:
        return None
    hits.sort(key=lambda r: (is_preprint(r), abs(len(_title_words(r.title)) - len(words))))
    return hits[0]


def dblp_keyword_search(query, limit):
    """Records whose title contains every word of `query` (for literature surveys)."""
    words = [w for w in _title_words(query) if len(w) > 2][:8]
    if not words:
        return []
    limit = max(1, min(int(limit), 50))
    # One regex on the two longest words, in either order, is the cheap scan
    # (~6 s); three CONTAINS filters took 25 s, and a DISTINCT subquery hit the
    # server's timeout. The remaining words are checked here.
    a, b = (sorted(words, key=len, reverse=True) + [""])[:2]
    pat = f"{a}.*{b}|{b}.*{a}" if b else a
    rows = _sparql(_DBLP_SELECT % ('?p dblp:title ?t0 . FILTER(REGEX(?t0, "%s", "i"))' % pat)
                   + " LIMIT %d" % (limit * 60))
    keep = [r for r in _rows_to_records(rows)
            if all(w in _title_words(r.title) for w in words)]
    return keep[:limit]


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
