import contextlib
import io
import os
import signal
import sys
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import dracmon  # noqa: E402
from dracmonlib import collector, store  # noqa: E402
from dracmonlib.config import Cluster, Config, GlobCampaign  # noqa: E402
from dracmonlib.frame import Section  # noqa: E402
from dracmonlib.ssh import PollResult  # noqa: E402
from dracmonlib.store import ParsedPoll, PollLock  # noqa: E402
from fakessh import FakeSshCase  # noqa: E402

H = 3600.0
DAY = 86400.0
NAME = "testcluster"
SQUEUE = "101|101|101|0|exp|gpu|RUNNING|0:10|1:00:00|N/A|4|8G|{gres}|nc101|acct-x|2026-11-17T10:00:00\n"


def sec(name, body="", rc=0, complete=True):
    return Section(name, rc, body, complete)


def result(sections, ok=True, tz="-0500", started=1000.0, cluster=NAME, error=None):
    secs = {"env": sec("env", f"user=jdoe\ntz={tz}\n")}
    secs.update({s.name: s for s in sections})
    return PollResult(cluster, started, started + 2, ok, None if ok else (error or "boom"),
                      list(secs), secs if ok else {}, {"tz": tz} if ok else {})


def local(epoch, tz_hours):
    return datetime.fromtimestamp(epoch, timezone(timedelta(hours=tz_hours))).strftime(
        "%Y-%m-%dT%H:%M:%S")


class ClassifyTests(unittest.TestCase):
    def test_classify_table(self):
        now, idle = 100000.0, 7200
        recent, old = now - 100, now - 10000
        rows = [
            (True, True, None, "active"),
            (True, False, recent, "active"),
            (True, False, old, "released"),
            (True, False, None, "released"),
            (False, True, None, "down"),
            (False, True, old, "down"),
            (False, False, recent, "down"),
            (False, False, old, "released"),
            (False, False, None, "disconnected"),
        ]
        for live, active, last, want in rows:
            with self.subTest(live=live, active=active, last=last):
                self.assertEqual(collector.classify(live, active, last, now, idle), want)

    def test_due_sections(self):
        cad = dict(Config().cadence)
        now = 100000.0
        none = {s: None for s in collector.SECTIONS}
        allsec = collector.due_sections("active", none, cad, now, False)
        self.assertEqual(allsec[0], "env")
        self.assertEqual(set(allsec), set(collector.SECTIONS) | {"env"})
        fresh = {s: now - 60 for s in collector.SECTIONS}
        self.assertEqual(collector.due_sections("active", fresh, cad, now, False), [])
        stale_q = dict(fresh, queue=now - 301, usage=now - 1000)
        self.assertEqual(collector.due_sections("active", stale_q, cad, now, False),
                         ["env", "queue"])
        # cells and globs follow the cells cadence
        stale_c = dict(fresh, cells=now - 301, globs=now - 301)
        self.assertEqual(collector.due_sections("active", stale_c, cad, now, False),
                         ["env", "cells", "globs"])
        self.assertEqual(collector.due_sections("released", none, cad, now, False), [])
        self.assertEqual(collector.due_sections("released", none, cad, now, True),
                         ["env", "queue"])
        for mode in ("down", "disconnected"):
            self.assertEqual(collector.due_sections(mode, none, cad, now, True), [])


class ParsePollTests(unittest.TestCase):
    def test_shards_from_same_poll(self):
        res = result([sec("partitions", "gpu*|up|1-00:00:00|2|idle|gpu:l40s:4,shard:l40s:16\n"),
                      sec("queue", SQUEUE.format(gres="gres/shard:l40s:2"))])
        p = collector.parse_poll(res, {}, {"l40s": 8})
        self.assertEqual(p.queue[0].gpus, 0.5)  # 2 shards of 4 per card
        self.assertEqual(len(p.partitions), 1)
        self.assertEqual(p.env["tz"], "-0500")

    def test_shards_hint_when_no_partitions(self):
        res = result([sec("queue", SQUEUE.format(gres="gres/shard:l40s:2"))])
        p = collector.parse_poll(res, {}, {"l40s": 8})
        self.assertEqual(p.queue[0].gpus, 0.25)
        self.assertIsNone(p.partitions)

    def test_failed_section_not_stored(self):
        res = result([sec("queue", "", rc=124), sec("disk", "", rc=127),
                      sec("accounting", "", rc=0), sec("steps", "", rc=1)])
        p = collector.parse_poll(res, {}, None)
        self.assertIsNone(p.queue)  # an empty body from a failed squeue is never "no jobs"
        self.assertIsNone(p.disk)
        self.assertIsNone(p.accounting)  # MaxRSS would be lost without steps

    def test_failed_poll_parses_nothing(self):
        p = collector.parse_poll(result([], ok=False), {}, None)
        self.assertEqual(p, ParsedPoll())

    def test_globs_and_cells(self):
        res = result([sec("globs", "#glob sweep 7\n#glob bad x\n"),
                      sec("cells", "#file 20 camp/a.log\n1000\tj1\tstart\tc1\t\n")])
        p = collector.parse_poll(res, {"camp/a.log": 0}, None)
        self.assertEqual(p.globs, [("sweep", 7)])
        self.assertEqual(len(p.cells), 1)
        self.assertEqual(p.cells[0].events[0].cell, "c1")
        self.assertEqual(p.skipped.get("globs"), 1)


class WindowTests(unittest.TestCase):
    """since and usage window, with the ssh layer mocked."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.conn = store.open_store(Path(self.tmp.name) / "dracmon.sqlite")
        self.addCleanup(self.conn.close)
        self.cfg = Config(clusters=[Cluster(NAME, "testhost", pinned=True)])
        self.now = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc).timestamp()
        self.calls = []

    def seed(self, sections, started, tz="-0800"):
        res = result([sec(s) for s in sections], tz=tz, started=started)
        store.write_poll(self.conn, res, collector.parse_poll(res, {}, None))

    def fake_poll(self, ok=True):
        def poll(cluster, sections, **kw):
            self.calls.append(kw)
            return result([sec("usage", "")], ok=ok, tz="-0800", started=self.now)
        return poll

    def cycle(self, ok=True):
        with mock.patch.object(collector.ssh, "socket_live", return_value=True), \
             mock.patch.object(collector.ssh, "poll_cluster", side_effect=self.fake_poll(ok)):
            collector.run_cycle(self.cfg, self.conn, self.now)
        return self.calls[-1]

    def test_since_uses_cluster_tz(self):
        self.seed(["accounting", "steps"], self.now - 2000)
        kw = self.cycle()
        # last accounting start - 1 h, in Pacific time: 12:00Z - 2000 s - 1 h
        self.assertEqual(kw["since"], local(self.now - 2000 - H, -8))
        self.assertEqual(kw["since"], "2026-11-17T02:26:40")

    def test_since_defaults_to_one_day_in_cluster_tz(self):
        self.seed(["queue"], self.now - 2000)  # env (tz) known, no accounting yet
        kw = self.cycle()
        self.assertEqual(kw["since"], "2026-11-16T04:00:00")

    def test_usage_first_poll_normal_window_starts_backfill(self):
        self.seed(["queue"], self.now - 2000)
        kw = self.cycle()
        self.assertEqual(kw["usage_window"], (local(self.now - 7 * DAY, -8), local(self.now, -8)))
        self.assertEqual(float(store.get_meta(self.conn, f"usage_backfill:{NAME}")),
                         self.now - 7 * DAY)

    def test_usage_backfill_window_moves_frontier(self):
        self.seed(["queue"], self.now - 2000)
        frontier = self.now - 7 * DAY
        store.set_meta(self.conn, f"usage_backfill:{NAME}", str(frontier))
        kw = self.cycle()
        self.assertEqual(kw["usage_window"], (local(frontier - 7 * DAY, -8), local(frontier, -8)))
        self.assertEqual(float(store.get_meta(self.conn, f"usage_backfill:{NAME}")),
                         frontier - 7 * DAY)

    def test_usage_backfill_frontier_kept_on_failure(self):
        self.seed(["queue"], self.now - 2000)
        frontier = self.now - 7 * DAY
        store.set_meta(self.conn, f"usage_backfill:{NAME}", str(frontier))
        self.cycle(ok=False)
        self.assertEqual(float(store.get_meta(self.conn, f"usage_backfill:{NAME}")), frontier)

    def test_usage_normal_window_after_backfill(self):
        self.seed(["queue"], self.now - 2000)
        store.set_meta(self.conn, f"usage_backfill:{NAME}", str(self.now - 29 * DAY))
        store.set_meta(self.conn, f"usage_recent:{NAME}", str(self.now - 2 * H))
        kw = self.cycle()
        self.assertEqual(kw["usage_window"], (local(self.now - 3 * H, -8), local(self.now, -8)))
        self.assertEqual(float(store.get_meta(self.conn, f"usage_recent:{NAME}")), self.now)

    def test_usage_window_unknown_tz_is_remote_default(self):
        kw = self.cycle()  # first poll ever: no env stored yet
        self.assertIsNone(kw["usage_window"])
        self.assertIsNone(kw["since"])


class CollectorTests(FakeSshCase):
    def setUp(self):
        super().setUp()
        self.state = self.tmp / "state"
        self.state.mkdir()
        self.conn = store.open_store(self.state / "dracmon.sqlite")
        self.addCleanup(self.conn.close)
        self.cfg = Config(clusters=[Cluster(NAME, "testhost")])
        self.t0 = time.time()

    def pin(self):
        self.cfg.clusters[0].pinned = True

    def cycle(self, dt=0.0, force=frozenset()):
        return collector.run_cycle(self.cfg, self.conn, self.t0 + dt, force)

    def cluster_mode(self):
        return store.cluster_status(self.conn)[NAME].mode

    def calls(self, prog):
        if not self.log.exists():
            return 0
        return sum(1 for ln in self.log.read_text().splitlines() if ln.startswith(prog + " "))

    def remote_runs(self):
        return [a for a in self.argvs() if "bash -l -s" in a]

    def released(self, checked_ago):
        store.set_cluster_mode(self.conn, NAME, "released", self.t0 - 3 * H)
        store.set_meta(self.conn, f"released_check:{NAME}", str(self.t0 - checked_ago))
        store.set_meta(self.conn, f"live:{NAME}", "1")

    def test_released_sends_nothing(self):
        self.make_socket()
        self.released(checked_ago=60)
        self.assertEqual(self.cycle(), [])
        self.assertEqual(self.remote_runs(), [])
        self.assertEqual(self.calls("squeue"), 0)
        self.assertEqual(self.cluster_mode(), "released")

    def test_released_light_check_hourly(self):
        os.environ["FAKE_SQUEUE_EMPTY"] = "1"
        self.make_socket()
        self.released(checked_ago=3601)
        res = self.cycle()
        self.assertEqual([r.requested for r in res], [["env", "queue"]])
        self.assertEqual(self.calls("squeue"), 1)
        self.assertEqual(self.calls("sacct"), 0)
        self.assertEqual(self.cluster_mode(), "released")
        self.cycle(60)
        self.assertEqual(self.calls("squeue"), 1)
        self.cycle(3600)
        self.assertEqual(self.calls("squeue"), 2)

    def test_socket_coming_back_triggers_light_check(self):
        os.environ["FAKE_SQUEUE_EMPTY"] = "1"
        self.released(checked_ago=60)
        store.set_meta(self.conn, f"live:{NAME}", "0")
        self.make_socket()  # the user ran `ssh <cluster>`
        self.cycle()
        self.assertEqual(self.calls("squeue"), 1)

    def test_down_keeps_last_queue(self):
        self.make_socket()
        self.cycle()  # first contact: light check finds a job
        self.assertEqual([r.job_id for r in store.queue(self.conn)], ["101"])
        self.assertEqual(self.cluster_mode(), "active")
        self.set_mode("failrun")  # the master answers -O check, the run fails
        res = self.cycle(400)
        self.assertEqual(len(res), 1)
        self.assertFalse(res[0].ok)
        self.assertEqual([r.job_id for r in store.queue(self.conn)], ["101"])
        self.assertEqual(self.cluster_mode(), "down")
        self.socket.unlink()  # socket gone: no poll at all, still down with its data
        n = len(self.remote_runs())
        self.assertEqual(self.cycle(800), [])
        self.assertEqual(len(self.remote_runs()), n)
        self.assertEqual(self.cluster_mode(), "down")
        self.assertEqual([r.job_id for r in store.queue(self.conn)], ["101"])

    def test_failed_poll_stays_down_until_success(self):
        # times follow the wall clock: fake-ssh polls record real finished times
        self.pin()
        self.make_socket()
        self.set_mode("failrun")  # -O check answers, every remote run fails
        now = time.time()
        res = collector.run_cycle(self.cfg, self.conn, now)
        self.assertFalse(res[0].ok)
        self.assertEqual(self.cluster_mode(), "down")
        # next tick, socket still live, nothing due yet: must not flip to active
        self.assertEqual(collector.run_cycle(self.cfg, self.conn, time.time() + 30), [])
        self.assertEqual(self.cluster_mode(), "down")
        self.set_mode("ok")
        res = collector.run_cycle(self.cfg, self.conn, time.time() + 400)  # queue due again
        self.assertTrue(res[0].ok, res[0].error)
        self.assertEqual(self.cluster_mode(), "active")

    def test_cadence_respected(self):
        self.pin()
        self.make_socket()
        first = self.cycle()
        self.assertTrue(first[0].ok, first[0].error)
        self.assertEqual(self.calls("squeue"), 1)
        self.assertEqual(self.cycle(60), [])
        self.assertEqual(self.calls("squeue"), 1)
        self.cycle(400)
        self.assertEqual(self.calls("squeue"), 2)

    def test_not_live_never_polled_even_forced(self):
        self.pin()
        self.assertEqual(self.cycle(force={NAME}), [])
        self.assertEqual(self.connecting_argvs(), [])
        self.assertEqual(self.cluster_mode(), "down")

    def test_refresh_file_forces(self):
        self.pin()
        self.make_socket()
        self.assertEqual(collector.collect(self.cfg, True, state=self.state,
                                           now=lambda: self.t0), 0)
        self.assertEqual(self.calls("squeue"), 1)
        self.assertEqual(collector.collect(self.cfg, True, state=self.state,
                                           now=lambda: self.t0 + 60), 0)
        self.assertEqual(self.calls("squeue"), 1)
        collector.request_refresh(self.state, None)
        self.assertEqual((self.state / "refresh").read_text().strip(), "*")
        collector.collect(self.cfg, True, state=self.state, now=lambda: self.t0 + 90)
        self.assertEqual(self.calls("squeue"), 2)
        self.assertFalse((self.state / "refresh").exists())
        collector.request_refresh(self.state, {"other"})
        collector.collect(self.cfg, True, state=self.state, now=lambda: self.t0 + 120)
        self.assertEqual(self.calls("squeue"), 2)  # another cluster: not forced
        log = (self.state / "collector.log").read_text()
        self.assertIn(NAME, log)
        self.assertEqual(sum(1 for ln in log.splitlines() if " poll " in ln), 2)

    def test_request_refresh_merges(self):
        collector.request_refresh(self.state, {"a"})
        collector.request_refresh(self.state, {"b"})
        self.assertEqual(collector.take_refresh(self.state, ["a", "b", "c"]), {"a", "b"})
        self.assertEqual(collector.take_refresh(self.state, ["a"]), set())
        collector.request_refresh(self.state, None)
        self.assertEqual(collector.take_refresh(self.state, ["a", "b"]), {"a", "b"})

    def test_second_collector_exits_1(self):
        held = PollLock(self.state)
        self.assertTrue(held.try_acquire())
        self.addCleanup(held.release)
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(err):
            rc = collector.collect(self.cfg, True, state=self.state)
        self.assertEqual(rc, 1)
        self.assertIn(f"another dracmon poller is running (pid {os.getpid()})", err.getvalue())
        self.assertEqual(self.argvs(), [])

    def test_campaign_keeps_cluster_active(self):
        os.environ["FAKE_SQUEUE_EMPTY"] = "1"
        ts = self.t0 - 600
        body = f"#file 40 camp/a.log\n{ts:.0f}\tj9\tstart\tc1\t\n"
        res = result([sec("cells", body)], started=self.t0 - 500)
        store.write_poll(self.conn, res, collector.parse_poll(res, {}, None))
        self.assertEqual(store.queue(self.conn), [])
        self.assertTrue(collector.is_active(self.conn, self.cfg, self.cfg.clusters[0], self.t0))
        self.make_socket()
        self.cycle()
        self.assertEqual(store.queue(self.conn), [])
        self.assertEqual(self.cluster_mode(), "active")
        # a day later the campaign is closed: idle, then released
        self.assertFalse(collector.is_active(self.conn, self.cfg, self.cfg.clusters[0],
                                             self.t0 + 2 * DAY))

    def test_globs_only_for_their_cluster(self):
        self.pin()
        self.make_socket()
        self.cfg.glob_campaigns = [GlobCampaign("sweep", NAME, "out/*.json", 10),
                                   GlobCampaign("else", "other", "x/*", 3)]
        (self.home / "out").mkdir()
        (self.home / "out" / "a.json").write_text("")
        res = self.cycle()
        self.assertIn("globs", res[0].requested)
        camp = {c.campaign: c for c in store.campaigns(self.conn, self.cfg)}
        self.assertEqual(len(camp["sweep"].done), 1)

    def test_loop_stops_on_sigterm(self):
        self.make_socket()
        timer = threading.Timer(0.3, os.kill, (os.getpid(), signal.SIGTERM))
        timer.start()
        self.addCleanup(timer.cancel)
        before = signal.getsignal(signal.SIGTERM)
        t = time.monotonic()
        rc = collector.collect(self.cfg, False, state=self.state, tick=0.1)
        self.assertEqual(rc, 0)
        self.assertLess(time.monotonic() - t, 2.5)
        self.assertIs(signal.getsignal(signal.SIGTERM), before)
        again = PollLock(self.state)
        self.assertTrue(again.try_acquire())  # the lock was released
        again.release()


class CliTests(unittest.TestCase):
    def test_collect_wired(self):
        with mock.patch("dracmonlib.collector.collect", return_value=0) as c, \
             mock.patch("dracmonlib.config.load_config", return_value=Config()):
            self.assertEqual(dracmon.main(["collect", "--once"]), 0)
        self.assertIs(c.call_args.args[1], True)


if __name__ == "__main__":
    unittest.main()
