"""Unit tests for the PDF -> pseudo-source shim.

Run: python3 -m unittest discover -s assets/tests -t assets

These cover the parse decisions that were wrong in measured runs. The
end-to-end accuracy numbers quoted in the skill come from three public papers
with LaTeX ground truth; those runs need network access and are not unit tests.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdfshim.refs import (  # noqa: E402
    bibtex_authors,
    parse_entry,
    parse_reference_list,
    split_entries,
    style,
    to_bibtex,
)
from pdfshim.text import flow, reference_sections  # noqa: E402

NUMBERED = """[1] Pengguang Chen, Shu Liu, Hengshuang Zhao, and Jiaya Jia.
Distilling knowledge via knowledge review. In CVPR, 2021.
6, 7, 8, 11, 13
[2] Xu Cheng, Zhefan Rao, Yilan Chen, and Quanshi Zhang.
Explaining knowledge distillation by quantifying the knowledge. In CVPR, 2020. 2
[3] Jang Hyun Cho and Bharath Hariharan. On the efficacy of
knowledge distillation. In ICCV, 2019. 2, 7
"""

INITIALS = """Abadi, M., Barham, P., Chen, J., Davis, A., Dean,
J., Devin, M., Ghemawat, S., Irving, G., Isard, M., et al.
Tensorflow: A system for large-scale machine learning. In
12th USENIX symposium on operating systems design
and implementation (OSDI 16), pp. 265-283, 2016.
Andreas, J., Klein, D., and Levine, S. Learning with latent language.
arXiv preprint arXiv:1711.00482, 2017.
Alcorn, M. A., Li, Q., Gong, Z., and Nguyen, A. Strike with a pose.
In Proceedings of the IEEE Conference, pp. 1-9, 2019.
"""

YEAR_FIRST = """Zhao, B.; Cui, Q.; Song, R.; Qiu, Y.; and Liang, J.
2022. Decoupled Knowledge Distillation. In IEEE/CVF Conference
on Computer Vision and Pattern Recognition (CVPR), 11953-11962.
Hinton, G.; Vinyals, O.; and Dean, J. 2015. Distilling the
Knowledge in a Neural Network. In NIPS Deep Learning Workshop.
Krizhevsky, A. 2009. Learning Multiple Layers of Features
from Tiny Images. Technical report, University of Toronto.
"""


class TestStyleDetection(unittest.TestCase):
    def test_numbered(self):
        self.assertEqual(style(NUMBERED), "numbered")

    def test_initials(self):
        self.assertEqual(style(INITIALS), "initials")

    def test_year_first_semicolons_are_initials(self):
        # "Zhao, B.;" opens with Surname, Initial. so it parses as initials;
        # the year-in-authors shape is then handled inside parse_entry.
        self.assertIn(style(YEAR_FIRST), {"initials", "plain"})


class TestEntrySplitting(unittest.TestCase):
    def test_numbered_splits_on_bracket(self):
        self.assertEqual(len(split_entries(NUMBERED, "numbered")), 3)

    def test_numbered_drops_trailing_backrefs(self):
        first = split_entries(NUMBERED, "numbered")[0]
        self.assertTrue(first.endswith("2021."), first)
        self.assertNotIn("6, 7, 8", first)

    def test_initials_splits_on_surname_initial(self):
        self.assertEqual(len(split_entries(INITIALS, "initials")), 3)

    def test_wrapped_hyphen_is_rejoined(self):
        entries = split_entries("Smith, J. Deep learn-\ning for vision. In X, 2020.\n",
                                "initials")
        self.assertIn("learning", entries[0])


class TestFieldExtraction(unittest.TestCase):
    def test_numbered_title(self):
        rec = parse_entry(split_entries(NUMBERED, "numbered")[0], "numbered")
        self.assertEqual(rec["title"],
                         "Distilling knowledge via knowledge review")
        self.assertEqual(rec["year"], "2021")

    def test_initials_title_when_authors_end_in_initial(self):
        # The failure this guards: "Levine, S. Learning with latent language"
        # -- a sentence splitter cannot tell that period from a mid-name one.
        recs = parse_reference_list(INITIALS)
        titles = [r["title"] for r in recs]
        self.assertIn("Learning with latent language", titles)

    def test_initials_title_with_et_al(self):
        recs = parse_reference_list(INITIALS)
        self.assertEqual(recs[0]["title"],
                         "Tensorflow: A system for large-scale machine learning")

    def test_year_in_author_block(self):
        recs = parse_reference_list(YEAR_FIRST)
        by_year = {r["year"]: r["title"] for r in recs}
        self.assertEqual(by_year.get("2022"), "Decoupled Knowledge Distillation")
        self.assertEqual(by_year.get("2015"),
                         "Distilling the Knowledge in a Neural Network")

    def test_arxiv_id_captured(self):
        recs = parse_reference_list(INITIALS)
        ids = [r.get("arxiv") for r in recs]
        self.assertIn("1711.00482", ids)


class TestConfidence(unittest.TestCase):
    def test_clean_entry_is_ok(self):
        rec = parse_entry(split_entries(NUMBERED, "numbered")[0], "numbered")
        self.assertEqual(rec["confidence"], "ok")

    def test_venue_as_title_is_low(self):
        rec = parse_entry(
            "Somebody, A. In Proceedings of the IEEE Conference, 2019.",
            "initials")
        if rec:
            self.assertEqual(rec["confidence"], "low")

    def test_missing_year_is_low(self):
        rec = parse_entry("Smith, J. A perfectly fine looking title here. Venue.",
                          "initials")
        self.assertEqual(rec["confidence"], "low")


class TestBibtexAuthors(unittest.TestCase):
    """Emitting the printed author list verbatim makes the bibliography checker
    read it as one author and report every co-author as missing. That is a
    finding manufactured by the shim, and in a report it looks exactly like a
    real one. It happened; these guard against it."""

    def test_full_names_separated_by_and(self):
        got = bibtex_authors("Pengguang Chen, Shu Liu, Hengshuang Zhao, and Jiaya Jia")
        self.assertEqual(got.count(" and "), 3)
        self.assertIn("Jiaya Jia", got)

    def test_surname_initial_commas_are_not_separators(self):
        got = bibtex_authors("Abadi, M., Barham, P., Chen, J.")
        self.assertEqual(got, "Abadi, M. and Barham, P. and Chen, J.")

    def test_et_al_dropped(self):
        self.assertNotIn("et al", bibtex_authors("Abadi, M., Barham, P., et al."))

    def test_single_author(self):
        self.assertEqual(bibtex_authors("Krizhevsky, A."), "Krizhevsky, A.")

    def test_emitted_bibtex_uses_and(self):
        recs = parse_reference_list(NUMBERED)
        for line in to_bibtex(recs).split("\n"):
            if line.strip().startswith("author ="):
                inner = line.split("{", 1)[1].rsplit("}", 1)[0]
                if "," in inner and " and " not in inner:
                    self.fail(f"comma-separated author list survived: {inner}")


class TestBibtex(unittest.TestCase):
    def test_keys_are_unique(self):
        recs = parse_reference_list(NUMBERED) + parse_reference_list(YEAR_FIRST)
        bib = to_bibtex(recs)
        keys = [l.split("{")[1].rstrip(",") for l in bib.split("\n")
                if l.startswith("@")]
        self.assertEqual(len(keys), len(set(keys)))

    def test_braces_are_stripped(self):
        bib = to_bibtex(parse_reference_list(INITIALS))
        for line in bib.split("\n"):
            if line.strip().startswith("title ="):
                inner = line.split("{", 1)[1].rsplit("}", 1)[0]
                self.assertNotIn("{", inner)


class TestText(unittest.TestCase):
    def test_flow_rejoins_hyphenated_break(self):
        self.assertIn("distillation", flow("distil-\nlation works"))

    def test_flow_unwraps_continuation(self):
        self.assertEqual(flow("the quick\nbrown fox"), "the quick brown fox")

    def test_flow_keeps_capitalised_line_break(self):
        # Known blind spot, documented so it is not mistaken for a bug.
        self.assertIn("\n", flow("probabilities in in\nEq. 3"))

    def test_multiple_reference_sections_found(self):
        doc = "body\nReferences\nA, B. 2020. T. V.\nAppendix\nReferences\nC, D. 2021. U. W.\n"
        self.assertEqual(len(reference_sections(doc)), 2)


if __name__ == "__main__":
    unittest.main()
