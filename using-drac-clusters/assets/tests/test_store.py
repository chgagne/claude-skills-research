import math
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ASSETS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ASSETS))

from dracmonlib import store  # noqa: E402
from dracmonlib.cells import CellChunk, CellEvent, parse_cells_section  # noqa: E402
from dracmonlib.config import Config, GlobCampaign  # noqa: E402
from dracmonlib.frame import Section  # noqa: E402
from dracmonlib.parse import (DiskRow, FinishedJob, PartitionRow, QueueRow,  # noqa: E402
                              ShareRow, UsageRow)
from dracmonlib.ssh import PollResult  # noqa: E402
from dracmonlib.store import ParsedPoll, PollLock  # noqa: E402

DAY = 86400.0


def qrow(job_id, cluster="alpha", state="RUNNING"):
    return QueueRow(cluster, job_id, None, None, "job", "cpu", state, 60, 3600, None,
                    4, 2 ** 30, 0.0, "node1", "acct-x", 1000.0, 1)


def fjob(job_id, end, state="COMPLETED", cluster="alpha"):
    return FinishedJob(cluster, job_id, "job", "acct-x", "cpu", state, "0:0", 100, 3600,
                       end - 200 if end else None, end - 100 if end else None, end,
                       "node1" if end else None, 4, 0.5, 2 ** 30, 2 ** 29, 300)


def disk(used, cluster="alpha"):
    return DiskRow(cluster, "/project", "group", used, 1000, 5, 100, "grp")


def result(cluster="alpha", ok=True, sections=("queue", "disk"), started=1000.0,
           error=None, complete=None):
    requested = ["env", *sections]
    complete = requested if complete is None else ["env", *complete]
    secs = {n: Section(n, 0, "", True) for n in complete} if ok else {}
    return PollResult(cluster, started, started + 5, ok, error, requested, secs,
                      {"tz": "-0500"} if ok else {})


def cells_chunk(body, offsets=None):
    return parse_cells_section(body, offsets or {})


class StoreCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.path = self.dir / "dracmon.sqlite"
        self.conn = store.open_store(self.path)

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def poll(self, res=None, **parsed):
        store.write_poll(self.conn, res or result(), ParsedPoll(**parsed))


class SchemaTests(StoreCase):
    def test_migration_from_empty(self):
        self.assertEqual(self.conn.execute("PRAGMA user_version").fetchone()[0],
                         store.SCHEMA_VERSION)
        self.assertEqual(self.conn.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        self.assertEqual(self.conn.execute("PRAGMA busy_timeout").fetchone()[0], 5000)
        self.assertEqual(self.conn.execute("PRAGMA synchronous").fetchone()[0], 1)  # NORMAL
        self.assertEqual(store.queue(self.conn), [])
        self.conn.close()
        self.conn = store.open_store(self.path)  # reopening is a no-op
        self.assertEqual(self.conn.execute("PRAGMA user_version").fetchone()[0],
                         store.SCHEMA_VERSION)

    def test_newer_schema_refused(self):
        self.conn.execute(f"PRAGMA user_version = {store.SCHEMA_VERSION + 1}")
        with self.assertRaises(RuntimeError):
            store.open_store(self.path)


class WriteTests(StoreCase):
    def test_partial_poll_keeps_good_sections(self):
        self.poll(queue=[qrow("1"), qrow("2")], disk=[disk(10)])
        res = result(started=2000.0, complete=("disk",))  # queue frame incomplete
        self.poll(res, queue=None, disk=[disk(20)])
        self.assertEqual([r.job_id for r in store.queue(self.conn)], ["1", "2"])
        self.assertEqual([d.used_bytes for d in store.disk(self.conn)], [20])
        self.assertEqual(store.last_ok(self.conn, "alpha", "queue"), 1005.0)
        self.assertEqual(store.last_ok(self.conn, "alpha", "disk"), 2005.0)
        row = self.conn.execute("SELECT ok, error FROM poll_section WHERE section='queue' "
                                "AND started=2000").fetchone()
        self.assertEqual(row[0], 0)
        self.assertTrue(row[1])

    def test_failed_poll_changes_no_data(self):
        self.poll(queue=[qrow("1")], disk=[disk(10)])
        res = result(ok=False, started=2000.0, error="timeout after 60s")
        # even if a caller passed parsed data, a failed poll must not store it
        self.poll(res, queue=[], disk=[])
        self.assertEqual([r.job_id for r in store.queue(self.conn)], ["1"])
        self.assertEqual([d.used_bytes for d in store.disk(self.conn)], [10])
        rows = self.conn.execute("SELECT section, ok, error FROM poll_section "
                                 "WHERE started=2000 ORDER BY section").fetchall()
        self.assertEqual(rows, [("disk", 0, "timeout after 60s"), ("env", 0, "timeout after 60s"),
                                ("queue", 0, "timeout after 60s")])
        st = store.cluster_status(self.conn)["alpha"]
        self.assertEqual((st.last_poll, st.last_ok, st.last_error),
                         (2005.0, 1005.0, "timeout after 60s"))
        self.assertEqual(st.env, {"tz": "-0500"})  # last good env kept

    def test_interrupted_write_leaves_previous_state(self):
        self.poll(queue=[qrow("1")], disk=[disk(10)])
        before = (store.queue(self.conn), store.disk(self.conn),
                  self.conn.execute("SELECT count(*) FROM poll").fetchone())
        boom = mock.patch.object(store, "_write_disk", side_effect=RuntimeError("boom"))
        with boom, self.assertRaises(RuntimeError):
            self.poll(result(started=2000.0), queue=[qrow("9")], disk=[disk(99)])
        reader = store.open_store(self.path)
        try:
            for c in (self.conn, reader):
                after = (store.queue(c), store.disk(c),
                         c.execute("SELECT count(*) FROM poll").fetchone())
                self.assertEqual(after, before)
        finally:
            reader.close()
        self.poll(result(started=3000.0), queue=[qrow("9")])  # connection still usable
        self.assertEqual([r.job_id for r in store.queue(self.conn)], ["9"])

    def test_failed_begin_error_not_masked(self):
        other = store.open_store(self.path)
        try:
            other.execute("BEGIN IMMEDIATE")
            self.conn.execute("PRAGMA busy_timeout = 0")
            with self.assertRaises(sqlite3.OperationalError) as cm:
                self.poll(queue=[qrow("1")])
            self.assertIn("locked", str(cm.exception))
        finally:
            other.execute("ROLLBACK")
            other.close()

    def test_error_after_failed_statement_not_masked(self):
        # SQLite can roll a transaction back by itself (disk full, I/O error):
        # the cleanup ROLLBACK must not replace the original exception
        def boom(conn, *a):
            conn.execute("ROLLBACK")
            raise ValueError("disk full")
        with mock.patch.object(store, "_write_disk", side_effect=boom):
            with self.assertRaises(ValueError):
                self.poll(queue=[qrow("1")], disk=[disk(1)])
        self.assertFalse(self.conn.in_transaction)
        with mock.patch.object(store, "_MIGRATIONS", [["ROLLBACK", "SELECT nope"]]), \
                mock.patch.object(store, "SCHEMA_VERSION", 1):
            self.conn.execute("PRAGMA user_version = 0")
            with self.assertRaises(sqlite3.OperationalError) as cm:
                store._migrate(self.conn)
            self.assertIn("nope", str(cm.exception))

    def test_reader_during_write(self):
        self.poll(queue=[qrow("1")])
        # EXCLUSIVE: without WAL this would lock readers out until commit
        self.conn.execute("BEGIN EXCLUSIVE")
        self.conn.execute("DELETE FROM queue")
        reader = store.open_store(self.path)
        try:
            self.assertEqual([r.job_id for r in store.queue(reader)], ["1"])
        finally:
            reader.close()
            self.conn.execute("ROLLBACK")

    def test_roundtrip_all_row_types(self):
        q = qrow("5")
        f = fjob("6", 5000.0)
        sh = ShareRow("alpha", "acct-x", "someone", 10, 0.1, math.inf, None)
        u = UsageRow("alpha", "7", "someone", "acct-x", "COMPLETED", 4000.0, 60, 2, 0.25)
        d = disk(1)
        p = PartitionRow("alpha", "gpu", "up", 3600, 4, "idle", "gpu:h100:4", True)
        res = result(sections=("queue", "accounting", "fairshare", "usage", "disk",
                               "partitions"))
        self.poll(res, queue=[q], accounting=[f], shares=[sh], usage=[u], disk=[d],
                  partitions=[p])
        self.assertEqual(store.queue(self.conn), [q])
        self.assertEqual(store.finished(self.conn, 0), [f])
        self.assertEqual(store.shares(self.conn), [sh])
        self.assertEqual(store.usage(self.conn), [u])
        self.assertEqual(store.disk(self.conn), [d])
        self.assertEqual(store.partitions(self.conn), [p])
        self.assertIs(store.partitions(self.conn)[0].is_default, True)
        self.assertEqual(store.shares(self.conn)[0].level_fs, math.inf)

    def test_upserts_and_finished_filter(self):
        res = result(sections=("accounting", "usage"))
        u1 = UsageRow("alpha", "7", "someone", "acct-x", "RUNNING", 4000.0, 60, 2, 0.0)
        self.poll(res, accounting=[fjob("1", None, "PENDING"), fjob("2", None, "RUNNING"),
                                   fjob("3", 5000.0)], usage=[u1])
        self.assertEqual([j.job_id for j in store.finished(self.conn, 0)], ["3"])
        u2 = UsageRow("alpha", "7", "someone", "acct-x", "COMPLETED", 4000.0, 600, 2, 0.0)
        self.poll(result(sections=("accounting", "usage"), started=2000.0),
                  accounting=[fjob("2", 6000.0, "FAILED")], usage=[u2])
        self.assertEqual([(j.job_id, j.state) for j in store.finished(self.conn, 0)],
                         [("2", "FAILED"), ("3", "COMPLETED")])
        self.assertEqual([j.job_id for j in store.finished(self.conn, 5500.0)], ["2"])
        self.assertEqual(store.usage(self.conn), [u2])
        self.assertEqual(store.accounting_since(self.conn, "alpha"), 2000.0)
        self.assertIsNone(store.accounting_since(self.conn, "beta"))

    def test_finished_only_terminal_states(self):
        live = ["PENDING", "RUNNING", "REQUEUED", "SUSPENDED", "CONFIGURING", "COMPLETING",
                "RESIZING", "REQUEUE_HOLD", "REQUEUE_FED"]
        done = ["COMPLETED", "FAILED", "CANCELLED by 0", "TIMEOUT", "OUT_OF_MEMORY"]
        jobs = [fjob(f"l{i}", 5000.0, st) for i, st in enumerate(live)]
        jobs += [fjob(f"d{i}", 5000.0, st) for i, st in enumerate(done)]
        self.poll(result(sections=("accounting",)), accounting=jobs)
        self.assertEqual(sorted(j.state for j in store.finished(self.conn, 0)), sorted(done))

    def test_duplicate_queue_row_does_not_abort_poll(self):
        self.poll(queue=[qrow("1"), qrow("1", state="PENDING"), qrow("2")], disk=[disk(5)])
        self.assertEqual([(r.job_id, r.state) for r in store.queue(self.conn)],
                         [("1", "PENDING"), ("2", "RUNNING")])
        self.assertEqual([d.used_bytes for d in store.disk(self.conn)], [5])

    def test_clusters_are_independent(self):
        self.poll(queue=[qrow("1")])
        self.poll(result(cluster="beta"), queue=[qrow("2", cluster="beta")])
        self.poll(result(started=2000.0), queue=[])
        self.assertEqual([(r.cluster, r.job_id) for r in store.queue(self.conn)], [("beta", "2")])


class CellTests(StoreCase):
    BODY = "#file 40 40 camp/7.log\n10\t7\tplan\t\t3\n11\t7\tstart\tA\t\n15\t7\tdone\tA\t\n"

    def cells(self, chunks, started=1000.0):
        self.poll(result(sections=("cells",), started=started), cells=chunks)

    def test_cell_offsets_advance_and_dedupe(self):
        chunks = cells_chunk(self.BODY)
        self.cells(chunks)
        self.cells(chunks, started=2000.0)  # same chunk again (e.g. offsets not yet read)
        self.assertEqual(len(store.campaign_cells(self.conn, "camp")), 3)
        consumed = chunks[0].consumed
        self.assertEqual(store.cells_offsets(self.conn, "alpha"), {"camp/7.log": consumed})
        more = cells_chunk("#file 54 54 camp/7.log\n20\t7\tstart\tB\t\n",
                           store.cells_offsets(self.conn, "alpha"))
        self.cells(more, started=3000.0)
        cells = store.campaign_cells(self.conn, "camp")
        self.assertEqual([e.event for _, e in cells], ["plan", "start", "done", "start"])
        self.assertEqual(store.cells_offsets(self.conn, "alpha")["camp/7.log"],
                         consumed + more[0].consumed)
        (st,) = store.campaigns(self.conn)
        self.assertEqual((st.campaign, st.plan, st.done, st.running), ("camp", 3, {"A"}, {"B"}))

    def test_reset_chunk_restarts_file(self):
        self.cells(cells_chunk(self.BODY))
        reset = cells_chunk("#file 5 5 camp/7.log\n", store.cells_offsets(self.conn, "alpha"))
        self.assertEqual(reset[0].start_offset, 0)
        self.cells(reset, started=2000.0)
        self.assertEqual(store.cells_offsets(self.conn, "alpha"), {"camp/7.log": 0})
        fresh = cells_chunk("#file 14 14 camp/7.log\n40\t8\tstart\tC\t\n", {"camp/7.log": 0})
        self.cells(fresh, started=3000.0)
        self.assertEqual([e.cell for _, e in store.campaign_cells(self.conn, "camp")], ["C"])

    def test_offset_advances_to_end_past_filtered_lines(self):
        # remotely filtered lines (not starting with a digit) are inside <end>:
        # the next poll must start after them, not re-read and drift
        chunk = cells_chunk("#file 60 60 camp/7.log\n10\t7\tstart\tA\t\n")
        self.assertEqual(chunk[0].consumed, 14)
        self.cells(chunk)
        self.assertEqual(store.cells_offsets(self.conn, "alpha"), {"camp/7.log": 60})
        torn = cells_chunk("#file 70 60 camp/7.log\n", store.cells_offsets(self.conn, "alpha"))
        self.cells(torn, started=2000.0)  # torn tail only: offset stays at <end>
        self.assertEqual(store.cells_offsets(self.conn, "alpha"), {"camp/7.log": 60})

    def test_chunk_without_offsets_rejected(self):
        bad = CellChunk("camp/1.log", "camp", 10, 0, [CellEvent(1.0, "1", "start", "A", "")], 10)
        with self.assertRaises(ValueError):
            self.cells([bad])

    def test_glob_campaigns(self):
        self.poll(result(sections=("globs",)), globs=[("sweep", 7)])
        cfg = Config(glob_campaigns=[GlobCampaign("sweep", "alpha", "out/*.done", 20)])
        self.assertEqual(store.campaigns(self.conn), [])
        (st,) = store.campaigns(self.conn, cfg)
        self.assertEqual((st.campaign, st.plan, len(st.done), st.clusters),
                         ("sweep", 20, 7, {"alpha"}))


class StatusMetaTests(StoreCase):
    def test_cluster_status_and_mode(self):
        self.poll()
        store.set_cluster_mode(self.conn, "alpha", "active", 1234.0)
        store.set_cluster_mode(self.conn, "beta", "released", None)
        st = store.cluster_status(self.conn)
        a = st["alpha"]
        self.assertEqual((a.cluster, a.mode, a.last_poll, a.last_ok, a.last_error, a.last_active),
                         ("alpha", "active", 1005.0, 1005.0, None, 1234.0))
        self.assertEqual(a.env, {"tz": "-0500"})
        b = st["beta"]
        self.assertEqual((b.mode, b.last_poll, b.last_ok, b.env), ("released", None, None, {}))

    def test_meta(self):
        self.assertIsNone(store.get_meta(self.conn, "usage_frontier"))
        store.set_meta(self.conn, "usage_frontier", "2026-10-01")
        store.set_meta(self.conn, "usage_frontier", "2026-09-01")
        self.assertEqual(store.get_meta(self.conn, "usage_frontier"), "2026-09-01")


class PruneTests(StoreCase):
    def test_prune_retention(self):
        now = 1000 * DAY
        res = result(sections=("accounting", "usage", "cells"), started=now - 91 * DAY)
        old_cells = cells_chunk(f"#file 999 999 camp/live.log\n{now - 60 * DAY}\t1\tplan\t\t2\n"
                                f"{now - 59 * DAY}\t1\tstart\tA\t\n"
                                f"#file 999 999 camp/gone.log\n{now - 58 * DAY}\t2\tstart\tB\t\n")
        self.poll(res, accounting=[fjob("old", now - 91 * DAY), fjob("new", now - 89 * DAY)],
                  usage=[UsageRow("alpha", "u1", "x", "a", "COMPLETED", now - 366 * DAY, 1, 1, 0),
                         UsageRow("alpha", "u2", "x", "a", "COMPLETED", now - 364 * DAY, 1, 1, 0)],
                  cells=old_cells)
        # a recent cells poll lists live.log only: gone.log was removed remotely
        offs = store.cells_offsets(self.conn, "alpha")
        live = cells_chunk(f"#file 2000 2000 camp/live.log\n{now - DAY}\t1\tdone\tA\t\n", offs)
        self.poll(result(sections=("cells",), started=now - DAY), cells=live)
        store.prune(self.conn, Config(), now)
        self.assertEqual([j.job_id for j in store.finished(self.conn, 0)], ["new"])
        self.assertEqual([u.job_id for u in store.usage(self.conn)], ["u2"])
        # the live file keeps its 60-day-old plan/start lines
        self.assertEqual([(e.event, e.cell) for _, e in store.campaign_cells(self.conn, "camp")],
                         [("plan", ""), ("start", "A"), ("done", "A")])
        self.assertEqual(set(store.cells_offsets(self.conn, "alpha")), {"camp/live.log"})
        (st,) = store.campaigns(self.conn)
        self.assertEqual((st.plan, st.done), (2, {"A"}))
        self.assertEqual(self.conn.execute("SELECT count(*) FROM poll").fetchone()[0], 1)
        self.assertEqual(self.conn.execute("SELECT min(started) FROM poll_section").fetchone()[0],
                         now - DAY)

    def test_prune_keeps_cells_of_unpolled_cluster(self):
        now = 1000 * DAY
        chunk = cells_chunk(f"#file 99 99 camp/1.log\n{now - 60 * DAY}\t1\tstart\tA\t\n")
        self.poll(result(sections=("cells",), started=now - 60 * DAY), cells=chunk)
        store.prune(self.conn, Config(), now)  # no later cells poll: nothing proves removal
        self.assertEqual(len(store.campaign_cells(self.conn, "camp")), 1)


class RecoverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.path = self.dir / "dracmon.sqlite"

    def tearDown(self):
        self.tmp.cleanup()

    def test_corrupt_file_recovered(self):
        junk = bytes(range(256)) * 64
        self.path.write_bytes(junk)
        Path(str(self.path) + "-wal").write_bytes(b"x" * 100)
        moved = store.check_and_recover(self.path)
        self.assertIsNotNone(moved)
        self.assertTrue(moved.name.startswith("dracmon.sqlite.corrupt-"))
        self.assertEqual(moved.read_bytes(), junk)
        self.assertTrue(Path(str(moved) + "-wal").exists())
        self.assertFalse(self.path.exists())
        conn = store.open_store(self.path)
        try:
            self.assertEqual(store.queue(conn), [])
        finally:
            conn.close()

    def test_stale_check_wal_replaced(self):
        stale = self.dir / "dracmon.sqlite.check-wal"
        stale.write_bytes(b"stale copy from a crashed check")
        self.path.write_bytes(b"not a database" * 100)
        Path(str(self.path) + "-wal").write_bytes(b"current wal")
        moved = store.check_and_recover(self.path)
        self.assertEqual(Path(str(moved) + "-wal").read_bytes(), b"current wal")
        self.assertFalse(stale.exists())

    def test_stale_check_wal_not_passed_off_as_wal(self):
        stale = self.dir / "dracmon.sqlite.check-wal"
        stale.write_bytes(b"stale copy from a crashed check")
        self.path.write_bytes(b"not a database" * 100)  # and no -wal at all
        moved = store.check_and_recover(self.path)
        self.assertFalse(Path(str(moved) + "-wal").exists())
        self.assertFalse(stale.exists())

    def test_stale_check_wal_removed_when_healthy(self):
        store.open_store(self.path).close()
        stale = self.dir / "dracmon.sqlite.check-wal"
        stale.write_bytes(b"stale")
        self.assertIsNone(store.check_and_recover(self.path))
        self.assertFalse(stale.exists())

    def test_healthy_or_missing_untouched(self):
        self.assertIsNone(store.check_and_recover(self.path))
        store.open_store(self.path).close()
        self.assertIsNone(store.check_and_recover(self.path))
        self.assertTrue(self.path.exists())

    def test_two_recoveries_same_second_do_not_collide(self):
        self.path.write_bytes(b"not a database at all" * 100)
        a = store.check_and_recover(self.path)
        self.path.write_bytes(b"still not a database" * 100)
        b = store.check_and_recover(self.path)
        self.assertNotEqual(a, b)
        self.assertTrue(a.exists() and b.exists())


class LockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def other_process_acquires(self):
        code = ("import sys; sys.path.insert(0, sys.argv[1]);"
                "from pathlib import Path; from dracmonlib.store import PollLock;"
                "print(PollLock(Path(sys.argv[2])).try_acquire())")
        out = subprocess.run([sys.executable, "-c", code, str(ASSETS), str(self.dir)],
                             capture_output=True, text=True, timeout=30, check=True)
        return out.stdout.strip() == "True"

    def test_two_pollers_one_lock(self):
        lock = PollLock(self.dir)
        self.assertTrue(lock.try_acquire())
        self.assertEqual((self.dir / "dracmon.lock").read_text().strip(),
                         str(__import__("os").getpid()))
        self.assertFalse(self.other_process_acquires())
        lock.release()
        self.assertTrue(self.other_process_acquires())

    def test_same_process_two_locks(self):
        a, b = PollLock(self.dir), PollLock(self.dir)
        self.assertTrue(a.try_acquire())
        self.assertFalse(b.try_acquire())
        a.release()
        self.assertTrue(b.try_acquire())
        b.release()

    def test_context_manager(self):
        with PollLock(self.dir) as lock:
            self.assertTrue(lock.held)
            with self.assertRaises(store.LockBusy):
                with PollLock(self.dir):
                    pass
        self.assertFalse(lock.held)
        self.assertTrue(PollLock(self.dir).try_acquire())


if __name__ == "__main__":
    unittest.main()
