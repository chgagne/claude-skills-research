"""Alliance status page (status.alliancecan.ca): one state per cluster.

The site has no JSON or RSS feed, so the status table on the home page is
parsed with ``html.parser``: one row per service holding its name, a Material
icon word for its state, and zero or more incident titles. The fetch runs in
the collector loop (or the TUI when it is the poller), never on the UI thread;
the result is cached in the store's ``meta`` table.
"""
from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser

URL = "https://status.alliancecan.ca/"
STALE_FACTOR = 2  # cached data older than 2 cadences is not shown
ICON_STATE = {"check": "ok", "warning_amber": "conditions", "cloud_off": "outage",
              "event": "scheduled", "power_off": "decommissioned"}
_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})\b")


@dataclass
class StatusEntry:
    state: str  # ok | conditions | outage | scheduled | decommissioned | unknown
    title: str  # first incident title, "" when none
    since: str | None  # leading YYYY-MM-DD of the first title, when it has one
    titles: tuple[str, ...] = ()  # every incident title


class _Table(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows: list[list[list[str]]] = []  # row -> cell -> text pieces per tag
        self._cell = -1
        self._tag: str | None = None
        self._buf: list[str] = []
        self._row: list[dict] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag == "td" and self._row is not None:
            self._row.append({"a": [], "i": []})
        elif tag in ("a", "i") and self._row:
            self._tag, self._buf = tag, []

    def handle_data(self, data):
        if self._tag:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag == self._tag and self._row:
            text = " ".join("".join(self._buf).split())
            if text:
                self._row[-1][tag].append(text)
            self._tag = None
        elif tag == "tr" and self._row is not None:
            if len(self._row) >= 3:
                self.rows.append(self._row)
            self._row = None


def parse_status(text: str) -> dict[str, StatusEntry]:
    """Lowercase service name -> entry; ``{}`` when no status table is found."""
    p = _Table()
    p.feed(text)
    out: dict[str, StatusEntry] = {}
    for cells in p.rows:
        names, icons, incidents = cells[0]["a"], cells[1]["i"], cells[2]["a"]
        if not names or not icons:
            continue
        titles = tuple(incidents)
        first = titles[0] if titles else ""
        m = _DATE.match(first)
        out[names[0].lower()] = StatusEntry(
            ICON_STATE.get(icons[0], "unknown"), first, m.group(1) if m else None, titles)
    return out


def fetch_status(timeout: int = 10) -> dict[str, StatusEntry] | None:
    """The parsed page, or None on any network or format failure."""
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "dracmon"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = parse_status(r.read().decode("utf-8", "replace"))
    except Exception:
        return None
    return data or None


# ---------------------------------------------------------------- store cache

def _due(conn, cadence: int, now: float) -> bool:
    from . import store
    tried = store.get_meta(conn, "status_page_try")
    try:
        return tried is None or now - float(tried) >= cadence
    except ValueError:
        return True


def refresh(conn, cfg, now: float, fetch=None) -> None:
    """Fetch when the cadence has elapsed since the last attempt and cache the
    result; a failed fetch keeps the last good data (``load`` ages it out)."""
    from . import store
    if not _due(conn, cfg.status_page, now):
        return
    store.set_meta(conn, "status_page_try", repr(now))
    try:
        data = (fetch or fetch_status)()
    except Exception:
        data = None
    if data is None:
        return
    payload = {k: [e.state, e.title, e.since, list(e.titles)] for k, e in data.items()}
    store.set_meta(conn, "status_page", json.dumps({"at": now, "data": payload}))


def load(conn, cfg, now: float) -> dict[str, StatusEntry]:
    """Cached entries, or ``{}`` when never fetched or older than 2 cadences."""
    from . import store
    raw = store.get_meta(conn, "status_page")
    if raw is None:
        return {}
    try:
        doc = json.loads(raw)
        if now - float(doc["at"]) >= STALE_FACTOR * cfg.status_page:
            return {}
        return {k: StatusEntry(v[0], v[1], v[2], tuple(v[3])) for k, v in doc["data"].items()}
    except (ValueError, KeyError, IndexError, TypeError):
        return {}
