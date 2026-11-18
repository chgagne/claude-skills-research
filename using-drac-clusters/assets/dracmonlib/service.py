"""Install the collector as a user service: launchd (macOS) or systemd --user (Linux).

The collector runs with askpass disabled, so no SSH_ASKPASS is set in the
service environment. On SIGTERM it finishes the current cycle (up to
``ssh_timeout``, 60 s), hence the 90 s stop timeouts.
"""
from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

from .config import state_dir

LABEL = "dracmon.collector"
UNIT = "dracmon"
STOP_TIMEOUT = 90
ENTRY = Path(__file__).resolve().parent.parent / "dracmon.py"


def collector_argv() -> list[str]:
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("uv not found on PATH; install it (https://docs.astral.sh/uv/) "
                           "so the service can run dracmon.py")
    # --wait-lock: while the TUI runs its own collector the service waits for the
    # lock instead of exiting 1 and being restarted every minute (log growth)
    return [os.path.abspath(uv), "run", "--script", str(ENTRY), "collect", "--wait-lock"]


def render_launchd(argv: list[str], log_dir: Path, path_env: str) -> str:
    env = {"PATH": path_env}
    if os.environ.get("HOME"):
        env["HOME"] = os.environ["HOME"]
    log = str(Path(log_dir) / "service.log")
    d = {"Label": LABEL, "ProgramArguments": list(argv), "RunAtLoad": True,
         "KeepAlive": True, "ThrottleInterval": 60, "ExitTimeOut": STOP_TIMEOUT,
         "StandardOutPath": log, "StandardErrorPath": log, "EnvironmentVariables": env}
    return plistlib.dumps(d).decode()


def _systemd_quote(arg: str) -> str:
    arg = arg.replace("%", "%%").replace("$", "$$")
    if arg and not any(c.isspace() or c in "\"'\\" for c in arg):
        return arg
    return '"' + arg.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_systemd(argv: list[str]) -> str:
    return ("[Unit]\nDescription=dracmon collector for DRAC Slurm clusters\n\n"
            "[Service]\n"
            f"ExecStart={' '.join(_systemd_quote(a) for a in argv)}\n"
            "Restart=on-failure\nRestartSec=60\n"
            f"TimeoutStopSec={STOP_TIMEOUT}\n\n"
            "[Install]\nWantedBy=default.target\n")


def _mac_paths() -> tuple[Path, str]:
    plist = Path.home() / "Library/LaunchAgents" / f"{LABEL}.plist"
    return plist, f"gui/{os.getuid()}"


def _unit_path() -> Path:
    return Path.home() / ".config/systemd/user" / f"{UNIT}.service"


def _sh(argv: list[str]) -> int:
    return subprocess.run(argv).returncode


def _platform() -> str | None:
    if sys.platform == "darwin":
        return "mac"
    if sys.platform.startswith("linux"):
        return "linux"
    return None


def _unsupported() -> int:
    print(f"dracmon service: unsupported platform {sys.platform!r}", file=sys.stderr)
    return 2


def _write(path: Path, text: str, force: bool) -> bool:
    """Write ``text``; False (with a message) when a differing file exists and not force."""
    if path.exists() and path.read_text() != text and not force:
        print(f"dracmon service: {path} exists and differs; use --force to overwrite",
              file=sys.stderr)
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return True


def install(force: bool = False) -> int:
    plat = _platform()
    if plat is None:
        return _unsupported()
    try:
        argv = collector_argv()
    except RuntimeError as e:
        print(f"dracmon service: {e}", file=sys.stderr)
        return 1
    if plat == "mac":
        plist, target = _mac_paths()
        text = render_launchd(argv, state_dir(), os.environ.get("PATH", "/usr/bin:/bin"))
        existed = plist.exists()
        if not _write(plist, text, force):
            return 1
        if existed:  # reload: bootstrap fails when the job is already loaded
            _sh(["launchctl", "bootout", f"{target}/{LABEL}"])
        return _sh(["launchctl", "bootstrap", target, str(plist)])
    if not _write(_unit_path(), render_systemd(argv), force):
        return 1
    rc = _sh(["systemctl", "--user", "daemon-reload"])
    if rc:
        return rc
    return _sh(["systemctl", "--user", "enable", "--now", UNIT])


def uninstall() -> int:
    plat = _platform()
    if plat is None:
        return _unsupported()
    if plat == "mac":
        plist, target = _mac_paths()
        rc = _sh(["launchctl", "bootout", f"{target}/{LABEL}"])
        plist.unlink(missing_ok=True)
        return rc
    rc = _sh(["systemctl", "--user", "disable", "--now", UNIT])
    _unit_path().unlink(missing_ok=True)
    _sh(["systemctl", "--user", "daemon-reload"])
    return rc


def status() -> int:
    plat = _platform()
    if plat is None:
        return _unsupported()
    if plat == "mac":
        return _sh(["launchctl", "print", f"{_mac_paths()[1]}/{LABEL}"])
    return _sh(["systemctl", "--user", "status", UNIT])
