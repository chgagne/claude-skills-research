r"""A real expansion, replayed. Offline, deterministic, and it ships.

    cd explaining-derivations/assets && python3 -m unittest tests.test_expansion_replay -v

The dispatch loop has closed twice. The first fragment cannot ship -- its rows
carry an unpublished draft's mathematics verbatim -- so it lives outside the
repository. **This one is from Bubeck, *Convex Optimization: Algorithms and
Complexity* (arXiv:1405.4980)**, which is exactly why that paper was chosen: a
public source turns a one-off into a regression test the repository can carry.

`fixtures/bubeck-lem-smoothconst.tex` is the lemma and proof verbatim;
`fixtures/bubeck-lem-smoothconst.json` is the `explain-fragment/1` a subagent
returned for it. All seven `content_hash` values match when the passage is built
on its own, so the fixture is self-contained: no network, no cached tarball.

**What it pins.** Every component was unit-tested before the first dispatch and
that run still produced six defects. The second produced five more, four of them
in the contract rather than the code -- a licence kind that did not exist, two
fields that were validated and then discarded, and a justification the ledger
attached to the wrong step. This asserts the outcome has not moved:

- the fragment validates, so the contract has not drifted from the code
- `content_hash` still binds, so a row cannot attach to a step that has changed
- the roll-up is still 3 `SUBSTANTIVE` and 1 `NOTATIONAL`
- the document still compiles with **no overfull boxes**
- the expander's framing paragraph and sub-steps still reach the page, which is
  the defect that discarded roughly a page of its output

It does not measure whether a *fresh* expander finds the same gaps again. That
needs a dispatched subagent; see `test_dispatch_acceptance.py`.
"""
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))

from explain import assemble, build, fragment, gaps, ledger_io, notation  # noqa: E402

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"
PASSAGE = FIXTURES / "bubeck-lem-smoothconst.tex"
FRAGMENT = FIXTURES / "bubeck-lem-smoothconst.json"
#: The verdicts the dispatcher supplied with the request. They ship because the
#: validator refuses a `checked` cell that was not supplied -- the expander may
#: not write a mechanical verdict it did not receive -- so replaying without them
#: fails for the right reason, which is not the reason this test exists to watch.
VERDICTS = FIXTURES / "bubeck-lem-smoothconst-verdicts.json"

CLAIM_ID = "claim/lem:smoothconst"
EXPECTED_ROWS = 7
EXPECTED_GAPS = {"SUBSTANTIVE": 3, "NOTATIONAL": 1}

#: `\cX` is the paper's own macro. Everything else the passage needs is amsmath.
PREAMBLE = "\n".join([
    r"\documentclass{article}",
    r"\usepackage{amsmath}",
    r"\newcommand{\cX}{\mathcal{X}}",
    r"\newtheorem{lemma}{Lemma}",
    r"\begin{document}",
])


def _paper():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "main.tex")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(PREAMBLE + "\n" + PASSAGE.read_text(encoding="utf-8")
                 + "\n\\end{document}\n")
    return d, path


class TestExpansionReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frag = json.loads(FRAGMENT.read_text(encoding="utf-8"))
        cls.workdir, main_tex = _paper()
        cls.led = ledger_io.build(main_tex)
        cls.steps = {s["id"]: s for s in cls.led["steps"]}
        cls.verdicts = json.loads(VERDICTS.read_text(encoding="utf-8"))
        cls.result = fragment.validate(cls.frag, cls.steps, cls.verdicts,
                                       "grad-ml")

    def test_the_fragment_still_validates(self):
        self.assertTrue(self.result.ok,
                        "the contract drifted from the code: %s"
                        % self.result.problems)

    def test_every_row_still_binds_to_a_step(self):
        """A row whose hash no longer matches is refused rather than attached to
        a step that has since changed. That refusal is the feature."""
        self.assertEqual(len(self.result.rows), EXPECTED_ROWS)

    def test_no_move_is_off_vocabulary(self):
        self.assertEqual([w for w in self.result.warnings
                          if "off-vocabulary" in w], [])

    def test_the_gap_ledger_rolls_up_unchanged(self):
        roll = gaps.rollup({CLAIM_ID: self.result.gaps})
        self.assertEqual({k: v for k, v in roll["by_severity"].items() if v},
                         EXPECTED_GAPS)

    def test_no_verdict_was_invented(self):
        """Every step of this proof came back UNVERIFIED. A row reporting
        anything stronger would be the skill inverting its own purpose."""
        for row in self.result.rows:
            self.assertIn((row.get("checked") or {}).get("verdict"),
                          ("UNVERIFIED", "not run", None))

    def test_a_verdict_that_was_not_supplied_is_refused(self):
        """The guard that makes the *Checked* column mean something. Replaying
        this fragment against an empty verdict map must fail."""
        bare = fragment.validate(self.frag, self.steps, {}, "grad-ml")
        self.assertFalse(bare.ok)
        self.assertTrue(any("did not receive" in p for p in bare.problems))

    def _document(self):
        claim = {c["id"]: c for c in self.led["claims"]}[CLAIM_ID]
        frozen = notation.freeze(self.led)
        used = {s for r in self.result.rows
                for s in self.steps.get(r["step_id"], {}).get("symbols_used", [])}
        return assemble.document(
            claim=claim, rows=self.result.rows, gaps=self.result.gaps,
            notation=dict(frozen, symbols=notation.glossary(frozen, used)),
            meta={"source_file": "main.tex", "ledger_hash": self.led["schema"],
                  "level": "grad-ml", "paper": "arXiv:1405.4980",
                  "date": "2026-08-16"},
            tex_fragment=self.frag.get("tex_fragment") or "")

    def test_the_framing_paragraph_reaches_the_document(self):
        """It was validated for forbidden tokens and then never rendered."""
        self.assertIn("gradient mapping", self._document())

    def test_the_sub_steps_reach_the_document(self):
        """`registers.md` asks for them, the validator accepted them, and nothing
        rendered them -- roughly a page of this expansion never reached the page."""
        self.assertIn("Read the projection lemma at the point", self._document())

    @unittest.skipUnless(shutil.which("latexmk"), "latexmk not installed")
    def test_it_compiles_with_no_overfull_boxes(self):
        """No unit test caught the gap ledger running 179pt off the right margin
        and being clipped mid-word. Only rendering the pages did."""
        out = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, out, True)
        path = assemble.write_document(out, "replay", self._document())
        r = build.build_pdf(path)
        self.assertTrue(r["ok"], r["detail"])
        self.assertEqual(r["warnings"], [],
                         "the layout regressed; render the pages and look at them")

    def test_summary(self):
        print("\n  replayed %d rows and %d gaps from arXiv:1405.4980"
              % (len(self.result.rows), len(self.result.gaps)))
        print("  problems: %s" % (self.result.problems or "none"))
        print("\n  Not measured: whether a fresh expander finds these gaps again.")


if __name__ == "__main__":
    unittest.main()
