import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bibcheck.normalize import (strip_dblp_suffix, fold, norm_title,
                                split_authors, family_key, author_diff)


class TestNormalize(unittest.TestCase):
    def test_strips_dblp_disambiguation_suffix(self):
        self.assertEqual(strip_dblp_suffix("Elena Rossi 0001"), "Elena Rossi")
        self.assertEqual(strip_dblp_suffix("Chenglong Wang 0005"), "Chenglong Wang")
        self.assertEqual(strip_dblp_suffix("Kevin Zeng Hu"), "Kevin Zeng Hu")

    def test_fold_removes_accents_and_case(self):
        self.assertEqual(fold("Dupré"), fold("Dupre"))
        self.assertEqual(fold("Kulhánek"), fold("KULHANEK"))

    def test_norm_title_ignores_punctuation_and_case(self):
        a = norm_title("{Draco}: An Approach to Generating Visualizations")
        b = norm_title("Draco - an approach to generating visualizations")
        self.assertEqual(a, b)

    def test_split_authors_both_orders(self):
        self.assertEqual(split_authors("Moritz, Dominik and Wang, Chenglong"),
                         ["Moritz, Dominik", "Wang, Chenglong"])
        self.assertEqual(split_authors("Dominik Moritz and Chenglong Wang"),
                         ["Dominik Moritz", "Chenglong Wang"])

    def test_family_key_handles_both_orders_and_initials(self):
        self.assertEqual(family_key("Dupré, B."), family_key("Benoit Dupré"))
        self.assertEqual(family_key("Rossi, E."), family_key("Elena Rossi 0001"))
        self.assertEqual(family_key("M Vastl"), family_key("Vastl, Martin"))

    # --- the observed false alarms must produce NO difference ---
    def test_initials_only_bib_matches_full_record(self):
        bib = ["Dupré, B.", "Dupont, C.", "Rossi, E."]
        rec = ["Benoit Dupré", "Claire Dupont", "Elena Rossi 0001"]
        self.assertEqual(author_diff(bib, rec), ([], []))

    def test_scholar_initials_form_matches(self):
        bib = ["Vastl, Martin", "Kulhánek, Jonáš"]
        rec = ["M Vastl", "J Kulhánek"]
        self.assertEqual(author_diff(bib, rec), ([], []))

    def test_compound_surname_matches_across_name_orders(self):
        """'Molina León, Gabriela' and 'Gabriela Molina León' are one person."""
        self.assertEqual(family_key("Molina León, Gabriela"),
                         family_key("Gabriela Molina León"))
        self.assertEqual(author_diff(["Molina León, Gabriela"],
                                     ["Gabriela Molina León"]), ([], []))

    def test_html_escaped_and_typographic_apostrophes_match(self):
        """DBLP returns 'O&apos;Reilly'; .bib files use ' or the typographic '."""
        self.assertEqual(family_key("O\u2019Reilly, Una-May"),
                         family_key("Una-May O&apos;Reilly"))
        self.assertEqual(author_diff(["O\u2019Reilly, Una-May"],
                                     ["Una-May O&apos;Reilly"]), ([], []))

    # --- the real finding must be visible as a SET DIFFERENCE ---
    def test_voyager_invented_and_dropped_authors(self):
        bib = ["Wongsuphasawat, Kanit", "Moritz, Dominik", "Anand, Anushka",
               "Mackinlay, Jock", "Bach, Bill", "Dragicevic, Pierre"]
        rec = ["Kanit Wongsuphasawat", "Dominik Moritz", "Anushka Anand",
               "Jock Mackinlay", "Bill Howe", "Jeffrey Heer"]
        only_bib, only_rec = author_diff(bib, rec)
        self.assertEqual(sorted(only_bib), ["Bach, Bill", "Dragicevic, Pierre"])
        self.assertEqual(sorted(only_rec), ["Bill Howe", "Jeffrey Heer"])


if __name__ == "__main__":
    unittest.main()
