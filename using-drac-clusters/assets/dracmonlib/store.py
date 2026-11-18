"""Local SQLite store: the collector writes, the TUI reads.

Crash safety: WAL with ``synchronous=NORMAL``; each poll is parsed fully before
``write_poll`` and written in ONE ``BEGIN IMMEDIATE ... COMMIT``, so an
interrupted write leaves the previous state intact. Readers never block on the
writer (WAL). ``check_and_recover`` moves a corrupt file aside and keeps it.
``PollLock`` makes sure one poller runs at a time, across and within processes.
"""
from __future__ import annotations

import fcntl
import json
import os
import shutil
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

from .cells import CampaignState, CellEvent, aggregate, glob_progress
from .config import Config
from .parse import DiskRow, FinishedJob, PartitionRow, QueueRow, ShareRow, UsageRow

SCHEMA_VERSION = 1
LOCK_NAME = "dracmon.lock"
# sacct keeps rows for jobs still alive; matched on the state's first word
# (states can read "CANCELLED by 0")
_ACTIVE_STATES = frozenset({"PENDING", "RUNNING", "REQUEUED", "SUSPENDED", "CONFIGURING",
                            "COMPLETING", "RESIZING", "REQUEUE_HOLD", "REQUEUE_FED"})
_CORRUPT_CODES = (11, 26)  # SQLITE_CORRUPT, SQLITE_NOTADB

# section name in PollResult.requested -> ParsedPoll field that carries its data
SECTION_FIELD = {"queue": "queue", "accounting": "accounting", "steps": "accounting",
                 "fairshare": "shares", "usage": "usage", "disk": "disk",
                 "partitions": "partitions", "cells": "cells", "globs": "globs",
                 "env": "env"}

_MIGRATIONS: list[list[str]] = [
    [  # 0 -> 1
        """CREATE TABLE poll (cluster TEXT NOT NULL, started REAL NOT NULL,
           finished REAL NOT NULL, ok INTEGER NOT NULL, error TEXT)""",
        "CREATE INDEX poll_cluster ON poll (cluster, finished)",
        """CREATE TABLE poll_section (cluster TEXT NOT NULL, section TEXT NOT NULL,
           started REAL NOT NULL, finished REAL NOT NULL, ok INTEGER NOT NULL,
           error TEXT, skipped INTEGER NOT NULL DEFAULT 0)""",
        "CREATE INDEX poll_section_key ON poll_section (cluster, section, ok, finished)",
        """CREATE TABLE cluster (cluster TEXT PRIMARY KEY, mode TEXT NOT NULL DEFAULT 'unknown',
           last_active REAL, env TEXT NOT NULL DEFAULT '{}')""",
        """CREATE TABLE queue (cluster TEXT NOT NULL, job_id TEXT NOT NULL,
           array_job_id TEXT, array_tasks TEXT, name TEXT, partition TEXT, state TEXT,
           elapsed_s INTEGER, limit_s INTEGER, start_est REAL, cpus INTEGER,
           mem_bytes INTEGER, gpus REAL, node_or_reason TEXT, account TEXT, submit REAL,
           task_count INTEGER, PRIMARY KEY (cluster, job_id))""",
        """CREATE TABLE finished (cluster TEXT NOT NULL, job_id TEXT NOT NULL, name TEXT,
           account TEXT, partition TEXT, state TEXT, exit_code TEXT, elapsed_s INTEGER,
           limit_s INTEGER, submit REAL, start REAL, "end" REAL, nodes TEXT, cpus INTEGER,
           gpus REAL, req_mem_bytes INTEGER, max_rss_bytes INTEGER, total_cpu_s INTEGER,
           seen REAL NOT NULL, PRIMARY KEY (cluster, job_id))""",
        """CREATE TABLE usage (cluster TEXT NOT NULL, job_id TEXT NOT NULL, user TEXT,
           account TEXT, state TEXT, start REAL, elapsed_s INTEGER, cpus INTEGER, gpus REAL,
           seen REAL NOT NULL, PRIMARY KEY (cluster, job_id))""",
        """CREATE TABLE share (cluster TEXT NOT NULL, account TEXT, user TEXT,
           raw_usage INTEGER, effective_usage REAL, level_fs REAL, fairshare REAL,
           level_fs_inf INTEGER NOT NULL DEFAULT 0)""",
        """CREATE TABLE disk (cluster TEXT NOT NULL, filesystem TEXT, scope TEXT,
           used_bytes INTEGER, quota_bytes INTEGER, files INTEGER, files_quota INTEGER,
           owner TEXT)""",
        """CREATE TABLE partition (cluster TEXT NOT NULL, partition TEXT, avail TEXT,
           limit_s INTEGER, nodes INTEGER, state TEXT, gres TEXT, is_default INTEGER)""",
        """CREATE TABLE cell_event (cluster TEXT NOT NULL, relpath TEXT NOT NULL,
           offset INTEGER NOT NULL, campaign TEXT NOT NULL, ts REAL NOT NULL,
           job_id TEXT, event TEXT, cell TEXT, detail TEXT,
           PRIMARY KEY (cluster, relpath, offset))""",
        "CREATE INDEX cell_event_campaign ON cell_event (campaign, ts)",
        """CREATE TABLE cell_file (cluster TEXT NOT NULL, relpath TEXT NOT NULL,
           campaign TEXT NOT NULL, offset INTEGER NOT NULL, size INTEGER, seen REAL NOT NULL,
           PRIMARY KEY (cluster, relpath))""",
        """CREATE TABLE glob_count (cluster TEXT NOT NULL, campaign TEXT NOT NULL,
           count INTEGER NOT NULL, seen REAL NOT NULL, PRIMARY KEY (cluster, campaign))""",
        "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
    ],
]
assert len(_MIGRATIONS) == SCHEMA_VERSION


@dataclass
class ParsedPoll:
    """Parsed data per section; ``None`` = section not run or incomplete, which
    leaves its stored rows untouched. ``skipped`` (section -> lines skipped by
    the parser) goes into the poll_section rows."""
    queue: list[QueueRow] | None = None
    accounting: list[FinishedJob] | None = None
    shares: list[ShareRow] | None = None
    usage: list[UsageRow] | None = None
    disk: list[DiskRow] | None = None
    partitions: list[PartitionRow] | None = None
    cells: list | None = None  # list[CellChunk]
    globs: list[tuple[str, int]] | None = None
    env: dict | None = None
    skipped: dict[str, int] = field(default_factory=dict)


@dataclass
class ClusterStatus:
    cluster: str
    mode: str
    last_poll: float | None
    last_ok: float | None
    last_error: str | None
    last_active: float | None
    env: dict


class LockBusy(RuntimeError):
    """Another poller holds dracmon.lock."""


# ---------------------------------------------------------------- open / recover

def open_store(path: Path) -> sqlite3.Connection:
    """Open (creating and migrating if needed). Autocommit mode: every write
    transaction is an explicit BEGIN IMMEDIATE. One connection per thread:
    sqlite3 connections must not be shared; separate writers are serialised by
    BEGIN IMMEDIATE + busy_timeout."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=5.0, isolation_level=None)
    try:
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        _migrate(conn)
    except BaseException:
        conn.close()
        raise
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version > SCHEMA_VERSION:
        raise RuntimeError(f"store schema v{version} is newer than this dracmon "
                           f"(v{SCHEMA_VERSION}); upgrade dracmon")
    if version == SCHEMA_VERSION:
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        version = conn.execute("PRAGMA user_version").fetchone()[0]  # re-read under lock
        for v in range(version, SCHEMA_VERSION):
            for stmt in _MIGRATIONS[v]:
                conn.execute(stmt)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:  # SQLite may already have rolled back
            conn.execute("ROLLBACK")
        raise


def check_and_recover(path: Path) -> Path | None:
    """``PRAGMA quick_check``; on corruption (or not a database) move the file
    and its -wal/-shm aside as ``<name>.corrupt-<YYYYmmddTHHMMSS>`` and return
    the new path. ``None`` when the file is missing or healthy. Other errors
    (e.g. a lock held too long) are raised, never treated as corruption."""
    path = Path(path)
    if not path.exists():
        return None
    # closing the check connection deletes the -wal of a file it cannot read:
    # keep a copy so the WAL is preserved for inspection
    wal = Path(str(path) + "-wal")
    wal_copy = path.with_name(f"{path.name}.check-wal")
    if wal_copy.exists():  # left by a check that crashed: not this file's WAL
        wal_copy.unlink()
    if wal.exists():
        shutil.copy2(wal, wal_copy)
    bad = False
    try:
        conn = sqlite3.connect(str(path), timeout=5.0, isolation_level=None)
        try:
            conn.execute("PRAGMA busy_timeout = 5000")
            rows = conn.execute("PRAGMA quick_check").fetchall()
            bad = rows != [("ok",)]
        except sqlite3.DatabaseError as e:
            if getattr(e, "sqlite_errorcode", None) not in _CORRUPT_CODES:
                raise
            bad = True
        finally:
            conn.close()
    finally:
        if not bad and wal_copy.exists():
            wal_copy.unlink()
    if not bad:
        return None
    stamp = time.strftime("%Y%m%dT%H%M%S")
    dest = path.with_name(f"{path.name}.corrupt-{stamp}")
    n = 1
    while any(Path(str(dest) + s).exists() for s in ("", "-wal", "-shm")):
        dest = path.with_name(f"{path.name}.corrupt-{stamp}-{n}")
        n += 1
    if wal_copy.exists():
        os.replace(wal_copy, str(dest) + "-wal")
    for suffix in ("-wal", "-shm", ""):  # main file last: a crash leaves it in place
        src = Path(str(path) + suffix)
        if src.exists():
            os.replace(src, str(dest) + suffix)
    return dest


# ---------------------------------------------------------------- lock

class PollLock:
    """Non-blocking exclusive flock on ``<state_dir>/dracmon.lock``. The file is
    opened per instance, and flock locks belong to the open file description,
    so two instances exclude each other within one process too.

    Lifetime: ``__del__`` releases the lock, so keep the object referenced for
    the whole poll (``PollLock(d).try_acquire()`` alone is released at once)."""

    def __init__(self, state_dir: Path):
        self.path = Path(state_dir) / LOCK_NAME
        self._fd: int | None = None

    @property
    def held(self) -> bool:
        return self._fd is not None

    def try_acquire(self) -> bool:
        if self._fd is not None:
            return True
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return False
        os.ftruncate(fd, 0)
        os.write(fd, f"{os.getpid()}\n".encode())
        self._fd = fd
        return True

    def release(self) -> None:
        if self._fd is None:
            return
        fd, self._fd = self._fd, None
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def __enter__(self) -> "PollLock":
        if not self.try_acquire():
            raise LockBusy(f"{self.path} is held by another poller")
        return self

    def __exit__(self, *exc) -> None:
        self.release()

    def __del__(self):
        try:
            self.release()
        except Exception:
            pass


# ---------------------------------------------------------------- writes

def _tx(conn: sqlite3.Connection, fn, *args) -> None:
    conn.execute("BEGIN IMMEDIATE")
    try:
        fn(conn, *args)
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:  # SQLite may already have rolled back
            conn.execute("ROLLBACK")
        raise


def _section_outcome(result, parsed: ParsedPoll, name: str) -> tuple[bool, str | None]:
    if not result.ok:
        return False, result.error or "poll failed"
    sec = result.sections.get(name)
    if sec is None:
        return False, "incomplete output"
    fld = SECTION_FIELD.get(name)
    if fld is not None and getattr(parsed, fld) is None:
        if name == "env" and result.env:
            return True, None
        return False, f"not stored (rc={sec.rc})" if sec.rc else "not stored"
    return True, None


def write_poll(conn: sqlite3.Connection, result, parsed: ParsedPoll) -> None:
    """Store one poll in a single transaction. Data rows change only when
    ``result.ok``; a failed poll records the poll and its sections, nothing else."""
    if result.ok and parsed.cells:
        for ch in parsed.cells:
            if len(ch.event_offsets) != len(ch.events):
                raise ValueError(f"cell chunk {ch.relpath!r} has no per-event offsets "
                                 "(build it with parse_cells_section)")
    _tx(conn, _write_poll, result, parsed)


def _write_poll(conn, result, parsed: ParsedPoll) -> None:
    c, t0, t1 = result.cluster, result.started, result.finished
    conn.execute("INSERT INTO poll VALUES (?,?,?,?,?)",
                 (c, t0, t1, int(bool(result.ok)), result.error))
    for name in result.requested:
        ok, err = _section_outcome(result, parsed, name)
        conn.execute("INSERT INTO poll_section VALUES (?,?,?,?,?,?,?)",
                     (c, name, t0, t1, int(ok), err, int(parsed.skipped.get(name, 0))))
    if not result.ok:
        return
    env = parsed.env if parsed.env is not None else result.env
    if env:
        conn.execute("INSERT INTO cluster (cluster, env) VALUES (?, ?) "
                     "ON CONFLICT (cluster) DO UPDATE SET env = excluded.env",
                     (c, json.dumps(env)))
    for fld, writer in (("queue", "_write_queue"), ("accounting", "_write_accounting"),
                        ("shares", "_write_shares"), ("usage", "_write_usage"),
                        ("disk", "_write_disk"), ("partitions", "_write_partitions"),
                        ("cells", "_write_cells"), ("globs", "_write_globs")):
        rows = getattr(parsed, fld)
        if rows is not None:
            globals()[writer](conn, c, rows, t1)  # looked up at call time (tests patch)


def _replace(conn, table: str, cluster: str, rows: list[tuple]) -> None:
    """Replace the cluster's rows. OR REPLACE: on a keyed table (queue) a
    duplicate row keeps the last one instead of aborting the whole poll."""
    conn.execute(f"DELETE FROM {table} WHERE cluster = ?", (cluster,))
    if rows:
        marks = ",".join("?" * len(rows[0]))
        conn.executemany(f"INSERT OR REPLACE INTO {table} VALUES ({marks})", rows)


def _write_queue(conn, cluster, rows, now):
    _replace(conn, "queue", cluster, [(
        cluster, r.job_id, r.array_job_id, r.array_tasks, r.name, r.partition, r.state,
        r.elapsed_s, r.limit_s, r.start_est, r.cpus, r.mem_bytes, r.gpus, r.node_or_reason,
        r.account, r.submit, r.task_count) for r in rows])


def _write_accounting(conn, cluster, rows, now):
    conn.executemany("INSERT OR REPLACE INTO finished VALUES "
                     "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [(
                         cluster, r.job_id, r.name, r.account, r.partition, r.state,
                         r.exit_code, r.elapsed_s, r.limit_s, r.submit, r.start, r.end,
                         r.nodes, r.cpus, r.gpus, r.req_mem_bytes, r.max_rss_bytes,
                         r.total_cpu_s, now) for r in rows])


def _write_usage(conn, cluster, rows, now):
    conn.executemany("INSERT OR REPLACE INTO usage VALUES (?,?,?,?,?,?,?,?,?,?)", [(
        cluster, r.job_id, r.user, r.account, r.state, r.start, r.elapsed_s, r.cpus,
        r.gpus, now) for r in rows])


def _finite(x):
    """LevelFS can be inf (no usage). Kept as NULL + a flag: portable, no
    Infinity in JSON exports."""
    if x is None or x != x or x in (float("inf"), float("-inf")):
        return None
    return x


def _write_shares(conn, cluster, rows, now):
    _replace(conn, "share", cluster, [(
        cluster, r.account, r.user, r.raw_usage, r.effective_usage, _finite(r.level_fs),
        r.fairshare, 1 if r.level_fs == float("inf") else 0) for r in rows])


def _write_disk(conn, cluster, rows, now):
    _replace(conn, "disk", cluster, [(
        cluster, r.filesystem, r.scope, r.used_bytes, r.quota_bytes, r.files,
        r.files_quota, r.owner) for r in rows])


def _write_partitions(conn, cluster, rows, now):
    _replace(conn, "partition", cluster, [(
        cluster, r.partition, r.avail, r.limit_s, r.nodes, r.state, r.gres,
        int(bool(r.is_default))) for r in rows])


def _write_cells(conn, cluster, chunks, now):
    stored = cells_offsets(conn, cluster)
    for ch in chunks:
        prev = stored.get(ch.relpath)
        if prev is not None and ch.size < prev:
            # file shrank (truncated or rewritten): its old content no longer
            # exists, and new lines will reuse the same byte offsets.
            # Ruled acceptable: a shrunk log was replaced, so its history goes with it.
            conn.execute("DELETE FROM cell_event WHERE cluster = ? AND relpath = ?",
                         (cluster, ch.relpath))
            new_off = 0
        else:
            # advance to the remote <end>, which covers lines the remote filter
            # dropped; never back over lines already read
            new_off = ch.start_offset + ch.consumed
            if ch.end is not None:
                new_off = max(new_off, ch.end)
            conn.executemany(
                "INSERT OR IGNORE INTO cell_event VALUES (?,?,?,?,?,?,?,?,?)",
                [(cluster, ch.relpath, off, ch.campaign, e.ts, e.job_id, e.event, e.cell,
                  e.detail) for off, e in zip(ch.event_offsets, ch.events)])
        conn.execute("INSERT OR REPLACE INTO cell_file VALUES (?,?,?,?,?,?)",
                     (cluster, ch.relpath, ch.campaign, new_off, ch.size, now))


def _write_globs(conn, cluster, globs, now):
    conn.execute("DELETE FROM glob_count WHERE cluster = ?", (cluster,))
    conn.executemany("INSERT INTO glob_count VALUES (?,?,?,?)",
                     [(cluster, camp, int(n), now) for camp, n in globs])


def set_cluster_mode(conn, cluster: str, mode: str, last_active: float | None) -> None:
    _tx(conn, lambda c: c.execute(
        "INSERT INTO cluster (cluster, mode, last_active) VALUES (?,?,?) "
        "ON CONFLICT (cluster) DO UPDATE SET mode = excluded.mode, "
        "last_active = excluded.last_active", (cluster, mode, last_active)))


def get_meta(conn, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def set_meta(conn, key: str, value: str) -> None:
    _tx(conn, lambda c: c.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (key, value)))


def prune(conn, cfg: Config, now: float) -> None:
    keep = now - cfg.retention_days * 86400
    keep_usage = now - cfg.usage_retention_days * 86400
    keep_cells = now - cfg.cells_retention_days * 86400

    def run(c):
        c.execute('DELETE FROM finished WHERE coalesce("end", seen) < ?', (keep,))
        c.execute("DELETE FROM usage WHERE coalesce(start, seen) < ?", (keep_usage,))
        # Cells are pruned per FILE, never per event: a live log keeps its old
        # plan/start lines (its offset is past them, they would never be re-read).
        # The remote lists every log on each cells poll and deletes logs older
        # than cells_retention_days, so a file is gone once a later ok cells
        # poll of its cluster no longer saw it.
        gone = ("FROM cell_file f WHERE f.seen < ? AND f.seen < ("
                "SELECT max(p.finished) FROM poll_section p WHERE p.cluster = f.cluster "
                "AND p.section = 'cells' AND p.ok = 1)")
        c.execute(f"DELETE FROM cell_event WHERE (cluster, relpath) IN "
                  f"(SELECT f.cluster, f.relpath {gone})", (keep_cells,))
        c.execute(f"DELETE FROM cell_file WHERE (cluster, relpath) IN "
                  f"(SELECT f.cluster, f.relpath {gone})", (keep_cells,))
        c.execute("DELETE FROM glob_count WHERE seen < ?", (keep_cells,))
        # poll records last: the cells rule above reads poll_section
        c.execute("DELETE FROM poll WHERE started < ?", (keep,))
        c.execute("DELETE FROM poll_section WHERE started < ?", (keep,))
    _tx(conn, run)


# ---------------------------------------------------------------- reads

def queue(conn) -> list[QueueRow]:
    return [QueueRow(*r) for r in conn.execute(
        "SELECT * FROM queue ORDER BY cluster, submit, job_id")]


def finished(conn, since: float) -> list[FinishedJob]:
    """Jobs in a terminal state that ended at or after ``since``."""
    rows = conn.execute('SELECT * FROM finished WHERE coalesce("end", seen) >= ? '
                        'ORDER BY "end" DESC, cluster, job_id', (since,))
    return [FinishedJob(*r[:18]) for r in rows
            if ((r[5] or "").split() or [""])[0] not in _ACTIVE_STATES]


def usage(conn) -> list[UsageRow]:
    return [UsageRow(*r[:9]) for r in conn.execute(
        "SELECT * FROM usage ORDER BY cluster, start, job_id")]


def shares(conn) -> list[ShareRow]:
    out = []
    for r in conn.execute("SELECT * FROM share ORDER BY cluster, rowid"):
        level = float("inf") if r[7] else r[5]
        out.append(ShareRow(r[0], r[1], r[2], r[3], r[4], level, r[6]))
    return out


def disk(conn) -> list[DiskRow]:
    return [DiskRow(*r) for r in conn.execute("SELECT * FROM disk ORDER BY cluster, rowid")]


def partitions(conn) -> list[PartitionRow]:
    return [PartitionRow(*r[:7], bool(r[7])) for r in conn.execute(
        "SELECT * FROM partition ORDER BY cluster, rowid")]


def cells_offsets(conn, cluster: str) -> dict[str, int]:
    return dict(conn.execute("SELECT relpath, offset FROM cell_file WHERE cluster = ?",
                             (cluster,)))


def campaign_cells(conn, campaign: str) -> list[tuple[str, CellEvent]]:
    return [(r[0], CellEvent(r[1], r[2], r[3], r[4], r[5])) for r in conn.execute(
        "SELECT cluster, ts, job_id, event, cell, detail FROM cell_event WHERE campaign = ? "
        "ORDER BY ts, cluster, relpath, offset", (campaign,))]


def campaigns(conn, cfg: Config | None = None) -> list[CampaignState]:
    """Hook-based campaigns from cell events, plus (with ``cfg``) the configured
    glob campaigns from their stored counts."""
    out = []
    names = [r[0] for r in conn.execute(
        "SELECT DISTINCT campaign FROM cell_event ORDER BY campaign")]
    for name in names:
        st = aggregate(campaign_cells(conn, name))
        st.campaign = name
        out.append(st)
    if cfg is not None:
        for g in cfg.glob_campaigns:
            row = conn.execute("SELECT count, seen FROM glob_count WHERE cluster = ? "
                               "AND campaign = ?", (g.cluster, g.campaign)).fetchone()
            if row is None:
                continue
            st = glob_progress(row[0], g.total)
            st.campaign, st.clusters, st.last_event = g.campaign, {g.cluster}, row[1]
            out.append(st)
    return out


def last_ok(conn, cluster: str, section: str) -> float | None:
    """When ``section`` last arrived complete and was stored (poll finish time)."""
    return conn.execute("SELECT max(finished) FROM poll_section WHERE cluster = ? "
                        "AND section = ? AND ok = 1", (cluster, section)).fetchone()[0]


def accounting_since(conn, cluster: str) -> float | None:
    """Start time of the last stored accounting poll: jobs ending after it may
    be missing, so the next sacct window starts there."""
    return conn.execute("SELECT max(started) FROM poll_section WHERE cluster = ? "
                        "AND section = 'accounting' AND ok = 1", (cluster,)).fetchone()[0]


def cluster_status(conn) -> dict[str, ClusterStatus]:
    out: dict[str, ClusterStatus] = {}
    names = [r[0] for r in conn.execute(
        "SELECT cluster FROM cluster UNION SELECT DISTINCT cluster FROM poll ORDER BY 1")]
    for c in names:
        meta = conn.execute("SELECT mode, last_active, env FROM cluster WHERE cluster = ?",
                            (c,)).fetchone() or ("unknown", None, "{}")
        last = conn.execute("SELECT finished, ok, error FROM poll WHERE cluster = ? "
                            "ORDER BY finished DESC LIMIT 1", (c,)).fetchone()
        good = conn.execute("SELECT max(finished) FROM poll WHERE cluster = ? AND ok = 1",
                            (c,)).fetchone()[0]
        try:
            env = json.loads(meta[2])
        except ValueError:
            env = {}
        out[c] = ClusterStatus(
            c, meta[0], last[0] if last else None, good,
            None if last is None or last[1] else (last[2] or "poll failed"), meta[1], env)
    return out
