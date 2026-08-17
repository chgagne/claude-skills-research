import unittest, sys, pathlib, re
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bibcheck.compare import Finding
from bibcheck.report import to_markdown, to_csv

F = [Finding("moritz2019draco", "title", "Draco: An Approach",
             "Formalizing Visualization Design Knowledge", "crossref", "CRITICAL"),
     Finding("shen2023nli2vis", "pages", "3121-3137", "3121-3144", "crossref", "MAJOR")]


class TestReport(unittest.TestCase):
    def test_markdown_groups_by_severity_critical_first(self):
        md = to_markdown(F, total=18, checked=18)
        self.assertLess(md.index("CRITICAL"), md.index("MAJOR"))
        self.assertIn("moritz2019draco", md)
        self.assertIn("18", md)

    def test_csv_header_and_row(self):
        csv = to_csv(F)
        self.assertEqual(csv.splitlines()[0],
                         "key,field,in_bib,in_record,source,severity")
        self.assertIn("moritz2019draco,title,", csv)

    def test_csv_quotes_embedded_commas(self):
        f = [Finding("k", "author", "+Bach, +Dragicevic", "-Howe", "crossref", "CRITICAL")]
        self.assertIn('"+Bach, +Dragicevic"', to_csv(f))

    def test_markdown_reports_no_findings(self):
        self.assertIn("No findings", to_markdown([], total=5, checked=5))

    def test_zero_checked_never_reads_as_a_clean_bill(self):
        # A report on disk read "Entries in file: 18. Entries checked: 0." and
        # then "No findings." -- which is what a clean bibliography looks like.
        # Nothing had been checked. Silence is the signal, so it must be said in
        # words rather than left to the reader to infer from a counter.
        md = to_markdown([], total=18, checked=0)
        self.assertNotIn("No findings", md)
        self.assertIn("Nothing was checked", md)

    def test_partial_clean_run_names_the_unchecked_remainder(self):
        md = to_markdown([], total=18, checked=11)
        self.assertNotIn("No findings.", md)
        self.assertIn("11 of 18", md)
        self.assertIn("7 were not", md)

    def test_markdown_escapes_pipes_in_values(self):
        f = [Finding("k", "title", "A | B", "C", "dblp", "WEAK")]
        row = [l for l in to_markdown(f, 1, 1).splitlines() if l.startswith("| `k`")][0]
        self.assertIn(r"A \| B", row)
        unescaped = len(re.findall(r"(?<!\\)\|", row))
        self.assertEqual(unescaped, 6, "an unescaped pipe would break the table")


if __name__ == "__main__":
    unittest.main()
