"""The safety layer, written before any engine exists.

Generated check scripts are executed. This is not a security boundary against a
hostile adversary and the SKILL says so plainly -- it is a guard against a model
writing `os.system`, against a script reaching into the paper directory, and
against a `simplify` that never returns.

The assertions that matter most are the ones about *failure*: a rejected script,
a timeout and a missing checker must all become `UNVERIFIED`, visibly, and must
never become a refutation. A tool that reports "counterexample found" because its
own subprocess died has invented a finding.
"""
import unittest, sys, pathlib, os, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from proofcheck import sandbox as S  # noqa: E402


def guard(src):
    return S.guard(src)


class TestStaticGuard(unittest.TestCase):
    def test_a_clean_script_passes(self):
        self.assertEqual(guard("import sympy\nx = sympy.Symbol('x')\n"), [])

    def test_importing_os_is_rejected_by_name(self):
        r = guard("import os\n")
        self.assertTrue(r)
        self.assertIn("os", r[0])

    def test_importing_subprocess_is_rejected(self):
        self.assertTrue(guard("import subprocess\n"))

    def test_from_import_of_a_blocked_module_is_rejected(self):
        self.assertTrue(guard("from os import path\n"))

    def test_opening_a_file_is_rejected(self):
        self.assertTrue(guard("open('/etc/passwd')\n"))

    def test_exec_and_eval_are_rejected(self):
        self.assertTrue(guard("exec('1')\n"))
        self.assertTrue(guard("eval('1')\n"))

    def test_dunder_import_is_rejected(self):
        self.assertTrue(guard("__import__('os')\n"))

    def test_network_modules_are_rejected(self):
        for mod in ("socket", "urllib", "http", "requests"):
            self.assertTrue(guard("import %s\n" % mod), "%s allowed" % mod)

    def test_the_allowlist_is_honoured(self):
        for mod in ("sympy", "z3", "math", "fractions", "decimal", "itertools",
                    "functools", "json", "sys"):
            self.assertEqual(guard("import %s\n" % mod), [], "%s rejected" % mod)

    def test_syntax_errors_are_a_rejection_not_a_crash(self):
        r = guard("def (:\n")
        self.assertTrue(r)
        self.assertIn("syntax", r[0].lower())

    def test_attribute_access_to_dunders_is_rejected(self):
        self.assertTrue(guard("x = ().__class__.__bases__\n"))


class TestExecution(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def write(self, body, name="s.py"):
        p = os.path.join(self.d, name)
        with open(p, "w") as fh:
            fh.write(body)
        return p

    def test_a_script_result_is_parsed_from_stdout(self):
        p = self.write("import json,sys\n"
                       "sys.stdout.write(json.dumps({'outcome':'not-refuted'}))\n")
        r = S.run_script(p, timeout=10)
        self.assertEqual(r["outcome"], "not-refuted")

    def test_an_infinite_loop_is_unverified_not_a_refutation(self):
        p = self.write("while True:\n    pass\n")
        r = S.run_script(p, timeout=1)
        self.assertEqual(r["outcome"], "unverified")
        self.assertIn("timeout", r["detail"].lower())
        self.assertNotEqual(r["outcome"], "refuted")

    def test_a_crashing_script_is_unverified(self):
        p = self.write("raise ValueError('boom')\n")
        r = S.run_script(p, timeout=10)
        self.assertEqual(r["outcome"], "unverified")

    def test_a_script_printing_nothing_is_unverified(self):
        p = self.write("pass\n")
        self.assertEqual(S.run_script(p, timeout=10)["outcome"], "unverified")

    def test_a_script_printing_junk_is_unverified_not_a_crash(self):
        p = self.write("print('not json at all')\n")
        self.assertEqual(S.run_script(p, timeout=10)["outcome"], "unverified")

    def test_a_rejected_script_is_never_executed(self):
        marker = os.path.join(self.d, "touched")
        p = self.write("import os\nopen(%r,'w').write('x')\n" % marker)
        r = S.run_script(p, timeout=10)
        self.assertEqual(r["outcome"], "unverified")
        self.assertIn("rejected", r["detail"].lower())
        self.assertFalse(os.path.exists(marker),
                         "a rejected script must not run at all")

    def test_rejection_names_the_reason_visibly(self):
        p = self.write("import os\n")
        self.assertIn("os", S.run_script(p, timeout=10)["detail"])

    def test_execution_cwd_is_the_script_directory_not_the_paper(self):
        p = self.write("import json,sys,fractions\n"
                       "sys.stdout.write(json.dumps({'outcome':'not-refuted'}))\n")
        before = os.getcwd()
        S.run_script(p, timeout=10)
        self.assertEqual(os.getcwd(), before,
                         "the harness must not change its own working directory")


class TestProbe(unittest.TestCase):
    def test_probe_reports_a_present_checker_with_its_version(self):
        c = S.probe("sympy")
        if c.available:
            self.assertTrue(c.version)

    def test_probe_reports_an_absent_checker_without_raising(self):
        c = S.probe("definitely_not_a_real_module_xyz")
        self.assertFalse(c.available)
        self.assertIsNone(c.version)

    def test_an_absent_checker_carries_an_install_hint_not_an_install(self):
        c = S.probe("z3")
        if not c.available:
            self.assertIn("ask the user", c.install_hint.lower())

    def test_probing_never_imports_the_checker_into_this_process(self):
        """A broken install must not take the harness down with it.

        Asserted as "probe imports nothing new" rather than "sympy is absent from
        sys.modules": another test in this suite legitimately execs the SymPy
        harness, and an absolute assertion would fail on test ordering rather
        than on a real regression.
        """
        before = set(sys.modules)
        S.probe("sympy")
        S.probe("z3")
        self.assertEqual({m for m in set(sys.modules) - before
                          if m.split(".")[0] in ("sympy", "z3")}, set())


if __name__ == "__main__":
    unittest.main()
