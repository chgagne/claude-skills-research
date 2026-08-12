import unittest, pathlib, re

ALLOWED = {"argparse", "csv", "dataclasses", "hashlib", "html", "io", "json", "os", "re",
           "sys", "time", "unicodedata", "urllib", "xml", "scholarly"}

ROOTS = [pathlib.Path(__file__).resolve().parents[1] / "bibcheck",
         pathlib.Path.home() / ".claude" / "skills" / "_shared" / "scholarly"]


class TestStdlibOnly(unittest.TestCase):
    def test_no_third_party_imports(self):
        bad = []
        for root in ROOTS:
            for p in sorted(root.glob("*.py")):
                for line in p.read_text().splitlines():
                    m = re.match(r"\s*(?:from|import)\s+([A-Za-z_][\w.]*)", line)
                    if m:
                        top = m.group(1).split(".")[0]
                        if top not in ALLOWED:
                            bad.append(f"{root.name}/{p.name}: {line.strip()}")
        self.assertEqual(bad, [], f"third-party imports found: {bad}")


if __name__ == "__main__":
    unittest.main()
