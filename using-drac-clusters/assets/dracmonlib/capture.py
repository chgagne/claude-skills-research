"""Raw capture of a cluster's remote output as an anonymised test fixture."""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

from .frame import Section, parse_frames, render_frames

ALL_SECTIONS = ["accounts", "queue", "accounting", "steps", "fairshare", "usage",
                "disk", "partitions", "cells", "globs"]

ACCOUNT_RE = re.compile(r"\b(def|aip|rrg|rpp|ctb)-([A-Za-z0-9]+)((?:_[a-z]+)?)")
MARKER = "@@dracmon "
CANCELLED_RE = re.compile(r"CANCELLED by \d+")


def _fields(body: str, idx: int, sep: str = "|") -> list[str]:
    out = []
    for line in body.splitlines():
        parts = line.split(sep)
        if len(parts) > idx and parts[idx]:
            out.append(parts[idx])
    return out


class _Namer:
    def __init__(self, prefix: str):
        self.prefix, self.map = prefix, {}

    def __call__(self, name: str) -> str:
        if name not in self.map:
            self.map[name] = f"{self.prefix}{len(self.map)}"
        return self.map[name]


def anonymise(text: str, env: dict[str, str], accounts: list[str]) -> str:
    """Remove usernames, accounts, paths, job, campaign and cell names from a
    framed capture. Numbers, states, nodes, partitions and gres are kept."""
    secs = parse_frames(text)

    users = _Namer("user")
    if env.get("user"):
        users(env["user"])
    for name, idx in (("usage", 1), ("fairshare", 1)):
        if name in secs:
            for u in _fields(secs[name].body, idx):
                users(u)

    groups = _Namer("group")
    for a in accounts:
        m = ACCOUNT_RE.fullmatch(a)
        if m:
            groups(m.group(2))

    jobs = _Namer("job")
    camps = _Namer("camp")
    cells = _Namer("cell")
    for name, idx in (("queue", 4), ("accounting", 1)):
        if name in secs:
            for j in _fields(secs[name].body, idx):
                jobs(j)
    if "cells" in secs:
        for line in secs["cells"].body.splitlines():
            if line.startswith("#file "):
                parts = line.split(" ", 3)
                if len(parts) == 4:
                    camps(parts[3].split("/")[0])
            else:
                p = line.split("\t")
                if len(p) >= 4 and p[3]:
                    cells(p[3])
    if "globs" in secs:
        for line in secs["globs"].body.splitlines():
            if line.startswith("#glob "):
                camps(line.split(" ")[1])

    def account(m: re.Match) -> str:
        return f"{m.group(1)}-{groups(m.group(2))}{m.group(3)}"

    user_alt = "|".join(re.escape(u) for u in sorted(users.map, key=len, reverse=True))
    user_re = re.compile(rf"(?<![A-Za-z0-9])({user_alt})(?![A-Za-z0-9])") if user_alt else None
    path_re = (re.compile(rf"/(home|scratch)/(?:[A-Za-z0-9]/)?({user_alt})(?![A-Za-z0-9])")
               if user_alt else None)
    scratch = env.get("scratch", "")

    def line_fields(section: str, line: str) -> str:
        if section == "queue":
            p = line.split("|")
            if len(p) > 4:
                p[4] = jobs(p[4])
            return "|".join(p)
        if section == "accounting":
            p = line.split("|")
            if len(p) > 1:
                p[1] = jobs(p[1])
            return "|".join(p)
        if section == "cells":
            if line.startswith("#file "):
                parts = line.split(" ", 3)  # #file <size> <end> <relpath>
                if len(parts) < 4:
                    return line
                head, sep, tail = parts[3].partition("/")
                return f"#file {parts[1]} {parts[2]} {camps(head)}{sep}{tail}"
            p = line.split("\t")
            if len(p) >= 4 and p[3]:
                p[3] = cells(p[3])
            if len(p) >= 5 and p[2] == "fail" and p[4]:
                p[4] = "reason"
            return "\t".join(p)
        if section == "globs" and line.startswith("#glob "):
            p = line.split(" ")
            if len(p) >= 3:
                p[1] = camps(p[1])
            return " ".join(p)
        return line

    out = []
    section = ""
    for line in text.splitlines():
        if line.startswith(MARKER):
            parts = line.split(" ")
            if len(parts) >= 3 and parts[1] == "begin":
                section = parts[2]
            out.append(line)
            continue
        line = line_fields(section, line)
        if scratch:
            line = line.replace(scratch, "/scratch/user0")
        line = ACCOUNT_RE.sub(account, line)
        if path_re:
            line = path_re.sub(lambda m: f"/{m.group(1)}/{users(m.group(2))}", line)
        line = re.sub(r"/project/\d+", "/project/000000", line)
        line = CANCELLED_RE.sub("CANCELLED by 0", line)  # numeric uid of the canceller
        if user_re:
            line = user_re.sub(lambda m: users(m.group(1)), line)
        out.append(line)
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def capture(clusters, out: Path, timeout: int = 120) -> list[Path]:
    """Poll every section of each cluster and save out/<cluster>.txt anonymised.

    A cluster without a live ssh master socket is refused (reason printed);
    nothing here ever prompts for MFA. Cell logs are fetched from offset 0 and
    never cleaned up remotely (huge retention)."""
    from . import ssh

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    since = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 2 * 86400))
    for cl in clusters:
        if not ssh.socket_live(cl.host):
            print(f"{cl.name}: no live ssh socket, skipped (open one first)", file=sys.stderr)
            continue
        res = ssh.poll_cluster(cl, list(ALL_SECTIONS), since=since, offsets={}, globs=[],
                               retention_days=36500, timeout=timeout)
        if not res.ok:
            print(f"{cl.name}: poll failed: {res.error}", file=sys.stderr)
            continue
        secs = dict(res.sections)
        if "env" not in secs:
            body = "".join(f"{k}={v}\n" for k, v in res.env.items())
            secs = {"env": Section("env", 0, body, True), **secs}
        text = render_frames(secs.values())
        accts = [a for a in secs["accounts"].body.splitlines() if a] if "accounts" in secs else []
        path = out / f"{cl.name}.txt"
        path.write_text(anonymise(text, dict(res.env), accts))
        written.append(path)
    return written
