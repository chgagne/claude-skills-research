"""TUI view tests (Textual): Jobs, Cells, Usage, Storage tabs and the compact
view. Skipped when Textual is not installed.

Run: uv run --with textual==8.2.8 python -m unittest tests.test_tui_views -v

The store is seeded from the six fixtures with ``now = ANCHOR`` (just after the
fixtures were captured) and the app clock is pinned to it, so time windows give
the same jobs whatever the day the tests run. No ssh is ever run.
"""
import dataclasses
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

try:
    import textual  # noqa: F401
    HAVE_TEXTUAL = True
except ImportError:
    HAVE_TEXTUAL = False

from dracmonlib import store  # noqa: E402
from dracmonlib.config import GlobCampaign  # noqa: E402
from dracmonlib.parse import QueueRow, UsageRow  # noqa: E402
from seed import seed_store  # noqa: E402

ANCHOR = 1794975200.0  # a little after the fixtures' env "now"
SIZE = (120, 40)
H = 3600


def add_cells(db, campaign, cluster, events, relpath=None):
    """Insert cell events (ts, job, event, cell, detail) as a cells poll would."""
    conn = store.open_store(db)
    rel = relpath or f"{campaign}/{cluster}.log"
    try:
        conn.execute("BEGIN")
        start = conn.execute("SELECT count(*) FROM cell_event WHERE cluster = ? AND relpath = ?",
                             (cluster, rel)).fetchone()[0]
        for i, (ts, job, ev, cell, detail) in enumerate(events, start):
            conn.execute("INSERT INTO cell_event VALUES (?,?,?,?,?,?,?,?,?)",
                         (cluster, rel, i * 100, campaign, ts, job, ev, cell, detail))
        conn.execute("COMMIT")
    finally:
        conn.close()


def campaign_events(n_done, n_running, n_failed, plan=None, t0=ANCHOR - 10 * H,
                    job="900", prefix="c"):
    ev = []
    if plan is not None:
        ev.append((t0, job, "plan", "-", str(plan)))
    t = t0
    for i in range(n_done):
        ev.append((t + 1, job, "start", f"{prefix}{i}", ""))
        ev.append((t + 1 + 600, job, "done", f"{prefix}{i}", ""))
        t += 700
    for i in range(n_running):
        ev.append((t + 1, job, "start", f"{prefix}r{i}", ""))
        t += 10
    for i in range(n_failed):
        ev.append((t + 1, job, "start", f"{prefix}f{i}", ""))
        ev.append((t + 5, job, "fail", f"{prefix}f{i}", "exit 1: CUDA out of memory"))
        t += 10
    return ev


class PureModelTests(unittest.TestCase):
    """Models behind the views (need no Textual, but live in the tui package)."""

    def setUp(self):
        if not HAVE_TEXTUAL:
            self.skipTest("textual is not installed")
        self.tmp = Path(tempfile.mkdtemp(prefix="dracmon-views-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.db = self.tmp / "dracmon.sqlite"
        self.cfg = seed_store(self.db, ANCHOR)

    def test_jobs_summary_tiles(self):
        from dracmonlib.tui import jobs
        conn = store.open_store(self.db)
        try:
            data = jobs.load_jobs(conn, self.cfg, ANCHOR)
        finally:
            conn.close()
        t = jobs.summarize(data.finished, data.queue, ANCHOR, 7 * 86400)
        self.assertEqual(t.jobs, 12)
        self.assertEqual((t.failed, t.timeout, t.oom), (3, 0, 0))
        self.assertAlmostEqual(t.gpu_hours, 628.3178, places=3)  # 8 x tamia + 4 x killarney GPUs
        self.assertAlmostEqual(t.cpu_hours, 5011.2222, places=3)
        self.assertEqual(t.median_wait, 16200)
        self.assertEqual((t.running, t.pending), (0, 12))
        day = jobs.summarize(data.finished, data.queue, ANCHOR, 86400)
        self.assertLess(day.jobs, 12)
        self.assertEqual(day.jobs, sum(1 for f in data.finished if f.end >= ANCHOR - 86400))

    def test_fractional_gpus_count_fractionally(self):
        from dracmonlib.parse import FinishedJob
        from dracmonlib.tui import jobs
        f = FinishedJob("c", "1", "n", "a", "p", "COMPLETED", "0:0", 7200, 9000,
                        ANCHOR - 9000, ANCHOR - 8000, ANCHOR - 800, "n1", 4, 3 / 7,
                        None, None, None)
        t = jobs.summarize([f], [], ANCHOR, 86400)
        self.assertAlmostEqual(t.gpu_hours, 2 * 3 / 7)

    def test_pending_array_shows_task_count(self):
        from dracmonlib.tui import jobs
        q = QueueRow("narval", "123_[0-99%10]", "123", "0-99%10", "sweep", "gpu", "PENDING",
                     0, 3600, None, 4, 8 * 2**30, 0.0, "(Priority)", "acct", ANCHOR - 60, 100)
        cells = jobs.queue_cells(q, ANCHOR)
        self.assertIn("×100", str(cells["id"]))
        self.assertEqual(str(cells["gpu"]), "0")  # known: no GPU
        unknown = jobs.queue_cells(dataclasses.replace(q, gpus=None), ANCHOR)
        self.assertEqual(str(unknown["gpu"]), "–")  # N/A in squeue
        t = jobs.summarize([], [q], ANCHOR, 86400)
        self.assertEqual(t.pending, 100)

    def test_usage_windows_split_user_and_group(self):
        from dracmonlib.tui import usage
        rows = [
            UsageRow("narval", "1", "me", "acct", "COMPLETED", ANCHOR - 2 * H, H, 4, 1.0),
            UsageRow("narval", "2", "other", "acct", "COMPLETED", ANCHOR - 3 * H, 2 * H, 2, 0.0),
            # started 2 d ago, ran 2 h: in the 7 d window only
            UsageRow("narval", "3", "me", "acct", "COMPLETED", ANCHOR - 2 * 86400, 2 * H, 1, 0.5),
            # straddles the 1 d edge: only the last hour counts in 1 d
            UsageRow("narval", "4", "me", "acct", "RUNNING", ANCHOR - 86400 - H, 2 * H, 10, 0.0),
            UsageRow("narval", "5", "me", "acct", "PENDING", None, 0, 0, 0.0),
        ]
        u = usage.windows(rows, "me", ANCHOR)
        self.assertAlmostEqual(u["me"]["cpu"][86400], 4 + 10)
        self.assertAlmostEqual(u["group"]["cpu"][86400], 4 + 4 + 10)
        self.assertAlmostEqual(u["me"]["cpu"][7 * 86400], 4 + 2 + 20)
        self.assertAlmostEqual(u["me"]["gpu"][86400], 1.0)
        self.assertAlmostEqual(u["me"]["gpu"][7 * 86400], 2.0)
        self.assertEqual(usage.WINDOWS, ((86400, "1 d"), (7 * 86400, "7 d"), (28 * 86400, "28 d")))

    def test_usage_partial_from_backfill_frontier(self):
        from dracmonlib.tui import usage
        self.assertEqual(usage.partial(None, ANCHOR), {86400: True, 7 * 86400: True,
                                                       28 * 86400: True})
        p = usage.partial(ANCHOR - 10 * 86400, ANCHOR)
        self.assertEqual(p, {86400: False, 7 * 86400: False, 28 * 86400: True})
        self.assertFalse(usage.partial(ANCHOR - 29 * 86400, ANCHOR)[28 * 86400])

    def test_cells_rollup_row(self):
        from dracmonlib.tui import cellsview
        add_cells(self.db, "expA", "narval", campaign_events(20, 1, 1, plan=48))
        add_cells(self.db, "expA", "rorqual", campaign_events(11, 1, 0, job="901", prefix="d"))
        self.cfg.glob_campaigns = [GlobCampaign("expG", "narval", "out/*", 10),
                                   GlobCampaign("expG", "rorqual", "out/*", 20)]
        conn = store.open_store(self.db)
        try:
            conn.execute("INSERT INTO glob_count VALUES ('narval', 'expG', 5, ?)", (ANCHOR - 60,))
            conn.execute("INSERT INTO glob_count VALUES ('rorqual', 'expG', 7, ?)", (ANCHOR - 60,))
            rows = cellsview.load_cells(conn, self.cfg, ANCHOR)
        finally:
            conn.close()
        by = {r.campaign: r for r in rows}
        self.assertEqual(set(by), {"expA", "expG"})
        a = by["expA"]
        self.assertEqual((a.done, a.running, a.failed, a.total), (31, 2, 1, 48))
        self.assertEqual(a.clusters, ["narval", "rorqual"])
        self.assertIsNotNone(a.eta)
        self.assertIn("CUDA out of memory", a.last_failure)
        self.assertTrue(a.open)
        g = by["expG"]
        self.assertEqual((g.done, g.total), (12, 30))
        self.assertEqual(g.clusters, ["narval", "rorqual"])
        cells = cellsview.row_cells(a, ANCHOR)
        self.assertEqual(str(cells["progress"]).count("▓"), 5)  # 31/48 of 8
        self.assertIn("31/2/1/48", str(cells["counts"]))

    def test_compact_lines(self):
        from dracmonlib.tui import compact
        add_cells(self.db, "expA", "narval", campaign_events(31, 1, 1, plan=48))
        conn = store.open_store(self.db)
        try:
            snap = compact.load_compact(conn, self.cfg, ANCHOR)
        finally:
            conn.close()
        lines = [str(t) for t in compact.compact_lines(snap, 120)]
        self.assertIn("narval ● 0R 0P", lines[0])
        self.assertIn("tamia ● 0R 8P", lines[0])
        self.assertIn("killarney ○ down", lines[0])
        self.assertIn("vulcan ○ released", lines[0])
        self.assertTrue(any(ln.startswith("expA") and "31/48" in ln and "1 failed" in ln
                            for ln in lines), lines)
        self.assertIn("tamia /project files 96 %", lines[-1])
        self.assertRegex(lines[-1], r"updated \d\d:\d\d$")
        self.assertEqual(len(lines[-1]), 120)  # right-aligned
        for width in (40, 20, 5):
            for ln in compact.compact_lines(snap, width):
                self.assertLessEqual(len(str(ln)), width)


class FakeProc:
    """A Popen stand-in whose first wait() times out."""

    def __init__(self, *a, **k):
        self.pid = 4242
        self.waits = 0
        self.killed = False

    def wait(self, timeout=None):
        import subprocess
        self.waits += 1
        if self.waits == 1:
            raise subprocess.TimeoutExpired("ssh", timeout)
        return -9

    def kill(self):
        self.killed = True


@unittest.skipUnless(HAVE_TEXTUAL, "textual is not installed")
class AskpassTimeoutTests(unittest.TestCase):
    def _run(self, killpg):
        from dracmonlib.tui import connect
        procs = []

        def popen(*a, **k):
            procs.append(FakeProc())
            return procs[-1]

        with mock.patch.object(connect.subprocess, "Popen", side_effect=popen), \
                mock.patch.object(connect.os, "killpg", side_effect=killpg) as kp, \
                mock.patch.object(connect.ssh, "register"), \
                mock.patch.object(connect.ssh, "unregister", return_value=False):
            rc, err = connect.open_master("somehost", True)
        return rc, err, kp, procs[0]

    def test_timeout_kills_the_process_group(self):
        import signal
        rc, err, kp, proc = self._run(None)
        kp.assert_called_once_with(4242, signal.SIGKILL)
        self.assertFalse(proc.killed)  # the group, not just the leader
        self.assertEqual(rc, 124)
        self.assertIn("no answer within", err)

    def test_group_already_gone_is_fine(self):
        rc, _, kp, _ = self._run(ProcessLookupError)
        self.assertEqual(kp.call_count, 1)
        self.assertEqual(rc, 124)


@unittest.skipUnless(HAVE_TEXTUAL, "textual is not installed")
class TuiViewsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from dracmonlib.tui import app as tui_app
        self.tui_app = tui_app
        self.tmp = Path(tempfile.mkdtemp(prefix="dracmon-views-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.db = self.tmp / "dracmon.sqlite"
        self.cfg = seed_store(self.db, ANCHOR)
        self.cycles = []
        patches = [
            mock.patch("dracmonlib.ssh.socket_live", return_value=True),
            mock.patch("dracmonlib.ssh.askpass_available", return_value=True),
            mock.patch("dracmonlib.tui.connect.open_master", return_value=(0, "")),
            mock.patch("dracmonlib.collector.run_cycle", side_effect=self._run_cycle),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _run_cycle(self, cfg, conn, now, force=frozenset(), stop=None):
        self.cycles.append(set(force))
        return []

    def make_app(self):
        class PinnedApp(self.tui_app.DracmonApp):
            clock = staticmethod(lambda: ANCHOR)
        return PinnedApp(self.cfg, self.db)

    async def settle(self, app, pilot):
        for _ in range(3):
            await app.workers.wait_for_complete()
            await pilot.pause()

    # ------------------------------------------------------------ jobs

    async def test_jobs_tab_tiles_and_window(self):
        from textual.widgets import DataTable
        app = self.make_app()
        async with app.run_test(size=SIZE) as pilot:
            await self.settle(app, pilot)
            queue = app.query_one("#queue-table", DataTable)
            self.assertEqual(queue.row_count, 12)
            fin = app.query_one("#finished-table", DataTable)
            day = fin.row_count
            self.assertIn("1 d", str(app.query_one("#finished-title").render()))
            await pilot.press("w")
            await pilot.pause()
            self.assertIn("7 d", str(app.query_one("#finished-title").render()))
            self.assertEqual(fin.row_count, 12)
            self.assertGreater(12, day)
            self.assertIn("628.3", str(app.query_one("#tile-gpu").render()))
            self.assertIn("3 / 0 / 0", str(app.query_one("#tile-failed").render()))
            await pilot.press("w")
            await pilot.pause()
            self.assertIn("30 d", str(app.query_one("#finished-title").render()))
            await pilot.press("w")
            await pilot.pause()
            self.assertIn("1 d", str(app.query_one("#finished-title").render()))

    async def test_filter_narrows_rows(self):
        from textual.widgets import DataTable
        app = self.make_app()
        async with app.run_test(size=SIZE) as pilot:
            await self.settle(app, pilot)
            await pilot.press("w")  # 7 d: tamia and killarney both have finished jobs
            queue = app.query_one("#queue-table", DataTable)
            fin = app.query_one("#finished-table", DataTable)
            self.assertEqual((queue.row_count, fin.row_count), (12, 12))
            await pilot.press("slash")
            await pilot.pause()
            await pilot.press(*"tamia")
            await pilot.pause()
            self.assertEqual(queue.row_count, 8)
            self.assertEqual(fin.row_count, 9)
            await pilot.press("escape")  # clears the filter
            await pilot.pause()
            self.assertEqual((queue.row_count, fin.row_count), (12, 12))
            await pilot.press("slash")
            await pilot.press(*"FAILED")
            await pilot.pause()
            self.assertEqual((queue.row_count, fin.row_count), (0, 3))

    async def test_slash_from_another_tab_opens_jobs_filter(self):
        from textual.widgets import Input, TabbedContent
        app = self.make_app()
        async with app.run_test(size=SIZE) as pilot:
            await self.settle(app, pilot)
            await pilot.press("4")
            await pilot.press("slash")
            await pilot.pause()
            self.assertEqual(app.query_one(TabbedContent).active, "jobs")
            self.assertIsInstance(app.focused, Input)

    # ------------------------------------------------------------ cells

    async def test_cells_tab_and_campaign_screen(self):
        from textual.widgets import DataTable
        from dracmonlib.tui.cellsview import CampaignScreen
        add_cells(self.db, "expA", "narval", campaign_events(20, 1, 1, plan=48))
        add_cells(self.db, "expA", "rorqual", campaign_events(11, 1, 0, job="901", prefix="d"))
        app = self.make_app()
        async with app.run_test(size=SIZE) as pilot:
            await self.settle(app, pilot)
            await pilot.press("2")
            await self.settle(app, pilot)
            table = app.query_one("#cells-table", DataTable)
            self.assertEqual(table.row_count, 1)
            row = " ".join(str(c) for c in table.get_row("expA"))
            self.assertIn("31/2/1/48", row)
            self.assertIn("narval rorqual", row)
            table.focus()
            await pilot.press("enter")
            await self.settle(app, pilot)
            self.assertIsInstance(app.screen, CampaignScreen)
            cells = app.screen.query_one(DataTable)
            self.assertEqual(cells.row_count, 34)  # 31 done + 2 running + 1 failed
            failed = " ".join(str(c) for c in cells.get_row("narval/cf0"))
            self.assertIn("failed", failed)
            self.assertIn("900", failed)
            app.reload()  # the periodic reload runs while the cell list is open
            await self.settle(app, pilot)
            self.assertIsInstance(app.screen, CampaignScreen)
            await pilot.press("escape")
            await pilot.pause()
            self.assertNotIsInstance(app.screen, CampaignScreen)

    # ------------------------------------------------------------ usage, storage

    async def test_usage_tab_shows_windows_and_fairshare(self):
        app = self.make_app()
        conn = store.open_store(self.db)
        store.set_meta(conn, "usage_backfill:rorqual", repr(ANCHOR - 10 * 86400))
        conn.close()
        async with app.run_test(size=SIZE) as pilot:
            await self.settle(app, pilot)
            await pilot.press("3")
            await self.settle(app, pilot)
            text = str(app.query_one("#usage-rorqual").render())
            self.assertIn("28 d", text)
            self.assertNotIn("30 d", text)
            self.assertIn("partial", text)  # 28 d not yet backfilled
            self.assertIn("LevelFS", text)
            self.assertIn("0.159", text)  # user0 fairshare on the gpu account
            self.assertIn("∞", str(app.query_one("#usage-nibi").render()))

    async def test_storage_levels(self):
        app = self.make_app()
        async with app.run_test(size=SIZE) as pilot:
            await self.settle(app, pilot)
            await pilot.press("4")
            await self.settle(app, pilot)
            sec = app.query_one("#storage-tamia")
            text = str(sec.render())
            self.assertIn("/project", text)
            self.assertIn("96 %", text)
            self.assertIn("88 %", text)
            self.assertIn("crit", sec.render_levels)  # files 96 %
            self.assertIn("warn", sec.render_levels)  # space 88 %

    async def test_stale_dimmed(self):
        conn = store.open_store(self.db)
        conn.execute("UPDATE poll_section SET finished = finished - 3 * 3600, "
                     "started = started - 3 * 3600 WHERE cluster = 'nibi' AND section = 'disk'")
        conn.close()
        app = self.make_app()
        async with app.run_test(size=SIZE) as pilot:
            await self.settle(app, pilot)
            await pilot.press("4")
            await self.settle(app, pilot)
            nibi = app.query_one("#storage-nibi")
            self.assertTrue(nibi.has_class("stale"))
            self.assertIn("3 h old", str(nibi.render()))
            self.assertFalse(app.query_one("#storage-narval").has_class("stale"))
            down = app.query_one("#storage-killarney")
            self.assertIn("down", str(down.render()))

    # ------------------------------------------------------------ compact view

    async def test_tiny_terminal_renders(self):
        from textual.widgets import TabbedContent
        from dracmonlib.tui.compact import CompactView
        app = self.make_app()
        async with app.run_test(size=(40, 10)) as pilot:
            await self.settle(app, pilot)
            view = app.query_one(CompactView)
            self.assertTrue(view.display)
            self.assertFalse(app.query_one(TabbedContent).display)
            text = str(view.render())
            self.assertIn("narval ●", text)
            for line in text.splitlines():
                self.assertLessEqual(len(line), 40)

    async def test_resize_switches_back(self):
        from textual.widgets import TabbedContent
        from dracmonlib.tui.compact import CompactView
        app = self.make_app()
        async with app.run_test(size=(60, 15)) as pilot:
            await self.settle(app, pilot)
            self.assertTrue(app.query_one(CompactView).display)
            await pilot.resize_terminal(120, 40)
            await self.settle(app, pilot)
            self.assertTrue(app.query_one(TabbedContent).display)
            self.assertFalse(app.query_one(CompactView).display)
            await pilot.resize_terminal(120, 19)  # too few rows
            await self.settle(app, pilot)
            self.assertTrue(app.query_one(CompactView).display)

    # ------------------------------------------------------------ Task 10 minors

    async def test_poll_waits_for_store_ready(self):
        gate = threading.Event()
        self.addCleanup(gate.set)
        opened = []
        real_open = store.open_store
        real_check = store.check_and_recover

        def slow_check(path):
            gate.wait(10)
            return real_check(path)

        def rec_open(path):
            opened.append(gate.is_set())
            return real_open(path)

        app = self.make_app()
        with mock.patch("dracmonlib.store.check_and_recover", side_effect=slow_check), \
                mock.patch("dracmonlib.store.open_store", side_effect=rec_open):
            async with app.run_test(size=SIZE) as pilot:
                await pilot.pause(0.05)
                self.assertTrue(app.is_poller)
                app.poll_cycle()  # e.g. the interval firing during recovery
                await pilot.pause(0.2)
                self.assertEqual(self.cycles, [])
                self.assertNotIn(False, opened)  # nothing opened the store before the check
                gate.set()
                await self.settle(app, pilot)
                self.assertGreaterEqual(len(self.cycles), 1)
                self.assertNotIn(False, opened)


if __name__ == "__main__":
    unittest.main()
