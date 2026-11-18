"""Compact view: replaces the tabs below 80 columns or 20 rows, e.g. a tmux
split. Every line is cut to the width, never wrapped::

    narval ● 2R 0P   rorqual ● 1R 3P   tamia ○ down
    exp065  31/48 ▓▓▓▓▓▓░░ ETA 3h10   1 failed
    tamia /project files 96 % ⚠          updated 15:51
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from rich.text import Text
from textual.widgets import Static

from ..config import Config
from . import fmt
from .cellsview import CampaignRow, load_cells
from .clusters import DOT, ClusterRow, load_clusters
from .jobs import _base, load_jobs
from .storage import load_storage, worst

MIN_WIDTH, MIN_HEIGHT = 80, 20
BAR = 8
SEP = "   "


def is_compact(width: int, height: int) -> bool:
    return width < MIN_WIDTH or height < MIN_HEIGHT


@dataclass
class CompactData:
    clusters: list = field(default_factory=list)  # (ClusterRow, running, pending)
    campaigns: list = field(default_factory=list)  # open CampaignRow
    disk: tuple | None = None  # worst entry at or above 80 %
    updated: float | None = None


def build(rows: list[ClusterRow], queue, campaigns: list[CampaignRow], storage) -> CompactData:
    run: dict[str, int] = {}
    pend: dict[str, int] = {}
    for q in queue:
        s = _base(q.state)
        if s == "RUNNING":
            run[q.cluster] = run.get(q.cluster, 0) + q.task_count
        elif s == "PENDING":
            pend[q.cluster] = pend.get(q.cluster, 0) + q.task_count
    w = worst(storage)
    return CompactData(
        clusters=[(r, run.get(r.name, 0), pend.get(r.name, 0)) for r in rows],
        campaigns=[c for c in campaigns if c.open],
        disk=w if w is not None and w[0] >= fmt.WARN_PCT else None,
        updated=max((r.last_ok for r in rows if r.last_ok is not None), default=None))


def load_compact(conn, cfg: Config, now: float) -> CompactData:
    return build(load_clusters(conn, cfg, now), load_jobs(conn, cfg, now).queue,
                 load_cells(conn, cfg, now), load_storage(conn, cfg, now))


def _cut(t: Text, width: int) -> Text:
    t = t.copy()
    t.no_wrap = True
    if t.cell_len > width:
        t.truncate(max(0, width), overflow="ellipsis")
    return t


def compact_lines(d: CompactData, width: int, height: int | None = None) -> list[Text]:
    width = max(0, width)
    items = []
    for r, nr, np_ in d.clusters:
        glyph, colour = DOT[r.dot]
        t = Text(f"{r.name} ")
        if r.mode == "active":
            t.append(glyph, style=colour)
            t.append(f" {nr}R {np_}P", style="dim" if r.stale else "")
        else:
            t.append(f"{glyph} {r.mode}", style=colour)
        items.append(t)
    # clusters are packed onto as many lines as the width needs (an item is
    # never split); each line is still cut to the width below
    lines = [Text()]
    for t in items:
        cur = lines[-1]
        if cur.cell_len and cur.cell_len + len(SEP) + t.cell_len > width:
            lines.append(Text())
            cur = lines[-1]
        if cur.cell_len:
            cur.append(SEP)
        cur.append_text(t)
    n_head = len(lines)
    for c in d.campaigns:
        t = Text(c.campaign, style="bold")
        total = "?" if c.total is None else str(c.total)
        t.append(f"  {c.done}/{total} ")
        t.append(fmt.bar(c.done, c.total or 0, BAR), style="green")
        if c.total is not None and c.done >= c.total:
            t.append(" done")
        elif c.eta is not None:
            t.append(f" ETA {fmt.hm(c.eta)}")
        if c.failed:
            t.append(f"   {c.failed} failed", style="red")
        lines.append(t)
    upd = Text("updated " + (time.strftime("%H:%M", time.localtime(d.updated))
                             if d.updated is not None else "never"), style="dim")
    tail = []
    if d.disk is not None:
        p, cluster, fs, kind = d.disk
        lv = fmt.level(p)
        disk = Text(f"{cluster} {fs} {kind} {round(p)} % ⚠",
                    style="bold red" if lv == "crit" else "dark_orange")
        gap = width - disk.cell_len - upd.cell_len
        if gap >= 2:
            tail.append(Text.assemble(disk, " " * gap, upd))
        else:
            tail += [disk, Text.assemble(" " * max(0, width - upd.cell_len), upd)]
    else:
        tail.append(Text.assemble(" " * max(0, width - upd.cell_len), upd))
    if height is not None and len(lines) + len(tail) > height:
        keep = max(n_head, height - len(tail) - 1)  # clusters + campaigns that fit + "+N more"
        more = len(lines) - keep
        if more > 0:
            lines = lines[:keep] + [Text(f"+{more} more campaigns", style="dim")]
    out = [_cut(t, width) for t in lines + tail]
    return out if height is None else out[:max(1, height)]


class CompactView(Static):
    """The whole summary in one widget; re-cut on every resize."""

    def __init__(self, **kw):
        super().__init__("", **kw)
        self.data = CompactData()

    def update_data(self, data: CompactData) -> None:
        self.data = data
        self._draw()

    def on_resize(self) -> None:
        self._draw()

    def _draw(self) -> None:
        w, h = self.size.width or self.app.size.width, self.size.height or self.app.size.height
        lines = compact_lines(self.data, w, h)
        out = Text("\n").join(lines)
        out.no_wrap = True
        self.update(out)
