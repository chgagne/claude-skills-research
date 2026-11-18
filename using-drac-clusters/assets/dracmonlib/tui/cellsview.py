"""Cells tab: one row per campaign, rolled up across clusters.

``Enter`` on a row opens ``CampaignScreen``, the campaign's cell list (loaded
in a thread worker with its own store connection).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Static

from .. import store
from ..cells import CampaignState, eta_seconds, is_open
from ..collector import _queue_ids
from ..config import Config
from . import fmt
from .clusters import freshness

BAR = 8
FAIL_WIDTH = 34
COLUMNS = (("campaign", "Campaign"), ("progress", "Progress"),
           ("counts", "Done/Run/Fail/Total"), ("eta", "ETA"), ("failure", "Last failure"),
           ("clusters", "Clusters"), ("updated", "Age"))
CELL_COLUMNS = (("cell", "Cell"), ("state", "State"), ("duration", "Duration"),
                ("job", "Job"), ("cluster", "Cluster"), ("when", "Last event"))
CELL_STYLE = {"running": "green", "failed": "red", "done": "grey62"}


@dataclass
class CampaignRow:
    campaign: str
    done: int
    running: int
    failed: int
    total: int | None
    eta: float | None
    last_failure: str  # "cell: detail", "" when none
    last_failure_ts: float | None
    clusters: list = field(default_factory=list)
    open: bool = False
    last_event: float | None = None
    glob: bool = False
    data_from: float | None = None  # oldest stale cells data among its clusters

    @property
    def stale(self) -> bool:
        return self.data_from is not None


def _live(conn, st: CampaignState, queues: dict) -> bool:
    events = store.campaign_cells(conn, st.campaign)
    return any(e.job_id in queues.get(cl, ()) or e.job_id.split("_", 1)[0] in queues.get(cl, ())
               for cl, e in events)


def _row(st: CampaignState, live: bool, now: float, glob: bool) -> CampaignRow:
    lf = st.last_failure
    return CampaignRow(
        campaign=st.campaign, done=len(st.done), running=len(st.running),
        failed=len(st.failed), total=st.plan, eta=eta_seconds(st),
        last_failure=f"{lf[0]}: {lf[1]}" if lf else "", last_failure_ts=lf[2] if lf else None,
        clusters=sorted(st.clusters), open=is_open(st, live, now),
        last_event=st.last_event, glob=glob)


def rollup(rows: list[CampaignRow]) -> list[CampaignRow]:
    """Merge rows with the same campaign name (a glob campaign counted on
    several clusters, or a name used by both kinds)."""
    out: dict[str, CampaignRow] = {}
    for r in rows:
        m = out.get(r.campaign)
        if m is None:
            out[r.campaign] = r
            continue
        m.done += r.done
        m.running += r.running
        m.failed += r.failed
        m.total = None if m.total is None or r.total is None else m.total + r.total
        etas = [e for e in (m.eta, r.eta) if e is not None]
        m.eta = max(etas) if etas else None
        if r.last_failure_ts is not None and (m.last_failure_ts is None
                                              or r.last_failure_ts > m.last_failure_ts):
            m.last_failure, m.last_failure_ts = r.last_failure, r.last_failure_ts
        m.clusters = sorted(set(m.clusters) | set(r.clusters))
        m.open = m.open or r.open
        m.last_event = max(t for t in (m.last_event, r.last_event, 0) if t is not None) or None
        m.glob = m.glob and r.glob
        olds = [t for t in (m.data_from, r.data_from) if t is not None]
        m.data_from = min(olds) if olds else None
    return sorted(out.values(), key=lambda r: (not r.open, -(r.last_event or 0), r.campaign))


def load_cells(conn, cfg: Config, now: float) -> list[CampaignRow]:
    names = {c.name for c in cfg.clusters}
    queues = {n: _queue_ids(conn, n) for n in names}
    fresh = {"cells": freshness(conn, cfg, "cells", now),
             "globs": freshness(conn, cfg, "globs", now)}
    rows = []
    for st in store.campaigns(conn, cfg):
        live = False if st.glob else _live(conn, st, queues)
        r = _row(st, live, now, st.glob)
        sec = fresh["globs" if st.glob else "cells"]
        old = [sec[c].last_ok for c in st.clusters
               if c in sec and sec[c].dim and sec[c].last_ok is not None]
        r.data_from = min(old) if old else None
        rows.append(r)
    return rollup(rows)


def eta_text(r: CampaignRow) -> str:
    if r.total is not None and r.done >= r.total:
        return "done"
    return fmt.hm(r.eta) if r.open else "closed"


def row_cells(r: CampaignRow, now: float) -> dict:
    total = "?" if r.total is None else str(r.total)
    dim = "" if r.open else "dim"
    counts = Text(f"{r.done}/{r.running}/", style=dim)
    counts.append(str(r.failed), style="red" if r.failed else dim)
    counts.append(f"/{total}", style=dim)
    prog = Text(fmt.bar(r.done, r.total or 0, BAR), style="green" if r.open else "grey50")
    if r.total:
        prog.append(f" {fmt.pct(r.done, r.total)}", style=dim)
    fail = r.last_failure
    if len(fail) > FAIL_WIDTH:
        fail = fail[:FAIL_WIDTH - 1] + "…"
    if r.last_failure_ts is not None:
        fail += f" ({fmt.age(r.last_failure_ts, now)})"
    out = {
        "campaign": Text(r.campaign + (" (glob)" if r.glob else ""),
                         style="bold" if r.open else "dim"),
        "progress": prog, "counts": counts,
        "eta": Text(eta_text(r), style=dim),
        "failure": Text(fail, style="red" if fail and r.open else dim),
        "clusters": Text(" ".join(r.clusters), style=dim),
        "updated": Text(fmt.age(r.last_event, now), style=dim),
    }
    if r.stale:  # dimmed whole, with the age of the oldest data it rests on
        out["updated"] = Text(f"data {fmt.age(r.data_from, now)} old", style="dark_orange")
        for k, v in out.items():
            if k != "updated":
                v.stylize("dim")
    return out


# ---------------------------------------------------------------- cell list

@dataclass
class CellRow:
    cluster: str
    cell: str
    state: str  # running | failed | done
    duration: float | None
    job: str
    when: float
    detail: str = ""


def cell_rows(events, now: float) -> list[CellRow]:
    """(cluster, CellEvent) pairs -> one row per (cluster, cell), latest state."""
    starts: dict = {}
    rows: dict = {}
    for cl, e in sorted(events, key=lambda p: p[1].ts):
        key = (cl, e.cell)
        if e.event == "start":
            starts[(cl, e.job_id, e.cell)] = e.ts
            if key not in rows or rows[key].state != "done":
                rows[key] = CellRow(cl, e.cell, "running", None, e.job_id, e.ts)
        elif e.event in ("done", "fail"):
            t0 = starts.get((cl, e.job_id, e.cell))
            if e.event == "fail" and key in rows and rows[key].state == "done":
                continue
            rows[key] = CellRow(cl, e.cell, "done" if e.event == "done" else "failed",
                                None if t0 is None else e.ts - t0, e.job_id, e.ts, e.detail)
    for r in rows.values():
        if r.state == "running":
            r.duration = now - r.when
    order = {"running": 0, "failed": 1, "done": 2}
    return sorted(rows.values(), key=lambda r: (order[r.state], -r.when, r.cluster, r.cell))


class CampaignScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "Back"),
                Binding("q", "app.pop_screen", "Back", show=False)]

    def __init__(self, row: CampaignRow, store_path, now: float):
        super().__init__()
        self.row = row
        self.store_path = store_path
        self.now = now

    def compose(self) -> ComposeResult:
        r = self.row
        total = "?" if r.total is None else r.total
        title = Text(f"{r.campaign}", style="bold")
        title.append(f"  {r.done}/{total} done · {r.running} running · {r.failed} failed"
                     f" · {' '.join(r.clusters)}")
        title.append("   Esc: back", style="dim")
        yield Static(title, id="campaign-title", classes="section-title")
        with Vertical():
            yield DataTable(id="campaign-cells", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        for key, label in CELL_COLUMNS:
            table.add_column(label, key=key)
        if self.row.glob:
            self.query_one("#campaign-title", Static).update(Text(
                f"{self.row.campaign}: a glob campaign is counted, not logged per cell"
                "   Esc: back"))
            return
        table.focus()
        self._load()

    @work(thread=True, group="campaign")
    def _load(self) -> None:
        try:
            conn = store.open_store(self.store_path)
            try:
                events = store.campaign_cells(conn, self.row.campaign)
            finally:
                conn.close()
        except Exception as e:
            self.app.notify(f"cannot read the store: {e}", severity="error")
            return
        rows = cell_rows(events, self.now)
        try:
            self.app.call_from_thread(self._show, rows)
        except RuntimeError:
            pass

    def _show(self, rows: list[CellRow]) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for r in rows:
            detail = f"  {r.detail}" if r.detail and r.state == "failed" else ""
            table.add_row(
                r.cell, Text(r.state + detail, style=CELL_STYLE[r.state]),
                fmt.duration(r.duration), r.job, r.cluster, fmt.age(r.when, self.now),
                key=f"{r.cluster}/{r.cell}")


class CellsView(Vertical):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.rows: dict[str, CampaignRow] = {}
        self.now = 0.0

    def compose(self) -> ComposeResult:
        yield Static("", id="cells-title", classes="section-title")
        yield DataTable(id="cells-table", cursor_type="row", zebra_stripes=True)

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        for key, label in COLUMNS:
            table.add_column(label, key=key)
        self._title(0)

    def _title(self, n_open: int) -> None:
        t = Text(f"Campaigns ({n_open} open, {len(self.rows)} kept)", style="bold")
        t.append("   Enter: cell list", style="dim")
        if not self.rows:
            t.append("\nNo campaign yet: jobs log their cells with dracmon-cell.", style="dim")
        self.query_one("#cells-title", Static).update(t)

    def update_rows(self, rows: list[CampaignRow], now: float) -> None:
        self.now = now
        self.rows = {r.campaign: r for r in rows}
        table = self.query_one(DataTable)
        keep = None
        if table.row_count:
            keep = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
        table.clear()
        for r in rows:
            table.add_row(*row_cells(r, now).values(), key=r.campaign)
        if keep in self.rows:
            table.move_cursor(row=table.get_row_index(keep), animate=False)
        self._title(sum(r.open for r in rows))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        event.stop()
        r = self.rows.get(event.row_key.value)
        if r is not None:
            self.app.push_screen(CampaignScreen(r, self.app.store_path, self.now))
