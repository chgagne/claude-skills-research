# tests/test_cli.py
import importlib.util, json, os, shutil, sys, tempfile, unittest

HERE = os.path.dirname(__file__)
spec = importlib.util.spec_from_file_location("render_ledger", os.path.join(HERE, "..", "render-ledger.py"))
cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)

ROW = {"id": "W1", "level": "mechanics", "section": "1", "para": 1, "anchor": "Our method is very novel",
       "replacement": "Our method is novel", "comment": "", "rationale": "intensifier", "rule": "",
       "confidence": 0.9, "status": "kept"}

class TestCLI(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        shutil.copy(os.path.join(HERE, "fixtures", "tiny.tex"), os.path.join(self.d, "main.tex"))
        self.ledger = os.path.join(self.d, "writing-ledger.jsonl")
        with open(self.ledger, "w") as fh:
            fh.write(json.dumps(ROW) + "\n")

    def tearDown(self):
        shutil.rmtree(self.d)

    def _args(self, **kw):
        a = ["--ledger", self.ledger, "--tex", os.path.join(self.d, "main.tex"),
             "--out", os.path.join(self.d, "main-annotated.tex"), "--report", os.path.join(self.d, "writing-report.md"),
             "--paper", "main.tex", "--mode", "A", "--no-build"]
        for k, v in kw.items():
            a += ["--" + k.replace("_", "-"), v]
        return a

    def test_no_build_writes_tex_report_and_ledger(self):
        rc = cli.main(self._args())
        self.assertEqual(rc, 0)
        with open(os.path.join(self.d, "main-annotated.tex")) as fh:
            tex = fh.read()
        self.assertIn("{changes}", tex); self.assertIn("{LG}", tex)
        self.assertIn(r"\chreplaced[id=LG]{Our method is novel}{Our method is very novel}", tex)
        # the paper's own \todo (defined after the last \usepackage) was commented out for todonotes
        self.assertIn("% LG: freed for todonotes", tex)
        self.assertNotIn("\n\\newcommand{\\todo}", tex)
        with open(os.path.join(self.d, "writing-report.md")) as fh:
            self.assertIn("### W1", fh.read())
        with open(self.ledger) as fh:
            self.assertEqual(json.loads(fh.readline())["status"], "applied")

    def test_refuses_to_overwrite_main_tex(self):
        args = self._args()
        args[args.index("--out") + 1] = os.path.join(self.d, "main.tex")
        self.assertEqual(cli.main(args), 1)

    def test_invalid_ledger_exits_1(self):
        with open(self.ledger, "a") as fh:
            fh.write(json.dumps({**ROW, "id": "nope"}) + "\n")
        self.assertEqual(cli.main(self._args()), 1)

    def test_original_untouched(self):
        with open(os.path.join(self.d, "main.tex")) as fh:
            before = fh.read()
        cli.main(self._args())
        with open(os.path.join(self.d, "main.tex")) as fh:
            self.assertEqual(fh.read(), before)
