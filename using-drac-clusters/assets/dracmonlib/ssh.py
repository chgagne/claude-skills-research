"""ssh layer: polls a cluster over an EXISTING ControlMaster socket only.

Every collector ssh carries ``-o BatchMode=yes -o ControlMaster=no``: it never
prompts (no MFA, no password, no host-key question) and never becomes a master.
With no usable socket it fails fast with rc 255, which the caller records as
"down", never as an empty queue. Only ``open_master_argv`` (run on an explicit
user request) omits BatchMode.
"""
from __future__ import annotations

import hashlib
import os
import pwd
import re
import shlex
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from .config import Cluster
from .frame import Section, parse_frames

REMOTE_SH = Path(__file__).resolve().parent / "remote.sh"
COLLECTOR_OPTS = ["-o", "BatchMode=yes", "-o", "ControlMaster=no"]
DEFAULT_SINCE = "now-1days"  # sacct relative time, used when since is None
_TOKEN = re.compile(r"%(.)")


@dataclass
class PollResult:
    cluster: str
    started: float
    finished: float
    ok: bool
    error: str | None
    requested: list[str]
    sections: dict[str, Section] = field(default_factory=dict)
    env: dict[str, str] = field(default_factory=dict)


def _ssh_config(host: str) -> dict[str, str]:
    """`ssh -G host`: a local config query, no connection is made."""
    try:
        p = subprocess.run(["ssh", "-G", *COLLECTOR_OPTS, host], capture_output=True,
                           text=True, stdin=subprocess.DEVNULL, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if p.returncode != 0:
        return {}
    cfg: dict[str, str] = {}
    for line in p.stdout.splitlines():
        key, _, value = line.partition(" ")
        cfg.setdefault(key.lower(), value)
    return cfg


def control_path(host: str) -> Path | None:
    """The ControlPath ssh would use for ``host``, or None if there is none."""
    cfg = _ssh_config(host)
    raw = cfg.get("controlpath", "none")
    if not raw or raw == "none":
        return None
    pw = pwd.getpwuid(os.getuid())
    lhost = socket.gethostname()
    rhost = cfg.get("hostname", host)
    port = cfg.get("port", "22")
    ruser = cfg.get("user", pw.pw_name)
    jump = cfg.get("proxyjump", "none")
    jump = "" if jump == "none" else jump
    tokens = {
        "%": "%", "r": ruser, "h": rhost, "p": port, "n": host, "u": pw.pw_name,
        "d": pw.pw_dir, "i": str(os.getuid()), "l": lhost,
        "C": hashlib.sha1(f"{lhost}{rhost}{port}{ruser}{jump}".encode()).hexdigest(),
    }
    path = _TOKEN.sub(lambda m: tokens.get(m.group(1), m.group(0)), raw)
    if path == "~" or path.startswith("~/"):
        path = pw.pw_dir + path[1:]
    return Path(path)


def socket_live(host: str) -> bool:
    """True when a master socket exists and answers ``-O check``. Never prompts:
    with no socket file no ssh connection is attempted at all."""
    path = control_path(host)
    if path is None or not path.exists():
        return False
    try:
        p = subprocess.run(["ssh", "-O", "check", *COLLECTOR_OPTS, host],
                           capture_output=True, stdin=subprocess.DEVNULL, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return p.returncode == 0


def _clean_lines(entries, ok) -> str:
    return "\n".join(f"{a}\t{b}" for a, b in entries if ok(str(a)) and ok(str(b)))


def build_script(sections: list[str], since: str | None, offsets: dict[str, int],
                 globs: list[tuple[str, str]], retention_days: int) -> str:
    """Preamble of shell assignments (values shlex-quoted) followed by remote.sh.

    ``env`` is always sent; ``accounting`` brings ``steps``. Offset and glob
    entries containing a tab or newline are dropped (they would break the
    line/tab format); campaign names must also be free of spaces."""
    want = ["env"]
    for s in sections:
        if s not in want:
            want.append(s)
        if s == "accounting" and "steps" not in want:
            want.append("steps")
    no_sep = lambda v: "\t" not in v and "\n" not in v  # noqa: E731
    offs = _clean_lines(((k, int(v)) for k, v in offsets.items()), no_sep)
    gl = "\n".join(f"{c}\t{g}" for c, g in globs
                   if c and no_sep(g) and not any(ch.isspace() for ch in c))
    pre = (f"DRACMON_SECTIONS={shlex.quote(' '.join(want))}\n"
           f"DRACMON_SINCE={shlex.quote(since or DEFAULT_SINCE)}\n"
           f"DRACMON_OFFSETS={shlex.quote(offs)}\n"
           f"DRACMON_GLOBS={shlex.quote(gl)}\n"
           f"DRACMON_CELLS_RETENTION={shlex.quote(str(int(retention_days)))}\n")
    return pre + REMOTE_SH.read_text()


def _requested(script: str) -> list[str]:
    m = re.search(r"^DRACMON_SECTIONS=(.*)$", script, re.M)
    if not m:
        return []
    try:
        return " ".join(shlex.split(m.group(1))).split()
    except ValueError:
        return []


def run_remote(host: str, script: str, timeout: int) -> tuple[int, str, str]:
    """Pipe ``script`` to ``bash -l -s`` on ``host`` over the existing master.

    Runs in its own process group; on timeout the whole group is killed and
    rc 124 is returned with whatever output had arrived."""
    argv = ["ssh", *COLLECTOR_OPTS, "-o", "ConnectTimeout=15"]
    if "usage" in _requested(script):
        argv += ["-o", "Compression=yes"]
    argv += [host, "bash -l -s"]
    try:
        p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, start_new_session=True)
    except OSError as e:
        return 255, "", f"cannot run ssh: {e}"
    try:
        out, err = p.communicate(script, timeout=timeout)
        return p.returncode, out, err
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            out, err = p.communicate(timeout=5)
        except subprocess.TimeoutExpired:  # a grandchild left the group holding the pipes
            p.kill()
            p.wait()
            out, err = "", ""
        return 124, out or "", err or ""


def _parse_env(body: str) -> dict[str, str]:
    env = {}
    for line in body.splitlines():
        k, sep, v = line.partition("=")
        if sep and k:
            env[k] = v
    return env


def poll_cluster(cluster: Cluster, sections: list[str], *, since, offsets, globs,
                 retention_days, timeout) -> PollResult:
    """One poll. ``ok`` only when ssh exited 0 and the env section is complete.

    ``sections`` holds the complete sections only; on an ssh failure (255) or a
    timeout (124) it may be empty, which means "no data", never "no jobs"."""
    script = build_script(sections, since, offsets, globs, retention_days)
    requested = _requested(script)
    started = time.time()
    rc, out, err = run_remote(cluster.host, script, timeout)
    finished = time.time()
    parsed = parse_frames(out) if rc in (0, 124) else {}
    complete = {k: s for k, s in parsed.items() if s.complete}
    env = _parse_env(complete["env"].body) if "env" in complete else {}
    error = None
    if rc == 124:
        error = f"timeout after {timeout}s"
    elif rc == 255:
        lines = [ln.strip() for ln in err.splitlines() if ln.strip()]
        error = lines[-1] if lines else "ssh failed (rc 255)"
    elif rc != 0:
        error = f"remote exited rc={rc}"
    elif "env" not in complete:
        error = "incomplete output: no env section"
    return PollResult(cluster.name, started, finished, error is None, error, requested,
                      complete, env)


def askpass_available() -> bool:
    """A GUI askpass the USER answers (never a script answering for them)."""
    ap = os.environ.get("SSH_ASKPASS", "")
    if not ap or not os.path.isfile(ap) or not os.access(ap, os.X_OK):
        return False
    return bool(os.environ.get("DISPLAY")) or sys.platform == "darwin"


def open_master_argv(host: str) -> list[str]:
    """Opens a master; may prompt. Only on an explicit, announced user request."""
    return ["ssh", "-fN", "-o", "ControlMaster=yes", host]


def open_master_env(use_askpass: bool) -> dict:
    env = dict(os.environ)
    if use_askpass:
        env["SSH_ASKPASS_REQUIRE"] = "force"
    return env
