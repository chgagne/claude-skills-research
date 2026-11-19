"""Seeded store for TUI tests: the six anonymised fixtures written as polls.

``seed_store(path, now)`` writes every fixture as a successful poll and sets the
cluster modes, so the TUI shows each state at least once:

- narval, rorqual, tamia: active, fresh data, live socket;
- nibi: active but its last poll is 20 min old (stale sections, amber dot);
- vulcan: released (last poll 3 h ago, no socket);
- killarney: down (good poll 1 h ago, then a failed one with an error).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from dracmonlib import collector, store  # noqa: E402
from dracmonlib.config import Cluster, Config  # noqa: E402
from dracmonlib.frame import parse_frames  # noqa: E402
from dracmonlib.ssh import PollResult, _parse_env  # noqa: E402

FIXTURES = HERE / "fixtures"
CLUSTERS = ("narval", "rorqual", "nibi", "tamia", "killarney", "vulcan")
DOWN_ERROR = "Control socket connect(/tmp/ssh-killarney): No such file or directory"

# cluster -> (mode, age of the good poll in seconds, socket live)
PLAN = {
    "narval": ("active", 60, True),
    "rorqual": ("active", 90, True),
    "nibi": ("active", 1200, True),
    "tamia": ("active", 45, True),
    "killarney": ("down", 3600, False),
    "vulcan": ("released", 3 * 3600, False),
}


def fixture_result(cluster: str, started: float) -> PollResult:
    """The fixture as a successful poll that started at ``started``."""
    secs = parse_frames((FIXTURES / f"{cluster}.txt").read_text())
    complete = {k: s for k, s in secs.items() if s.complete}
    requested = [k for k in complete if k in store.SECTION_FIELD]
    env = _parse_env(complete["env"].body)
    return PollResult(cluster, started, started + 3, True, None, requested, complete, env)


def seed_store(path: Path, now: float) -> Config:
    """Write all six fixtures into a fresh store at ``path``; return a Config
    that lists those clusters (host alias = name)."""
    conn = store.open_store(Path(path))
    try:
        for name in CLUSTERS:
            mode, age, live = PLAN[name]
            res = fixture_result(name, now - age - 3)
            store.write_poll(conn, res, collector.parse_poll(res, {}, None))
            if mode == "down":
                t = now - 120
                bad = PollResult(name, t, t + 1, False, DOWN_ERROR, ["env", "queue"])
                store.write_poll(conn, bad, collector.parse_poll(bad, {}, None))
            store.set_cluster_mode(conn, name, mode, now - age)
            store.set_meta(conn, f"live:{name}", "1" if live else "0")
    finally:
        conn.close()
    return Config(clusters=[Cluster(n, n) for n in CLUSTERS])
