"""dracmon TUI shell: tabs, header dots, poller role, announced connections.

Threads: the event loop never waits on ssh or on a sqlite write. Store reads
(every 10 s), collector cycles (every 30 s when this app is the poller), socket
checks and the askpass connection run in thread workers, each opening its own
sqlite connection. Only the non-askpass connection runs on the UI thread, inside
``App.suspend()``: the TUI is paused while the user answers MFA in the terminal.

Poller role: on mount the app tries ``PollLock``. With the lock it polls itself
and releases the lock on exit; without it (a collector service or another TUI
runs) it only reads, and ``R`` writes the refresh request file.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult, SuspendNotSupported
from textual.binding import Binding
from textual.widgets import Footer, Static, TabbedContent, TabPane

from .. import collector, ssh, status_page, store
from ..config import Cluster, Config
from . import compact, connect
from .cellsview import CellsView, load_cells
from .clusters import ClustersView, header_text, load_clusters
from .jobs import JobsView, load_jobs
from .storage import StorageView, load_storage
from .usage import UsageView, load_usage

RELOAD_EVERY = 10.0
TABS = (("jobs", "Jobs"), ("cells", "Cells"), ("usage", "Usage"),
        ("storage", "Storage"), ("clusters", "Clusters"))


@dataclass
class Snapshot:
    """Everything the views show, read from the store in one worker pass."""
    clusters: list
    jobs: object
    cells: list
    usage: list
    storage: list


class DracmonApp(App):
    CSS_PATH = str(Path(__file__).resolve().parent / "theme.tcss")  # absolute: subclasses live elsewhere
    TITLE = "dracmon"
    BINDINGS = [
        *[Binding(str(i), f"show_tab('{tab}')", label, show=False)
          for i, (tab, label) in enumerate(TABS, 1)],
        Binding("R", "refresh", "Refresh"),
        Binding("w", "window", "Window"),
        Binding("slash", "filter", "Filter"),
        Binding("question_mark", "help", "Help"),
        Binding("q", "quit", "Quit"),
    ]

    clock = staticmethod(time.time)  # tests pin it

    def __init__(self, cfg: Config, store_path: Path):
        super().__init__()
        self.cfg = cfg
        self.store_path = Path(store_path)
        self.state_dir = self.store_path.parent
        self.is_poller = False
        self._lock = store.PollLock(self.state_dir)  # referenced: __del__ releases
        self._cycle_lock = threading.Lock()
        self._reload_lock = threading.Lock()
        self._release_lock = threading.Lock()
        self._stop = threading.Event()
        self._store_ready = threading.Event()  # store checked (poller) or not ours to check
        self._connecting = False
        self._log_handler: logging.Handler | None = None
        self.rows = []

    # ------------------------------------------------------------ layout

    def compose(self) -> ComposeResult:
        yield Static("dracmon", id="dots")
        with TabbedContent(initial="jobs"):
            for tab, label in TABS:
                with TabPane(label, id=tab):
                    if tab == "jobs":
                        yield JobsView()
                    elif tab == "cells":
                        yield CellsView()
                    elif tab == "usage":
                        yield UsageView(self.cfg)
                    elif tab == "storage":
                        yield StorageView(self.cfg)
                    else:
                        yield ClustersView(self.cfg)
        yield compact.CompactView(id="compact")
        yield Footer()

    def on_mount(self) -> None:
        self._fit_layout(self.size.width, self.size.height)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.is_poller = self._lock.try_acquire()
        self.set_interval(RELOAD_EVERY, self.reload)
        if self.is_poller:
            self._start_log()
            self.set_interval(collector.TICK, self.poll_cycle)
            self._recover_then_poll()
        else:
            self._store_ready.set()
            self.reload()

    @work(thread=True, group="poll")
    def _recover_then_poll(self) -> None:
        """Poller only, as the collector does: move a corrupt store aside
        before anything opens it, then read and poll."""
        try:
            moved = store.check_and_recover(self.store_path)
            if moved is not None:
                collector.log.warning("store was corrupt, moved aside to %s", moved)
                self.notify(f"the store was corrupt; moved aside to {moved.name}",
                            severity="warning", timeout=15)
        except Exception as e:
            self.notify(f"cannot check the store: {e}", severity="error")
        finally:
            self._store_ready.set()
        self._from_thread(self.reload)
        self._from_thread(self.poll_cycle)

    async def action_quit(self) -> None:
        self._stop_polling()
        self.exit()

    def _stop_polling(self) -> None:
        """Stop polling and kill running ssh, so the worker threads (joined at
        exit) end within a second instead of at their ssh timeouts."""
        self._stop.set()
        ssh.kill_all_running()

    def on_unmount(self) -> None:
        self._stop_polling()
        # a cycle still running releases the lock itself when it ends
        if self._cycle_lock.acquire(blocking=False):
            try:
                self._release_poller()
            finally:
                self._cycle_lock.release()

    def _release_poller(self) -> None:
        # idempotent and thread-safe: the cycle worker and on_unmount may both call it
        with self._release_lock:
            self._lock.release()
            if self._log_handler is not None:
                collector.log.removeHandler(self._log_handler)
                self._log_handler.close()
                self._log_handler = None

    def _start_log(self) -> None:
        # the collector logger has no handler of its own: without one, warnings
        # would reach stderr (the terminal the TUI draws on)
        h = RotatingFileHandler(self.state_dir / collector.LOG_NAME,
                                maxBytes=1_000_000, backupCount=3)
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s tui %(message)s"))
        collector.log.addHandler(h)
        collector.log.setLevel(logging.INFO)
        self._log_handler = h

    # ------------------------------------------------------------ store reads

    @work(thread=True, group="reload")
    def reload(self) -> None:
        if not self._store_ready.is_set() or not self._reload_lock.acquire(blocking=False):
            return
        try:
            now = self.clock()
            conn = store.open_store(self.store_path)
            try:
                snap = Snapshot(
                    clusters=load_clusters(conn, self.cfg, now),
                    jobs=load_jobs(conn, self.cfg, now),
                    cells=load_cells(conn, self.cfg, now),
                    usage=load_usage(conn, self.cfg, now),
                    storage=load_storage(conn, self.cfg, now))
            finally:
                conn.close()
        except Exception as e:  # a store problem must not kill the UI
            self.notify(f"cannot read the store: {e}", severity="error")
            return
        finally:
            self._reload_lock.release()
        self._from_thread(self._apply, snap, now)

    def _from_thread(self, fn, *args) -> None:
        try:
            self.call_from_thread(fn, *args)
        except RuntimeError:  # the app is closing
            pass

    def _apply(self, snap: "Snapshot", now: float) -> None:
        self.rows = rows = snap.clusters
        updated = max((r.last_ok for r in rows if r.last_ok is not None), default=None)
        self.query_one("#dots", Static).update(header_text(rows, updated))
        self.query_one(ClustersView).update_rows(rows, now)
        self.query_one(JobsView).update_data(snap.jobs, now)
        self.query_one(CellsView).update_rows(snap.cells, now)
        self.query_one(UsageView).update_data(snap.usage, now)
        self.query_one(StorageView).update_data(snap.storage, now)
        self.query_one(compact.CompactView).update_data(
            compact.build(rows, snap.jobs.queue, snap.cells, snap.storage))

    # ------------------------------------------------------------ compact layout

    def on_resize(self, event) -> None:
        self._fit_layout(event.size.width, event.size.height)

    def _fit_layout(self, width: int, height: int) -> None:
        small = compact.is_compact(width, height)
        self.query_one(compact.CompactView).display = small
        for w in (self.query_one(TabbedContent), self.query_one("#dots"),
                  self.query_one(Footer)):
            w.display = not small

    # ------------------------------------------------------------ polling

    @work(thread=True, group="poll")
    def poll_cycle(self, force: frozenset = frozenset(), wait: bool = False) -> None:
        """One collector cycle (poller only). A tick skips while a cycle runs;
        a forced cycle (``wait``) runs after it."""
        if not self.is_poller or self._stop.is_set():
            return
        while not self._store_ready.wait(0.1):  # recovery runs before any open
            if self._stop.is_set():
                return
        if not self._cycle_lock.acquire(blocking=wait):
            return
        try:
            if self._stop.is_set():
                return
            conn = store.open_store(self.store_path)
            try:
                now = time.time()
                names = [c.name for c in self.cfg.clusters]
                due = set(force) | collector.take_refresh(self.state_dir, names)
                collector.run_cycle(self.cfg, conn, now, due, self._stop)
                status_page.refresh(conn, self.cfg, now)
                collector._maybe_prune(conn, self.cfg, now)
            finally:
                conn.close()
        except Exception as e:
            collector.log.exception("tui cycle failed")
            self.notify(f"poll failed: {e}", severity="error")
        finally:
            self._cycle_lock.release()
            if self._stop.is_set():
                self._release_poller()  # the app has gone while we polled (idempotent)
        self._from_thread(self.reload)

    def action_refresh(self) -> None:
        if self.is_poller:
            self.poll_cycle(frozenset(c.name for c in self.cfg.clusters), True)
            self.notify("refreshing all clusters")
        else:
            collector.request_refresh(self.state_dir, None)
            self.notify("refresh requested from the running collector")
        self.reload()

    # ------------------------------------------------------------ tabs, misc keys

    def action_show_tab(self, tab: str) -> None:
        self.query_one(TabbedContent).active = tab

    def action_filter(self) -> None:
        """``/``: the jobs filter (from any tab)."""
        if self.query_one(compact.CompactView).display:
            return
        self.action_show_tab("jobs")
        self.query_one(JobsView).open_filter()

    def action_window(self) -> None:
        tabs = self.query_one(TabbedContent)
        if tabs.display and tabs.active == "jobs":
            self.query_one(JobsView).cycle_window()

    def action_help(self) -> None:
        if self.screen.query("HelpPanel"):
            self.action_hide_help_panel()
        else:
            self.action_show_help_panel()

    # ------------------------------------------------------------ connect flow

    def _cluster(self, name: str | None) -> Cluster | None:
        if name is None:
            name = self.query_one(ClustersView).selected()
        return next((c for c in self.cfg.clusters if c.name == name), None)

    def action_connect(self, name: str | None = None) -> None:
        """Announced connection: socket check, modal, one ssh, verify, refresh.
        One attempt at a time; never retried automatically."""
        cluster = self._cluster(name)
        if cluster is None:
            return
        if self._connecting:
            self.notify("a connection attempt is already in progress", severity="warning")
            return
        self._connecting = True
        self._precheck(cluster)

    @work(thread=True, group="connect")
    def _precheck(self, cluster: Cluster) -> None:
        try:
            live = ssh.socket_live(cluster.host)
            use_askpass = ssh.askpass_available()
        except Exception as e:
            self._connecting = False
            self.notify(f"{cluster.name}: cannot check the socket: {e}", severity="error")
            return
        self._from_thread(self._after_precheck, cluster, live, use_askpass)

    def _after_precheck(self, cluster: Cluster, live: bool, use_askpass: bool) -> None:
        if live:
            self._connecting = False
            self.notify(f"{cluster.name}: already connected")
            return
        self.push_screen(connect.ConnectScreen(cluster, use_askpass),
                         callback=lambda ok: self._confirmed(cluster, use_askpass, ok))

    def _confirmed(self, cluster: Cluster, use_askpass: bool, ok: bool | None) -> None:
        if not ok:
            self._connecting = False
            return
        if use_askpass:
            self._open_with_askpass(cluster)
            return
        try:
            with self.suspend():  # the user answers MFA in the real terminal
                rc, err = connect.open_master(cluster.host, False)
        except SuspendNotSupported:
            self._connecting = False
            self.notify(f"{cluster.name}: this terminal cannot be paused; "
                        f"run ssh {cluster.host} in another one", severity="warning")
            return
        except Exception as e:
            rc, err = 255, f"cannot run ssh: {e}"
        self._verify(cluster, rc, err)

    @work(thread=True, group="connect")
    def _open_with_askpass(self, cluster: Cluster) -> None:
        try:
            rc, err = connect.open_master(cluster.host, True)
        except Exception as e:
            rc, err = 255, f"cannot run ssh: {e}"
        self._check_connected(cluster, rc, err)

    @work(thread=True, group="connect")
    def _verify(self, cluster: Cluster, rc: int, err: str) -> None:
        self._check_connected(cluster, rc, err)

    def _check_connected(self, cluster: Cluster, rc: int, err: str) -> None:
        """Worker thread: verify with ``socket_live``, report, then refresh."""
        try:
            try:
                live = ssh.socket_live(cluster.host)
            except Exception:
                live = False
            if not live:
                why = connect.last_line(err) or f"ssh exited with status {rc}"
                self.notify(f"{cluster.name}: failed: {why}", severity="error", timeout=10)
                return
            self.notify(f"{cluster.name}: connected")
            if self.is_poller:
                self._from_thread(self.poll_cycle, frozenset({cluster.name}), True)
            else:
                collector.request_refresh(self.state_dir, {cluster.name})
        finally:
            self._connecting = False
