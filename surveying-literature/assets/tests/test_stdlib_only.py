import unittest, pathlib, re

ALLOWED = {"argparse", "csv", "datetime", "dataclasses", "gzip", "hashlib", "html",
           "io", "json", "math", "os", "re", "shutil", "statistics", "subprocess",
           "sys", "tarfile", "tempfile", "time", "unicodedata", "urllib", "xml",
           "scholarly"}

ROOT = pathlib.Path(__file__).resolve().parents[1] / "survey"


class TestStdlibOnly(unittest.TestCase):
    def test_no_third_party_imports(self):
        bad = []
        for p in sorted(ROOT.glob("*.py")):
            for line in p.read_text().splitlines():
                m = re.match(r"\s*(?:from|import)\s+([A-Za-z_][\w.]*)", line)
                if m and m.group(1).split(".")[0] not in ALLOWED:
                    bad.append(f"{p.name}: {line.strip()}")
        self.assertEqual(bad, [], f"third-party imports found: {bad}")


if __name__ == "__main__":
    unittest.main()
