"""Parsers: raw section bodies of the remote script -> typed rows (stdlib only).

Field orders follow remote.sh exactly. A malformed line is skipped, never
fatal; each parser exposes ``last_skipped`` (lines skipped by its last call)
for the poll record. Times are converted with the cluster's own UTC offset
(``tz`` from the env section, e.g. ``-0500``).
"""
from __future__ import annotations

import functools
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .gpu import gpu_count

# ---------------------------------------------------------------- helpers

_DURATION = re.compile(r"^(?:(\d+)-)?(?:(\d+):)?(\d+):(\d+)(?:\.\d+)?$")
_MEM = re.compile(r"^(\d+(?:\.\d+)?)([KMGTP]?)[nc]?$")
_POW = {"": 0, "K": 1, "M": 2, "G": 3, "T": 4, "P": 5, "E": 6}
_TZ = re.compile(r"^([+-])(\d\d)(\d\d)$")
_NO_TIME = {"", "Unknown", "N/A", "None"}


def parse_duration(s: str) -> int | None:
    """Seconds from ``[D-]HH:MM:SS``, ``MM:SS`` or ``MM:SS.mmm`` (fraction
    dropped). ``UNLIMITED``, ``INVALID``, empty or anything else -> None."""
    m = _DURATION.match((s or "").strip())
    if not m:
        return None
    d, h, mi, sec = (int(x) if x else 0 for x in m.groups())
    return ((d * 24 + h) * 60 + mi) * 60 + sec


def parse_mem(s: str, default_unit: str = "M") -> int | None:
    """Bytes from a Slurm memory string: ``200G``, ``1000000M``, ``209713624K``,
    ``937.50G``, old-style ``4000Mc``/``8Gn``. Units are binary (K = 1024).
    A bare number is in ``default_unit`` (Slurm's MB); ``0`` is 0."""
    m = _MEM.match((s or "").strip())
    if not m:
        return None
    unit = m.group(2) or default_unit
    return int(float(m.group(1)) * 1024 ** _POW[unit])


def parse_slurm_time(s: str, tz: str) -> float | None:
    """Epoch seconds of a naive Slurm time ``YYYY-MM-DDTHH:MM:SS`` read at UTC
    offset ``tz`` (``-0500``). ``Unknown``/``N/A``/``None``/empty, an
    unparseable time or an unparseable offset -> None."""
    s = (s or "").strip()
    m = _TZ.match((tz or "").strip())
    if s in _NO_TIME or not m:
        return None
    sign = -1 if m.group(1) == "-" else 1
    off = timezone(sign * timedelta(hours=int(m.group(2)), minutes=int(m.group(3))))
    try:
        d = datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None
    return d.replace(tzinfo=off).timestamp()


def parse_env(body: str) -> dict[str, str]:
    env = {}
    for line in body.splitlines():
        k, sep, v = line.partition("=")
        if sep and k:
            env[k] = v
    return env


def count_tasks(spec: str) -> int:
    """Number of tasks in an array spec ``0-99%10``, ``1,3,5-7``, ``0-10:2``, ``5``."""
    total = 0
    for part in spec.split("%", 1)[0].split(","):
        part = part.strip()
        if not part:
            continue
        rng, _, step = part.partition(":")
        a, dash, b = rng.partition("-")
        try:
            if dash:
                total += len(range(int(a), int(b) + 1, int(step) if step else 1))
            else:
                int(a)
                total += 1
        except ValueError:
            continue  # a bad part is skipped, the rest still counts
    return max(total, 1)


def _fields(line: str, n: int, name_idx: int) -> list[str] | None:
    """Split a ``|`` line into n fields. Extra ``|`` are assumed to belong to
    the free-text job name at ``name_idx``; fewer fields -> None."""
    p = line.split("|")
    if len(p) < n:
        return None
    extra = len(p) - n
    if extra:
        p = p[:name_idx] + ["|".join(p[name_idx:name_idx + extra + 1])] + p[name_idx + extra + 1:]
    return p


def _counted(fn):
    """Parser body returns (rows, skipped); the wrapper returns rows and keeps
    the count in ``wrapper.last_skipped``."""
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        rows, skipped = fn(*a, **kw)
        wrapper.last_skipped = skipped
        return rows
    wrapper.last_skipped = 0
    return wrapper


# ---------------------------------------------------------------- rows

@dataclass
class QueueRow:
    cluster: str
    job_id: str
    array_job_id: str | None
    array_tasks: str | None
    name: str
    partition: str
    state: str
    elapsed_s: int | None
    limit_s: int | None
    start_est: float | None
    cpus: int
    mem_bytes: int | None
    gpus: float | None  # per node (squeue %b); None when %b is N/A
    node_or_reason: str
    account: str
    submit: float | None
    task_count: int


@dataclass
class FinishedJob:
    cluster: str
    job_id: str
    name: str
    account: str
    partition: str
    state: str
    exit_code: str
    elapsed_s: int | None
    limit_s: int | None
    submit: float | None
    start: float | None
    end: float | None
    nodes: str | None
    cpus: int
    gpus: float
    req_mem_bytes: int | None
    max_rss_bytes: int | None
    total_cpu_s: int | None


@dataclass
class ShareRow:
    cluster: str
    account: str
    user: str | None
    raw_usage: int
    effective_usage: float
    level_fs: float | None
    fairshare: float | None


@dataclass
class UsageRow:
    cluster: str
    job_id: str
    user: str
    account: str
    state: str
    start: float | None
    elapsed_s: int | None
    cpus: int
    gpus: float


@dataclass
class DiskRow:
    cluster: str
    filesystem: str
    scope: str
    used_bytes: int
    quota_bytes: int
    files: int
    files_quota: int
    owner: str = ""  # the user/project/group name in "(project def-xyz)"


@dataclass
class PartitionRow:
    cluster: str
    partition: str
    avail: str
    limit_s: int | None
    nodes: int
    state: str
    gres: str
    is_default: bool = False  # sinfo marks the default partition with "*"


# ---------------------------------------------------------------- parsers

_NO_GRES = ("N/A", "(null)")  # %b unknown: QueueRow.gpus None, not 0
_ARRAY_IN_ID = re.compile(r"^(\d+)_\[?([^\]]+)\]?$")


@_counted
def parse_squeue(body: str, cluster: str, tz: str, shards: dict[str, int]):
    """squeue -o '%i|%A|%F|%K|%j|%P|%T|%M|%l|%S|%C|%m|%b|%R|%a|%V'.
    A pending array range (``123_[0-99%10]``) is one row with task_count 100."""
    rows, skipped = [], 0
    for line in body.splitlines():
        if not line.strip():
            continue
        p = _fields(line, 16, 4)
        if p is None:
            skipped += 1
            continue
        jid, _a, f_arr, k_task, name, part, state, el, lim, start, cpus, mem, gres, reason, acct, sub = p
        try:
            ncpu = int(cpus)
        except ValueError:
            skipped += 1
            continue
        tasks = k_task if k_task not in ("", "N/A") else None
        arr_job = f_arr if tasks else None
        if tasks is None:
            m = _ARRAY_IN_ID.match(jid)
            if m:
                arr_job, tasks = m.group(1), m.group(2)
        rows.append(QueueRow(
            cluster, jid, arr_job, tasks, name, part, state, parse_duration(el),
            parse_duration(lim), parse_slurm_time(start, tz), ncpu, parse_mem(mem),
            None if gres.strip() in _NO_GRES else gpu_count(gres, shards),
            reason, acct, parse_slurm_time(sub, tz),
            count_tasks(tasks) if tasks else 1))
    return rows, skipped


def _steps(steps_body: str) -> tuple[dict[str, int], dict[str, int], int]:
    """From ``JobID|MaxRSS[|TotalCPU]`` lines (older captures have two
    columns): {job id: max MaxRSS over its steps}, {job id: sum of TotalCPU
    over its steps}, skipped lines. The allocation row itself (no ``.``)
    is not a step and is ignored."""
    rss: dict[str, int] = {}
    cpu: dict[str, int] = {}
    skipped = 0
    for line in steps_body.splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) not in (2, 3):
            skipped += 1
            continue
        job, dot, _step = parts[0].partition(".")
        if not dot:
            continue
        b = parse_mem(parts[1]) if parts[1].strip() else None
        if b is not None and b > rss.get(job, -1):
            rss[job] = b
        if len(parts) == 3 and parts[2].strip():
            s = parse_duration(parts[2])
            if s is not None:
                cpu[job] = cpu.get(job, 0) + s
    return rss, cpu, skipped


def _total_cpu(alloc: int | None, steps: int | None) -> int | None:
    return steps if not alloc and steps else alloc


@_counted
def parse_sacct(body: str, steps_body: str, cluster: str, tz: str, shards: dict[str, int]):
    """sacct -X -o JobID,JobName,Account,Partition,State,ExitCode,Elapsed,Timelimit,
    Submit,Start,End,NodeList,AllocTRES,ReqMem,TotalCPU,NCPUS, plus the steps
    section (JobID,MaxRSS,TotalCPU) for max_rss_bytes, and for total_cpu_s
    when the allocation row reports 0 (as ``sacct -X`` does on DRAC clusters):
    then it is the sum over the job's steps (batch, extern, numbered). Every
    row is kept, PENDING ones included (start/end None, nodes None for
    ``None assigned``)."""
    rss, step_cpu, skipped = _steps(steps_body)
    rows = []
    for line in body.splitlines():
        if not line.strip():
            continue
        p = _fields(line, 16, 1)
        if p is None:
            skipped += 1
            continue
        (jid, name, acct, part, state, exitc, el, lim, sub, start, end, nodes, tres,
         reqmem, totcpu, ncpus) = p
        try:
            ncpu = int(ncpus)
        except ValueError:
            skipped += 1
            continue
        rows.append(FinishedJob(
            cluster, jid, name, acct, part, state, exitc, parse_duration(el),
            parse_duration(lim), parse_slurm_time(sub, tz), parse_slurm_time(start, tz),
            parse_slurm_time(end, tz), None if nodes in ("", "None assigned") else nodes,
            ncpu, gpu_count(tres, shards), parse_mem(reqmem), rss.get(jid),
            _total_cpu(parse_duration(totcpu), step_cpu.get(jid))))
    return rows, skipped


def _opt_float(s: str) -> float | None:
    s = s.strip()
    return float(s) if s else None  # "inf" -> math.inf (LevelFS with no usage)


@_counted
def parse_sshare(body: str, cluster: str):
    """sshare -P -n -o Account,User,RawUsage,EffectvUsage,LevelFS,FairShare.
    Account lines have no user and no FairShare; user lines start with a space."""
    rows, skipped = [], 0
    for line in body.splitlines():
        if not line.strip():
            continue
        p = line.split("|")
        if len(p) != 6:
            skipped += 1
            continue
        try:
            rows.append(ShareRow(cluster, p[0].strip(), p[1].strip() or None, int(p[2]),
                                 float(p[3]), _opt_float(p[4]), _opt_float(p[5])))
        except ValueError:
            skipped += 1
    return rows, skipped


_CPU = re.compile(r"(?:^|,)cpu=(\d+)")


@_counted
def parse_usage(body: str, cluster: str, tz: str, shards: dict[str, int]):
    """sacct -X -a -o JobID,User,Account,State,Start,Elapsed,AllocTRES (the
    group's jobs). Pending or never-started jobs have start None, 0 cpus/gpus."""
    rows, skipped = [], 0
    for line in body.splitlines():
        if not line.strip():
            continue
        p = line.split("|")
        if len(p) != 7:
            skipped += 1
            continue
        jid, user, acct, state, start, el, tres = p
        m = _CPU.search(tres)
        rows.append(UsageRow(cluster, jid, user, acct, state, parse_slurm_time(start, tz),
                             parse_duration(el), int(m.group(1)) if m else 0,
                             gpu_count(tres, shards)))
    return rows, skipped


_DISK = re.compile(
    r"^\s*(/\S+)\s+\(([a-z]+)\s+([^)\s]+)\)\s+"
    r"([\d.]+)\s*([KMGTPE]?i?B)\s*/\s*([\d.]+)\s*([KMGTPE]?i?B)\s+"
    r"(?:->\s*)?([\d.]+)\s*([KMGT]?)\s*/\s*([\d.]+)\s*([KMGT]?)\s*$")
_FILES = {"": 1, "K": 10**3, "M": 10**6, "G": 10**9, "T": 10**12}


def _disk_bytes(num: str, unit: str) -> int:
    prefix = unit[0] if unit[0] != "B" else ""
    base = 1024 if "i" in unit else 1000  # MB/GB decimal (Narval, Rorqual), MiB/GiB binary
    return int(float(num) * base ** _POW[prefix])


@_counted
def parse_disk(body: str, cluster: str):
    """diskusage_report rows such as ``/home (user u)  124MiB/  50GiB   7670 / 500K``.
    Decimal (KB..TB) and binary (KiB..TiB) units, ``4096  B``, file counts with
    K/M/G (decimal), a ``->`` near-quota marker (TamIA). Header, explanatory
    text and ``diskusage_explorer`` lines are not data; a ``/``-led line that
    does not match is skipped and counted."""
    rows, skipped = [], 0
    for line in body.splitlines():
        m = _DISK.match(line)
        if not m:
            if line.strip().startswith("/"):
                skipped += 1
            continue
        fs, scope, owner, un, uu, qn, qu, fn, fu, fqn, fqu = m.groups()
        try:
            rows.append(DiskRow(cluster, fs, scope, _disk_bytes(un, uu), _disk_bytes(qn, qu),
                                int(float(fn) * _FILES[fu]), int(float(fqn) * _FILES[fqu]),
                                owner))
        except (ValueError, KeyError):
            skipped += 1
    return rows, skipped


_SOCKETS = re.compile(r"\([^)]*\)")


@_counted
def parse_sinfo(body: str, cluster: str):
    """sinfo -h -o '%P|%a|%l|%D|%T|%G'. The default partition's trailing ``*``
    becomes is_default; ``(S:0-1)`` socket suffixes are dropped from gres and
    ``(null)`` becomes ''. States keep their suffixes (``mixed-``, ``drained*``)."""
    rows, skipped = [], 0
    for line in body.splitlines():
        if not line.strip():
            continue
        p = line.split("|")
        if len(p) != 6:
            skipped += 1
            continue
        part, avail, lim, nodes, state, gres = p
        try:
            n = int(nodes)
        except ValueError:
            skipped += 1
            continue
        gres = "" if gres.strip() == "(null)" else _SOCKETS.sub("", gres).strip()
        rows.append(PartitionRow(cluster, part.rstrip("*"), avail, parse_duration(lim), n,
                                 state, gres, part.endswith("*")))
    return rows, skipped
