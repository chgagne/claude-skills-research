"""Clusters tab: one row per configured cluster, read from the store.

``load_clusters`` is the model (store reads only, no ssh): it runs in a worker
thread with that thread's own sqlite connection. ``ClustersView`` renders it;
``Enter`` or ``c`` on a row asks the app to open that cluster's connection.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import DataTable, Static

from .. import store
from ..collector import CADENCE_KEY
from ..config import Config

STALE_FACTOR = 2  # stale = older than 2 cadences
NO_STATUS = "–"  # status page column, filled by a later task
ERR_WIDTH = 26  # the full error is in the detail line under the table
_MIG = re.compile(r"\d+g\.\d+gb$")

COLUMNS = (("cluster", "Cluster"), ("mode", "Mode"), ("socket", "Socket"),
           ("last_poll", "Last poll"), ("last_ok", "Last ok"), ("error", "Error"),
           ("status", "Status"), ("partitions", "Partitions"))  # longest last

DOT = {"green": ("●", "green"), "amber": ("●", "dark_orange"),
       "red": ("○", "red"), "grey": ("○", "grey50")}


@dataclass
class ClusterRow:
    name: str
    host: str
    mode: str  # active | released | down | disconnected | unknown
    live: bool | None  # socket state seen by the last collector cycle
    last_poll: float | None
    last_ok: float | None
    error: str | None
    partitions: str
    stale: bool  # some section of an active cluster is older than 2 cadences
    data_stale: bool  # the queue data shown for this cluster is stale
    parts_stale: bool

    @property
    def dot(self) -> str:
        if self.mode == "active":
            return "amber" if self.stale else "green"
        if self.mode == "down":
            return "red"
        return "grey"


# ---------------------------------------------------------------- formatting

def fmt_age(seconds: float) -> str:
    s = max(0, int(seconds))
    if s < 90:
        return f"{s}s"
    if s < 90 * 60:
        return f"{s // 60}m"
    if s < 36 * 3600:
        return f"{s // 3600}h"
    return f"{s // 86400}d"


def fmt_when(t: float | None, now: float) -> str:
    if t is None:
        return "never"
    fmt = "%H:%M" if now - t < 86400 else "%m-%d %H:%M"
    return f"{time.strftime(fmt, time.localtime(t))} ({fmt_age(now - t)})"


def _idle(state: str) -> bool:
    return state.rstrip("-") == "idle"  # idle*, idle~ ... are not usable now


def partition_summary(rows) -> str:
    """``<idle>/<total> nodes`` of the largest partition (nodes appear in
    several partitions, so they cannot be summed), then the GPU models seen in
    any partition's gres (MIG slices collapsed into ``+MIG``)."""
    if not rows:
        return "no data"
    total: dict[str, int] = {}
    idle: dict[str, int] = {}
    gpus: set[str] = set()
    mig = False
    for r in rows:
        total[r.partition] = total.get(r.partition, 0) + r.nodes
        if _idle(r.state):
            idle[r.partition] = idle.get(r.partition, 0) + r.nodes
        for item in (r.gres or "").split(","):
            parts = item.strip().split(":")
            if len(parts) >= 3 and parts[0] == "gpu":
                if _MIG.search(parts[1]):
                    mig = True
                else:
                    gpus.add(parts[1])
    big = max(total, key=lambda p: (total[p], p))
    out = f"{idle.get(big, 0)}/{total[big]} nodes"
    kinds = " ".join(sorted(gpus)) + (" +MIG" if mig else "")
    return f"{out} · {kinds.strip()}" if kinds.strip() else out


# ---------------------------------------------------------------- model

def _is_stale(t: float | None, cadence: int, now: float) -> bool:
    return t is not None and now - t >= STALE_FACTOR * cadence


def load_clusters(conn, cfg: Config, now: float) -> list[ClusterRow]:
    """One row per configured cluster, in config order (store reads only)."""
    status = store.cluster_status(conn)
    parts: dict[str, list] = {}
    for p in store.partitions(conn):
        parts.setdefault(p.cluster, []).append(p)
    out = []
    for c in cfg.clusters:
        st = status.get(c.name)
        live_meta = store.get_meta(conn, f"live:{c.name}")
        oks = {s: store.last_ok(conn, c.name, s) for s in CADENCE_KEY}
        mode = st.mode if st else "unknown"
        # sections that never arrived (e.g. a command missing on that
        # cluster) are not "stale": they have no data to age
        stale = mode == "active" and any(
            _is_stale(t, cfg.cadence[CADENCE_KEY[s]], now) for s, t in oks.items())
        out.append(ClusterRow(
            name=c.name, host=c.host, mode=mode,
            live=None if live_meta is None else live_meta == "1",
            last_poll=st.last_poll if st else None,
            last_ok=st.last_ok if st else None,
            error=st.last_error if st else None,
            partitions=partition_summary(parts.get(c.name, [])),
            stale=stale,
            data_stale=_is_stale(oks["queue"], cfg.cadence["queue"], now),
            parts_stale=_is_stale(oks["partitions"], cfg.cadence["partitions"], now),
        ))
    return out


def header_text(rows: list[ClusterRow], updated: float | None) -> Text:
    t = Text()
    for r in rows:
        glyph, colour = DOT[r.dot]
        t.append(f"{glyph} {r.name}", style=colour)
        t.append("  ")
    t.append("updated " + (time.strftime("%H:%M", time.localtime(updated))
                           if updated is not None else "never"), style="bold")
    return t


def _mode_cell(r: ClusterRow) -> Text:
    colour = {"active": "green", "down": "red"}.get(r.mode, "grey50")
    if r.mode == "active" and r.stale:
        colour = "dark_orange"
    return Text(r.mode, style=colour)


def row_cells(r: ClusterRow, now: float) -> dict[str, Text | str]:
    dim = "dim"
    socket = {True: Text("live", style="green"), False: Text("none", style="grey50"),
              None: Text("?", style="grey50")}[r.live]
    err = (r.error or "")
    if len(err) > ERR_WIDTH:  # ssh puts the reason last: keep the tail
        err = "…" + err[-(ERR_WIDTH - 1):]
    return {
        "cluster": Text(r.name, style="bold"),
        "mode": _mode_cell(r),
        "socket": socket,
        "last_poll": "never" if r.last_poll is None else f"{fmt_age(now - r.last_poll)} ago",
        "last_ok": Text(fmt_when(r.last_ok, now), style=dim if r.data_stale else ""),
        "error": Text(err, style="red" if err else ""),
        "partitions": Text(r.partitions, style=dim if r.parts_stale else ""),
        "status": NO_STATUS,
    }


def detail_text(r: ClusterRow, now: float) -> Text:
    """The highlighted cluster in full: host, poll times, untruncated error,
    and what Enter does."""
    t = Text()
    t.append(f"{r.name}", style="bold")
    t.append(f" (ssh {r.host})  last poll {fmt_when(r.last_poll, now)}"
             f"  last ok {fmt_when(r.last_ok, now)}")
    if r.error:
        t.append("\nerror: ", style="red")
        t.append(r.error)
    hint = "socket live" if r.live else "Enter or c: open a connection (asks first)"
    t.append(f"\n{hint}", style="dim")
    return t


# ---------------------------------------------------------------- widget

class ClustersView(Vertical):
    BINDINGS = [Binding("c", "connect", "Connect")]

    def __init__(self, cfg: Config, **kw):
        super().__init__(**kw)
        self.cfg = cfg
        self.rows: dict[str, ClusterRow] = {}
        self.now = 0.0

    def compose(self) -> ComposeResult:
        yield DataTable(cursor_type="row", zebra_stripes=True, id="clusters-table")
        yield Static("", id="cluster-detail")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        for key, label in COLUMNS:
            table.add_column(label, key=key)
        for c in self.cfg.clusters:
            cells = {key: "" for key, _ in COLUMNS}
            cells.update(cluster=c.name, status=NO_STATUS)
            table.add_row(*(cells[key] for key, _ in COLUMNS), key=c.name)

    def update_rows(self, rows: list[ClusterRow], now: float) -> None:
        table = self.query_one(DataTable)
        self.rows = {r.name: r for r in rows}
        self.now = now
        for r in rows:
            for key, value in row_cells(r, now).items():
                table.update_cell(r.name, key, value, update_width=True)
        self._show_detail(self.selected())

    def _show_detail(self, name: str | None) -> None:
        r = self.rows.get(name) if name else None
        self.query_one("#cluster-detail", Static).update(
            detail_text(r, self.now) if r else "")

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._show_detail(event.row_key.value if event.row_key else None)

    def selected(self) -> str | None:
        table = self.query_one(DataTable)
        if table.row_count == 0:
            return None
        return table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        event.stop()
        self.app.action_connect(event.row_key.value)

    def action_connect(self) -> None:
        name = self.selected()
        if name is not None:
            self.app.action_connect(name)
