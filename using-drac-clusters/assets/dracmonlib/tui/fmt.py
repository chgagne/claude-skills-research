"""Display formatters shared by the views (pure, stdlib only)."""
from __future__ import annotations

NONE = "–"
FULL, EMPTY = "▓", "░"
WARN_PCT, CRIT_PCT = 80, 95


def duration(s) -> str:
    """Slurm-style elapsed time: ``1:04:53``, ``2-03:00:00``."""
    if s is None or s < 0:
        return NONE
    s = int(s)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{d}-{h:02d}:{m:02d}:{s:02d}" if d else f"{h}:{m:02d}:{s:02d}"


def hm(s) -> str:
    """Short remaining time: ``45m``, ``3h10``, ``2d03h``."""
    if s is None or s < 0:
        return NONE
    m = int(round(s / 60))
    d, m = divmod(m, 1440)
    h, m = divmod(m, 60)
    if d:
        return f"{d}d{h:02d}h"
    return f"{h}h{m:02d}" if h else f"{m}m"


def bytes_(n) -> str:
    """Binary units: ``16.5 GiB``, ``200 GiB`` (no decimal from 100 up);
    bytes as an integer."""
    if n is None:
        return NONE
    n = float(n)
    if abs(n) < 1024:
        return f"{int(n)} B"
    for unit in ("KiB", "MiB", "GiB", "TiB", "PiB"):
        n /= 1024
        if abs(n) < 1024 or unit == "PiB":
            return f"{n:.0f} {unit}" if abs(n) >= 100 else f"{n:.1f} {unit}"
    return NONE  # unreachable


def percent(a, b) -> float | None:
    if a is None or not b:
        return None
    return 100.0 * a / b


def pct(a, b) -> str:
    p = percent(a, b)
    return NONE if p is None else f"{round(p)} %"


def bar(done, total, width: int) -> str:
    """``width`` cells, filled in proportion (rounded down, never past full)."""
    if width <= 0:
        return ""
    n = 0 if not total else int(width * min(max(done, 0), total) / total)
    return FULL * n + EMPTY * (width - n)


def age(ts, now: float) -> str:
    if ts is None:
        return "never"
    s = max(0, int(now - ts))
    if s < 60:
        return f"{s} s"
    if s < 90 * 60:
        return f"{s // 60} min"
    if s < 48 * 3600:
        return f"{s // 3600} h"
    return f"{s // 86400} d"


def level(p) -> str:
    if p is None:
        return "ok"
    if p >= CRIT_PCT:
        return "crit"
    if p >= WARN_PCT:
        return "warn"
    return "ok"


def hours(h) -> str:
    """CPU/GPU-hours: one decimal below 1000, grouped integers above."""
    if h is None:
        return NONE
    if h == 0:
        return "0"
    return f"{h:.1f}" if abs(h) < 1000 else f"{h:,.0f}"


def num(x) -> str:
    """LevelFS / fairshare: three significant digits, ``∞`` for infinity."""
    if x is None:
        return NONE
    if x == float("inf"):
        return "∞"
    if x >= 100:
        return f"{x:.0f}"
    return f"{x:.3g}"
