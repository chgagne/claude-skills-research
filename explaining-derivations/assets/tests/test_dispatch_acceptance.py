r"""Dispatch acceptance: does a defective step reach the expander, and does a
returned fragment become an honest document? Offline, deterministic, shippable.

    cd explaining-derivations/assets && python3 -m unittest tests.test_dispatch_acceptance -v

It ships, unlike the sibling skills' acceptance suites, because its fixtures are
synthetic -- the same reason `verifying-proofs` ships its seeded-error benchmark.

Scores the half of `explaining-derivations` that is code. Read the next two
paragraphs before reading any number below them.

**What this cannot measure.** The expansion itself is written by a subagent. No
unittest can dispatch one, so nothing here grades whether a real expander finds
a real gap — that was measured once, by hand, on a live draft, and it is written
up under *What the first real run cost* in `SKILL.md`. What is graded here is the
dispatcher: whether a defective step reaches the expander at all, and whether a
returned fragment is turned into an honest document. Both have failed in the
field. Triage once dropped every restated theorem, which on a paper that states
results in the body and proves them in an appendix meant its five main results
never reached a subagent; and assembly has silently clipped a gap's text off the
right margin while producing a PDF that looked finished.

**Why not the seeded-error corpus.** The plan for this file said to grade
`verifying-proofs/assets/tests/test_seeded_errors.py`. Those fixtures cannot
score this skill: their proofs are two sentences of prose, so the ledger reports
**zero inference steps** on every one of the six and there is nothing to expand.
A benchmark run on them would report 0/6 for a reason that has nothing to do with
expansion. The fixtures below are the same methodology — one correct derivation,
one copy with a single defect at a known step — rewritten as derivations with
algebra in them.

**The headline metric is the false-`BLOCKING` rate on the untouched originals,
and it must be zero.** A gap ledger that cries wolf on a correct derivation is
worse than no ledger, for the same reason a false `CRITICAL` is worse than a
missed one. Recall against seeded defects is reported too, but seeded defects are
cleaner than real ones and will overstate it.
"""
import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))

from explain import fragment, gaps, ledger_io, notation, triage  # noqa: E402

PREAMBLE = "\n".join([
    r"\documentclass{article}",
    r"\usepackage{amsmath}",
    r"\newtheorem{thm}{Theorem}",
    r"\newtheorem{lem}[thm]{Lemma}",
    r"\begin{document}",
])
CLOSING = r"\end{document}"


# --- fixtures ----------------------------------------------------------------
# Each pair differs by one edit, and each case names a fragment of text that
# identifies the step the edit lands on. Text rather than a step number: how a
# proof segments into steps is one of the things this benchmark exists to notice
# changing, and a fixture keyed on an ordinal would report a segmentation change
# as a missed defect.

GEOMETRIC_OK = r"""
\begin{thm}\label{t:geo} For $\gamma \in [0,1)$, $\sum_{k=0}^{\infty}\gamma^k
= \frac{1}{1-\gamma}$. \end{thm}
\begin{proof}
Write $S_n$ for the partial sum. Then
\begin{align}
S_n &= \sum_{k=0}^{n}\gamma^k \\
\gamma S_n &= \sum_{k=1}^{n+1}\gamma^k \\
S_n - \gamma S_n &= 1 - \gamma^{n+1} \\
S_n &= \frac{1-\gamma^{n+1}}{1-\gamma}.
\end{align}
Since $\gamma \in [0,1)$ we have $\gamma^{n+1}\to 0$, so
$S_n \to \frac{1}{1-\gamma}$.
\end{proof}
"""

# The hypothesis that makes the limit true is removed from the step that uses it.
GEOMETRIC_BAD = GEOMETRIC_OK.replace(
    r"Since $\gamma \in [0,1)$ we have $\gamma^{n+1}\to 0$",
    r"Clearly $\gamma^{n+1}\to 0$")

CANCEL_OK = r"""
\begin{thm}\label{t:cancel} For $x \neq 1$, $\frac{x^2-1}{x-1} = x+1$. \end{thm}
\begin{proof}
Factor the numerator and cancel, which is available because $x \neq 1$:
\begin{align}
\frac{x^2-1}{x-1} &= \frac{(x-1)(x+1)}{x-1} \\
&= x+1.
\end{align}
\end{proof}
"""

# The side condition that licenses the cancellation is dropped.
CANCEL_BAD = CANCEL_OK.replace(
    r"Factor the numerator and cancel, which is available because $x \neq 1$:",
    r"Factor the numerator and cancel:")

INTERCHANGE_OK = r"""
\begin{thm}\label{t:swap} If $\sum_i \sup_t |a_i^{(t)}| < \infty$ then
$\lim_t \sum_i a_i^{(t)} = \sum_i \lim_t a_i^{(t)}$. \end{thm}
\begin{proof}
The summable envelope $\sup_t |a_i^{(t)}|$ dominates every term, so
\begin{align}
\lim_t \sum_i a_i^{(t)} &= \sum_i \lim_t a_i^{(t)}
\end{align}
by dominated convergence.
\end{proof}
"""

# The dominating bound goes; the interchange is then unlicensed.
INTERCHANGE_BAD = INTERCHANGE_OK.replace(
    r"The summable envelope $\sup_t |a_i^{(t)}|$ dominates every term, so",
    r"Interchanging the limit and the sum,").replace(
    r"by dominated convergence.", r"as required.")

REINDEX_OK = r"""
\begin{lem}\label{l:shift} For every $n$,
$\sum_{k=1}^{n} k = \sum_{j=0}^{n-1} (j+1)$. \end{lem}
\begin{proof}
Substituting $j = k-1$ shifts both endpoints:
\begin{align}
\sum_{k=1}^{n} k &= \sum_{j=0}^{n-1} (j+1) \\
&= \frac{n(n+1)}{2}.
\end{align}
\end{proof}
"""

# One endpoint is shifted and the other is not: the sums no longer agree.
REINDEX_BAD = REINDEX_OK.replace(
    r"\sum_{k=1}^{n} k &= \sum_{j=0}^{n-1} (j+1) \\",
    r"\sum_{k=1}^{n} k &= \sum_{j=0}^{n} (j+1) \\")

#: (name, correct, defective, text identifying the step the defect lands on)
CASES = [
    ("limit taken without the hypothesis that licenses it",
     GEOMETRIC_OK, GEOMETRIC_BAD, r"S_n \to"),
    ("cancellation with the side condition dropped", CANCEL_OK, CANCEL_BAD,
     r"= x+1."),
    ("limit and sum interchanged with no dominating bound",
     INTERCHANGE_OK, INTERCHANGE_BAD, r"\lim_t \sum_i"),
    ("reindexing that shifts one endpoint and not the other",
     REINDEX_OK, REINDEX_BAD, r"\sum_{j=0}^{n} (j+1)"),
]


# --- harness -----------------------------------------------------------------

def _paper(body):
    d = tempfile.mkdtemp()
    path = os.path.join(d, "main.tex")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(PREAMBLE + "\n" + body + "\n" + CLOSING)
    return path


def _request(body):
    """The object a subagent would receive, built through the shipped path."""
    led = ledger_io.build(_paper(body))
    plan = triage.plan(led)
    assert plan, "triage planned nothing; there is no dispatch to grade"
    return led, plan[0], triage.request_for(led, plan[0], {})


def _expansion(request, decline_at=None):
    """A fragment as an expander would return it.

    `decline_at` is a step id the expander could not justify, which becomes a
    `BLOCKING` gap. With it `None`, every step is explained -- that is the
    fragment an untouched original must produce no `BLOCKING` from.
    """
    rows, gap_rows = [], []
    for step in request["steps"]:
        if step["id"] == decline_at:
            gap_rows.append({
                "step_id": step["id"], "severity": "BLOCKING",
                "kind": "cannot-justify",
                "what_is_missing": "the licence for this step",
                "what_would_close_it": "state the condition the move needs",
                "quote": (step.get("prose_tex") or "")[:60]})
            continue
        rows.append({
            "step_id": step["id"], "content_hash": step["content_hash"],
            "before_tex": "a", "after_tex": "b",
            "move": "algebraic-rearrangement",
            "licensed_by": {"kind": "equation", "value": "eq:1"},
            "breaks_if": "the rearrangement divides by zero",
            "gloss": "Rearranged.", "expanded_into": []})
    return {"request_id": request["request_id"],
            "contract": "explain-fragment/1", "tex_fragment": "",
            "rows": rows, "gaps": gap_rows, "symbols_introduced": [],
            "macros_requested": [],
            "self_check": {"rows_cover_all_inference_steps": decline_at is None,
                           "unexplained_steps": 1 if decline_at else 0,
                           "forbidden_tokens_present": False}}


def _blocking(led, frag):
    steps = {s["id"]: s for s in led["steps"]}
    result = fragment.validate(frag, steps, {}, "grad-ml")
    assert result.ok, "the fragment was refused: %s" % result.problems
    roll = gaps.rollup({frag["request_id"]: result.gaps})
    return roll["by_severity"].get("BLOCKING", 0), result


def _step_carrying(request, marker):
    """The step the seeded edit lands on, found by its text.

    Located by a distinguishing fragment rather than by ordinal: how a proof
    segments into steps is exactly the thing this benchmark exists to notice
    changing, so a fixture keyed on a step number would report a segmentation
    change as a missed defect.
    """
    want = " ".join(marker.split())
    for step in request["steps"]:
        haystack = " ".join(("%s %s" % (step.get("math_tex") or "",
                                        step.get("prose_tex") or "")).split())
        if want in haystack:
            return step["id"]
    return None


class TestAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = []
        for name, ok, bad, marker in CASES:
            led_bad, _, req_bad = _request(bad)
            led_ok, _, req_ok = _request(ok)
            target = _step_carrying(req_bad, marker)
            cls.rows.append({
                "name": name, "marker": marker, "target": target,
                "inference_steps_bad": len(req_bad["steps"]),
                "inference_steps_ok": len(req_ok["steps"]),
                "led_bad": led_bad, "req_bad": req_bad,
                "led_ok": led_ok, "req_ok": req_ok})

    def test_every_defective_derivation_reaches_a_subagent(self):
        """Dispatch coverage. Triage dropping a claim is silent and total: the
        expander cannot find a gap in a proof it was never sent."""
        for r in self.rows:
            self.assertGreater(r["inference_steps_bad"], 0,
                               "%s: nothing to expand was planned" % r["name"])

    def test_the_defective_step_itself_is_in_the_request(self):
        """A request that reaches the right proof but omits the wrong step is
        the same failure one level down."""
        for r in self.rows:
            self.assertIsNotNone(
                r["target"],
                "%s: the step carrying %r never reached the expander; the "
                "request carries %s"
                % (r["name"], r["marker"],
                   [s["id"].split("/")[-1] for s in r["req_bad"]["steps"]]))

    def test_a_declined_step_becomes_a_blocking_gap(self):
        for r in self.rows:
            frag = _expansion(r["req_bad"], decline_at=r["target"])
            count, _ = _blocking(r["led_bad"], frag)
            self.assertEqual(count, 1, "%s: the refusal did not reach the ledger"
                             % r["name"])

    def test_no_false_blocking_on_the_untouched_originals(self):
        """The headline metric."""
        for r in self.rows:
            frag = _expansion(r["req_ok"], decline_at=None)
            count, _ = _blocking(r["led_ok"], frag)
            self.assertEqual(count, 0, "%s: false BLOCKING on correct mathematics"
                             % r["name"])

    def test_a_fragment_written_against_the_other_paper_is_refused(self):
        """Content-hash binding. An explanation attached to a step that has since
        changed is worse than no explanation, and the refusal is the feature."""
        refused = 0
        for r in self.rows:
            frag = _expansion(r["req_ok"], decline_at=None)
            frag["request_id"] = r["req_bad"]["request_id"]
            steps = {s["id"]: s for s in r["led_bad"]["steps"]}
            result = fragment.validate(frag, steps, {}, "grad-ml")
            if not result.ok:
                refused += 1
        self.assertGreater(refused, 0,
                           "no fragment was refused when applied to the edited "
                           "paper; the hash binding is not doing anything")

    def test_a_reported_verdict_that_was_never_supplied_is_refused(self):
        """The join with verifying-proofs, in the direction that matters: the
        expander may not invent mechanical evidence."""
        r = self.rows[0]
        frag = _expansion(r["req_bad"], decline_at=None)
        frag["rows"][0]["checked"] = {"verdict": "CRITICAL", "engine": "sympy",
                                      "script": "checks/invented.py"}
        steps = {s["id"]: s for s in r["led_bad"]["steps"]}
        result = fragment.validate(frag, steps, {}, "grad-ml")
        self.assertFalse(result.ok)
        self.assertTrue(any("verdict" in p for p in result.problems),
                        result.problems)

    def test_notation_is_frozen_before_dispatch(self):
        frozen = notation.freeze(self.rows[0]["led_bad"])
        self.assertIn("preamble_packages", frozen)
        self.assertIn("amsmath", frozen["preamble_packages"])

    def test_summary(self):
        """Prints; asserts nothing."""
        print("\n  %-52s %6s %8s" % ("seeded defect", "steps", "reached"))
        for r in self.rows:
            print("  %-52s %6d %8s"
                  % (r["name"][:52], r["inference_steps_bad"],
                     "yes" if r["target"] else "NO"))
        false_blocking = 0
        for r in self.rows:
            count, _ = _blocking(r["led_ok"], _expansion(r["req_ok"]))
            false_blocking += count
        print("\n  false BLOCKING on untouched originals: %d of %d  "
              "(this is the headline; it must be 0)"
              % (false_blocking, len(CASES)))
        print("  reached the expander: %d of %d"
              % (sum(1 for r in self.rows if r["target"]), len(CASES)))
        print("\n  Not measured here: whether a real expander finds a real gap.")
        print("  That needs a dispatched subagent. It was measured once by hand;")
        print("  see 'What the first real run cost' in the skill's SKILL.md.")


if __name__ == "__main__":
    unittest.main()
