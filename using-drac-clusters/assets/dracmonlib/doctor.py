"""``dracmon doctor``: read-only checks of the ssh setup. Prints fixes, edits nothing."""
from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass

from . import ssh


@dataclass
class Finding:
    level: str  # "ok" | "warn" | "error"
    message: str
    fix: str | None = None


def check_host(host: str) -> list[Finding]:
    # No COLLECTOR_OPTS here: -o ControlMaster=no would mask the user's setting.
    # ssh._run strips SSH_ASKPASS/DISPLAY, and -G makes no connection anyway.
    rc, out, err = ssh._run(["ssh", "-G", "-o", "BatchMode=yes", host], None, ssh.CHECK_TIMEOUT)
    if rc != 0:
        msg = (err.strip().splitlines() or [f"rc {rc}"])[-1]
        return [Finding("error", f"{host}: `ssh -G` failed: {msg}")]
    cfg: dict[str, str] = {}
    for line in out.splitlines():
        k, _, v = line.partition(" ")
        cfg.setdefault(k.lower(), v.strip())
    res: list[Finding] = []
    cm = cfg.get("controlmaster", "false").lower()
    if cm in ("auto", "autoask", "yes", "true", "ask"):
        res.append(Finding("ok", f"{host}: ControlMaster {cm}"))
    else:
        res.append(Finding("error", f"{host}: ControlMaster is {cm}; no shared connection",
                           f"add to ~/.ssh/config under `Host {host}`: ControlMaster auto"))
    raw = cfg.get("controlpath", "none")
    path = ssh.control_path(host) if raw not in ("", "none") else None
    if path is None:
        res.append(Finding("error", f"{host}: no ControlPath",
                           f"add to ~/.ssh/config under `Host {host}`: "
                           "ControlPath ~/.ssh/cm/%C"))
    elif path.parent.is_dir():
        res.append(Finding("ok", f"{host}: ControlPath directory {path.parent} exists"))
    else:
        res.append(Finding("error", f"{host}: ControlPath directory {path.parent} is missing",
                           f"mkdir -p {path.parent} && chmod 700 {path.parent}"))
    cp = cfg.get("controlpersist", "no").lower()
    if cp in ("no", "false", "0"):
        res.append(Finding("error", f"{host}: ControlPersist is off; the master dies with its shell",
                           f"add to ~/.ssh/config under `Host {host}`: ControlPersist 4h"))
    else:
        res.append(Finding("ok", f"{host}: ControlPersist {cp}"))
    return res


def run(cfg) -> int:
    findings: list[Finding] = []
    uv = shutil.which("uv")
    findings.append(Finding("ok", f"uv: {uv}") if uv else
                    Finding("error", "uv not found on PATH", "install uv: https://docs.astral.sh/uv/"))
    v = sys.version_info
    findings.append(Finding("ok", f"python {v.major}.{v.minor}") if v >= (3, 11) else
                    Finding("error", f"python {v.major}.{v.minor} is below 3.11",
                            "use a Python >= 3.11 (uv fetches one)"))
    findings.append(Finding("ok", "askpass available (you answer MFA dialogs)")
                    if ssh.askpass_available() else
                    Finding("warn", "no GUI askpass; `open master` will need a terminal",
                            "set SSH_ASKPASS to a GUI helper if you want dialogs"))
    for c in cfg.clusters:
        findings.extend(check_host(c.host))
    mark = {"ok": "ok   ", "warn": "warn ", "error": "ERROR"}
    for f in findings:
        print(f"{mark[f.level]} {f.message}")
        if f.fix:
            print(f"      fix: {f.fix}")
    return 1 if any(f.level == "error" for f in findings) else 0
