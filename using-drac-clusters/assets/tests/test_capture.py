import contextlib
import io
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dracmonlib import capture  # noqa: E402
from dracmonlib.config import Cluster  # noqa: E402
from dracmonlib.frame import parse_frames  # noqa: E402
from fakessh import FakeSshCase  # noqa: E402
import dracmon  # noqa: E402

SAMPLE = """\
@@dracmon begin env
user=jdoe
cluster=testcluster
scratch=/scratch/j/jdoe
host=login1
now=1790000000
tz=-0500
@@dracmon end env rc=0
@@dracmon begin accounts
def-jdoe_cpu
def-jdoe_gpu
@@dracmon end accounts rc=0
@@dracmon begin queue
101|101|101|0|secretexp|cpu|RUNNING|0:10|1:00:00|N/A|4|8G|gres:gpu:1|nc101|def-jdoe_gpu|2026-11-17T10:00:00
102|102|102|0|other-run|gpu|PENDING|0:00|1:00:00|N/A|4|8G|gres:gpu:h100:1|(Priority)|def-jdoe_cpu|2026-11-17T10:00:00
@@dracmon end queue rc=0
@@dracmon begin accounting
101|secretexp|def-jdoe_gpu|cpu|COMPLETED|0:0|0:10|1:00:00|a|b|c|nc101|cpu=4|8G|00:01|4
@@dracmon end accounting rc=0
@@dracmon begin fairshare
def-jdoe_gpu||1000|0.5|0.9|
def-jdoe_gpu|jdoe|1000|0.5|0.9|0.8
@@dracmon end fairshare rc=0
@@dracmon begin usage
101|jdoe|def-jdoe_gpu|COMPLETED|2026-11-16T00:00:00|01:00:00|gres/gpu=1
102|asmith|def-jdoe_gpu|COMPLETED|2026-11-16T00:00:00|01:00:00|gres/gpu=1
103|bwong|rrg-wong-ab|COMPLETED|2026-11-16T00:00:00|01:00:00|gres/gpu=1
@@dracmon end usage rc=0
@@dracmon begin disk
/home (user jdoe) 1G/50G
/project (def-jdoe_cpu) 2G/1T
@@dracmon end disk rc=0
@@dracmon begin cells
#file 120 120 secretcamp/101.log
1790000000\t101\tplan\t\t4
1790000001\t101\tstart\tcell-alpha\t
1790000002\t101\tfail\tcell-alpha\tsecret reason
@@dracmon end cells rc=0
@@dracmon begin globs
#glob secretcamp 3
@@dracmon end globs rc=0
@@dracmon begin extra
/home/j/jdoe/x /project/6001234/jdoe /scratch/j/jdoe/run1
@@dracmon end extra rc=0
"""
ENV = {"user": "jdoe", "scratch": "/scratch/j/jdoe"}
ACCTS = ["def-jdoe_cpu", "def-jdoe_gpu"]


class AnonymiseTests(unittest.TestCase):
    def setUp(self):
        self.out = capture.anonymise(SAMPLE, ENV, ACCTS)

    def test_anonymise_removes_identifiers(self):
        for s in ("jdoe", "def-jdoe", "/home/j/jdoe", "6001234", "secretexp", "asmith",
                  "bwong", "wong", "secretcamp", "cell-alpha", "secret reason", "other-run",
                  "/scratch/j"):
            self.assertNotIn(s, self.out, s)
        self.assertIn("def-group0_gpu", self.out)
        self.assertIn("def-group0_cpu", self.out)
        self.assertIn("/home/user0/x", self.out)
        self.assertIn("/project/000000/user0", self.out)
        self.assertIn("/scratch/user0/run1", self.out)
        self.assertIn("scratch=/scratch/user0", self.out)

    def test_users_consistent_and_others_numbered(self):
        self.assertIn("101|user0|def-group0_gpu", self.out)
        self.assertIn("102|user1|def-group0_gpu", self.out)
        self.assertIn("103|user2|rrg-group1-ab", self.out)
        self.assertIn("user=user0", self.out)

    def test_names_mapped_consistently_numbers_kept(self):
        q = parse_frames(self.out)["queue"].body.splitlines()
        a = parse_frames(self.out)["accounting"].body.split("|")
        self.assertEqual(q[0].split("|")[4], a[1])
        self.assertRegex(a[1], r"^job\d+$")
        self.assertNotEqual(q[0].split("|")[4], q[1].split("|")[4])
        self.assertIn("gres:gpu:h100:1", q[1])
        self.assertIn("|RUNNING|0:10|1:00:00|", q[0])
        self.assertIn("nc101", q[0])
        self.assertIn("1790000000", self.out)

    def test_cells_and_globs_renamed(self):
        secs = parse_frames(self.out)
        cells = secs["cells"].body.splitlines()
        self.assertRegex(cells[0], r"^#file 120 120 camp\d+/101\.log$")
        self.assertRegex(cells[2].split("\t")[3], r"^cell\d+$")
        self.assertEqual(cells[2].split("\t")[3], cells[3].split("\t")[3])
        self.assertEqual(cells[1].split("\t")[4], "4")
        self.assertEqual(cells[0].split()[3].split("/")[0],
                         secs["globs"].body.split()[1])

    def test_cancelled_by_uid_scrubbed(self):
        text = ("@@dracmon begin usage\n"
                "101|jdoe|def-jdoe_gpu|CANCELLED by 3051234|None|00:00:00|\n"
                "102|jdoe|def-jdoe_gpu|CANCELLED by 0|None|00:00:00|\n"
                "@@dracmon end usage rc=0\n"
                "@@dracmon begin accounting\n"
                "103|x|def-jdoe_gpu|cpu|CANCELLED by 42|0:0|0:10|1:00:00|a|b|c|n|cpu=4|8G|00:01|4\n"
                "@@dracmon end accounting rc=0\n")
        out = capture.anonymise(text, ENV, ACCTS)
        self.assertNotIn("3051234", out)
        self.assertNotIn("by 42", out)
        self.assertEqual(out.count("CANCELLED by 0|"), 3)

    def test_frames_survive(self):
        secs = parse_frames(self.out)
        self.assertTrue(all(s.complete for s in secs.values()))
        self.assertEqual(set(secs), set(parse_frames(SAMPLE)))


class CaptureTests(FakeSshCase):
    def test_capture_refuses_dead_socket(self):
        out = self.tmp / "out"
        with contextlib.redirect_stderr(io.StringIO()) as se, \
                contextlib.redirect_stdout(io.StringIO()) as so:
            written = capture.capture([Cluster("testcluster", "testhost")], out)
        self.assertIn("no live ssh socket", se.getvalue())
        self.assertEqual(so.getvalue(), "")
        self.assertEqual(written, [])
        self.assertEqual(list(out.glob("*")), [])
        self.assertEqual(self.connecting_argvs(), [])

    def test_capture_stale_socket_refused(self):
        self.make_socket()
        self.set_mode("stale")
        out = self.tmp / "out"
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(capture.capture([Cluster("testcluster", "testhost")], out), [])
        self.assertFalse(any("bash -l -s" in a for a in self.argvs()))

    def test_capture_happy_path(self):
        self.make_socket()
        out = self.tmp / "out"
        written = capture.capture([Cluster("testcluster", "testhost")], out)
        self.assertEqual(written, [out / "testcluster.txt"])
        text = written[0].read_text()
        secs = parse_frames(text)
        for name in ("env", "accounts", "queue", "accounting", "steps", "fairshare",
                     "usage", "disk", "partitions", "cells", "globs"):
            self.assertIn(name, secs)
            self.assertTrue(secs[name].complete, name)
        self.assertNotIn("jdoe", text)
        self.assertNotIn("secretexp", text)
        self.assertIn("user=user0", text)
        remote = [a for a in self.argvs() if "bash -l -s" in a]
        self.assertEqual(len(remote), 1)
        self.assertIn("BatchMode=yes", remote[0])
        self.assertIn("ControlMaster=no", remote[0])

    def test_cli_capture(self):
        self.make_socket()
        os.environ["XDG_CONFIG_HOME"] = str(self.tmp / "cfg")  # no config: default clusters
        out = self.tmp / "out"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(dracmon.main(["capture", "narval", "--out", str(out)]), 0)
        self.assertTrue((out / "narval.txt").exists())

    def test_cli_capture_unknown_cluster(self):
        os.environ["XDG_CONFIG_HOME"] = str(self.tmp / "cfg")
        out = self.tmp / "out"
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = dracmon.main(["capture", "narval", "nosuch", "--out", str(out)])
        self.assertEqual(rc, 2)
        self.assertIn("nosuch", err.getvalue())
        self.assertEqual(self.argvs(), [])

    def test_cli_capture_partial_failure_rc(self):
        os.environ["XDG_CONFIG_HOME"] = str(self.tmp / "cfg")
        out = self.tmp / "out"
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(dracmon.main(["capture", "narval", "--out", str(out)]), 1)


if __name__ == "__main__":
    unittest.main()
