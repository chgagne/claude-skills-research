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
from logging.handlers import RotatingFileHandler
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult, SuspendNotSupported
from textual.binding import Binding
from textual.widgets import Footer, Static, TabbedContent, TabPane

from .. import collector, ssh, store
from ..config import Cluster, Config
from . import connect
from .clusters import ClustersView, header_text, load_clusters

RELOAD_EVERY = 10.0
TABS = (("jobs", "Jobs"), ("cells", "Cells"), ("usage", "Usage"),
        ("storage", "Storage"), ("clusters", "Clusters"))


class DracmonApp(App):
    CSS_PATH = str(Path(__file__).resolve().parent / "theme.tcss")  # absolute: subclasses live elsewhere
    TITLE = "dracmon"
    BINDINGS = [
        *[Binding(str(i), f"show_tab('{tab}')", label, show=False)
          for i, (tab, label) in enumerate(TABS, 1)],
        Binding("R", "refresh", "Refresh"),
        Binding("slash", "filter", "Filter"),
        Binding("question_mark", "help", "Help"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, cfg: Config, store_path: Path):
        super().__init__()
        self.cfg = cfg
        self.store_path = Path(store_path)
        self.state_dir = self.store_path.parent
        self.is_poller = False
        self._lock = store.PollLock(self.state_dir)  # referenced: __del__ releases
        self._cycle_lock = threading.Lock()
        self._reload_lock = threading.Lock()
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
                    if tab == "clusters":
                        yield ClustersView(self.cfg)
                    else:
                        yield Static(f"{label}: this view comes in the next version.",
                                     classes="placeholder")
        yield Footer()

    def on_mount(self) -> None:
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
            now = time.time()
            conn = store.open_store(self.store_path)
            try:
                rows = load_clusters(conn, self.cfg, now)
            finally:
                conn.close()
        except Exception as e:  # a store problem must not kill the UI
            self.notify(f"cannot read the store: {e}", severity="error")
            return
        finally:
            self._reload_lock.release()
        self._from_thread(self._apply, rows, now)

    def _from_thread(self, fn, *args) -> None:
        try:
            self.call_from_thread(fn, *args)
        except RuntimeError:  # the app is closing
            pass

    def _apply(self, rows, now: float) -> None:
        self.rows = rows
        updated = max((r.last_ok for r in rows if r.last_ok is not None), default=None)
        self.query_one("#dots", Static).update(header_text(rows, updated))
        self.query_one(ClustersView).update_rows(rows, now)

    # ------------------------------------------------------------ polling

    @work(thread=True, group="poll")
    def poll_cycle(self, force: frozenset = frozenset(), wait: bool = False) -> None:
        """One collector cycle (poller only). A tick skips while a cycle runs;
        a forced cycle (``wait``) runs after it."""
        if not self.is_poller or self._stop.is_set():
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
                collector._maybe_prune(conn, self.cfg, now)
            finally:
                conn.close()
        except Exception as e:
            collector.log.exception("tui cycle failed")
            self.notify(f"poll failed: {e}", severity="error")
        finally:
            if self._stop.is_set():
                self._release_poller()  # the app has gone while we polled
            self._cycle_lock.release()
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
        self.notify("filter: available with the jobs view")

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
