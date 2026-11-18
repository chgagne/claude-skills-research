"""Test helper: run with the fake ssh in tests/fakebin first on PATH.

Nothing here contacts a network: tests/fakebin/ssh runs the remote script
with the local bash, or fails/hangs on demand (FAKE_SSH_MODE)."""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

FAKEBIN = Path(__file__).resolve().parent / "fakebin"


class FakeSshCase(unittest.TestCase):
    mode = "ok"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.log = self.tmp / "fake.log"
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.socket = self.tmp / "sock"
        patcher = mock.patch.dict(os.environ, {
            "PATH": f"{FAKEBIN}:/usr/bin:/bin",
            "FAKEBIN_LOG": str(self.log),
            "FAKE_SSH_MODE": self.mode,
            "FAKE_SSH_CONTROLPATH": str(self.socket),
            "USER": "jdoe",
            "CC_CLUSTER": "testcluster",
            "SCRATCH": "",
            "HOME": str(self.home),
        })
        patcher.start()
        self.addCleanup(patcher.stop)

    def set_mode(self, mode):
        os.environ["FAKE_SSH_MODE"] = mode

    def make_socket(self):
        self.socket.write_text("")

    def argvs(self):
        if not self.log.exists():
            return []
        return [ln for ln in self.log.read_text().splitlines() if ln.startswith("ssh ")]

    def connecting_argvs(self):
        """ssh invocations other than the local config query `ssh -G`."""
        return [a for a in self.argvs() if " -G " not in f"{a} "]
