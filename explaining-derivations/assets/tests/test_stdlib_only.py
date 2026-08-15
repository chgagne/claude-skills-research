"""Stdlib-only guard, parsed with `ast` rather than matched line by line."""
import unittest, ast, pathlib

ALLOWED = {"argparse", "ast", "csv", "datetime", "dataclasses", "decimal",
           "fractions", "functools", "hashlib", "io", "itertools", "json",
           "math", "os", "random", "re", "shutil", "statistics", "subprocess",
           "sys", "tempfile", "textwrap", "time", "unicodedata",
           "latexmath", "scholarly"}

ROOT = pathlib.Path(__file__).resolve().parents[1] / "explain"


def real_imports(path):
    out = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            out += [(a.name.split(".")[0], node.lineno) for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            out.append((node.module.split(".")[0], node.lineno))
    return out


class TestStdlibOnly(unittest.TestCase):
    def test_no_third_party_imports(self):
        bad = ["%s:%d imports %s" % (p.name, line, mod)
               for p in sorted(ROOT.glob("*.py"))
               for mod, line in real_imports(p) if mod not in ALLOWED]
        self.assertEqual(bad, [], "third-party imports found: %s" % bad)


class TestTemplatesShip(unittest.TestCase):
    def test_every_template_referenced_by_assemble_exists(self):
        tpl = ROOT.parent / "templates"
        for name in ("derivation.tex.in", "preamble.tex"):
            self.assertTrue((tpl / name).exists(), "missing template %s" % name)

    def test_the_preamble_defines_the_macros_the_assembler_emits(self):
        body = (ROOT.parent / "templates" / "preamble.tex").read_text()
        for macro in (r"\newcommand{\stepblock}", r"\newcommand{\stepgap}"):
            self.assertIn(macro, body, "preamble does not define %s" % macro)


if __name__ == "__main__":
    unittest.main()
