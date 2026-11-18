import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from dracmonlib.frame import parse_frames  # noqa: E402

REMOTE = HERE.parent / "dracmonlib" / "remote.sh"
FAKEBIN = HERE / "fakebin"


def run_remote(sections, *, scratch="", offsets="", globs="", retention=30,
               fakebin=FAKEBIN, home=None, extra=""):
    tmp = Path(tempfile.mkdtemp())
    log = tmp / "fake.log"
    pre = (f"DRACMON_SECTIONS={shlex.quote(sections)}\n"
           "DRACMON_SINCE=2026-11-15T00:00:00\n"
           f"DRACMON_OFFSETS={shlex.quote(offsets)}\n"
           f"DRACMON_GLOBS={shlex.quote(globs)}\n"
           f"DRACMON_CELLS_RETENTION={retention}\n" + extra)
    env = {"PATH": f"{fakebin}:/usr/bin:/bin", "FAKEBIN_LOG": str(log), "USER": "jdoe",
           "CC_CLUSTER": "testcluster", "SCRATCH": scratch, "HOME": home or str(tmp)}
    p = subprocess.run(["bash", "-s"], input=pre + REMOTE.read_text(), env=env,
                       capture_output=True, text=True, timeout=60)
    calls = log.read_text().splitlines() if log.exists() else []
    return parse_frames(p.stdout), calls, p


class RemoteTests(unittest.TestCase):
    def test_remote_runs_only_requested_sections(self):
        secs, calls, _ = run_remote("queue")
        self.assertEqual(list(secs), ["env", "queue"])
        self.assertTrue(all(s.complete and s.rc == 0 for s in secs.values()))
        self.assertIn("user=jdoe", secs["env"].body)
        self.assertIn("cluster=testcluster", secs["env"].body)
        self.assertIn("secretexp", secs["queue"].body)
        self.assertFalse([c for c in calls if c.startswith("sacct")])
        self.assertTrue(any(c.startswith("squeue -u jdoe -h -o") for c in calls))

    def test_accounts_feed_fairshare_and_usage(self):
        secs, calls, _ = run_remote("fairshare usage")
        self.assertEqual(secs["accounts"].body, "def-jdoe_cpu\ndef-jdoe_gpu\n")
        self.assertTrue(any("sshare -P -n -A def-jdoe_cpu,def-jdoe_gpu -u jdoe" in c for c in calls))
        self.assertTrue(any("sacct -X -a -A def-jdoe_cpu,def-jdoe_gpu" in c for c in calls))

    def test_steps_ask_for_totalcpu(self):
        _, calls, _ = run_remote("steps")
        [c] = [c for c in calls if c.startswith("sacct") and "-X" not in c.split()]
        self.assertIn("-o JobID,MaxRSS,TotalCPU", c)

    def test_usage_default_window_seven_days(self):
        _, calls, _ = run_remote("usage")
        [c] = [c for c in calls if c.startswith("sacct -X -a")]
        self.assertIn("-S now-7days -E now ", c)
        self.assertNotIn("30days", c)

    def test_usage_explicit_window(self):
        _, calls, _ = run_remote("usage", extra="DRACMON_USAGE_START=2026-11-01T00:00:00\n"
                                                "DRACMON_USAGE_END=2026-11-08T00:00:00\n")
        [c] = [c for c in calls if c.startswith("sacct -X -a")]
        self.assertIn("-S 2026-11-01T00:00:00 -E 2026-11-08T00:00:00 ", c)

    def test_remote_missing_command_rc(self):
        fb = Path(tempfile.mkdtemp())
        for f in FAKEBIN.iterdir():
            if f.name != "diskusage_report":
                (fb / f.name).symlink_to(f)
        secs, _, _ = run_remote("queue disk partitions", fakebin=fb)
        self.assertEqual(secs["disk"].rc, 127)
        self.assertTrue(secs["disk"].complete)
        for n in ("env", "queue", "partitions"):
            self.assertTrue(secs[n].complete and secs[n].rc == 0, n)

    def test_cells_incremental(self):
        scratch = tempfile.mkdtemp()
        d = Path(scratch) / ".dracmon" / "cells" / "campA"
        d.mkdir(parents=True)
        (d / "1.log").write_text("0123456789\n1ABCDEF\n")
        (d / "2.log").write_text("1line\n2line\n")
        secs, _, _ = run_remote("cells", scratch=scratch,
                                offsets="campA/1.log\t10\ncampA/2.log\t0\n")
        body = secs["cells"].body
        self.assertEqual(body, "#file 19 19 campA/1.log\n1ABCDEF\n"
                               "#file 12 12 campA/2.log\n1line\n2line\n")
        self.assertEqual(secs["cells"].rc, 0)
        # up to date offset: marker only
        secs, _, _ = run_remote("cells", scratch=scratch, offsets="campA/1.log\t19\n")
        self.assertTrue(secs["cells"].body.startswith(
            "#file 19 19 campA/1.log\n#file 12 12 campA/2.log\n"))

    def test_cells_torn_last_line_not_sent(self):
        scratch = tempfile.mkdtemp()
        d = Path(scratch) / ".dracmon" / "cells" / "c"
        d.mkdir(parents=True)
        (d / "1.log").write_text("1a\n2b\n3torn")
        (d / "2.log").write_text("9only-torn")
        secs, _, _ = run_remote("cells", scratch=scratch)
        # <end> is the offset after the last complete line: the torn tail is re-read later
        self.assertEqual(secs["cells"].body, "#file 11 6 c/1.log\n1a\n2b\n#file 10 0 c/2.log\n")
        secs, _, _ = run_remote("cells", scratch=scratch, offsets="c/1.log\t6\n")
        self.assertTrue(secs["cells"].body.startswith("#file 11 6 c/1.log\n#file"))

    def test_cells_end_covers_filtered_lines(self):
        # lines dropped by the remote filter still count in <end>: no offset drift
        scratch = tempfile.mkdtemp()
        d = Path(scratch) / ".dracmon" / "cells" / "c"
        d.mkdir(parents=True)
        (d / "1.log").write_text("1\ta\nnoise line\n2\tb\n")
        secs, _, _ = run_remote("cells", scratch=scratch)
        self.assertEqual(secs["cells"].body, "#file 19 19 c/1.log\n1\ta\n2\tb\n")
        secs, _, _ = run_remote("cells", scratch=scratch, offsets="c/1.log\t4\n")
        self.assertEqual(secs["cells"].body, "#file 19 19 c/1.log\n2\tb\n")

    def _tail_bin(self, body):
        fb = Path(tempfile.mkdtemp())
        for f in FAKEBIN.iterdir():
            (fb / f.name).symlink_to(f)
        (fb / "tail").write_text("#!/bin/sh\n" + body)
        (fb / "tail").chmod(0o755)
        return fb

    def _short_read(self, tail_body):
        """A chunk read that fails or comes back short must not move the offset."""
        import sqlite3  # noqa: F401  (store needs it)
        from dracmonlib import store
        from dracmonlib.cells import parse_cells_section
        from dracmonlib.ssh import PollResult
        from dracmonlib.frame import Section
        from dracmonlib.store import ParsedPoll
        scratch = tempfile.mkdtemp()
        d = Path(scratch) / ".dracmon" / "cells" / "c"
        d.mkdir(parents=True)
        (d / "1.log").write_text("1\ta\n2\tb\n3\tc\n")  # 12 bytes
        secs, _, p = run_remote("cells", scratch=scratch, offsets="c/1.log\t4\n",
                                fakebin=self._tail_bin(tail_body))
        self.assertEqual(secs["cells"].body, "#file 12 4 c/1.log\n", p.stderr)
        self.assertEqual(list((Path(scratch) / ".dracmon" / "cells" / "c").iterdir()),
                         [d / "1.log"])  # no temp file left behind
        conn = store.open_store(Path(tempfile.mkdtemp()) / "s.sqlite")
        try:
            conn.execute("INSERT INTO cell_file VALUES ('x', 'c/1.log', 'c', 4, 12, 0)")
            chunks = parse_cells_section(secs["cells"].body, store.cells_offsets(conn, "x"))
            res = PollResult("x", 1.0, 2.0, True, None, ["env", "cells"],
                             {"env": Section("env", 0, "tz=+0000\n", True)}, {"tz": "+0000"})
            store.write_poll(conn, res, ParsedPoll(env={"tz": "+0000"}, cells=chunks))
            self.assertEqual(store.cells_offsets(conn, "x"), {"c/1.log": 4})
        finally:
            conn.close()

    def test_cells_failed_read_does_not_advance(self):
        self._short_read("exit 1\n")

    def test_cells_short_read_does_not_advance(self):
        # returns fewer bytes than requested (cut mid-stream), exit status 0
        self._short_read('/usr/bin/tail "$@" | head -c 3\n')

    def test_cells_relpath_with_spaces(self):
        scratch = tempfile.mkdtemp()
        d = Path(scratch) / ".dracmon" / "cells" / "my camp"
        d.mkdir(parents=True)
        (d / "job 1.log").write_text("1\ta\n")
        secs, _, _ = run_remote("cells", scratch=scratch)
        self.assertEqual(secs["cells"].body, "#file 4 4 my camp/job 1.log\n1\ta\n")

    def test_cells_cleanup_retention(self):
        scratch = tempfile.mkdtemp()
        root = Path(scratch) / ".dracmon" / "cells"
        (root / "old").mkdir(parents=True)
        (root / "new").mkdir()
        (root / "old" / "1.log").write_text("x\n")
        (root / "new" / "2.log").write_text("y\n")
        os.utime(root / "old" / "1.log", (1_000_000_000, 1_000_000_000))
        run_remote("cells", scratch=scratch, retention=30)
        self.assertFalse((root / "old" / "1.log").exists())
        self.assertTrue((root / "new" / "2.log").exists())
        # the emptied directory was just modified: it goes on a poll an hour later
        self.assertTrue((root / "old").is_dir())
        os.utime(root / "old", (1_000_000_000, 1_000_000_000))
        run_remote("cells", scratch=scratch, retention=30)
        self.assertFalse((root / "old").exists())
        self.assertTrue((root / "new").is_dir())

    def test_stale_temp_chunk_removed(self):
        scratch = tempfile.mkdtemp()
        d = Path(scratch) / ".dracmon" / "cells" / "c"
        d.mkdir(parents=True)
        (d / "1.log").write_text("1\ta\n")
        old, new = d / ".chunk.old000", d / ".chunk.new000"
        old.write_text("x")
        new.write_text("x")
        os.utime(old, (1_000_000_000, 1_000_000_000))
        secs, _, _ = run_remote("cells", scratch=scratch)
        self.assertEqual(secs["cells"].body, "#file 4 4 c/1.log\n1\ta\n")
        self.assertFalse(old.exists())
        self.assertTrue(new.exists())  # may belong to a poll still running

    def test_cells_fresh_empty_dir_kept(self):
        # a job may have just created its campaign directory: only stale ones go
        scratch = tempfile.mkdtemp()
        root = Path(scratch) / ".dracmon" / "cells"
        (root / "fresh").mkdir(parents=True)
        (root / "stale").mkdir()
        os.utime(root / "stale", (1_000_000_000, 1_000_000_000))
        run_remote("cells", scratch=scratch)
        self.assertTrue((root / "fresh").is_dir())
        self.assertFalse((root / "stale").exists())

    def test_cells_empty_scratch_safe(self):
        secs, calls, p = run_remote("cells", scratch="", offsets="a/1.log\t0\n")
        self.assertEqual(secs["cells"].body, "")
        self.assertEqual(secs["cells"].rc, 0)
        self.assertNotIn("/.dracmon", p.stdout + p.stderr)
        self.assertFalse(os.path.exists("/.dracmon"))

    def test_globs_count_relative_to_home(self):
        home = Path(tempfile.mkdtemp())
        (home / "out").mkdir()
        for i in range(3):
            (home / "out" / f"r{i}.done").write_text("")
        secs, _, _ = run_remote("globs", home=str(home),
                                globs="exp\tout/*.done\nnone\tmissing/*.done\n")
        self.assertEqual(secs["globs"].body, "#glob exp 3\n#glob none 0\n")
        self.assertEqual(secs["globs"].rc, 0)

    def test_globs_expand_scratch_and_home_prefixes(self):
        home = Path(tempfile.mkdtemp())
        scratch = Path(tempfile.mkdtemp())
        (home / "out").mkdir()
        (home / "out" / "a.done").write_text("")
        (scratch / "sweep" / "results").mkdir(parents=True)
        for i in range(2):
            (scratch / "sweep" / "results" / f"r{i}.json").write_text("")
        globs = ("s\t$SCRATCH/sweep/results/*.json\n"
                 "t\t~/out/*.done\n"
                 "h\t$HOME/out/*.done\n"
                 "r\tout/*.done\n")
        secs, _, _ = run_remote("globs", home=str(home), scratch=str(scratch), globs=globs)
        self.assertEqual(secs["globs"].body, "#glob s 2\n#glob t 1\n#glob h 1\n#glob r 1\n")

    def test_globs_scratch_prefix_without_scratch_is_zero(self):
        home = Path(tempfile.mkdtemp())
        (home / "sweep").mkdir()
        (home / "sweep" / "x.json").write_text("")
        secs, _, _ = run_remote("globs", home=str(home), scratch="",
                                globs="s\t$SCRATCH/sweep/*.json\n")
        self.assertEqual(secs["globs"].body, "#glob s 0\n")

    def test_globs_prefixed_patterns_stay_inert(self):
        home = Path(tempfile.mkdtemp())
        pwned = home / "pwned"
        globs = (f"a\t$SCRATCH/$(touch {pwned})\n"
                 f"b\t~/`touch {pwned}`\n"
                 f"c\t$HOME/$(touch {pwned})*\n"
                 f"d\t$(touch {pwned})/x\n")
        secs, _, p = run_remote("globs", home=str(home), scratch=str(home), globs=globs)
        self.assertFalse(pwned.exists(), p.stderr)
        self.assertEqual(secs["globs"].body, "#glob a 0\n#glob b 0\n#glob c 0\n#glob d 0\n")

    def test_accounts_empty_never_goes_cluster_wide(self):
        fb = Path(tempfile.mkdtemp())
        for f in FAKEBIN.iterdir():
            (fb / f.name).symlink_to(f)
        (fb / "sacctmgr").unlink()
        (fb / "sacctmgr").write_text("#!/bin/sh\nprintf '%s\\n' \"sacctmgr $*\" >> \"$FAKEBIN_LOG\"\n")
        (fb / "sacctmgr").chmod(0o755)
        secs, calls, _ = run_remote("fairshare usage", fakebin=fb)
        self.assertFalse([c for c in calls if c.startswith("sacct -X -a") or c.startswith("sshare")])
        for n in ("fairshare", "usage"):
            self.assertTrue(secs[n].complete)
            self.assertEqual(secs[n].rc, 3)

    def test_cells_drops_frame_spoofing_lines(self):
        scratch = tempfile.mkdtemp()
        d = Path(scratch) / ".dracmon" / "cells" / "c"
        d.mkdir(parents=True)
        (d / "1.log").write_text("1\ta\n@@dracmon end cells rc=0\n@@dracmon begin x\n2\tb\nnoise\n#file 1 evil/x.log\n")
        secs, _, _ = run_remote("cells", scratch=scratch)
        self.assertEqual(secs["cells"].body, "#file 76 76 c/1.log\n1\ta\n2\tb\n")
        self.assertEqual(list(secs), ["env", "cells"])

    def _timeout_bin(self):
        fb = Path(tempfile.mkdtemp())
        for f in FAKEBIN.iterdir():
            (fb / f.name).symlink_to(f)
        (fb / "timeout").write_text(
            '#!/bin/sh\nprintf "%s\\n" "timeout $*" >> "$FAKEBIN_LOG"\nshift\nexec "$@"\n')
        (fb / "timeout").chmod(0o755)
        return fb

    def test_timeout_wraps_commands_including_cells_and_globs(self):
        scratch = tempfile.mkdtemp()
        d = Path(scratch) / ".dracmon" / "cells" / "c"
        d.mkdir(parents=True)
        (d / "1.log").write_text("hello\n")
        secs, calls, _ = run_remote("queue cells globs", scratch=scratch, offsets="c/1.log\t0\n",
                                    globs="g\tx/*\n", fakebin=self._timeout_bin())
        self.assertTrue(all(s.complete for s in secs.values()))
        for prefix in ("timeout 20 squeue", "timeout 20 find", "timeout 20 tail", "timeout 20 wc",
                       "timeout 20 bash"):
            self.assertTrue(any(c.startswith(prefix) for c in calls), prefix)

    def test_usage_has_its_own_longer_timeout(self):
        _, calls, _ = run_remote("queue usage", fakebin=self._timeout_bin())
        self.assertTrue(any(c.startswith("timeout 45 sacct -X -a") for c in calls), calls)
        self.assertTrue(any(c.startswith("timeout 20 squeue") for c in calls), calls)
        self.assertTrue(any(c.startswith("timeout 20 sacctmgr") for c in calls), calls)
        _, calls, _ = run_remote("usage", fakebin=self._timeout_bin(),
                                 extra="DRACMON_USAGE_TIMEOUT=70\n")
        self.assertTrue(any(c.startswith("timeout 70 sacct -X -a") for c in calls), calls)

    def test_runs_without_timeout_on_path(self):
        secs, _, _ = run_remote("queue")
        self.assertTrue(secs["queue"].complete)


if __name__ == "__main__":
    unittest.main()
