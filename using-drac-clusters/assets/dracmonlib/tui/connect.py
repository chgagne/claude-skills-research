"""Announced connection opening: the modal, and the one ssh that may prompt.

Nothing here runs without the user's confirmation in ``ConnectScreen``. The
ssh started by ``open_master`` may show an MFA prompt (that is its purpose);
it is never retried and never run by the collector.
"""
from __future__ import annotations

import os
import signal
import subprocess
import tempfile

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from .. import ssh
from ..config import Cluster

ASKPASS_WHERE = "in a dialog on your screen"
TERMINAL_WHERE = "in this terminal (the monitor pauses until you answer)"
ASKPASS_TIMEOUT = 300  # seconds for the user to answer the dialog


def modal_title(cluster: Cluster) -> str:
    return f"Open a connection to {cluster.name}"


def modal_body(cluster: Cluster, use_askpass: bool) -> str:
    where = ASKPASS_WHERE if use_askpass else TERMINAL_WHERE
    return (f"This will run: ssh {cluster.host}\n"
            f"An MFA prompt (Duo push or passcode) will arrive {where}.\n"
            "Nothing is sent until you confirm.")


def last_line(text: str) -> str:
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def open_master(host: str, use_askpass: bool) -> tuple[int, str]:
    """Run ``ssh -fN -o ControlMaster=yes host`` once; return (rc, stderr).

    With askpass the prompt goes to the user's GUI dialog; stderr goes to a
    temporary file, not a pipe, so a backgrounded master holding it cannot
    block us. Without askpass the caller has suspended the TUI and ssh talks
    to the real terminal (stderr is not captured)."""
    argv = ssh.open_master_argv(host)
    env = ssh.open_master_env(use_askpass)
    if not use_askpass:
        return subprocess.run(argv, env=env).returncode, ""
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace") as err:
        try:
            # own process group, registered: quitting the app kills an attempt
            # still waiting for its MFA answer (a master already forked by -f
            # has left the group and is not touched)
            p = subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=err,
                                 start_new_session=True)
        except OSError as e:
            return 255, f"cannot run ssh: {e}"
        ssh.register(p)
        try:
            try:
                rc = p.wait(timeout=ASKPASS_TIMEOUT)
            except subprocess.TimeoutExpired:
                # the whole group: ssh may have started a ProxyCommand or askpass
                try:
                    os.killpg(p.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                p.wait()
                rc = 124
                err.write(f"\nno answer within {ASKPASS_TIMEOUT}s\n")
        finally:
            killed = ssh.unregister(p)
        if killed:
            return 255, ssh.STOPPED
        err.seek(0)
        return rc, err.read()


class ConnectScreen(ModalScreen[bool]):
    """Confirmation before any ssh that may prompt. Dismisses with True on
    Connect, False on Cancel or Escape. Cancel has the focus by default."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, cluster: Cluster, use_askpass: bool):
        super().__init__()
        self.cluster = cluster
        self.use_askpass = use_askpass

    def compose(self) -> ComposeResult:
        with Vertical(id="connect-box"):
            yield Label(modal_title(self.cluster), id="connect-title")
            yield Static(modal_body(self.cluster, self.use_askpass), id="connect-body")
            with Horizontal(id="connect-buttons"):
                yield Button("Connect", id="connect", variant="warning")
                yield Button("Cancel", id="cancel", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#cancel", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(event.button.id == "connect")

    def action_cancel(self) -> None:
        self.dismiss(False)
