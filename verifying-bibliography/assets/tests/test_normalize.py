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

    # --- false-alarm modes found on a real AAAI submission ---
    def test_bibtex_and_others_is_not_a_person(self):
        """`author = {A and B and others}` is the et-al idiom, not an author."""
        self.assertEqual(
            author_diff(["Towers, Mark", "others"], ["Mark Towers"]), ([], []),
            "'others' must never be reported as a missing author")

    def test_and_others_excuses_extra_record_authors(self):
        """`and others` declares the list abbreviated, so more authors is expected."""
        self.assertEqual(
            author_diff(["Towers, Mark", "others"], ["Mark Towers", "Jun Jet Tai"]),
            ([], []))

    def test_and_others_does_not_excuse_an_invented_author(self):
        """An author in the .bib who is on no record is still a finding."""
        only_bib, _ = author_diff(["Towers, Mark", "Ghost, A", "others"],
                                  ["Mark Towers", "Jun Jet Tai"])
        self.assertEqual(only_bib, ["Ghost, A"])

    def test_latex_tie_inside_a_surname(self):
        """`De~Vylder, Bart` is one name; the tie is typography, not a separator."""
        self.assertEqual(family_key("De~Vylder, Bart"), family_key("Bart De Vylder"))
        self.assertEqual(author_diff(["De~Vylder, Bart"], ["Bart De Vylder"]), ([], []))

    def test_unicode_dash_variants_in_surnames(self):
        """OpenAlex returns Cesa-Bianchi with U+2010, the .bib uses ASCII."""
        self.assertEqual(family_key("Cesa-Bianchi, Nicolo"),
                         family_key("Nicol\u00f2 Cesa\u2010Bianchi"))
        self.assertEqual(
            author_diff(["Cesa-Bianchi, Nicolo"], ["Nicol\u00f2 Cesa\u2010Bianchi"]),
            ([], []))

    def test_non_latin_script_record_is_not_a_missing_author(self):
        """A Greek-script record of a Latin-script name is a transliteration,
        not a different person. It cannot be matched, so report neither side."""
        only_bib, only_rec = author_diff(["Koutsoupias, Elias"],
                                         ["\u0397\u03bb\u03af\u03b1\u03c2 "
                                          "\u039a\u03bf\u03c5\u03c4\u03c3\u03bf"
                                          "\u03c5\u03c0\u03b9\u03ac\u03c2"])
        self.assertEqual(only_bib, [], "cannot claim an author is invented on a "
                                       "script mismatch")

    def test_organisation_as_author_is_not_a_person_mismatch(self):
        """Some records list a publisher or institute where the .bib lists people."""
        only_bib, _ = author_diff(["Horni, Andreas", "Nagel, Kai"], ["ETH Z\u00fcrich"])
        self.assertEqual(only_bib, [])

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
