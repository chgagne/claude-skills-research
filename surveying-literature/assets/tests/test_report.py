import unittest, sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from survey.report import to_markdown, to_json
from survey.traverse import Candidate
from survey.seeds import Seed

SEED = Seed(title="A Framework for Chart Repair", abstract="",
            cited_keys={"a"}, cited_titles=["LIDA: A Tool"],
            contributions=["a repair loop"], angles=["chart repair"])


def cand(title, grade_paths, cites=10, year=2024, doi="10.1/x"):
    return Candidate(title=title, authors=["A Author", "B Author"], year=year,
                     venue="CHI", doi=doi, paths=list(grade_paths),
                     cited_by_count=cites)


RANKED = [
    (cand("Execution-guided chart repair", ["backward:LIDA: A Tool", "topical:chart repair"]),
     4.5, "THREAT"),
    (cand("Chart code generation", ["forward:LIDA: A Tool"]), 3.2, "RELATED"),
    (cand("Compiler register allocation", ["backward:LIDA: A Tool"], year=1998), 1.1,
     "BACKGROUND"),
]


class TestReport(unittest.TestCase):
    def test_groups_threat_before_related_before_background(self):
        md = to_markdown(RANKED, SEED, unresolved=[])
        self.assertLess(md.index("THREAT"), md.index("RELATED"))
        self.assertLess(md.index("RELATED"), md.index("BACKGROUND"))

    def test_shows_why_a_candidate_surfaced(self):
        md = to_markdown(RANKED, SEED, unresolved=[])
        self.assertIn("backward", md)
        self.assertIn("topical", md)

    def test_reports_unresolved_seeds_as_a_coverage_limit(self):
        md = to_markdown(RANKED, SEED, unresolved=["Building Effective Agents"])
        self.assertIn("Building Effective Agents", md)
        self.assertIn("coverage", md.lower())

    def test_no_candidates_reads_as_no_gaps_not_as_success(self):
        md = to_markdown([], SEED, unresolved=[])
        self.assertIn("No candidates", md)

    def test_escapes_pipes_so_tables_do_not_break(self):
        import re
        rows = [(cand("A | B title", ["topical:x"]), 1.0, "RELATED")]
        md = to_markdown(rows, SEED, unresolved=[])
        row = [l for l in md.splitlines() if "A " in l and l.startswith("|")][0]
        self.assertEqual(len(re.findall(r"(?<!\\)\|", row)), 7)  # 6 columns

    def test_unknown_citation_count_renders_as_not_reported(self):
        rows = [(cand("arXiv only", ["topical:x"], cites=None), 1.0, "RELATED")]
        md = to_markdown(rows, SEED, unresolved=[])
        row = [l for l in md.splitlines() if l.startswith("| arXiv only")][0]
        self.assertIn("n/r", row)
        self.assertNotIn("None", row)

    def test_json_round_trips_with_grade_and_paths(self):
        data = json.loads(to_json(RANKED))
        self.assertEqual(len(data), 3)
        first = data[0]
        self.assertEqual(first["grade"], "THREAT")
        self.assertEqual(first["title"], "Execution-guided chart repair")
        self.assertIn("backward:LIDA: A Tool", first["paths"])
        self.assertIsInstance(first["score"], float)

    def test_json_is_sorted_like_the_markdown(self):
        data = json.loads(to_json(RANKED))
        self.assertEqual([d["grade"] for d in data],
                         ["THREAT", "RELATED", "BACKGROUND"])


if __name__ == "__main__":
    unittest.main()
