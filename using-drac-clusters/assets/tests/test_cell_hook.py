import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ASSETS))

PY = str(ASSETS / "dracmon_cell.py")
SH = str(ASSETS / "dracmon-cell")


def make_env(scratch, **extra):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("SLURM_") and k not in ("SCRATCH", "DRACMON_CAMPAIGN")}
    if scratch is not None:
        env["SCRATCH"] = scratch
    env.update(extra)
    return env


def run(cmd, env):
    return subprocess.run(cmd, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=60)


def read_lines(scratch, campaign, name):
    p = Path(scratch) / ".dracmon" / "cells" / campaign / (name + ".log")
    return p.read_bytes().split(b"\n")


class CellHookTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.scratch = self.td.name
        self.addCleanup(self.td.cleanup)

    def test_python_writes_line(self):
        env = make_env(self.scratch, SLURM_JOB_ID="42", DRACMON_CAMPAIGN="camp")
        r = run([sys.executable, PY, "start", "cellA"], env)
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, b"", b""))
        run([sys.executable, PY, "plan", "48"], env)
        lines = read_lines(self.scratch, "camp", "42")
        self.assertEqual(lines[-1], b"")
        f = lines[0].split(b"\t")
        self.assertEqual(len(f), 5)
        self.assertTrue(f[0].isdigit())
        self.assertEqual(f[1:], [b"42", b"start", b"cellA", b""])
        f = lines[1].split(b"\t")
        self.assertEqual(f[1:], [b"42", b"plan", b"", b"48"])

    def test_array_jobid_and_fallbacks(self):
        env = make_env(self.scratch, SLURM_JOB_ID="9", SLURM_ARRAY_JOB_ID="7",
                       SLURM_ARRAY_TASK_ID="3", DRACMON_CAMPAIGN="c")
        run([sys.executable, PY, "done", "x"], env)
        self.assertEqual(read_lines(self.scratch, "c", "7_3")[0].split(b"\t")[1], b"7_3")
        env = make_env(self.scratch, DRACMON_CAMPAIGN="c")
        run([sys.executable, PY, "done", "x"], env)
        run([SH, "done", "x"], env)
        self.assertEqual(len(read_lines(self.scratch, "c", "local")), 3)
        env = make_env(self.scratch, SLURM_JOB_NAME="jn")
        run([sys.executable, PY, "done", "x"], env)
        self.assertTrue((Path(self.scratch) / ".dracmon/cells/jn/local.log").exists())
        run([sys.executable, PY, "done", "x"], make_env(self.scratch))
        self.assertTrue((Path(self.scratch) / ".dracmon/cells/default/local.log").exists())

    def test_shell_writes_identical_format(self):
        cases = [
            (["plan", "48"], {}),
            (["start", "a\tb\nc"], {}),
            (["done", "cell-1"], {"SLURM_JOB_ID": "5"}),
            (["fail", "cell", "bad\treason\nhere"], {"SLURM_ARRAY_JOB_ID": "1", "SLURM_ARRAY_TASK_ID": "2"}),
            (["fail", "cell"], {}),
            (["fail", "céll", "réason " + "x" * 700], {}),
            (["start", "y" * 600], {}),
        ]
        for i, (args, extra) in enumerate(cases):
            camp = "my camp/éx"
            sa, sb = Path(self.scratch) / ("a%d" % i), Path(self.scratch) / ("b%d" % i)
            sa.mkdir(); sb.mkdir()
            ea = make_env(str(sa), DRACMON_CAMPAIGN=camp, **extra)
            eb = make_env(str(sb), DRACMON_CAMPAIGN=camp, **extra)
            ra = run([sys.executable, PY] + args, ea)
            rb = run([SH] + args, eb)
            self.assertEqual((ra.returncode, rb.returncode), (0, 0))
            self.assertEqual((rb.stdout, rb.stderr), (b"", b""))
            fa = sorted(Path(sa).rglob("*.log"))
            fb = sorted(Path(sb).rglob("*.log"))
            self.assertEqual([p.relative_to(sa) for p in fa], [p.relative_to(sb) for p in fb])
            la = fa[0].read_bytes().split(b"\t", 1)[1]
            lb = fb[0].read_bytes().split(b"\t", 1)[1]
            self.assertEqual(la, lb, args)
            self.assertLessEqual(len(fa[0].read_bytes()), 512)
            self.assertTrue(la.endswith(b"\n"))
            self.assertEqual(la.count(b"\n"), 1)
            if len(fa[0].read_bytes()) < 512:
                self.assertEqual(la.count(b"\t"), 3)

    def test_truncation(self):
        env = make_env(self.scratch, DRACMON_CAMPAIGN="t", SLURM_JOB_ID="1")
        run([sys.executable, PY, "start", "y" * 600], env)
        data = (Path(self.scratch) / ".dracmon/cells/t/1.log").read_bytes()
        self.assertEqual(len(data), 512)

    def test_context_manager_records_fail_and_reraises(self):
        import dracmon_cell
        env = make_env(self.scratch, SLURM_JOB_ID="8", DRACMON_CAMPAIGN="cm")
        with mock.patch.dict(os.environ, env, clear=True):
            with dracmon_cell.cell("ok"):
                pass
            with self.assertRaises(ValueError):
                with dracmon_cell.cell("boom"):
                    raise ValueError("bad\tthing")
            dracmon_cell.fail("direct", "why")
            dracmon_cell.plan(3)
        lines = [l.split(b"\t") for l in read_lines(self.scratch, "cm", "8") if l]
        self.assertEqual([(l[2], l[3]) for l in lines],
                         [(b"start", b"ok"), (b"done", b"ok"), (b"start", b"boom"),
                          (b"fail", b"boom"), (b"fail", b"direct"), (b"plan", b"")])
        self.assertEqual(lines[3][4], b"ValueError: bad thing")
        self.assertEqual(lines[4][4], b"why")

    def test_no_scratch_is_silent_noop(self):
        for cmd in ([sys.executable, PY, "start", "x"], [SH, "start", "x"]):
            for scratch in (None, ""):
                env = make_env(scratch)
                if scratch is None:
                    env.pop("SCRATCH", None)
                before = set(Path(self.scratch).rglob("*"))
                r = run(cmd, env)
                self.assertEqual((r.returncode, r.stdout, r.stderr), (0, b"", b""))
                self.assertEqual(before, set(Path(self.scratch).rglob("*")))

    def test_unwritable_is_silent_noop(self):
        blocker = Path(self.scratch) / "file"
        blocker.write_text("x")
        for scratch in (str(blocker), "/nonexistent/definitely/not"):
            for cmd in ([sys.executable, PY, "fail", "x", "r"], [SH, "fail", "x", "r"],
                        [sys.executable, PY, "bogus"], [SH, "bogus"], [SH], [sys.executable, PY]):
                r = run(cmd, make_env(scratch))
                self.assertEqual((r.returncode, r.stdout, r.stderr), (0, b"", b""), cmd)

    def test_concurrent_appends_not_interleaved(self):
        for cmd in ("py", "sh"):
            scratch = Path(self.scratch) / cmd
            scratch.mkdir()
            env = make_env(str(scratch), SLURM_JOB_ID="1", DRACMON_CAMPAIGN="cc")
            if cmd == "py":
                code = ("import sys; sys.path.insert(0, %r); import dracmon_cell as d\n"
                        "for i in range(200): d.start('cell-%%d-' %% i + 'z' * 100)\n" % str(ASSETS))
                argv = [sys.executable, "-c", code]
            else:
                argv = ["sh", "-c", 'i=0; while [ $i -lt 200 ]; do %s start "cell-$i-%s"; i=$((i+1)); done'
                        % (SH, "z" * 100)]
            procs = [subprocess.Popen(argv, env=env) for _ in range(8)]
            for p in procs:
                self.assertEqual(p.wait(timeout=120), 0)
            lines = read_lines(str(scratch), "cc", "1")
            self.assertEqual(lines[-1], b"")
            lines = lines[:-1]
            self.assertEqual(len(lines), 1600)
            for l in lines:
                f = l.split(b"\t")
                self.assertEqual(len(f), 5, l)
                self.assertEqual(f[2], b"start")

    def test_campaign_sanitised(self):
        for cmd in ([sys.executable, PY], [SH]):
            env = make_env(self.scratch, SLURM_JOB_ID="3", DRACMON_CAMPAIGN="a b/../c:d.e-f_g")
            run(cmd + ["start", "x"], env)
        d = Path(self.scratch) / ".dracmon/cells"
        self.assertEqual([p.name for p in d.iterdir()], ["a_b_.._c_d.e-f_g"])
        self.assertEqual(len(read_lines(self.scratch, "a_b_.._c_d.e-f_g", "3")), 3)


if __name__ == "__main__":
    unittest.main()
