import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ASSETS))

from dracmonlib import launcher  # noqa: E402


class RenderTests(unittest.TestCase):
    def test_launcher_is_posix_sh_pointing_at_entry(self):
        text = launcher.render(Path("/opt/skills x/assets/dracmon.py"))
        self.assertTrue(text.startswith("#!/bin/sh\n"))
        self.assertIn("'/opt/skills x/assets/dracmon.py'", text)
        self.assertIn('exec "$uv" run --quiet --script', text)
        self.assertIn('"$@"', text)

    def test_quotes_single_quote_in_path(self):
        text = launcher.render(Path("/a/it's/dracmon.py"))
        self.assertIn("'/a/it'\\''s/dracmon.py'", text)

    def test_launcher_runs_and_passes_arguments(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            fake_uv = d / "uv"
            fake_uv.write_text('#!/bin/sh\nprintf "%s|" "$@"\n')
            fake_uv.chmod(0o755)
            entry = d / "dracmon.py"
            entry.write_text("")
            script = d / "dracmon"
            script.write_text(launcher.render(entry))
            script.chmod(0o755)
            out = subprocess.run([str(script), "doctor", "a b"], capture_output=True,
                                 text=True, env={"PATH": f"{d}:/usr/bin:/bin"})
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(out.stdout, f"run|--quiet|--script|{entry}|doctor|a b|")

    def test_launcher_reports_missing_entry(self):
        with tempfile.TemporaryDirectory() as d:
            script = Path(d) / "dracmon"
            script.write_text(launcher.render(Path(d) / "gone.py"))
            script.chmod(0o755)
            out = subprocess.run([str(script)], capture_output=True, text=True,
                                 env={"PATH": "/usr/bin:/bin"})
            self.assertNotEqual(out.returncode, 0)
            self.assertIn("not found", out.stderr)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name) / "bin"

    def tearDown(self):
        self.tmp.cleanup()

    def test_install_creates_executable_and_reports_path(self):
        rc, msg = launcher.install(self.dir, path_env="/usr/bin")
        target = self.dir / "dracmon"
        self.assertEqual(rc, 0)
        self.assertTrue(target.exists())
        self.assertTrue(target.stat().st_mode & stat.S_IXUSR)
        self.assertIn("not on your PATH", msg)
        self.assertIn(f'export PATH="{self.dir}:$PATH"', msg)

    def test_install_on_path_says_so(self):
        rc, msg = launcher.install(self.dir, path_env=f"/usr/bin:{self.dir}")
        self.assertEqual(rc, 0)
        self.assertNotIn("not on your PATH", msg)
        self.assertIn("run: dracmon", msg)

    def test_refuses_to_overwrite_a_different_file(self):
        self.dir.mkdir(parents=True)
        (self.dir / "dracmon").write_text("#!/bin/sh\necho mine\n")
        rc, msg = launcher.install(self.dir, path_env="")
        self.assertEqual(rc, 1)
        self.assertIn("--force", msg)
        self.assertEqual((self.dir / "dracmon").read_text(), "#!/bin/sh\necho mine\n")

    def test_force_overwrites_and_identical_is_fine(self):
        self.dir.mkdir(parents=True)
        (self.dir / "dracmon").write_text("old")
        self.assertEqual(launcher.install(self.dir, path_env="", force=True)[0], 0)
        self.assertEqual(launcher.install(self.dir, path_env="")[0], 0)  # identical now

    def test_never_edits_shell_config(self):
        home = Path(self.tmp.name) / "home"
        home.mkdir()
        rc = home / ".zshrc"
        rc.write_text("# mine\n")
        old = os.environ.get("HOME")
        os.environ["HOME"] = str(home)
        try:
            launcher.install(self.dir, path_env="")
        finally:
            if old is None:
                del os.environ["HOME"]
            else:
                os.environ["HOME"] = old
        self.assertEqual(rc.read_text(), "# mine\n")


class CliTests(unittest.TestCase):
    def test_cli_wires_install_launcher(self):
        with tempfile.TemporaryDirectory() as d:
            out = subprocess.run([sys.executable, str(ASSETS / "dracmon.py"),
                                  "install-launcher", "--dir", d],
                                 capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertTrue((Path(d) / "dracmon").exists())


if __name__ == "__main__":
    unittest.main()
