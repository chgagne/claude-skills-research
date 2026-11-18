import math
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from dracmonlib import parse  # noqa: E402
from dracmonlib.frame import parse_frames  # noqa: E402
from dracmonlib.parse import (parse_disk, parse_duration, parse_env, parse_mem,  # noqa: E402
                              parse_sacct, parse_sinfo, parse_slurm_time, parse_squeue,
                              parse_sshare, parse_usage)

FIX = HERE / "fixtures"
CLUSTERS = ("narval", "rorqual", "nibi", "tamia", "killarney", "vulcan")
GiB, MiB, KiB = 2**30, 2**20, 2**10


def secs(cluster):
    return parse_frames((FIX / f"{cluster}.txt").read_text())


def ep(s, hours):
    """Epoch of a naive Slurm time at UTC offset `hours` (computed independently)."""
    d = datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
    return d.replace(tzinfo=timezone(timedelta(hours=hours))).timestamp()


class Recorded:
    """Parse every section of one recorded cluster."""

    def __init__(self, cluster):
        s = secs(cluster)
        self.s = s
        self.env = parse_env(s["env"].body)
        self.tz = self.env["tz"]
        self.parts = parse_sinfo(s["partitions"].body, cluster)
        from dracmonlib.gpu import shards_per_card
        self.shards = shards_per_card(self.parts)
        self.queue = parse_squeue(s["queue"].body, cluster, self.tz, self.shards)
        self.acct = parse_sacct(s["accounting"].body, s["steps"].body, cluster, self.tz,
                                self.shards)
        self.share = parse_sshare(s["fairshare"].body, cluster)
        self.usage = parse_usage(s["usage"].body, cluster, self.tz, self.shards)
        self.disk = parse_disk(s["disk"].body, cluster)


class HelperTests(unittest.TestCase):
    def test_duration(self):
        self.assertEqual(parse_duration("1-00:00:00"), 86400)
        self.assertEqual(parse_duration("16:00:00"), 57600)
        self.assertEqual(parse_duration("3:00:00"), 10800)
        self.assertEqual(parse_duration("0:00"), 0)
        self.assertEqual(parse_duration("05:06.789"), 306)
        self.assertEqual(parse_duration("7-00:00:00"), 7 * 86400)
        self.assertEqual(parse_duration("2-03:04:05"), 2 * 86400 + 3 * 3600 + 245)
        for v in ("UNLIMITED", "INVALID", "", "N/A", "abc"):
            self.assertIsNone(parse_duration(v), v)

    def test_mem(self):
        self.assertEqual(parse_mem("200G"), 200 * GiB)
        self.assertEqual(parse_mem("1000000M"), 1000000 * MiB)
        self.assertEqual(parse_mem("209713624K"), 209713624 * KiB)
        self.assertEqual(parse_mem("4000Mc"), 4000 * MiB)
        self.assertEqual(parse_mem("8Gn"), 8 * GiB)
        self.assertEqual(parse_mem("2T"), 2 * 2**40)
        self.assertEqual(parse_mem("937.50G"), int(937.5 * GiB))
        self.assertEqual(parse_mem("0"), 0)
        for v in ("", "N/A", "x"):
            self.assertIsNone(parse_mem(v), v)

    def test_times_use_cluster_offset(self):
        a = parse_slurm_time("2026-11-17T21:34:33", "-0800")
        b = parse_slurm_time("2026-11-17T21:34:33", "-0500")
        self.assertEqual(a - b, 10800)
        self.assertEqual(b, ep("2026-11-17T21:34:33", -5))
        for v in ("Unknown", "N/A", "None", ""):
            self.assertIsNone(parse_slurm_time(v, "-0500"), v)

    def test_env(self):
        env = parse_env(secs("vulcan")["env"].body)
        self.assertEqual(env["tz"], "-0600")
        self.assertEqual(env["cluster"], "vulcan")
        self.assertEqual(env["now"], "1794974985")


class SyntheticTests(unittest.TestCase):
    def test_pending_array_range_counts_tasks(self):
        line = ("123_[0-99%10]|123|123|0-99%10|exp|gpu|PENDING|0:00|1:00:00|N/A|4|8G|"
                "gres/gpu:h100:1|(Priority)|def-group0_gpu|2026-11-17T10:00:00")
        [r] = parse_squeue(line + "\n", "c", "-0500", {})
        self.assertEqual(r.task_count, 100)
        self.assertEqual(r.array_tasks, "0-99%10")
        self.assertEqual(r.array_job_id, "123")
        self.assertEqual(r.job_id, "123_[0-99%10]")

    def test_array_task_forms(self):
        def row(i, k):
            return (f"{i}|9|123|{k}|exp|gpu|RUNNING|0:10|1:00:00|N/A|4|8G|N/A|nc1|"
                    "def-group0_gpu|2026-11-17T10:00:00\n")
        body = row("123_5", "5") + row("123_[1,3,5-7]", "1,3,5-7") + row("124", "N/A")
        a, b, c = parse_squeue(body, "c", "-0500", {})
        self.assertEqual((a.task_count, a.array_tasks, a.array_job_id), (1, "5", "123"))
        self.assertEqual(b.task_count, 5)
        self.assertEqual((c.task_count, c.array_tasks, c.array_job_id), (1, None, None))

    def test_maxrss_from_steps(self):
        acct = ("55|exp|def-group0_gpu|gpu|COMPLETED|0:0|01:00:00|02:00:00|2026-11-17T10:00:00|"
                "2026-11-17T10:00:05|2026-11-17T11:00:05|nc1|cpu=4,gres/gpu=1,mem=8G|8G|"
                "01:02:03|4\n")
        steps = "55|\n55.batch|1000K\n55.extern|2000K\n55.0|3G\n55.1|500M\n56.batch|9T\n"
        [j] = parse_sacct(acct, steps, "c", "-0500", {})
        self.assertEqual(j.max_rss_bytes, 3 * GiB)
        self.assertEqual(j.total_cpu_s, 3723)
        self.assertEqual(j.gpus, 1.0)

    def test_maxrss_none_without_steps(self):
        acct = ("57|exp|a|p|PENDING|0:0|00:00:00|02:00:00|2026-11-17T10:00:00|Unknown|Unknown|"
                "None assigned||8G|00:00:00|0\n")
        [j] = parse_sacct(acct, "57|\n", "c", "-0500", {})
        self.assertIsNone(j.max_rss_bytes)
        self.assertIsNone(j.start)
        self.assertIsNone(j.nodes)

    def test_aip_account_no_suffix_ok(self):
        r = Recorded("killarney")
        self.assertEqual({q.account for q in r.queue}, {"aip-group0"})
        self.assertEqual({j.account for j in r.acct}, {"aip-group0"})
        self.assertEqual([s.account for s in r.share], ["aip-group0", "aip-group0"])
        disk = {d.filesystem: d for d in r.disk}
        self.assertEqual((disk["/project"].scope, disk["/project"].owner),
                         ("project", "aip-group0"))

    def test_unparseable_line_skipped_not_fatal(self):
        good = ("7|7|7|N/A|exp|gpu|RUNNING|0:10|1:00:00|N/A|4|8G|N/A|nc1|a|"
                "2026-11-17T10:00:00\n")
        body = good + "garbage line\n" + "1|2|3\n" + good.replace("|4|8G|", "|four|8G|")
        rows = parse_squeue(body, "c", "-0500", {})
        self.assertEqual(len(rows), 1)
        self.assertEqual(parse_squeue.last_skipped, 3)
        parse_squeue(good, "c", "-0500", {})
        self.assertEqual(parse_squeue.last_skipped, 0)
        rows = parse_sacct("x|y\n", "bad\n", "c", "-0500", {})
        self.assertEqual((rows, parse_sacct.last_skipped), ([], 2))  # one acct + one step line
        rows = parse_sshare("a|b|notint|0.1|0.2|\n", "c")
        self.assertEqual((rows, parse_sshare.last_skipped), ([], 1))
        rows = parse_usage("1|u|a|COMPLETED\n", "c", "-0500", {})
        self.assertEqual((rows, parse_usage.last_skipped), ([], 1))
        rows = parse_sinfo("p|up|1:00:00|many|idle|(null)\n", "c")
        self.assertEqual((rows, parse_sinfo.last_skipped), ([], 1))
        rows = parse_disk("  /home (user u)  lots/ 50GiB  1 / 2\nheader text\n", "c")
        self.assertEqual((rows, parse_disk.last_skipped), ([], 1))
        self.assertTrue(hasattr(parse, "QueueRow"))


class ReviewFixTests(unittest.TestCase):
    def test_disk_exa_units_and_never_raises(self):
        rows = parse_disk("  /home (user u)  1EB/ 2EB  1 / 2\n", "c")
        self.assertEqual([(r.used_bytes, r.quota_bytes) for r in rows], [(10**18, 2 * 10**18)])
        rows = parse_disk("  /home (user u)  1EiB/ 2EiB  1 / 2\n", "c")
        self.assertEqual(rows[0].used_bytes, 2**60)

    def test_count_tasks_skips_bad_part_only(self):
        self.assertEqual(parse.count_tasks("1,x,5-7"), 4)
        self.assertEqual(parse.count_tasks("0-9,a-b%2"), 10)
        self.assertEqual(parse.count_tasks("junk"), 1)


class DiskVariantTests(unittest.TestCase):
    def test_disk_report_variants(self):
        for c in CLUSTERS:
            s = secs(c)["disk"]
            self.assertEqual(s.rc, 0, c)  # every recording has diskusage_report
            rows = parse_disk(s.body, c)
            self.assertTrue(any(r.quota_bytes > 0 for r in rows), c)
            self.assertEqual(parse_disk.last_skipped, 0, c)


class NarvalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = Recorded("narval")

    def test_squeue(self):
        self.assertEqual(self.r.queue, [])

    def test_sacct(self):
        self.assertEqual(self.r.acct, [])

    def test_usage_failed_section_empty(self):
        self.assertEqual(self.r.s["usage"].rc, 1)
        self.assertEqual(self.r.usage, [])

    def test_sshare(self):
        sh = self.r.share
        self.assertEqual(len(sh), 4)
        self.assertEqual((sh[0].account, sh[0].user, sh[0].raw_usage, sh[0].fairshare),
                         ("def-group0_cpu", None, 2784862037, None))
        self.assertAlmostEqual(sh[0].level_fs, 14.027213)
        u = sh[3]
        self.assertEqual((u.account, u.user, u.raw_usage), ("def-group0_gpu", "user0", 424301))
        self.assertAlmostEqual(u.effective_usage, 0.000071)
        self.assertAlmostEqual(u.level_fs, 785.774837)
        self.assertAlmostEqual(u.fairshare, 0.236917)

    def test_disk(self):
        d = self.r.disk
        self.assertEqual(len(d), 10)
        h = d[0]
        self.assertEqual((h.filesystem, h.scope, h.owner), ("/home", "user", "user0"))
        self.assertEqual((h.used_bytes, h.quota_bytes, h.files, h.files_quota),
                         (3592 * 10**6, 50 * 10**9, 101000, 500000))
        self.assertEqual((d[1].used_bytes, d[1].quota_bytes, d[1].files), (304 * 10**6, 20 * 10**12, 163))
        near = [r for r in d if r.filesystem == "/nearline"]
        self.assertEqual(len(near), 7)
        self.assertTrue(all(r.scope == "project" and r.files_quota == 5000 for r in near))
        self.assertEqual(near[0].owner, "def-group0")
        self.assertEqual(near[0].used_bytes, 138 * 10**9)
        self.assertEqual(near[5].used_bytes, 1062 * 10**3)

    def test_sinfo(self):
        p = self.r.parts
        self.assertEqual(len(p), 241)
        self.assertEqual(p[0], parse.PartitionRow("narval", "cpubase_interac", "up", 28800, 1,
                                                  "inval", "", False))
        mig = [r for r in p if "a100_3g.20gb:4" in r.gres]
        self.assertTrue(mig)
        self.assertEqual(mig[0].gres, "gpu:a100_3g.20gb:4,gpu:a100_2g.10gb:4,gpu:a100_1g.5gb:8")
        self.assertFalse(any("(" in r.gres for r in p))
        self.assertFalse(any(r.is_default for r in p))


class RorqualTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = Recorded("rorqual")

    def test_squeue(self):
        self.assertEqual(self.r.queue, [])

    def test_sacct(self):
        self.assertEqual(self.r.acct, [])

    def test_usage(self):
        u = self.r.usage
        self.assertEqual(len(u), 817)
        self.assertEqual(parse_usage.last_skipped, 0)
        by = {r.job_id: r for r in u}
        mig = by["24879049"]
        self.assertEqual((mig.user, mig.account, mig.state, mig.cpus, mig.elapsed_s),
                         ("user1", "def-group0_gpu", "FAILED", 4, 2))
        self.assertAlmostEqual(mig.gpus, 2 / 7)
        self.assertEqual(mig.start, ep("2026-10-21T18:23:40", -5))
        arr = by["25228302_[0-23]"]
        self.assertEqual((arr.state, arr.start, arr.cpus, arr.gpus, arr.elapsed_s),
                         ("CANCELLED by 0", None, 0, 0.0, 0))
        self.assertEqual(sum(1 for r in u if r.state == "TIMEOUT"), 21)
        self.assertEqual(sum(1 for r in u if r.start is None), 55)

    def test_disk(self):
        d = self.r.disk
        self.assertEqual([(r.filesystem, r.scope) for r in d],
                         [("/home", "user"), ("/scratch", "user"), ("/project", "project"),
                          ("/nearline", "project")])
        self.assertEqual((d[1].used_bytes, d[1].files, d[1].files_quota),
                         (244 * 10**9, 2404, 1000000))
        self.assertEqual((d[3].used_bytes, d[3].files, d[3].files_quota), (294 * 10**3, 12, 5000))

    def test_sinfo(self):
        p = self.r.parts
        self.assertEqual(len(p), 151)
        dflt = [r for r in p if r.is_default]
        self.assertTrue(dflt)
        self.assertEqual({r.partition for r in dflt}, {"cpubase_bycore_b1"})
        self.assertEqual(dflt[0].nodes, 89)
        self.assertEqual(dflt[0].state, "mixed-")


class NibiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = Recorded("nibi")

    def test_squeue(self):
        self.assertEqual(self.r.queue, [])

    def test_sacct(self):
        self.assertEqual(self.r.acct, [])

    def test_sshare_inf_levelfs(self):
        u = [s for s in self.r.share if s.user]
        self.assertEqual(len(u), 2)
        self.assertTrue(all(math.isinf(s.level_fs) for s in u))
        self.assertEqual(u[0].raw_usage, 0)

    def test_usage(self):
        u = self.r.usage
        self.assertEqual(len(u), 122)
        self.assertEqual(sum(1 for r in u if r.state == "PENDING"), 5)
        arr = [r for r in u if r.job_id.endswith("_[1-2%1]")]
        self.assertEqual(len(arr), 7)
        mig = {r.job_id: r for r in u}["25077415"]
        self.assertEqual((mig.user, mig.state, mig.cpus, mig.elapsed_s),
                         ("user2", "COMPLETED", 4, 2441))
        self.assertAlmostEqual(mig.gpus, 2 / 7)
        self.assertEqual(mig.start, ep("2026-10-26T22:24:41", -5))

    def test_disk(self):
        d = self.r.disk
        self.assertEqual(len(d), 10)
        self.assertEqual((d[0].used_bytes, d[0].quota_bytes, d[0].files, d[0].files_quota),
                         (4096, 50 * GiB, 23, 500000))
        self.assertEqual((d[1].used_bytes, d[1].quota_bytes), (0, 1024 * GiB))
        self.assertEqual((d[2].used_bytes, d[2].quota_bytes, d[2].files),
                         (693 * GiB, 931 * GiB, 189000))
        near = d[3:]
        self.assertTrue(all(r.scope == "group" and r.quota_bytes == 9537 * GiB
                            and r.files_quota == 1025 for r in near))
        self.assertEqual(near[0].owner, "def-group0-ab")
        self.assertEqual(near[3].used_bytes, 1626 * MiB)
        self.assertEqual(near[5].used_bytes, 12 * KiB)

    def test_sinfo(self):
        p = self.r.parts
        self.assertEqual(len(p), 205)
        self.assertIn("inactive", {r.avail for r in p})
        mig = [r for r in p if "hbm3" in r.gres][0]
        self.assertEqual(mig.gres, "gpu:nvidia_h100_80gb_hbm3_3g.40gb:8,"
                                   "gpu:nvidia_h100_80gb_hbm3_2g.20gb:8,"
                                   "gpu:nvidia_h100_80gb_hbm3_1g.10gb:16")


class TamiaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = Recorded("tamia")

    def test_squeue(self):
        q = self.r.queue
        self.assertEqual(len(q), 8)
        self.assertEqual(parse_squeue.last_skipped, 0)
        j = q[0]
        self.assertEqual(
            (j.cluster, j.job_id, j.array_job_id, j.array_tasks, j.partition, j.state,
             j.elapsed_s, j.limit_s, j.cpus, j.mem_bytes, j.gpus, j.node_or_reason,
             j.account, j.task_count),
            ("tamia", "704130", None, None, "gpubase_bynode_b3", "PENDING", 0, 57600, 48, 0,
             8.0, "(Priority)", "aip-group0", 1))
        self.assertEqual(j.start_est, ep("2026-11-18T10:04:34", -5))
        self.assertEqual(j.submit, ep("2026-11-17T22:32:51", -5))
        self.assertRegex(j.name, r"^job\d+$")

    def test_sacct(self):
        a = self.r.acct
        self.assertEqual(len(a), 17)
        self.assertEqual(parse_sacct.last_skipped, 0)
        j = a[0]
        self.assertEqual(
            (j.job_id, j.state, j.exit_code, j.elapsed_s, j.limit_s, j.nodes, j.cpus, j.gpus,
             j.req_mem_bytes, j.max_rss_bytes, j.total_cpu_s),
            ("698858", "COMPLETED", "0:0", 9 * 3600 + 27 * 60 + 49, 57600, "tg10503", 64, 8.0,
             1000000 * MiB, 321281396 * KiB, 0))
        self.assertEqual(j.start, ep("2026-11-15T20:49:29", -5))
        self.assertEqual(j.end, ep("2026-11-16T06:17:18", -5))
        pend = [x for x in a if x.state == "PENDING"]
        self.assertEqual(len(pend), 8)
        self.assertTrue(all(x.start is None and x.end is None and x.nodes is None
                            and x.max_rss_bytes is None and x.gpus == 0.0 for x in pend))

    def test_usage(self):
        u = self.r.usage
        self.assertEqual(len(u), 692)
        by = {r.job_id: r for r in u}
        self.assertEqual((by["659425"].cpus, by["659425"].gpus), (96, 8.0))
        self.assertEqual(by["631244"].state, "OUT_OF_MEMORY")
        self.assertEqual(by["703325_[1-4%4]"].start, None)

    def test_disk_warning_marker(self):
        d = self.r.disk
        self.assertEqual(len(d), 3)
        p = d[2]
        self.assertEqual((p.filesystem, p.scope, p.used_bytes, p.quota_bytes, p.files,
                          p.files_quota),
                         ("/project", "project", 4517 * GiB, 5120 * GiB, 478000, 500000))
        self.assertEqual((d[0].used_bytes, d[0].quota_bytes, d[0].files, d[0].files_quota),
                         (370 * MiB, 25 * GiB, 12000, 250000))

    def test_sinfo(self):
        self.assertEqual(len(self.r.parts), 39)
        self.assertIn("gpu:h200:8", {r.gres for r in self.r.parts})


class KillarneyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = Recorded("killarney")

    def test_squeue(self):
        q = self.r.queue
        self.assertEqual(len(q), 4)
        self.assertEqual([x.node_or_reason for x in q],
                         ["(JobHeldUser)"] * 3 + ["(Priority)"])
        self.assertTrue(all(x.start_est is None for x in q[:3]))
        j = q[3]
        self.assertEqual((j.job_id, j.partition, j.limit_s, j.cpus, j.mem_bytes, j.gpus),
                         ("7741239", "gpubase_h100_b1", 7200, 24, 200 * GiB, 4.0))
        self.assertEqual(j.start_est, ep("2026-11-18T06:45:00", -5))

    def test_sacct(self):
        a = self.r.acct
        self.assertEqual(len(a), 4)
        j = a[0]
        self.assertEqual(
            (j.job_id, j.partition, j.state, j.exit_code, j.elapsed_s, j.limit_s, j.nodes,
             j.cpus, j.gpus, j.req_mem_bytes, j.max_rss_bytes),
            ("7627390", "gpubase_h100_b3", "FAILED", "1:0", 2301, 57600, "kn176", 24, 4.0,
             200 * GiB, 209713624 * KiB))
        self.assertEqual(a[2].max_rss_bytes, 148045940 * KiB)
        self.assertEqual((a[3].state, a[3].cpus, a[3].max_rss_bytes), ("PENDING", 0, None))

    def test_sshare(self):
        sh = self.r.share
        self.assertEqual([(s.account, s.user) for s in sh],
                         [("aip-group0", None), ("aip-group0", "user0")])
        self.assertEqual(sh[1].raw_usage, 2944747076)
        self.assertAlmostEqual(sh[1].fairshare, 0.469061)

    def test_usage(self):
        u = self.r.usage
        self.assertEqual(len(u), 31)
        self.assertEqual(sum(r.gpus for r in u if r.start is not None), 14 * 1 + 16 * 4)
        self.assertEqual(u[-1].state, "PENDING")

    def test_disk(self):
        d = self.r.disk
        self.assertEqual(len(d), 3)
        self.assertEqual((d[0].used_bytes, d[0].quota_bytes, d[0].files, d[0].files_quota),
                         (124 * MiB, 50 * GiB, 7670, 500000))
        self.assertEqual((d[1].files, d[1].files_quota), (7145, 1000000))
        self.assertEqual((d[2].used_bytes, d[2].quota_bytes, d[2].files, d[2].files_quota),
                         (664 * GiB, 1000 * GiB, 422000, 2000000))

    def test_sinfo(self):
        p = self.r.parts
        self.assertEqual(len(p), 49)
        self.assertEqual(p[0], parse.PartitionRow("killarney", "gpubase_h100_b1", "up", 10800, 2,
                                                  "mixed-", "gpu:h100:8", False))
        self.assertEqual({r.state for r in p} & {"fail*", "draining@", "down*"},
                         {"fail*", "draining@", "down*"})


class VulcanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = Recorded("vulcan")

    def test_squeue(self):
        self.assertEqual(self.r.queue, [])

    def test_sacct(self):
        self.assertEqual(self.r.acct, [])

    def test_usage(self):
        self.assertEqual(self.r.usage, [])

    def test_sshare(self):
        sh = self.r.share
        self.assertEqual(len(sh), 2)
        self.assertTrue(math.isinf(sh[1].level_fs))
        self.assertAlmostEqual(sh[0].level_fs, 1802.190998)

    def test_disk(self):
        d = self.r.disk
        self.assertEqual([(r.used_bytes, r.quota_bytes, r.files, r.files_quota) for r in d],
                         [(0, 50 * GiB, 30, 105 * 10**6), (0, 5120 * GiB, 1, 11 * 10**9),
                          (0, 7680 * GiB, 11, 16 * 10**9)])

    def test_sinfo(self):
        p = self.r.parts
        self.assertEqual(len(p), 82)
        d = [r for r in p if r.is_default]
        self.assertEqual(len(d), 7)
        self.assertEqual(d[0].partition, "gpubase_bygpu_b1")
        sh = [r for r in p if "shard" in r.gres][0]
        self.assertEqual(sh.gres, "gpu:l40s:4,shard:l40s:16")
        self.assertIn("", {r.gres for r in p})
        self.assertEqual(self.r.shards, {"l40s": 4})


if __name__ == "__main__":
    unittest.main()
