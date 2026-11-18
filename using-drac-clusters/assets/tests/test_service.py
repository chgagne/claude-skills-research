import os
import plistlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from dracmonlib import service  # noqa: E402

ARGV = ["/opt/bin/uv", "run", "--script", "/opt/dracmon.py", "collect"]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        for p in (mock.patch.object(Path, "home", return_value=self.home),
                  mock.patch.dict(os.environ, {"HOME": self.tmp.name,
                                               "XDG_STATE_HOME": self.tmp.name + "/state"}),
                  mock.patch.object(service, "collector_argv", return_value=ARGV)):
            p.start()
            self.addCleanup(p.stop)
        self.run_mock = mock.patch.object(service.subprocess, "run").start()
        self.run_mock.return_value = mock.Mock(returncode=0)
        self.addCleanup(mock.patch.stopall)

    def calls(self):
        return [c.args[0] for c in self.run_mock.call_args_list]


class TestRender(unittest.TestCase):
    def test_launchd_plist_valid(self):
        text = service.render_launchd(ARGV, Path("/tmp/logs"), "/usr/bin:/opt/bin")
        d = plistlib.loads(text.encode())
        self.assertEqual(d["ProgramArguments"], ARGV)
        self.assertEqual(d["Label"], "dracmon.collector")
        self.assertIs(d["RunAtLoad"], True)
        self.assertIs(d["KeepAlive"], True)
        self.assertEqual(d["ThrottleInterval"], 60)
        self.assertEqual(d["ExitTimeOut"], 90)
        self.assertEqual(d["StandardOutPath"], "/tmp/logs/service.log")
        self.assertEqual(d["StandardErrorPath"], "/tmp/logs/service.log")
        self.assertEqual(d["EnvironmentVariables"]["PATH"], "/usr/bin:/opt/bin")
        self.assertNotIn("SSH_ASKPASS", d["EnvironmentVariables"])

    def test_launchd_home_included_when_set(self):
        with mock.patch.dict(os.environ, {"HOME": "/h/x"}):
            d = plistlib.loads(service.render_launchd(ARGV, Path("/l"), "/bin").encode())
        self.assertEqual(d["EnvironmentVariables"]["HOME"], "/h/x")

    def test_systemd_unit_has_execstart(self):
        u = service.render_systemd(["/opt/bin/uv", "run", "--script", "/p q/dracmon.py", "collect"])
        self.assertIn("[Service]", u)
        self.assertIn("ExecStart=/opt/bin/uv run --script \"/p q/dracmon.py\" collect", u)
        self.assertIn("Restart=on-failure", u)
        self.assertIn("RestartSec=60", u)
        self.assertIn("TimeoutStopSec=90", u)
        self.assertIn("[Install]\nWantedBy=default.target", u)

    def test_collector_argv_needs_uv(self):
        with mock.patch.object(service.shutil, "which", return_value=None):
            with self.assertRaises(RuntimeError) as cm:
                service.collector_argv()
        self.assertIn("uv", str(cm.exception))

    def test_collector_argv_shape(self):
        with mock.patch.object(service.shutil, "which", return_value="/x/uv"):
            a = service.collector_argv()
        self.assertEqual(a[:3], ["/x/uv", "run", "--script"])
        self.assertTrue(a[3].endswith("dracmon.py") and os.path.isabs(a[3]))
        self.assertEqual(a[4], "collect")


class TestMac(Base):
    def setUp(self):
        super().setUp()
        p = mock.patch.object(service.sys, "platform", "darwin")
        p.start()
        self.addCleanup(p.stop)
        self.plist = self.home / "Library/LaunchAgents/dracmon.collector.plist"
        self.target = f"gui/{os.getuid()}"

    def test_install_writes_and_bootstraps(self):
        self.assertEqual(service.install(), 0)
        self.assertEqual(plistlib.loads(self.plist.read_bytes())["ProgramArguments"], ARGV)
        self.assertEqual(self.calls(), [["launchctl", "bootstrap", self.target, str(self.plist)]])

    def test_install_refuses_overwrite(self):
        self.plist.parent.mkdir(parents=True)
        self.plist.write_text("different")
        self.assertEqual(service.install(), 1)
        self.assertEqual(self.plist.read_text(), "different")
        self.assertEqual(self.calls(), [])
        self.assertEqual(service.install(force=True), 0)
        self.assertNotEqual(self.plist.read_text(), "different")
        self.assertEqual(self.calls()[-1][:2], ["launchctl", "bootstrap"])

    def test_install_identical_is_ok(self):
        service.install()
        self.assertEqual(service.install(), 0)

    def test_uninstall_and_status(self):
        service.install()
        self.run_mock.reset_mock()
        self.assertEqual(service.status(), 0)
        self.assertEqual(self.calls(), [["launchctl", "print", f"{self.target}/dracmon.collector"]])
        self.run_mock.reset_mock()
        self.assertEqual(service.uninstall(), 0)
        self.assertEqual(self.calls(), [["launchctl", "bootout", f"{self.target}/dracmon.collector"]])
        self.assertFalse(self.plist.exists())


class TestLinux(Base):
    def setUp(self):
        super().setUp()
        p = mock.patch.object(service.sys, "platform", "linux")
        p.start()
        self.addCleanup(p.stop)
        self.unit = self.home / ".config/systemd/user/dracmon.service"

    def test_install(self):
        self.assertEqual(service.install(), 0)
        self.assertIn("ExecStart=", self.unit.read_text())
        self.assertEqual(self.calls(), [["systemctl", "--user", "daemon-reload"],
                                        ["systemctl", "--user", "enable", "--now", "dracmon"]])

    def test_install_refuses_overwrite(self):
        self.unit.parent.mkdir(parents=True)
        self.unit.write_text("other")
        self.assertEqual(service.install(), 1)
        self.assertEqual(self.unit.read_text(), "other")
        self.assertEqual(self.calls(), [])

    def test_uninstall_status(self):
        service.install()
        self.run_mock.reset_mock()
        service.status()
        self.assertEqual(self.calls(), [["systemctl", "--user", "status", "dracmon"]])
        self.run_mock.reset_mock()
        service.uninstall()
        self.assertEqual(self.calls(), [["systemctl", "--user", "disable", "--now", "dracmon"],
                                        ["systemctl", "--user", "daemon-reload"]])
        self.assertFalse(self.unit.exists())


class TestOther(Base):
    def test_unsupported(self):
        with mock.patch.object(service.sys, "platform", "win32"):
            for f in (service.install, service.uninstall, service.status):
                self.assertEqual(f(), 2)
        self.assertEqual(self.calls(), [])


if __name__ == "__main__":
    unittest.main()
