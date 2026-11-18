"""Collector: decides which clusters and sections are due, polls them in
parallel over EXISTING ssh sockets, parses the output and stores it.

Threads: worker threads only run ``ssh.socket_live`` / ``ssh.poll_cluster``
(subprocesses, no sqlite). Parsing and every store write happen on the main
thread, one writer, one connection.

Cluster modes (keepalive policy of the spec):
- ``active``: live socket and (jobs, an open cells campaign, pinned, or active
  within ``idle_release``). Polled on its cadences; each poll keeps the master up.
- ``released``: idle. No remote command at all, except a light ``env``+``queue``
  check once per ``released_check`` or when the socket comes back.
- ``down``: active or recent but the socket is gone, or the poll failed. The
  stored data is kept (the store never writes data rows from a failed poll).
- ``disconnected``: never active and no live socket.
"""
from __future__ import annotations

import logging
import os
import re
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from . import parse, ssh, store
from .cells import is_open, parse_cells_section
from .config import Cluster, Config, state_dir
from .gpu import shards_per_card
from .store import ParsedPoll

DB_NAME = "dracmon.sqlite"
LOG_NAME = "collector.log"
REFRESH_NAME = "refresh"
TICK = 30.0
GRACE = 15.0  # half a tick: a section due a few seconds after this tick runs now
HOUR = 3600.0
DAY = 86400.0
USAGE_STEP = 7 * DAY  # one sacct usage window (DRAC rejects ranges >= 29 d)
USAGE_HISTORY = 28 * DAY  # backfill depth
PRUNE_EVERY = DAY

# polled sections (env is always added) -> the cadence key that schedules them
SECTIONS = ("queue", "accounting", "fairshare", "usage", "disk", "partitions", "cells", "globs")
CADENCE_KEY = {"queue": "queue", "accounting": "accounting", "fairshare": "usage",
               "usage": "usage", "disk": "disk", "partitions": "partitions",
               "cells": "cells", "globs": "cells"}

log = logging.getLogger("dracmon.collector")
log.propagate = False  # collector.log (added by collect) is the only sink
_TZ = re.compile(r"^([+-])(\d\d)(\d\d)$")
_GLOB = re.compile(r"^#glob (\S+) (\d+)$")


# ---------------------------------------------------------------- pure rules

def classify(live: bool, active: bool, last_active: float | None, now: float,
             idle_release: int) -> str:
    recent = last_active is not None and now - last_active < idle_release
    if live:
        return "active" if active or recent else "released"
    if active or recent:
        return "down"
    return "released" if last_active is not None else "disconnected"


def _older(t: float | None, period: float, now: float) -> bool:
    return t is None or now - t >= period - GRACE


def due_sections(mode: str, last_ok: dict[str, float | None], cadence: dict[str, int],
                 now: float, released_check_due: bool,
                 attempted: dict[str, float | None] | None = None) -> list[str]:
    """Sections to request now. ``active``: each section whose last success is
    older than its cadence (cells and globs on the cells cadence; ``accounting``
    brings ``steps`` in the ssh layer) and, when ``attempted`` is given, not
    tried within its cadence either (a section that always fails, such as
    ``disk`` where diskusage_report is absent, is retried on its cadence, not
    every tick). ``env`` leads any non-empty list. ``released``: ``env`` and
    ``queue`` when the light check is due. ``down``/``disconnected``: nothing."""
    if mode == "active":
        attempted = attempted or {}
        due = [s for s in SECTIONS
               if _older(last_ok.get(s), cadence[CADENCE_KEY[s]], now)
               and _older(attempted.get(s), cadence[CADENCE_KEY[s]], now)]
        return ["env", *due] if due else []
    if mode == "released" and released_check_due:
        return ["env", "queue"]
    return []


def cluster_time(epoch: float, tz: str) -> str | None:
    """``YYYY-MM-DDTHH:MM:SS`` at UTC offset ``tz`` (``-0800``), as sacct reads it
    on that cluster. None when the offset is unknown or malformed."""
    m = _TZ.match((tz or "").strip())
    if not m:
        return None
    sign = -1 if m.group(1) == "-" else 1
    off = timezone(sign * timedelta(hours=int(m.group(2)), minutes=int(m.group(3))))
    return datetime.fromtimestamp(epoch, off).strftime("%Y-%m-%dT%H:%M:%S")


def _ok(result, name: str):
    """The section's body when it arrived complete with rc 0, else None. A
    failed command's empty output must never read as "no jobs"."""
    s = result.sections.get(name)
    return s.body if s is not None and s.complete and s.rc == 0 else None


def parse_poll(result, offsets: dict[str, int], shards_hint: dict[str, int] | None) -> ParsedPoll:
    """PollResult -> ParsedPoll (pure). A failed poll parses nothing. GPU shards
    per card come from this poll's partitions when present, else ``shards_hint``
    (the stored partitions of that cluster)."""
    p = ParsedPoll()
    if not result.ok:
        return p
    env_body = _ok(result, "env")
    p.env = parse.parse_env(env_body) if env_body is not None else dict(result.env)
    tz = p.env.get("tz", "")
    cluster = result.cluster
    body = _ok(result, "partitions")
    if body is not None:
        p.partitions = parse.parse_sinfo(body, cluster)
        p.skipped["partitions"] = parse.parse_sinfo.last_skipped
    shards = (shards_per_card(p.partitions) if p.partitions else {}) or dict(shards_hint or {})
    body = _ok(result, "queue")
    if body is not None:
        p.queue = parse.parse_squeue(body, cluster, tz, shards)
        p.skipped["queue"] = parse.parse_squeue.last_skipped
    body, steps = _ok(result, "accounting"), _ok(result, "steps")
    if body is not None and steps is not None:  # without steps MaxRSS would be lost
        p.accounting = parse.parse_sacct(body, steps, cluster, tz, shards)
        p.skipped["accounting"] = parse.parse_sacct.last_skipped
    body = _ok(result, "fairshare")
    if body is not None:
        p.shares = parse.parse_sshare(body, cluster)
        p.skipped["fairshare"] = parse.parse_sshare.last_skipped
    body = _ok(result, "usage")
    if body is not None:
        p.usage = parse.parse_usage(body, cluster, tz, shards)
        p.skipped["usage"] = parse.parse_usage.last_skipped
    body = _ok(result, "disk")
    if body is not None:
        p.disk = parse.parse_disk(body, cluster)
        p.skipped["disk"] = parse.parse_disk.last_skipped
    body = _ok(result, "cells")
    if body is not None:
        p.cells = parse_cells_section(body, offsets)
    body = _ok(result, "globs")
    if body is not None:
        globs, bad = [], 0
        for line in body.splitlines():
            if not line.strip():
                continue
            m = _GLOB.match(line.strip())
            if m:
                globs.append((m.group(1), int(m.group(2))))
            else:
                bad += 1
        p.globs = globs
        if bad:
            p.skipped["globs"] = bad
    return p


# ---------------------------------------------------------------- store-derived state

def _queue_ids(conn, cluster: str) -> set[str]:
    ids: set[str] = set()
    for job, arr in conn.execute("SELECT job_id, array_job_id FROM queue WHERE cluster = ?",
                                 (cluster,)):
        ids.add(job)
        if arr:
            ids.add(arr)
    return ids


def _active_map(conn, cfg: Config, now: float, only: str | None = None) -> dict[str, bool]:
    """cluster -> has stored queue rows, an open cells campaign, or is pinned.
    Glob campaigns do not count: their stored count is refreshed by every poll,
    so they would keep a cluster active forever."""
    clusters = [c for c in cfg.clusters if only is None or c.name == only]
    queues = {c.name: _queue_ids(conn, c.name) for c in clusters}
    out = {c.name: c.pinned or bool(queues[c.name]) for c in clusters}
    if all(out.values()):
        return out
    for st in store.campaigns(conn):
        todo = [n for n in st.clusters if n in out and not out[n]]
        if not todo:
            continue
        events = store.campaign_cells(conn, st.campaign)
        for n in todo:
            live_job = any(cl == n and (e.job_id in queues[n]
                                        or e.job_id.split("_", 1)[0] in queues[n])
                           for cl, e in events)
            out[n] = is_open(st, live_job, now)
    return out


def is_active(conn, cfg: Config, cluster: Cluster, now: float) -> bool:
    if cluster not in cfg.clusters:
        cfg = Config(clusters=[cluster])
    return _active_map(conn, cfg, now, only=cluster.name)[cluster.name]


def _last_attempts(conn, cluster: str) -> dict[str, float]:
    return dict(conn.execute("SELECT section, max(finished) FROM poll_section "
                             "WHERE cluster = ? GROUP BY section", (cluster,)))


def _meta_float(conn, key: str) -> float | None:
    v = store.get_meta(conn, key)
    try:
        return float(v) if v is not None else None
    except ValueError:
        return None


def _usage_plan(conn, cluster: str, tz: str, now: float):
    """(usage_window or None, (kind, start epoch)). While the backfill frontier
    (oldest covered epoch) is later than now - 28 d, the window is the next
    older 7-day window; otherwise [max(last normal success - 1 h, now - 7 d), now].
    Unknown tz: the remote default (last 7 days)."""
    frontier = _meta_float(conn, f"usage_backfill:{cluster}")
    if tz and frontier is not None and frontier > now - USAGE_HISTORY:
        start, end, kind = frontier - USAGE_STEP, frontier, "backfill"
    else:
        recent = _meta_float(conn, f"usage_recent:{cluster}")
        start = now - USAGE_STEP if recent is None else max(recent - HOUR, now - USAGE_STEP)
        end, kind = now, "normal"
    a, b = cluster_time(start, tz), cluster_time(end, tz)
    window = (a, b) if a and b else None
    if window is None:
        start, kind = now - USAGE_STEP, "normal"
    return window, (kind, start)


def _record_usage(conn, cluster: str, result, plan) -> None:
    kind, start = plan
    if kind == "backfill":
        store.set_meta(conn, f"usage_backfill:{cluster}", repr(start))
        return
    store.set_meta(conn, f"usage_recent:{cluster}", repr(result.started))
    if store.get_meta(conn, f"usage_backfill:{cluster}") is None:
        store.set_meta(conn, f"usage_backfill:{cluster}", repr(start))


def _set_mode(conn, cluster: str, mode: str, last_active, status) -> None:
    if status is not None and (status.mode, status.last_active) == (mode, last_active):
        return
    if status is None or status.mode != mode:
        log.info("%s mode %s", cluster, mode)
    store.set_cluster_mode(conn, cluster, mode, last_active)


def _safe_poll(cluster: Cluster, sections: list[str], kw: dict):
    try:
        return ssh.poll_cluster(cluster, sections, **kw)
    except Exception as e:  # never let one cluster take the cycle down
        t = time.time()
        return ssh.PollResult(cluster.name, t, t, False, f"poll error: {e}", ["env", *sections])


# ---------------------------------------------------------------- one cycle

def run_cycle(cfg: Config, conn, now: float, force=frozenset(), stop=None) -> list:
    """One collector cycle; returns the PollResults written. ``force`` makes
    every section due for those clusters (still only when the socket is live)."""
    clusters = list(cfg.clusters)
    if not clusters:
        return []
    with ThreadPoolExecutor(max_workers=len(clusters)) as ex:
        lives = dict(zip([c.name for c in clusters],
                         ex.map(lambda c: ssh.socket_live(c.host), clusters)))
    status = store.cluster_status(conn)
    active = _active_map(conn, cfg, now)
    plans = {}
    for c in clusters:
        st = status.get(c.name)
        live, act = lives[c.name], active[c.name]
        last_active = now if act else (st.last_active if st else None)
        mode = classify(live, act, last_active, now, cfg.idle_release)
        # A live master can answer -O check while the remote side keeps failing:
        # stay down until a poll succeeds. Scheduling still uses the classified
        # mode, so the cluster keeps being polled on its cadences and can recover.
        shown = "down" if mode == "active" and st is not None and st.last_error else mode
        prev_live = store.get_meta(conn, f"live:{c.name}")
        if prev_live != ("1" if live else "0"):
            store.set_meta(conn, f"live:{c.name}", "1" if live else "0")
        checked = _meta_float(conn, f"released_check:{c.name}")
        released_due = live and (prev_live == "0" or _older(checked, cfg.released_check, now))
        globs = [(g.campaign, g.done_glob) for g in cfg.glob_campaigns if g.cluster == c.name]
        if not live:
            secs = []
        elif c.name in force:
            secs = ["env", *SECTIONS]
        else:
            last = {s: store.last_ok(conn, c.name, s) for s in SECTIONS}
            secs = due_sections(mode, last, cfg.cadence, now, released_due,
                                _last_attempts(conn, c.name))
        if not globs:
            secs = [s for s in secs if s != "globs"]
        if secs in ([], ["env"]):
            _set_mode(conn, c.name, shown, last_active, st)
            continue
        if mode == "released":
            store.set_meta(conn, f"released_check:{c.name}", repr(now))
        tz = (st.env if st else {}).get("tz", "")
        acc = store.accounting_since(conn, c.name)
        since = cluster_time(acc - HOUR if acc is not None else now - DAY, tz) if tz else None
        window, uplan = _usage_plan(conn, c.name, tz, now)
        offsets = store.cells_offsets(conn, c.name)
        kw = dict(since=since, offsets=offsets, globs=globs,
                  retention_days=cfg.cells_retention_days, timeout=cfg.ssh_timeout,
                  usage_window=window)
        plans[c.name] = (c, secs, kw, uplan, mode, last_active, st)
    results = []
    if not plans or (stop is not None and stop.is_set()):
        return results
    with ThreadPoolExecutor(max_workers=len(plans)) as ex:
        futs = {ex.submit(_safe_poll, c, secs, kw): name
                for name, (c, secs, kw, *_rest) in plans.items()}
        for fut in as_completed(futs):
            name = futs[fut]
            c, secs, kw, uplan, mode, last_active, st = plans[name]
            res = fut.result()
            try:
                _store_result(conn, cfg, res, kw, uplan, mode, last_active, st, now)
            except Exception:
                log.exception("%s: storing the poll failed", name)
                continue
            results.append(res)
    return results


def _store_result(conn, cfg, res, kw, uplan, mode, last_active, st, now) -> None:
    name = res.cluster
    hint = shards_per_card([p for p in store.partitions(conn) if p.cluster == name])
    parsed = parse_poll(res, kw["offsets"], hint)
    store.write_poll(conn, res, parsed)
    log.info("%s poll %s %.1fs sections=%s%s", name, "ok" if res.ok else "FAIL",
             res.finished - res.started, ",".join(res.requested),
             "" if res.ok else f" error={res.error}")
    if res.ok:
        if parsed.usage is not None:
            _record_usage(conn, name, res, uplan)
        cl = next(c for c in cfg.clusters if c.name == name)
        act = is_active(conn, cfg, cl, now)
        last_active = now if act else last_active
        mode = classify(True, act, last_active, now, cfg.idle_release)
    elif mode == "active":
        mode = "down"  # data untouched: the store wrote the poll record only
    _set_mode(conn, name, mode, last_active, st)


# ---------------------------------------------------------------- refresh trigger

def request_refresh(state_dir: Path, clusters: set[str] | None) -> None:
    """Ask the running collector to poll now: ``*`` (all) or cluster names, one
    per line. Merges with a request not yet taken."""
    path = Path(state_dir) / REFRESH_NAME
    lines: set[str] = set()
    try:
        lines = {ln.strip() for ln in path.read_text().splitlines() if ln.strip()}
    except OSError:
        pass
    lines |= {"*"} if clusters is None else set(clusters)
    tmp = path.with_name(f"{REFRESH_NAME}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text("".join(f"{x}\n" for x in sorted(lines)))
    os.replace(tmp, path)


def take_refresh(state_dir: Path, names) -> set[str]:
    """Consume the trigger file (renamed first, so a request written meanwhile
    is not lost) and return the configured clusters it names."""
    path = Path(state_dir) / REFRESH_NAME
    taking = path.with_name(f"{REFRESH_NAME}.taking")
    try:
        os.replace(path, taking)
    except FileNotFoundError:
        return set()
    try:
        want = {ln.strip() for ln in taking.read_text().splitlines() if ln.strip()}
    finally:
        taking.unlink(missing_ok=True)
    names = list(names)
    return set(names) if "*" in want else {n for n in names if n in want}


# ---------------------------------------------------------------- loop

def _lock_holder(path: Path) -> str:
    try:
        return path.read_text().strip() or "?"
    except OSError:
        return "?"


def _maybe_prune(conn, cfg: Config, now: float) -> None:
    last = _meta_float(conn, "last_prune")
    if last is None or now - last >= PRUNE_EVERY:
        store.prune(conn, cfg, now)
        store.set_meta(conn, "last_prune", repr(now))
        log.info("pruned")


def _wait(stop: threading.Event, tick: float, refresh: Path) -> None:
    """Interruptible wait: returns early on stop or on a refresh request."""
    end = time.monotonic() + tick
    while not stop.is_set():
        left = end - time.monotonic()
        if left <= 0 or refresh.exists():
            return
        stop.wait(min(1.0, left))


def collect(cfg: Config, once: bool, *, state: Path | None = None, now=time.time,
            tick: float = TICK, stop: threading.Event | None = None) -> int:
    """Run the collector (one cycle with ``once``). Returns 1 when another
    poller holds the lock. SIGTERM/SIGINT let the current cycle's writes finish,
    release the lock and return 0."""
    sd = Path(state) if state is not None else state_dir()
    sd.mkdir(parents=True, exist_ok=True)
    lock = store.PollLock(sd)  # referenced until the finally below: __del__ would release it
    if not lock.try_acquire():
        print(f"another dracmon poller is running (pid {_lock_holder(lock.path)})",
              file=sys.stderr)
        return 1
    stop = stop or threading.Event()
    handler = RotatingFileHandler(sd / LOG_NAME, maxBytes=1_000_000, backupCount=3)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    old_handlers = {}
    if threading.current_thread() is threading.main_thread():
        for sig in (signal.SIGTERM, signal.SIGINT):
            old_handlers[sig] = signal.signal(sig, lambda *_: stop.set())
    conn = None
    try:
        db = sd / DB_NAME
        moved = store.check_and_recover(db)
        if moved is not None:
            log.warning("store was corrupt, moved aside to %s", moved)
        conn = store.open_store(db)
        names = [c.name for c in cfg.clusters]
        while True:
            t = now()
            try:
                run_cycle(cfg, conn, t, take_refresh(sd, names), stop)
                _maybe_prune(conn, cfg, t)
            except Exception:
                log.exception("collector cycle failed")
            if once or stop.is_set():
                break
            _wait(stop, tick, sd / REFRESH_NAME)
            if stop.is_set():
                break
    finally:
        for sig, h in old_handlers.items():
            signal.signal(sig, h)
        if conn is not None:
            conn.close()
        log.removeHandler(handler)
        handler.close()
        lock.release()
    return 0
