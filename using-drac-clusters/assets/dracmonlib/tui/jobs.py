"""Jobs tab: summary tiles, the queue across clusters, finished jobs.

``load_jobs`` (store reads only) runs in the app's reload worker. The window
(``w``) and the filter (``/``) are applied on the UI thread to the loaded rows,
so neither touches the store.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from statistics import median

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Input, Static

from .. import store
from ..config import Config
from . import fmt
from .clusters import Freshness, freshness

WINDOWS = ((86400, "1 d"), (7 * 86400, "7 d"), (30 * 86400, "30 d"))
FAILED = ("FAILED", "NODE_FAIL", "BOOT_FAIL")
STATE_STYLE = {"RUNNING": "green", "PENDING": "dark_orange", "COMPLETED": "grey62",
               "COMPLETING": "green", "CONFIGURING": "green", "REQUEUED": "dark_orange",
               "SUSPENDED": "dark_orange", "CANCELLED": "grey50",
               "TIMEOUT": "red", "OUT_OF_MEMORY": "red", **{s: "red" for s in FAILED}}

QUEUE_COLUMNS = (("cluster", "Cluster"), ("id", "Job"), ("name", "Name"),
                 ("partition", "Partition"), ("state", "State"), ("elapsed", "Elapsed"),
                 ("left", "Left"), ("start", "Start"), ("cpus", "CPUs"), ("mem", "Mem"),
                 ("gpu", "GPU/node"), ("reason", "Node/reason"))
FINISHED_COLUMNS = (("cluster", "Cluster"), ("id", "Job"), ("name", "Name"),
                    ("state", "State"), ("exit", "Exit"), ("elapsed", "Elapsed"),
                    ("limit", "% limit"), ("mem", "Mem peak (% asked)"), ("cpu", "CPU eff"),
                    ("wait", "Wait"), ("ended", "Ended"), ("node", "Node"))


@dataclass
class JobsData:
    queue: list
    finished: list  # terminal jobs that ended within the longest window
    fresh: dict = field(default_factory=dict)  # cluster -> Freshness of the queue


@dataclass
class Tiles:
    jobs: int
    running: int
    pending: int  # pending tasks: an array range counts each task
    gpu_hours: float
    cpu_hours: float
    failed: int
    timeout: int
    oom: int
    median_wait: float | None


def load_jobs(conn, cfg: Config, now: float) -> JobsData:
    names = {c.name for c in cfg.clusters}
    return JobsData(
        queue=[q for q in store.queue(conn) if q.cluster in names],
        finished=[f for f in store.finished(conn, now - WINDOWS[-1][0]) if f.cluster in names],
        fresh=freshness(conn, cfg, "queue", now))


def _base(state: str) -> str:
    return (state.split() or [""])[0]  # "CANCELLED by 123" -> "CANCELLED"


def in_window(finished, now: float, window: float) -> list:
    return [f for f in finished if (f.end if f.end is not None else now) >= now - window]


def summarize(finished, queue, now: float, window: float) -> Tiles:
    jobs = in_window(finished, now, window)
    states = [_base(f.state) for f in jobs]
    waits = [f.start - f.submit for f in jobs
             if f.start is not None and f.submit is not None and f.start >= f.submit]
    return Tiles(
        jobs=len(jobs),
        running=sum(q.task_count for q in queue if _base(q.state) == "RUNNING"),
        pending=sum(q.task_count for q in queue if _base(q.state) == "PENDING"),
        gpu_hours=sum((f.gpus or 0) * (f.elapsed_s or 0) for f in jobs) / 3600,
        cpu_hours=sum((f.cpus or 0) * (f.elapsed_s or 0) for f in jobs) / 3600,
        failed=sum(s in FAILED for s in states),
        timeout=states.count("TIMEOUT"),
        oom=states.count("OUT_OF_MEMORY"),
        median_wait=median(waits) if waits else None)


# ---------------------------------------------------------------- cells

def _when(t: float | None, now: float) -> str:
    if t is None:
        return fmt.NONE
    f = "%H:%M" if abs(t - now) < 86400 else "%m-%d %H:%M"
    return time.strftime(f, time.localtime(t))


def _gpus(n: float | None) -> str:
    if n is None:
        return fmt.NONE  # N/A in squeue
    return f"{n:g}" if float(n).is_integer() else f"{n:.2f}"


def _state(state: str) -> Text:
    return Text(state, style=STATE_STYLE.get(_base(state), ""))


def queue_cells(q, now: float) -> dict:
    pending = _base(q.state) == "PENDING"
    jid = q.job_id + (f" ×{q.task_count}" if q.task_count > 1 else "")
    left = None if q.limit_s is None else q.limit_s - (q.elapsed_s or 0)
    return {
        "cluster": q.cluster, "id": jid, "name": q.name, "partition": q.partition,
        "state": _state(q.state),
        "elapsed": fmt.NONE if pending else fmt.duration(q.elapsed_s),
        "left": fmt.duration(left), "start": _when(q.start_est, now),
        "cpus": str(q.cpus), "mem": fmt.bytes_(q.mem_bytes) if q.mem_bytes else fmt.NONE,
        "gpu": _gpus(q.gpus), "reason": q.node_or_reason,
    }


def finished_cells(f, now: float) -> dict:
    mem = fmt.bytes_(f.max_rss_bytes)
    if f.max_rss_bytes is not None and f.req_mem_bytes:
        mem += f" ({fmt.pct(f.max_rss_bytes, f.req_mem_bytes)})"
    eff = (fmt.pct(f.total_cpu_s, f.cpus * f.elapsed_s)
           if f.total_cpu_s and f.cpus and f.elapsed_s else fmt.NONE)
    wait = (f.start - f.submit if f.start is not None and f.submit is not None else None)
    exit_style = "" if f.exit_code in ("0:0", "") else "red"
    return {
        "cluster": f.cluster, "id": f.job_id, "name": f.name, "state": _state(f.state),
        "exit": Text(f.exit_code, style=exit_style), "elapsed": fmt.duration(f.elapsed_s),
        "limit": fmt.pct(f.elapsed_s, f.limit_s), "mem": mem, "cpu": eff,
        "wait": fmt.duration(wait), "ended": _when(f.end, now), "node": f.nodes or "",
    }


def matches(text: str, *fields) -> bool:
    t = text.strip().lower()
    return not t or any(t in (x or "").lower() for x in fields)


def _dimmed(cells: dict, dim: bool) -> list:
    out = []
    for v in cells.values():
        if dim:
            v = v.copy() if isinstance(v, Text) else Text(str(v))
            v.stylize("dim")
        out.append(v)
    return out


# ---------------------------------------------------------------- widget

class FilterInput(Input):
    BINDINGS = [Binding("escape", "clear", "Clear filter")]

    def action_clear(self) -> None:
        self.value = ""
        self.display = False
        self.screen.query_one("#queue-table", DataTable).focus()


class JobsView(Vertical):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.data = JobsData([], [])
        self.now = 0.0
        self.window_i = 0

    def compose(self) -> ComposeResult:
        with Horizontal(id="tiles"):
            for key in ("jobs", "gpu", "cpu", "failed", "wait"):
                yield Static("", id=f"tile-{key}", classes="tile")
        yield Static("", id="queue-title", classes="section-title")
        yield DataTable(id="queue-table", cursor_type="row", zebra_stripes=True)
        yield Static("", id="finished-title", classes="section-title")
        yield DataTable(id="finished-table", cursor_type="row", zebra_stripes=True)
        yield FilterInput(placeholder="filter: name, state, job id or cluster (Esc clears)",
                          id="jobs-filter")

    def on_mount(self) -> None:
        for sel, cols in (("#queue-table", QUEUE_COLUMNS), ("#finished-table", FINISHED_COLUMNS)):
            table = self.query_one(sel, DataTable)
            for key, label in cols:
                table.add_column(label, key=key)
        self.query_one("#jobs-filter").display = False
        self._redraw()

    # ------------------------------------------------------------ state

    @property
    def window(self) -> tuple[int, str]:
        return WINDOWS[self.window_i]

    @property
    def filter_text(self) -> str:
        return self.query_one("#jobs-filter", Input).value

    def update_data(self, data: JobsData, now: float) -> None:
        self.data, self.now = data, now
        self._redraw()

    def cycle_window(self) -> None:
        self.window_i = (self.window_i + 1) % len(WINDOWS)
        self._redraw()

    def open_filter(self) -> None:
        box = self.query_one("#jobs-filter", Input)
        box.display = True
        box.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        event.stop()
        self._redraw()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.query_one("#queue-table", DataTable).focus()

    # ------------------------------------------------------------ render

    def _redraw(self) -> None:
        secs, label = self.window
        now, text = self.now, self.filter_text
        t = summarize(self.data.finished, self.data.queue, now, secs)
        self._tiles(t, label)
        queue = [q for q in self.data.queue
                 if matches(text, q.name, q.state, q.job_id, q.cluster)]
        finished = [f for f in in_window(self.data.finished, now, secs)
                    if matches(text, f.name, f.state, f.job_id, f.cluster)]
        fresh: dict[str, Freshness] = self.data.fresh
        self._fill("#queue-table", [
            (f"{q.cluster}/{q.job_id}", _dimmed(queue_cells(q, now),
                                                 fresh.get(q.cluster) is not None
                                                 and fresh[q.cluster].dim))
            for q in queue])
        self._fill("#finished-table", [
            (f"{f.cluster}/{f.job_id}", _dimmed(finished_cells(f, now), False))
            for f in finished])
        qt = Text(f"Queue ({len(queue)})", style="bold")
        notes = []
        for f in fresh.values():
            if f.mode == "down" and any(q.cluster == f.name for q in self.data.queue):
                notes.append(f"{f.name} down, queue from {fmt.age(f.last_ok, now)} ago")
            elif f.stale and f.mode == "active":
                notes.append(f"{f.name} queue {fmt.age(f.last_ok, now)} old")
        if notes:
            qt.append("   " + " · ".join(notes), style="dark_orange")
        if text.strip():
            qt.append(f"   filter: {text.strip()}", style="italic")
        self.query_one("#queue-title", Static).update(qt)
        self.query_one("#finished-title", Static).update(Text.assemble(
            (f"Finished · last {label} ({len(finished)})", "bold"),
            ("   w: window", "dim")))

    def _tiles(self, t: Tiles, label: str) -> None:
        def tile(key, title, value, sub="", style="bold"):
            w = self.query_one(f"#tile-{key}", Static)
            w.border_title = title
            body = Text(value, style=style)
            if sub:
                body.append(f"  {sub}", style="dim")
            w.update(body)

        tile("jobs", f"Jobs · {label}", str(t.jobs), f"now {t.running} R · {t.pending} P")
        tile("gpu", f"GPU-hours · {label}", fmt.hours(t.gpu_hours))
        tile("cpu", f"CPU-hours · {label}", fmt.hours(t.cpu_hours))
        bad = t.failed + t.timeout + t.oom
        tile("failed", "Fail/timeout/OOM", f"{t.failed} / {t.timeout} / {t.oom}",
             style="bold red" if bad else "bold")
        tile("wait", "Median wait", fmt.hm(t.median_wait))

    def _fill(self, sel: str, rows: list) -> None:
        table = self.query_one(sel, DataTable)
        keep = None
        if table.row_count and table.cursor_row is not None:
            try:
                keep = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
            except Exception:
                keep = None
        table.clear()
        for key, cells in rows:
            table.add_row(*cells, key=key)
        if keep is not None:
            try:
                table.move_cursor(row=table.get_row_index(keep), animate=False)
            except Exception:
                pass
