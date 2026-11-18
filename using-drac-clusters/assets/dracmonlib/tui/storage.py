"""Storage tab: ``diskusage_report`` per cluster and filesystem, space and
file count; at or above 80 % amber, at or above 95 % red."""
from __future__ import annotations

from dataclasses import dataclass, field

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from .. import store
from ..config import Config
from . import fmt
from .clusters import Freshness, fresh_label, freshness
from .grid import grid, wid

LEVEL_STYLE = {"ok": "", "warn": "dark_orange", "crit": "bold red"}
HEAD = ("Filesystem", "Owner", "Used", "Quota", "%", "Files", "Quota", "%")


@dataclass
class StorageData:
    cluster: str
    rows: list = field(default_factory=list)  # DiskRow
    fresh: Freshness | None = None


def load_storage(conn, cfg: Config, now: float) -> list[StorageData]:
    fresh = freshness(conn, cfg, "disk", now)
    by: dict[str, list] = {}
    for d in store.disk(conn):
        by.setdefault(d.cluster, []).append(d)
    return [StorageData(c.name, by.get(c.name, []), fresh[c.name]) for c in cfg.clusters]


def count(n) -> str:
    if n is None:
        return fmt.NONE
    for div, unit in ((10**9, "G"), (10**6, "M"), (10**3, "k")):
        if n >= div:
            v = n / div
            return f"{v:.0f}{unit}" if v >= 100 else f"{v:.1f}{unit}"
    return str(n)


def levels(d) -> tuple[str, str]:
    return (fmt.level(fmt.percent(d.used_bytes, d.quota_bytes)),
            fmt.level(fmt.percent(d.files, d.files_quota)))


def _pct_cell(a, b) -> Text:
    lv = fmt.level(fmt.percent(a, b))
    t = Text(fmt.pct(a, b), style=LEVEL_STYLE[lv])
    if lv != "ok":
        t.append(" ⚠", style=LEVEL_STYLE[lv])
    return t


def disk_cells(d) -> list[Text]:
    return [Text(d.filesystem), Text(d.owner or d.scope, style="dim"),
            Text(fmt.bytes_(d.used_bytes)), Text(fmt.bytes_(d.quota_bytes), style="dim"),
            _pct_cell(d.used_bytes, d.quota_bytes),
            Text(count(d.files)), Text(count(d.files_quota), style="dim"),
            _pct_cell(d.files, d.files_quota)]


def worst(data: list[StorageData]):
    """(pct, cluster, filesystem, "space"|"files") of the fullest entry, or None."""
    best = None
    for s in data:
        for d in s.rows:
            for kind, a, b in (("space", d.used_bytes, d.quota_bytes),
                               ("files", d.files, d.files_quota)):
                p = fmt.percent(a, b)
                if p is not None and (best is None or p > best[0]):
                    best = (p, s.cluster, d.filesystem, kind)
    return best


def section_text(s: StorageData, now: float) -> Text:
    t = fresh_label(s.fresh, now, "disk") if s.fresh else Text(s.cluster, style="bold")
    if not s.rows:
        return t
    body = [[Text(h, style="bold") for h in HEAD]]
    body += [disk_cells(d) for d in s.rows]
    t.append("\n")
    t.append_text(grid(body, right=range(2, 8), indent=2))
    return t


class StorageSection(Static):
    render_levels: set = set()


class StorageView(VerticalScroll):
    def __init__(self, cfg: Config, **kw):
        super().__init__(**kw)
        self.cfg = cfg

    def compose(self) -> ComposeResult:
        yield Static(Text.assemble(("Storage", "bold"), (
            "   diskusage_report · amber at 80 %, red at 95 %", "dim")),
            classes="section-title")
        for c in self.cfg.clusters:
            yield StorageSection(Text(c.name, style="bold"), id=wid("storage", c.name),
                                 classes="cluster-section")

    def update_data(self, data: list[StorageData], now: float) -> None:
        for s in data:
            for sec in self.query(f"#{wid('storage', s.cluster)}"):
                sec.update(section_text(s, now))
                sec.render_levels = {lv for d in s.rows for lv in levels(d)}
                sec.set_class(bool(s.fresh and s.fresh.dim), "stale")
