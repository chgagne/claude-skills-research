import hashlib
import os
import pwd
import shlex
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from dracmonlib import ssh  # noqa: E402
from dracmonlib.config import Cluster  # noqa: E402
from fakessh import FAKEBIN, FakeSshCase  # noqa: E402

CL = Cluster("testcluster", "testhost")


def poll(sections=("queue",), timeout=20, **kw):
    args = dict(since="2026-11-15T00:00:00", offsets={}, globs=[], retention_days=30,
                timeout=timeout)
    args.update(kw)
    return ssh.poll_cluster(CL, list(sections), **args)


def fakessh_running():
    p = subprocess.run(["pgrep", "-f", "fakebin/ssh"], capture_output=True, text=True)
    return p.stdout.strip()


def alive(pid):
    for _ in range(20):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        time.sleep(0.05)
    return True


class CollectorArgvTests(FakeSshCase):
    def test_collector_argv_has_batchmode(self):
        self.make_socket()
        self.assertTrue(ssh.socket_live("testhost"))
        res = poll(["queue", "usage"])
        self.assertTrue(res.ok, res.error)
        argvs = self.argvs()
        self.assertTrue(any("-O check" in a for a in argvs))
        self.assertTrue(any("bash -l -s" in a for a in argvs))
        for a in argvs:
            self.assertIn("BatchMode=yes", a)
            self.assertIn("ControlMaster=no", a)

    def test_run_remote_argv(self):
        rc, out, err = ssh.run_remote("testhost", ssh.build_script(["queue"], None, {}, [], 30), 20)
        self.assertEqual(rc, 0, err)
        argv = self.connecting_argvs()[-1]
        for opt in ("BatchMode=yes", "ControlMaster=no", "ConnectTimeout=15"):
            self.assertIn(f"-o {opt}", argv)
        self.assertNotIn("Compression", argv)
        self.assertTrue(argv.endswith("testhost bash -l -s"), argv)

    def test_compression_only_with_usage(self):
        ssh.run_remote("testhost", ssh.build_script(["usage"], None, {}, [], 30), 20)
        self.assertIn("-o Compression=yes", self.connecting_argvs()[-1])

    def test_missing_socket_no_subprocess(self):
        with mock.patch.object(ssh, "control_path", return_value=self.tmp / "absent"):
            self.assertFalse(ssh.socket_live("testhost"))
        self.assertEqual(self.argvs(), [])

    def test_missing_socket_only_config_query(self):
        # unpatched: the only subprocess is the local `ssh -G` config query
        self.assertFalse(ssh.socket_live("testhost"))
        self.assertEqual(self.connecting_argvs(), [])

    def test_no_controlpath_is_not_live(self):
        os.environ["FAKE_SSH_CONTROLPATH"] = "none"
        self.assertIsNone(ssh.control_path("testhost"))
        self.assertFalse(ssh.socket_live("testhost"))
        self.assertEqual(self.connecting_argvs(), [])

    def test_stale_socket_never_prompts(self):
        self.make_socket()
        self.set_mode("stale")
        self.assertFalse(ssh.socket_live("testhost"))
        checks = [a for a in self.argvs() if "-O check" in a]
        self.assertEqual(len(checks), 1)
        self.assertIn("BatchMode=yes", checks[0])
        self.assertIn("ControlMaster=no", checks[0])


class FailureTests(FakeSshCase):
    def test_hang_is_killed_and_down(self):
        self.set_mode("hang")
        t0 = time.monotonic()
        res = poll(timeout=2)
        self.assertLess(time.monotonic() - t0, 5)
        self.assertFalse(res.ok)
        self.assertIn("timeout", res.error)
        self.assertEqual(res.error, "timeout after 2s")
        self.assertEqual(res.sections, {})
        self.assertEqual(fakessh_running(), "")
        child = int(Path(f"{self.log}.child").read_text())
        self.assertFalse(alive(child), "the ssh's child survived: group not killed")

    def test_fail_is_not_empty_queue(self):
        self.set_mode("fail")
        res = poll()
        self.assertFalse(res.ok)
        self.assertEqual(res.sections, {})
        self.assertEqual(res.env, {})
        self.assertEqual(res.error, "Permission denied (keyboard-interactive).")

    def test_no_env_section_is_not_ok(self):
        # rc 0 but the stream carries no env frame: not ok
        with mock.patch.object(ssh, "run_remote", return_value=(0, "", "")):
            res = poll()
        self.assertFalse(res.ok)
        self.assertTrue(res.error)

    def test_truncated_env_is_not_ok(self):
        out = "@@dracmon begin env\nuser=jdoe\n"
        with mock.patch.object(ssh, "run_remote", return_value=(0, out, "")):
            res = poll()
        self.assertFalse(res.ok)
        self.assertNotIn("env", res.sections)


class RoundtripTests(FakeSshCase):
    def test_ok_roundtrip(self):
        res = poll(["queue", "accounting"])
        self.assertTrue(res.ok, res.error)
        self.assertIsNone(res.error)
        self.assertEqual(res.cluster, "testcluster")
        self.assertLessEqual(res.started, res.finished)
        self.assertEqual(res.requested, ["env", "queue", "accounting", "steps"])
        self.assertEqual(res.env["user"], "jdoe")
        self.assertEqual(res.env["cluster"], "testcluster")
        self.assertIn("tz", res.env)
        for name in ("env", "queue", "accounting", "steps"):
            self.assertTrue(res.sections[name].complete, name)
        self.assertIn("101|", res.sections["queue"].body)
        self.assertNotIn("disk", res.sections)


class BuildScriptTests(FakeSshCase):
    def run_script(self, script):
        return subprocess.run(["bash", "-s"], input=script, capture_output=True, text=True,
                              env=dict(os.environ), timeout=30)

    def preamble(self, script):
        remote = (HERE.parent / "dracmonlib" / "remote.sh").read_text()
        self.assertTrue(script.endswith(remote))
        return script[: len(script) - len(remote)]

    def test_sections_env_and_steps(self):
        s = ssh.build_script(["accounting"], "2026-11-15T00:00:00", {}, [], 30)
        self.assertIn("DRACMON_SECTIONS='env accounting steps'", s)
        s = ssh.build_script(["queue", "queue"], None, {}, [], 30)
        self.assertIn("DRACMON_SECTIONS='env queue'", s)
        self.assertTrue(s.rstrip().endswith("exit 0"))

    def test_preamble_quoting(self):
        canary = self.home / "canary"
        canary.write_text("x")
        pwned = self.tmp / "pwned"
        globs = [("camp", "x'; rm -rf ~"), ("camp2", f"$(touch {pwned})"),
                 ("camp3", f"`touch {pwned}`")]
        offsets = {"a'; rm -rf ~;'.log": 5, f"$(touch {pwned}).log": 3}
        s = ssh.build_script(["globs", "cells"], "x'; rm -rf ~", offsets, globs, 30)
        # five assignments, each one shell word
        words = shlex.split(self.preamble(s))
        self.assertEqual([w.split("=", 1)[0] for w in words],
                         ["DRACMON_SECTIONS", "DRACMON_SINCE", "DRACMON_OFFSETS",
                          "DRACMON_GLOBS", "DRACMON_CELLS_RETENTION"])
        self.assertEqual(words[1], "DRACMON_SINCE=x'; rm -rf ~")
        p = self.run_script(s)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(canary.exists())
        self.assertFalse(pwned.exists())
        self.assertIn("#glob camp 0", p.stdout)
        self.assertIn("#glob camp2 0", p.stdout)

    def test_preamble_values_roundtrip(self):
        offsets = {"c1/101.log": 120, "c 2/7.log": 0}
        globs = [("camp", "runs/*/done"), ("other", "a b/*.ok")]
        s = ssh.build_script(["globs"], "2026-11-15T00:00:00", offsets, globs, 12)
        probe = self.preamble(s) + (
            'printf "%s\\n--\\n" "$DRACMON_SECTIONS" "$DRACMON_SINCE" "$DRACMON_OFFSETS" '
            '"$DRACMON_GLOBS" "$DRACMON_CELLS_RETENTION"\n')
        p = self.run_script(probe)
        parts = p.stdout.split("\n--\n")
        self.assertEqual(parts[0], "env globs")
        self.assertEqual(parts[1], "2026-11-15T00:00:00")
        self.assertEqual(parts[2], "c1/101.log\t120\nc 2/7.log\t0")
        self.assertEqual(parts[3], "camp\truns/*/done\nother\ta b/*.ok")
        self.assertEqual(parts[4], "12")

    def test_unsafe_entries_dropped(self):
        s = ssh.build_script(["globs"], None, {"a\tb.log": 1, "x\ny.log": 2},
                             [("ca mp", "*"), ("c", "a\nb"), ("ok", "*")], 30)
        p = self.run_script(self.preamble(s) + 'printf "%s|%s" "$DRACMON_OFFSETS" "$DRACMON_GLOBS"\n')
        self.assertEqual(p.stdout, "|ok\t*")


class ControlPathTests(FakeSshCase):
    def test_control_path_tokens(self):
        os.environ["FAKE_SSH_CONTROLPATH"] = "~/.ssh/cm-%r@%h:%p-%n-%u-%d-%i-%l-%%-%C"
        pw = pwd.getpwuid(os.getuid())
        lhost = socket.gethostname()
        rhost = "testhost.example.invalid"
        chash = hashlib.sha1(f"{lhost}{rhost}22remoteuser".encode()).hexdigest()
        want = (f"{pw.pw_dir}/.ssh/cm-remoteuser@{rhost}:22-testhost-{pw.pw_name}-"
                f"{pw.pw_dir}-{os.getuid()}-{lhost}-%-{chash}")
        self.assertEqual(ssh.control_path("testhost"), Path(want))

    def test_expanded_path_kept(self):
        self.assertEqual(ssh.control_path("testhost"), self.socket)


class MasterTests(unittest.TestCase):
    def test_open_master(self):
        self.assertEqual(ssh.open_master_argv("narval"),
                         ["ssh", "-fN", "-o", "ControlMaster=yes", "narval"])
        with mock.patch.dict(os.environ, {"PATH": "/usr/bin"}):
            env = ssh.open_master_env(True)
            self.assertEqual(env["SSH_ASKPASS_REQUIRE"], "force")
            self.assertEqual(env["PATH"], "/usr/bin")
            self.assertNotIn("SSH_ASKPASS_REQUIRE", ssh.open_master_env(False))

    def test_askpass_available(self):
        exe = FAKEBIN / "ssh"
        with mock.patch.dict(os.environ, {"SSH_ASKPASS": str(exe), "DISPLAY": ":0"}):
            self.assertTrue(ssh.askpass_available())
        with mock.patch.dict(os.environ, {"SSH_ASKPASS": "/nonexistent/askpass", "DISPLAY": ":0"}):
            self.assertFalse(ssh.askpass_available())
        with mock.patch.dict(os.environ, {"SSH_ASKPASS": str(FAKEBIN)}):
            self.assertFalse(ssh.askpass_available())  # a directory is not executable
        env = {k: v for k, v in os.environ.items() if k not in ("SSH_ASKPASS", "DISPLAY")}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertFalse(ssh.askpass_available())
        env["SSH_ASKPASS"] = str(exe)
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(sys, "platform", "linux"):
                self.assertFalse(ssh.askpass_available())
            with mock.patch.object(sys, "platform", "darwin"):
                self.assertTrue(ssh.askpass_available())


if __name__ == "__main__":
    unittest.main()
