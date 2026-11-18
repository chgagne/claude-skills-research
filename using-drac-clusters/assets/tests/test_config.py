import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dracmonlib import config  # noqa: E402

DEFAULT_NAMES = ["narval", "rorqual", "fir", "nibi", "trillium", "tamia", "killarney", "vulcan"]


def write(text):
    d = tempfile.mkdtemp()
    p = Path(d) / "config.toml"
    p.write_text(text)
    return p


class ConfigTests(unittest.TestCase):
    def test_defaults_without_file(self):
        cfg = config.load_config(Path(tempfile.mkdtemp()) / "absent.toml")
        self.assertEqual([c.name for c in cfg.clusters], DEFAULT_NAMES)
        self.assertTrue(all(c.host == c.name and not c.pinned for c in cfg.clusters))
        self.assertEqual(cfg.cadence["queue"], 300)
        self.assertEqual(cfg.cadence["accounting"], 900)
        self.assertEqual(cfg.idle_release, 7200)
        self.assertEqual(cfg.released_check, 3600)
        self.assertEqual(cfg.ssh_timeout, 60)
        self.assertEqual(cfg.glob_campaigns, [])

    def test_toml_overrides(self):
        p = write('[cadence]\nqueue = 120\n\n[[cluster]]\nname="narval"\nhost="nv"\npinned=true\n')
        cfg = config.load_config(p)
        self.assertEqual(len(cfg.clusters), 1)
        self.assertEqual((cfg.clusters[0].name, cfg.clusters[0].host, cfg.clusters[0].pinned),
                         ("narval", "nv", True))
        self.assertEqual(cfg.cadence["queue"], 120)
        self.assertEqual(cfg.cadence["cells"], 300)
        self.assertEqual(cfg.cadence["disk"], 3600)

    def test_glob_campaign_parsed(self):
        p = write('[[glob_campaign]]\ncampaign="c1"\ncluster="fir"\ndone_glob="out/*.json"\ntotal=40\n')
        cfg = config.load_config(p)
        self.assertEqual(cfg.glob_campaigns,
                         [config.GlobCampaign("c1", "fir", "out/*.json", 40)])

    def test_xdg_paths(self):
        old = {k: os.environ.get(k) for k in ("XDG_STATE_HOME", "XDG_CONFIG_HOME")}
        try:
            d = tempfile.mkdtemp()
            os.environ["XDG_STATE_HOME"] = d
            os.environ["XDG_CONFIG_HOME"] = "/cfg"
            self.assertEqual(config.state_dir(), Path(d) / "dracmon")
            self.assertTrue((Path(d) / "dracmon").is_dir())
            self.assertEqual(config.config_path(), Path("/cfg/dracmon/config.toml"))
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_unknown_key_rejected(self):
        for text, key in [
            ('bogus = 1\n', "bogus"),
            ('[cadence]\nnope = 1\n', "nope"),
            ('[[cluster]]\nname="a"\nhost="a"\nfoo=1\n', "foo"),
            ('[[glob_campaign]]\ncampaign="a"\ncluster="b"\ndone_glob="x"\ntotal=1\nzap=2\n', "zap"),
        ]:
            with self.assertRaises(ValueError) as cm:
                config.load_config(write(text))
            self.assertIn(key, str(cm.exception))


if __name__ == "__main__":
    unittest.main()
