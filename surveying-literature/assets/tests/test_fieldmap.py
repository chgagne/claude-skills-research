import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from survey.fieldmap import cluster, order_clusters, to_markdown
from survey.traverse import Candidate


def c(title, year, refs, cites=0):
    cand = Candidate(title=title, authors=["A"], year=year, venue="V", doi=None,
                     paths=["topical:x"], cited_by_count=cites)
    cand.referenced = set(refs)
    return cand


class TestCluster(unittest.TestCase):
    def test_papers_sharing_references_cluster_together(self):
        a = c("A", 2020, ["r1", "r2", "r3"])
        b = c("B", 2021, ["r1", "r2", "r3"])
        far = c("C", 2022, ["z1", "z2", "z3"])
        groups = cluster({"a": a, "b": b, "c": far}, min_shared=3)
        sizes = sorted(len(g) for g in groups)
        self.assertEqual(sizes, [1, 2])

    def test_below_threshold_does_not_cluster(self):
        a = c("A", 2020, ["r1", "r2", "r3"])
        b = c("B", 2021, ["r1", "r9", "r8"])
        self.assertEqual(sorted(len(g) for g in cluster({"a": a, "b": b},
                                                        min_shared=3)), [1, 1])

    def test_coupling_is_transitive(self):
        """A couples to B, B couples to D, so all three are one line of work,
        even though A and D share only two references."""
        a = c("A", 2020, ["r1", "r2", "r3"])
        b = c("B", 2021, ["r1", "r2", "r3", "r4"])
        d = c("D", 2022, ["r2", "r3", "r4"])
        self.assertEqual(len(a.referenced & d.referenced), 2, "A~D is below threshold")
        self.assertEqual([len(g) for g in cluster({"a": a, "b": b, "d": d},
                                                  min_shared=3)], [3])

    def test_papers_without_reference_data_stand_alone(self):
        a = c("A", 2020, [])
        b = c("B", 2021, [])
        self.assertEqual(sorted(len(g) for g in cluster({"a": a, "b": b},
                                                        min_shared=3)), [1, 1])


class TestOrdering(unittest.TestCase):
    def test_clusters_are_ordered_by_median_year(self):
        old = [c("Old1", 2001, []), c("Old2", 2003, [])]
        new = [c("New1", 2023, []), c("New2", 2025, [])]
        self.assertEqual([g[0].title for g in order_clusters([new, old])],
                         ["Old1", "New1"])

    def test_missing_years_do_not_crash_ordering(self):
        g1 = [c("NoYear", None, [])]
        g2 = [c("Dated", 2010, [])]
        self.assertEqual(len(order_clusters([g1, g2])), 2)


class TestFieldMapReport(unittest.TestCase):
    def test_lineage_order_is_visible(self):
        groups = [[c("Early", 2005, [])], [c("Recent", 2024, [])]]
        md = to_markdown(order_clusters(groups), topic="symbolic regression")
        self.assertIn("symbolic regression", md)
        self.assertLess(md.index("Early"), md.index("Recent"))

    def test_reports_span_of_each_cluster(self):
        md = to_markdown([[c("A", 2010, []), c("B", 2020, [])]], topic="t")
        self.assertIn("2010", md)
        self.assertIn("2020", md)

    def test_empty_map_is_stated_not_implied(self):
        self.assertIn("No clusters", to_markdown([], topic="t"))


if __name__ == "__main__":
    unittest.main()
