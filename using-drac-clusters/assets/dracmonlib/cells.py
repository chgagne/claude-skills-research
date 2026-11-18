"""Parse the `cells` section and aggregate per-campaign progress."""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median
from typing import Iterable

EVENTS = ("plan", "start", "done", "fail")


@dataclass(frozen=True)
class CellEvent:
    ts: float
    job_id: str
    event: str
    cell: str
    detail: str


@dataclass
class CellChunk:
    relpath: str
    campaign: str
    size: int
    start_offset: int
    events: list = field(default_factory=list)
    consumed: int = 0


@dataclass
class CampaignState:
    campaign: str
    plan: int | None = None
    done: set = field(default_factory=set)
    running: set = field(default_factory=set)
    failed: dict = field(default_factory=dict)
    durations: list = field(default_factory=list)
    last_failure: tuple | None = None
    last_event: float | None = None
    clusters: set = field(default_factory=set)


def parse_line(line: str) -> CellEvent | None:
    parts = line.split("\t", 4)
    if len(parts) < 4 or parts[2] not in EVENTS:
        return None
    try:
        ts = float(parts[0])
    except ValueError:
        return None
    if ts != ts or ts in (float("inf"), float("-inf")):
        return None
    detail = parts[4] if len(parts) > 4 else ""
    return CellEvent(ts, parts[1], parts[2], parts[3], detail)


def parse_cells_section(body: str, offsets: dict | None = None) -> list:
    offsets = offsets or {}
    chunks: list[CellChunk] = []
    cur: CellChunk | None = None
    skip = False
    for line in body.splitlines(keepends=True):
        if line.startswith("#file "):
            rest = line[6:].rstrip("\n").split(" ", 1)
            try:
                size = int(rest[0])
                rel = rest[1]
            except (ValueError, IndexError):
                cur = None
                continue
            off = offsets.get(rel, 0)
            reset = size < off
            cur = CellChunk(rel, rel.split("/", 1)[0], size, 0 if reset else off)
            skip = reset
            chunks.append(cur)
            continue
        if cur is None or skip or not line.endswith("\n"):
            continue  # no marker yet, reset chunk, or torn final line
        cur.consumed += len(line.encode("utf-8"))
        e = parse_line(line[:-1])
        if e is not None:
            cur.events.append(e)
    return chunks


def aggregate(events: Iterable) -> CampaignState:
    s = CampaignState("")
    items = sorted(events, key=lambda p: p[1].ts)  # stable: file order breaks ties
    starts: dict = {}  # (cluster, job, cell) -> latest start ts
    latest: dict = {}  # cell -> latest start/fail event
    plan_ts = None
    for cluster, e in items:
        s.clusters.add(cluster)
        s.last_event = e.ts if s.last_event is None else max(s.last_event, e.ts)
        if e.event == "plan":
            try:
                n = int(e.detail)
            except ValueError:
                continue
            if plan_ts is None or e.ts >= plan_ts:
                s.plan, plan_ts = n, e.ts
        elif e.event == "start":
            starts[(cluster, e.job_id, e.cell)] = e.ts
            latest[e.cell] = e
        elif e.event == "fail":
            latest[e.cell] = e
            s.last_failure = (e.cell, e.detail, e.ts)
        elif e.event == "done":
            s.done.add(e.cell)
            t0 = starts.get((cluster, e.job_id, e.cell))
            if t0 is not None:
                s.durations.append(e.ts - t0)
    for cell, e in latest.items():
        if cell in s.done:
            continue
        if e.event == "start":
            s.running.add(cell)
        else:
            s.failed[cell] = e.detail
    return s


def eta_seconds(s: CampaignState) -> float | None:
    if s.plan is None or not s.durations:
        return None
    remaining = max(0, s.plan - len(s.done))
    return remaining * median(s.durations) / max(1, len(s.running))


def is_open(s: CampaignState, campaign_has_live_job: bool, now: float, window: int = 86400) -> bool:
    if campaign_has_live_job:
        return True
    return s.last_event is not None and now - s.last_event < window


def glob_progress(count: int, total: int) -> CampaignState:
    s = CampaignState("", plan=total)
    s.done = {f"item{i}" for i in range(count)}
    return s
