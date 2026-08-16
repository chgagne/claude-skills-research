r"""Do two independent expanders find the same gaps? Offline, and it ships.

    cd explaining-derivations/assets && python3 -m unittest tests.test_expander_agreement -v

**This is the question the skill could not answer for three rounds.** Every other
fixture pins *assembly*: the same fragment in, the same document out. None of them
says whether a fresh expander, handed the contract and nothing else, reaches the
same conclusions — and the whole thesis is that an expansion which cannot be
completed is evidence about the derivation. Evidence that depends on which
subagent you asked is not evidence.

The same lemma of Bubeck (arXiv:1405.4980) was expanded twice, by separate
subagents, against **materially different requests**: the first had no referenced
equations, an 81-symbol glossary and a 70-entry macro table; the second had the
cited equations, 6 symbols and no macros. If the gaps were an artefact of
prompting, that is where it would show.

**Measured: every substantive gap found by the first run reappears in the second**
(the second splits one of them in two). The two runs disagree about *where to hang
a gap* and *what to call its kind* -- and that disagreement is itself the finding
recorded below, because `kind` is free text and step attribution is a judgement.

Agreement is matched on **substance**, not on `step_id` or `kind`. Matching on
either would measure the labels rather than the mathematics, and would have
reported disagreement where there is none.
"""
import json
import pathlib
import re
import unittest

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"
RUN2 = FIXTURES / "bubeck-lem-smoothconst.json"
RUN3 = FIXTURES / "bubeck-lem-smoothconst-gaps-run3.json"

#: The four things wrong with this proof, named by what a reader would say they
#: are rather than by anything either run wrote. A gap matches a topic when its
#: text carries any of the topic's markers.
TOPICS = {
    "f's regularity is never assumed": (
        r"convex", r"smooth", r"regularity"),
    "the sign of beta is never fixed": (
        r"\\beta > 0", r"sign of \$?\\beta", r"divides.{0,40}\\beta",
        r"\\beta \\neq 0"),
    "the projection and its set are never pinned down": (
        r"\\Pi", r"projection", r"closed", r"non-empty"),
    "the cited lemma's variables collide with this one's": (
        r"rebound", r"variable-capture", r"collide", r"bound variables",
        r"its own \$x\$ and \$y\$"),
}


def _text(gap):
    return " ".join(str(gap.get(k) or "") for k in
                    ("kind", "what_is_missing", "what_would_close_it", "quote"))


def _topics(gaps):
    """Which topics each run raised, matched on substance."""
    found = {}
    for name, markers in TOPICS.items():
        for g in gaps:
            if any(re.search(m, _text(g), re.I) for m in markers):
                found.setdefault(name, []).append(g)
    return found


class TestTwoExpandersAgree(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.run2 = json.loads(RUN2.read_text(encoding="utf-8"))["gaps"]
        cls.run3 = json.loads(RUN3.read_text(encoding="utf-8"))["gaps"]
        cls.t2, cls.t3 = _topics(cls.run2), _topics(cls.run3)

    def test_both_runs_found_something(self):
        self.assertTrue(self.run2)
        self.assertTrue(self.run3)

    def test_every_topic_the_first_run_raised_the_second_raised_too(self):
        """The headline. A gap that only one expander sees is a gap that depends
        on who you asked, and this skill reports gaps as evidence."""
        missing = sorted(set(self.t2) - set(self.t3))
        self.assertEqual(missing, [],
                         "the second expander did not reproduce: %s" % missing)

    def test_and_the_reverse(self):
        missing = sorted(set(self.t3) - set(self.t2))
        self.assertEqual(missing, [],
                         "the first expander did not reproduce: %s" % missing)

    def test_all_four_known_topics_are_covered(self):
        """If a topic stops being found by either run, the expansion got worse
        and this file is where that shows."""
        self.assertEqual(sorted(self.t2), sorted(TOPICS))

    def test_neither_run_invented_a_critical_severity(self):
        for gaps in (self.run2, self.run3):
            for g in gaps:
                self.assertIn(g["severity"],
                              ("BLOCKING", "SUBSTANTIVE", "NOTATIONAL", "COSMETIC"))

    def test_every_substantive_gap_says_what_would_close_it(self):
        for gaps in (self.run2, self.run3):
            for g in gaps:
                if g["severity"] in ("BLOCKING", "SUBSTANTIVE"):
                    self.assertTrue((g.get("what_would_close_it") or "").strip(),
                                    "a gap that names no remedy cannot be acted on")

    def test_summary(self):
        """Prints the disagreement, which is the interesting half."""
        print("\n  Two independent expansions of one lemma, different requests.\n")
        print("  %-52s %-8s %-8s" % ("topic", "run 2", "run 3"))
        for name in TOPICS:
            a, b = self.t2.get(name, []), self.t3.get(name, [])
            print("  %-52s %-8s %-8s" % (name[:52], len(a) or "-", len(b) or "-"))
        print("\n  Agreement on substance: %d of %d topics, both directions."
              % (len(set(self.t2) & set(self.t3)), len(TOPICS)))
        print("\n  Where they differ -- and this is why matching is on substance:")
        for name in TOPICS:
            a = self.t2.get(name, [{}])[0]
            b = self.t3.get(name, [{}])[0]
            if a.get("step_id") != b.get("step_id") or a.get("kind") != b.get("kind"):
                print("    %-46s %s/%s vs %s/%s"
                      % (name[:46],
                         (a.get("step_id") or "-").split("/")[-1], a.get("kind"),
                         (b.get("step_id") or "-").split("/")[-1], b.get("kind")))
        print("\n  Step attribution and `kind` are judgements; the mathematics is not.")


if __name__ == "__main__":
    unittest.main()
