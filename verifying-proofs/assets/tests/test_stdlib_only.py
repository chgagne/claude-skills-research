"""The guard that keeps the dependency policy honest.

SymPy and Z3 are *optional external checkers*, probed at runtime and executed in
a subprocess. The moment one of them appears in a real import statement in this
package, the skill has silently acquired a hard dependency and the README's "no
dependencies" claim has become false.

This parses with `ast` rather than matching lines, unlike the sibling skills'
version of this test. Those packages contain no source strings; this one carries
the check-script harnesses as text, and a line-based guard reports `import sympy`
inside a string literal as a dependency. A guard that cries wolf about its own
source gets edited into uselessness, so it reads the syntax tree instead.
"""
import unittest, ast, pathlib

ALLOWED = {"argparse", "ast", "csv", "datetime", "dataclasses", "decimal",
           "fractions", "functools", "hashlib", "io", "itertools", "json",
           "math", "os", "random", "re", "resource", "shutil", "statistics",
           "subprocess", "sys", "tempfile", "textwrap", "time", "unicodedata",
           "latexmath", "scholarly"}

CHECKERS = {"sympy", "z3", "jax", "numpy", "scipy", "torch"}

ROOT = pathlib.Path(__file__).resolve().parents[1] / "proofcheck"


def real_imports(path):
    """(module, lineno) for every import actually executed by this file."""
    tree = ast.parse(path.read_text())
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out.append((a.name.split(".")[0], node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                out.append((node.module.split(".")[0], node.lineno))
    return out


def sources():
    return sorted(list(ROOT.glob("*.py")) + list(ROOT.glob("*/*.py")))


class TestStdlibOnly(unittest.TestCase):
    def test_no_third_party_imports(self):
        bad = ["%s:%d imports %s" % (p.name, line, mod)
               for p in sources() for mod, line in real_imports(p)
               if mod not in ALLOWED]
        self.assertEqual(bad, [], "third-party imports found: %s" % bad)

    def test_the_harness_never_imports_a_checker(self):
        """Named separately because it is the whole dependency policy."""
        bad = ["%s:%d imports %s" % (p.name, line, mod)
               for p in sources() for mod, line in real_imports(p)
               if mod in CHECKERS]
        self.assertEqual(bad, [], "the harness must never import a checker: %s"
                                  % bad)

    def test_the_guard_would_catch_a_real_import(self):
        """The guard must still bite. A test that cannot fail protects nothing."""
        import tempfile, os
        d = tempfile.mkdtemp()
        p = pathlib.Path(os.path.join(d, "offender.py"))
        p.write_text("import sympy\n")
        self.assertIn(("sympy", 1), real_imports(p))

    def test_a_checker_named_only_inside_a_string_is_not_an_import(self):
        """Harness source text mentions `import sympy`; that is data, not a dep."""
        import tempfile, os
        d = tempfile.mkdtemp()
        p = pathlib.Path(os.path.join(d, "innocent.py"))
        p.write_text('HARNESS = """\nimport sympy\n"""\n')
        self.assertEqual(real_imports(p), [])


if __name__ == "__main__":
    unittest.main()
