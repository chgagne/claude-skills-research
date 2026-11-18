"""Usage tab: per cluster, personal and group CPU/GPU-hours over 1, 7 and 28
days, then LevelFS and fairshare per account.

Windows stop at 28 days: DRAC rejects sacct ranges of 29 days or more and the
collector backfills usage 7 days at a time, so a window older than the
backfill frontier (meta ``usage_backfill:<cluster>``) is marked "partial".
Each job counts the part of its run that falls inside the window; GPU counts
are already fractional (MIG slices and shards, see ``gpu.py``). A running
job counts up to its elapsed time at the last usage poll, so it lags by up
to one usage cadence.
"""
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

WINDOWS = ((86400, "1 d"), (7 * 86400, "7 d"), (28 * 86400, "28 d"))


@dataclass
class UsageData:
    cluster: str
    user: str | None
    hours: dict  # see windows()
    partial: dict  # window -> bool
    shares: list = field(default_factory=list)  # ShareRow of this cluster
    fresh: Freshness | None = None
    has_rows: bool = False
    fresh_fs: Freshness | None = None  # the fairshare section's own age


def _overlap(start, elapsed, lo, hi) -> float:
    if start is None or not elapsed:
        return 0.0
    return max(0.0, min(start + elapsed, hi) - max(start, lo))


def windows(rows, user: str | None, now: float) -> dict:
    """{"me"|"group": {"cpu"|"gpu": {window_s: hours}}}."""
    out = {who: {kind: {w: 0.0 for w, _ in WINDOWS} for kind in ("cpu", "gpu")}
           for who in ("me", "group")}
    for r in rows:
        for w, _ in WINDOWS:
            sec = _overlap(r.start, r.elapsed_s, now - w, now)
            if not sec:
                continue
            whos = ("group", "me") if user is not None and r.user == user else ("group",)
            for who in whos:
                out[who]["cpu"][w] += sec * (r.cpus or 0) / 3600
                out[who]["gpu"][w] += sec * (r.gpus or 0) / 3600
    return out


def partial(frontier: float | None, now: float) -> dict:
    return {w: frontier is None or frontier > now - w for w, _ in WINDOWS}


def load_usage(conn, cfg: Config, now: float) -> list[UsageData]:
    status = store.cluster_status(conn)
    fresh = freshness(conn, cfg, "usage", now)
    fresh_fs = freshness(conn, cfg, "fairshare", now)
    by: dict[str, list] = {}
    for r in store.usage(conn):
        by.setdefault(r.cluster, []).append(r)
    shares: dict[str, list] = {}
    for s in store.shares(conn):
        shares.setdefault(s.cluster, []).append(s)
    out = []
    for c in cfg.clusters:
        st = status.get(c.name)
        user = (st.env or {}).get("user") if st else None
        raw = store.get_meta(conn, f"usage_backfill:{c.name}")
        try:
            frontier = float(raw) if raw is not None else None
        except ValueError:
            frontier = None
        rows = by.get(c.name, [])
        out.append(UsageData(c.name, user, windows(rows, user, now), partial(frontier, now),
                             shares.get(c.name, []), fresh[c.name], bool(rows),
                             fresh_fs[c.name]))
    return out


def section_text(u: UsageData, now: float) -> Text:
    t = fresh_label(u.fresh, now, "usage") if u.fresh else Text(u.cluster, style="bold")
    if u.user:
        t.append(f"  ({u.user})", style="dim")
    if u.has_rows:
        head = [Text("")]
        for kind in ("CPU-h", "GPU-h"):
            for w, label in WINDOWS:
                cell = Text(f"{kind} {label}", style="bold")
                if u.partial[w]:  # older than the backfill frontier
                    cell.append(" partial", style="dim italic")
                head.append(cell)
        body = [head]
        for who in ("me", "group"):
            line = [Text(who)]
            for kind in ("cpu", "gpu"):
                for w, _ in WINDOWS:
                    line.append(Text(fmt.hours(u.hours[who][kind][w])))
            body.append(line)
        t.append("\n")
        t.append_text(grid(body, right=range(1, 7), indent=2))
    if u.shares:
        accts: dict[str, dict] = {}
        for s in u.shares:
            a = accts.setdefault(s.account, {"me": None, "group": None, "fs": None})
            if s.user is None:
                a["group"] = s.level_fs
            elif u.user is not None and s.user == u.user:  # unknown user: no "me"
                a["me"], a["fs"] = s.level_fs, s.fairshare
        rows = [[Text("account", style="bold"), Text("LevelFS me", style="bold"),
                 Text("LevelFS group", style="bold"), Text("Fairshare", style="bold")]]
        for name, a in accts.items():
            rows.append([Text(name), _levelfs(a["me"]), _levelfs(a["group"]),
                         Text(fmt.num(a["fs"]))])
        t.append("\n")
        if u.fresh_fs is not None and u.fresh_fs.last_ok is not None:
            f = u.fresh_fs
            if f.dim:
                t.append(f"  fairshare data {fmt.age(f.last_ok, now)} old\n", style="dark_orange")
            else:
                t.append(f"  fairshare {fmt.age(f.last_ok, now)} ago\n", style="dim")
        t.append_text(grid(rows, right=range(1, 4), indent=2))
    return t


def _levelfs(x) -> Text:
    # LevelFS < 1: used more than the share (lower priority); > 1: under-used
    style = "" if x is None else ("dark_orange" if x < 1 else "green")
    return Text(fmt.num(x), style=style)


class UsageSection(Static):
    pass


class UsageView(VerticalScroll):
    def __init__(self, cfg: Config, **kw):
        super().__init__(**kw)
        self.cfg = cfg

    def compose(self) -> ComposeResult:
        yield Static(Text.assemble(("Usage", "bold"), (
            "   hours each job ran inside the window · 28 d is the longest range sacct "
            "accepts", "dim")), classes="section-title")
        for c in self.cfg.clusters:
            yield UsageSection(Text(c.name, style="bold"), id=wid("usage", c.name),
                               classes="cluster-section")

    def update_data(self, data: list[UsageData], now: float) -> None:
        for u in data:
            for sec in self.query(f"#{wid('usage', u.cluster)}"):
                sec.update(section_text(u, now))
                sec.set_class(bool(u.fresh and u.fresh.dim), "stale")
