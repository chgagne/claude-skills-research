import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))
from compare.assemble import build, ratio_note, seed_note
from compare.axes import AXES, Evidence
from compare.fulltext import Document


def ev(axis, value, quote="q", section="S", found=True):
    return Evidence(axis=axis, value=value, quote=quote, section=section, found=found)


class TestRatioNote(unittest.TestCase):
    def test_scale_ratio_is_computed_and_stated(self):
        draft = ev("training_scale", "6.4M examples (100K updates x 64 batch)")
        other = ev("training_scale", "60M examples (stated)")
        note = ratio_note(draft, other)
        self.assertIn("6.4M", note)
        self.assertIn("60M", note)
        self.assertIn("11%", note)

    def test_no_note_when_either_side_is_missing(self):
        draft = ev("training_scale", "6.4M examples")
        missing = Evidence(axis="training_scale")
        self.assertEqual(ratio_note(draft, missing), "")
        self.assertEqual(ratio_note(missing, draft), "")

    def test_no_note_when_a_value_has_no_parseable_number(self):
        self.assertEqual(ratio_note(ev("training_scale", "a large corpus"),
                                    ev("training_scale", "60M examples")), "")

    def test_comparable_scales_are_reported_as_such(self):
        note = ratio_note(ev("training_scale", "58M examples"),
                          ev("training_scale", "60M examples"))
        self.assertIn("97%", note)


class TestSeedNote(unittest.TestCase):
    def test_single_seed_is_named(self):
        note = seed_note(ev("seeds", "", quote="All variants are trained from "
                                                "scratch with training seed 0."))
        self.assertIn("single", note.lower())

    def test_multiple_seeds_are_counted(self):
        note = seed_note(ev("seeds", "", quote="We report the mean over three seeds."))
        self.assertIn("3", note)

    def test_no_note_when_seeds_not_found(self):
        self.assertEqual(seed_note(Evidence(axis="seeds")), "")

    def test_no_note_when_the_sentence_says_nothing_countable(self):
        self.assertEqual(
            seed_note(ev("seeds", "", quote="We fix the random seed for sampling.")),
            "")


class TestBuild(unittest.TestCase):
    def test_rows_cover_every_axis_even_when_absent(self):
        empty = Document(sections=[], source="abstract", degraded=True)
        rows = build(empty, {"other": empty})
        self.assertEqual([r.axis for r in rows], list(AXES))

    def test_note_is_filled_for_training_scale(self):
        draft = Document(sections=[
            ("Optimization", "a total of 10^5 updates. global batch size of 64.")],
            source="arxiv-latex")
        other = Document(sections=[
            ("Pre-training", "pre-trained on approximately 60 million examples.")],
            source="arxiv-latex")
        rows = {r.axis: r for r in build(draft, {"SNIP": other})}
        self.assertIn("11%", rows["training_scale"].note)

    def test_no_note_is_invented_for_judgement_axes(self):
        d = Document(sections=[("Setup", "We evaluate on dataset A with metric M.")],
                     source="arxiv-latex")
        o = Document(sections=[("Setup", "We evaluate on dataset B with metric N.")],
                     source="arxiv-latex")
        rows = {r.axis: r for r in build(d, {"other": o})}
        self.assertEqual(rows["data"].note, "",
                         "differing datasets is a judgement, not a computed note")
        self.assertEqual(rows["metrics"].note, "")
        self.assertEqual(rows["results"].note, "")

    def test_others_are_keyed_by_the_name_given(self):
        d = Document(sections=[("S", "text")], source="arxiv-latex")
        rows = build(d, {"SNIP": d, "Kamienny": d})
        self.assertEqual(sorted(rows[0].others), ["Kamienny", "SNIP"])


if __name__ == "__main__":
    unittest.main()
