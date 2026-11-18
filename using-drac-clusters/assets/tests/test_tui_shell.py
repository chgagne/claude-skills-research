"""TUI shell tests (Textual). Skipped when Textual is not installed.

Run: uv run --with textual==8.2.8 python -m unittest tests.test_tui_shell -v

No ssh is ever run: ``ssh.socket_live``, ``ssh.askpass_available``,
``connect.open_master`` and ``collector.run_cycle`` are replaced by fakes.
"""
import asyncio
import contextlib
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

try:
    import textual  # noqa: F401
    HAVE_TEXTUAL = True
except ImportError:  # the stdlib-only suite must stay green without Textual
    HAVE_TEXTUAL = False

from dracmonlib import collector  # noqa: E402
from dracmonlib.store import PollLock  # noqa: E402
from seed import seed_store  # noqa: E402

SIZE = (120, 40)


class FakeSsh:
    """Socket liveness per host; ``open_master`` makes the host live (or not)."""

    def __init__(self, live=(), connect_ok=True, stderr="Permission denied (keyboard-interactive)."):
        self.live = set(live)
        self.connect_ok = connect_ok
        self.stderr = stderr
        self.opened = []  # (host, use_askpass)
        self.checked = []
        self.gate = None  # threading.Event: open_master blocks until set
        self.lock = threading.Lock()

    def socket_live(self, host):
        with self.lock:
            self.checked.append(host)
            return host in self.live

    def open_master(self, host, use_askpass):
        with self.lock:
            self.opened.append((host, use_askpass))
        if self.gate is not None:
            self.gate.wait(10)
        if self.connect_ok:
            with self.lock:
                self.live.add(host)
            return 0, ""
        return 255, f"some banner\n{self.stderr}\n"


@unittest.skipUnless(HAVE_TEXTUAL, "textual is not installed")
class TuiShellTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from dracmonlib.tui import app as tui_app
        self.tui_app = tui_app
        self.tmp = Path(tempfile.mkdtemp(prefix="dracmon-tui-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.now = time.time()
        self.db = self.tmp / "dracmon.sqlite"
        self.cfg = seed_store(self.db, self.now)
        self.fake = FakeSsh(live={"narval", "rorqual", "nibi", "tamia"})
        self.cycles = []
        self.askpass = True
        patches = [
            mock.patch("dracmonlib.ssh.socket_live", side_effect=self.fake.socket_live),
            mock.patch("dracmonlib.ssh.askpass_available", side_effect=lambda: self.askpass),
            mock.patch("dracmonlib.tui.connect.open_master", side_effect=self.fake.open_master),
            mock.patch("dracmonlib.collector.run_cycle", side_effect=self._run_cycle),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _run_cycle(self, cfg, conn, now, force=frozenset(), stop=None):
        self.cycles.append(set(force))
        return []

    def make_app(self):
        notes = []

        class RecApp(self.tui_app.DracmonApp):
            def notify(self, message, *a, **k):
                notes.append(str(message))
                return super().notify(message, *a, **k)

        app = RecApp(self.cfg, self.db)
        app.notes = notes
        return app

    async def settle(self, app, pilot):
        for _ in range(3):
            await app.workers.wait_for_complete()
            await pilot.pause()

    async def enter_on(self, app, pilot, name, key="enter"):
        from textual.widgets import DataTable
        await pilot.press("5")
        await self.settle(app, pilot)
        table = app.query_one("#clusters DataTable", DataTable)
        table.focus()
        table.move_cursor(row=table.get_row_index(name))
        await pilot.pause()
        await pilot.press(key)
        await self.settle(app, pilot)

    def screen_text(self, app):
        from textual.widgets import Button, Label, Static
        parts = []
        for w in app.screen.query("*"):
            if isinstance(w, (Label, Static, Button)):
                parts.append(str(w.render()))
        return "\n".join(parts)

    # ------------------------------------------------------------ shell

    async def test_tabs_switch_with_digits(self):
        from textual.widgets import TabbedContent
        app = self.make_app()
        async with app.run_test(size=SIZE) as pilot:
            await self.settle(app, pilot)
            tabs = app.query_one(TabbedContent)
            for key, tab in zip("12345", ("jobs", "cells", "usage", "storage", "clusters")):
                await pilot.press(key)
                await pilot.pause()
                self.assertEqual(tabs.active, tab)
            await pilot.press("1")
            await pilot.pause()
            self.assertEqual(tabs.active, "jobs")

    async def test_clusters_rows_and_header(self):
        from textual.widgets import DataTable
        app = self.make_app()
        async with app.run_test(size=SIZE) as pilot:
            await pilot.press("5")
            await self.settle(app, pilot)
            table = app.query_one("#clusters DataTable", DataTable)
            self.assertEqual(table.row_count, 6)
            down = " ".join(str(c) for c in table.get_row("killarney"))
            self.assertIn("down", down)
            self.assertIn("Control socket connect(", down)  # the start, cut at the end
            self.assertIn("…", down)
            self.assertIn("–", down)  # status column, filled by a later task
            table.move_cursor(row=table.get_row_index("killarney"))
            await pilot.pause()
            detail = str(app.query_one("#cluster-detail").render())
            self.assertIn("Control socket connect(/tmp/ssh-killarney): No such file", detail)
            narval = " ".join(str(c) for c in table.get_row("narval"))
            self.assertIn("active", narval)
            self.assertRegex(narval, r"\d+/\d+ nodes")
            header = str(app.query_one("#dots").render())
            self.assertIn("updated", header)
            self.assertIn("○ killarney", header)
            self.assertIn("● narval", header)

    # ------------------------------------------------------------ connect flow

    async def test_connect_modal_shows_mfa_warning_before_any_ssh(self):
        from dracmonlib.tui.connect import ConnectScreen
        app = self.make_app()
        async with app.run_test(size=SIZE) as pilot:
            await self.enter_on(app, pilot, "killarney")
            self.assertIsInstance(app.screen, ConnectScreen)
            text = self.screen_text(app)
            self.assertIn("Open a connection to killarney", text)
            self.assertIn("This will run: ssh killarney", text)
            self.assertIn("MFA prompt", text)
            self.assertIn("in a dialog on your screen", text)
            self.assertIn("Nothing is sent until you confirm.", text)
            self.assertEqual(app.focused.id, "cancel")
            self.assertEqual(self.fake.opened, [])

    async def test_terminal_wording_without_askpass(self):
        self.askpass = False
        app = self.make_app()
        async with app.run_test(size=SIZE) as pilot:
            await self.enter_on(app, pilot, "vulcan", key="c")
            self.assertIn("in this terminal (the monitor pauses until you answer)",
                          self.screen_text(app))
            self.assertEqual(self.fake.opened, [])

    async def test_cancel_sends_nothing(self):
        from dracmonlib.tui.connect import ConnectScreen
        app = self.make_app()
        async with app.run_test(size=SIZE) as pilot:
            await self.enter_on(app, pilot, "killarney")
            self.assertIsInstance(app.screen, ConnectScreen)
            await pilot.press("enter")  # default focus is Cancel
            await self.settle(app, pilot)
            self.assertNotIsInstance(app.screen, ConnectScreen)
            self.assertEqual(self.fake.opened, [])
            # nothing left in flight: the modal opens again
            await self.enter_on(app, pilot, "killarney")
            self.assertIsInstance(app.screen, ConnectScreen)
            await pilot.press("escape")
            await self.settle(app, pilot)
            self.assertEqual(self.fake.opened, [])

    async def test_confirm_runs_open_master_once_then_refreshes(self):
        app = self.make_app()
        async with app.run_test(size=SIZE) as pilot:
            await self.settle(app, pilot)
            self.cycles.clear()
            await self.enter_on(app, pilot, "killarney")
            await pilot.click("#connect")
            await self.settle(app, pilot)
            self.assertEqual(self.fake.opened, [("killarney", True)])
            self.assertIn("killarney: connected", app.notes)
            self.assertIn({"killarney"}, self.cycles)

    async def test_failed_connect_reports_last_stderr_line_and_is_not_retried(self):
        self.fake.connect_ok = False
        app = self.make_app()
        async with app.run_test(size=SIZE) as pilot:
            await self.settle(app, pilot)
            self.cycles.clear()
            await self.enter_on(app, pilot, "killarney")
            await pilot.click("#connect")
            await self.settle(app, pilot)
            await pilot.pause(0.3)
            self.assertEqual(self.fake.opened, [("killarney", True)])
            self.assertIn("killarney: failed: Permission denied (keyboard-interactive).",
                          app.notes)
            self.assertNotIn({"killarney"}, self.cycles)

    async def test_without_askpass_runs_in_suspended_terminal(self):
        self.askpass = False
        suspended = []

        @contextlib.contextmanager
        def fake_suspend(app_self):
            suspended.append("in")
            yield
            suspended.append("out")

        app = self.make_app()
        with mock.patch.object(type(app), "suspend", fake_suspend):
            async with app.run_test(size=SIZE) as pilot:
                await self.enter_on(app, pilot, "vulcan")
                await pilot.click("#connect")
                await self.settle(app, pilot)
                self.assertEqual(self.fake.opened, [("vulcan", False)])
                self.assertEqual(suspended, ["in", "out"])
                self.assertIn("vulcan: connected", app.notes)

    async def test_live_socket_skips_modal(self):
        from dracmonlib.tui.connect import ConnectScreen
        app = self.make_app()
        async with app.run_test(size=SIZE) as pilot:
            await self.enter_on(app, pilot, "narval")
            self.assertNotIsInstance(app.screen, ConnectScreen)
            self.assertIn("narval: already connected", app.notes)
            self.assertEqual(self.fake.opened, [])

    async def test_single_attempt_in_flight(self):
        from dracmonlib.tui.connect import ConnectScreen
        self.fake.gate = threading.Event()
        self.addCleanup(self.fake.gate.set)
        app = self.make_app()
        async with app.run_test(size=SIZE) as pilot:
            await self.enter_on(app, pilot, "killarney")
            await pilot.click("#connect")
            for _ in range(50):  # wait until the attempt is blocked inside ssh
                await pilot.pause(0.02)
                if self.fake.opened:
                    break
            self.assertEqual(self.fake.opened, [("killarney", True)])
            table = app.query_one("#clusters DataTable")
            table.focus()
            table.move_cursor(row=table.get_row_index("vulcan"))
            await pilot.press("enter")
            await pilot.pause(0.1)
            self.assertNotIsInstance(app.screen, ConnectScreen)
            self.assertIn("a connection attempt is already in progress", app.notes)
            self.fake.gate.set()
            await self.settle(app, pilot)
            self.assertEqual(self.fake.opened, [("killarney", True)])

    # ------------------------------------------------------------ poller role

    async def test_second_instance_does_not_poll(self):
        held = PollLock(self.tmp)
        self.assertTrue(held.try_acquire())
        self.addCleanup(held.release)
        app = self.make_app()
        async with app.run_test(size=SIZE) as pilot:
            await self.settle(app, pilot)
            await pilot.press("R")
            await self.settle(app, pilot)
            self.assertEqual(self.cycles, [])
            self.assertFalse(app.is_poller)
            self.assertEqual((self.tmp / collector.REFRESH_NAME).read_text(), "*\n")

    async def test_second_instance_connect_requests_refresh(self):
        held = PollLock(self.tmp)
        self.assertTrue(held.try_acquire())
        self.addCleanup(held.release)
        app = self.make_app()
        async with app.run_test(size=SIZE) as pilot:
            await self.enter_on(app, pilot, "killarney")
            await pilot.click("#connect")
            await self.settle(app, pilot)
            self.assertEqual(self.cycles, [])
            self.assertEqual((self.tmp / collector.REFRESH_NAME).read_text(), "killarney\n")

    async def test_poller_polls_and_releases_lock_on_exit(self):
        app = self.make_app()
        async with app.run_test(size=SIZE) as pilot:
            await self.settle(app, pilot)
            self.assertTrue(app.is_poller)
            self.assertGreaterEqual(len(self.cycles), 1)
            other = PollLock(self.tmp)
            self.assertFalse(other.try_acquire())
            self.cycles.clear()
            await pilot.press("R")
            await self.settle(app, pilot)
            self.assertEqual(self.cycles, [{c.name for c in self.cfg.clusters}])
        other = PollLock(self.tmp)
        self.assertTrue(other.try_acquire())
        other.release()


    # ------------------------------------------------------------ store recovery

    async def test_poller_moves_corrupt_store_aside(self):
        self.db.unlink()
        for suffix in ("-wal", "-shm"):
            Path(str(self.db) + suffix).unlink(missing_ok=True)
        self.db.write_bytes(b"this is not a database" * 100)
        app = self.make_app()
        async with app.run_test(size=SIZE) as pilot:
            await self.settle(app, pilot)
            self.assertTrue(app.is_poller)
            self.assertEqual(len(list(self.tmp.glob("dracmon.sqlite.corrupt-*"))), 1)
            self.assertTrue(any("corrupt" in n for n in app.notes), app.notes)

    async def test_reader_leaves_corrupt_store_alone(self):
        held = PollLock(self.tmp)
        self.assertTrue(held.try_acquire())
        self.addCleanup(held.release)
        self.db.unlink()
        for suffix in ("-wal", "-shm"):
            Path(str(self.db) + suffix).unlink(missing_ok=True)
        self.db.write_bytes(b"this is not a database" * 100)
        app = self.make_app()
        async with app.run_test(size=SIZE) as pilot:
            await self.settle(app, pilot)
            self.assertFalse(app.is_poller)
            self.assertEqual(list(self.tmp.glob("dracmon.sqlite.corrupt-*")), [])
            self.assertTrue(any("cannot read the store" in n for n in app.notes), app.notes)


@unittest.skipUnless(HAVE_TEXTUAL, "textual is not installed")
class TuiQuitTests(unittest.IsolatedAsyncioTestCase):
    """Real collector cycle against the fake ssh (no network): quitting during
    a hung poll must kill it and return promptly."""

    def setUp(self):
        import os
        from fakessh import FAKEBIN
        self.tmp = Path(tempfile.mkdtemp(prefix="dracmon-quit-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.log = self.tmp / "fake.log"
        home = self.tmp / "home"
        home.mkdir()
        sock = self.tmp / "sock"
        sock.write_text("")
        p = mock.patch.dict(os.environ, {
            "PATH": f"{FAKEBIN}:/usr/bin:/bin", "FAKEBIN_LOG": str(self.log),
            "FAKE_SSH_MODE": "hang", "FAKE_SSH_CONTROLPATH": str(sock),
            "USER": "jdoe", "CC_CLUSTER": "testcluster", "SCRATCH": "", "HOME": str(home)})
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(lambda: __import__("dracmonlib.ssh").ssh.kill_all_running())

    async def test_quit_during_hung_poll_is_prompt(self):
        from dracmonlib.config import Cluster, Config
        from dracmonlib.tui.app import DracmonApp
        from test_ssh import alive, fakessh_running
        cfg = Config(clusters=[Cluster("testcluster", "testhost", pinned=True)])
        app = DracmonApp(cfg, self.tmp / "dracmon.sqlite")
        child = Path(f"{self.log}.child")
        async with app.run_test(size=SIZE) as pilot:
            for _ in range(250):  # until the remote run hangs inside ssh
                await pilot.pause(0.02)
                if child.exists() and child.read_text().strip():
                    break
            self.assertTrue(app.is_poller)
            self.assertTrue(app._cycle_lock.locked())
            t0 = time.monotonic()
            await pilot.press("q")
        while app._cycle_lock.locked() and time.monotonic() - t0 < 5:
            await asyncio.sleep(0.05)
        self.assertLess(time.monotonic() - t0, 3)
        self.assertFalse(app._cycle_lock.locked())
        self.assertEqual(fakessh_running(), "")
        self.assertFalse(alive(int(child.read_text())))
        other = PollLock(self.tmp)  # released by the worker once it ended
        self.assertTrue(other.try_acquire())
        other.release()


class LazyImportTests(unittest.TestCase):
    def test_cli_and_collector_do_not_import_textual(self):
        import subprocess
        code = ("import sys; sys.path.insert(0, %r); import dracmon; "
                "from dracmonlib import collector, doctor, service; "
                "dracmon.build_parser().parse_args(['doctor']); "
                "sys.exit(1 if 'textual' in sys.modules else 0)" % str(HERE.parent))
        self.assertEqual(subprocess.run([sys.executable, "-c", code]).returncode, 0)


if __name__ == "__main__":
    unittest.main()
