import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from dracmonlib import doctor  # noqa: E402
from dracmonlib.config import Config, Cluster  # noqa: E402


def fake_g(sockdir, **over):
    d = {"hostname": "h.example", "port": "22", "user": "u", "controlmaster": "auto",
         "controlpath": f"{sockdir}/%C", "controlpersist": "14400"}
    d.update(over)
    return "\n".join(f"{k} {v}" for k, v in d.items() if v is not None) + "\n"


class TestDoctor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sock = self.tmp.name

    def check(self, **over):
        out = fake_g(self.sock, **over)
        with mock.patch("dracmonlib.ssh._run", return_value=(0, out, "")) as r:
            res = doctor.check_host("x")
        self.argv = r.call_args_list[0].args[0]
        return res

    def levels(self, fs):
        return [f.level for f in fs]

    def test_doctor_ok_config(self):
        fs = self.check()
        self.assertEqual(set(self.levels(fs)), {"ok"})
        self.assertEqual(self.argv[:2], ["ssh", "-G"])

    def test_doctor_flags_missing_controlmaster(self):
        fs = self.check(controlmaster="false")
        bad = [f for f in fs if f.level == "error"]
        self.assertTrue(bad)
        self.assertIn("ControlMaster", bad[0].fix)

    def test_doctor_flags_missing_socket_dir(self):
        fs = self.check(controlpath="/nonexistent-dracmon-dir/%C")
        bad = [f for f in fs if f.level == "error"]
        self.assertTrue(bad)
        self.assertIn("mkdir", bad[0].fix)

    def test_no_controlpath(self):
        fs = self.check(controlpath="none")
        self.assertIn("error", self.levels(fs))

    def test_controlpersist_no(self):
        fs = self.check(controlpersist="no")
        self.assertIn("error", self.levels(fs))

    def test_ssh_g_failure(self):
        with mock.patch("dracmonlib.ssh._run", return_value=(255, "", "boom")):
            fs = doctor.check_host("x")
        self.assertEqual(self.levels(fs), ["error"])

    def test_run_returns_1_on_error_and_never_edits(self):
        cfg = Config(clusters=[Cluster("a", "a")])
        out = fake_g(self.sock, controlmaster="false")
        with mock.patch("dracmonlib.ssh._run", return_value=(0, out, "")), \
                mock.patch.object(doctor.shutil, "which", return_value="/x/uv"), \
                mock.patch("builtins.print") as pr:
            self.assertEqual(doctor.run(cfg), 1)
        text = "\n".join(str(c.args[0]) for c in pr.call_args_list if c.args)
        self.assertIn("fix:", text)

    def test_run_ok(self):
        cfg = Config(clusters=[Cluster("a", "a")])
        out = fake_g(self.sock)
        with mock.patch("dracmonlib.ssh._run", return_value=(0, out, "")), \
                mock.patch.object(doctor.shutil, "which", return_value="/x/uv"), \
                mock.patch("builtins.print"):
            self.assertEqual(doctor.run(cfg), 0)

    def test_run_missing_uv_is_error(self):
        cfg = Config(clusters=[])
        with mock.patch.object(doctor.shutil, "which", return_value=None), \
                mock.patch("builtins.print"):
            self.assertEqual(doctor.run(cfg), 1)


if __name__ == "__main__":
    unittest.main()
