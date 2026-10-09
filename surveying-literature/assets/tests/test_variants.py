"""Opt-in sweep variants for the improvement loop: a seed-set recommendation path,
agent-supplied angles, and coupling-based ranking."""
import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from survey import traverse
from survey.rank import rank
from survey.seeds import Seed


class Base(unittest.TestCase):
    def setUp(self):
        self.orig = {n: getattr(traverse, n) for n in
                     ("_lookup_refs", "_lookup_citers", "_lookup_related", "_lookup_topical",
                      "_s2_resolve", "_seedset_recommend")}
        traverse._lookup_refs = lambda t, n: []
        traverse._lookup_citers = lambda t, n: []
        traverse._lookup_related = lambda t, n: []
        self.queries = []
        traverse._lookup_topical = lambda q, n: (self.queries.append(q), [])[1]

    def tearDown(self):
        for n, f in self.orig.items():
            setattr(traverse, n, f)


class TestSeedSet(Base):
    def test_seedset_path_is_off_by_default(self):
        called = []
        traverse._seedset_recommend = lambda ids, n: called.append(ids) or []
        traverse.expand(Seed(cited_titles=["A", "B"], angles=[]))
        self.assertEqual(called, [])

    def test_seedset_recommends_from_every_resolved_seed(self):
        traverse._s2_resolve = lambda t: {"A": "pa", "B": None, "C": "pc"}[t]
        got = {}
        def rec(ids, n):
            got["ids"] = ids
            return [{"title": "Missing Prior Work", "year": 2025, "cited_by_count": 3}]
        traverse._seedset_recommend = rec
        store = traverse.expand(Seed(cited_titles=["A", "B", "C"], angles=[]), seedset=True)
        self.assertEqual(got["ids"], ["pa", "pc"])
        self.assertIn("related-set", store["missing prior work"].paths)


class TestAngles(Base):
    def test_supplied_angles_go_first_and_keep_their_wording(self):
        traverse.expand(Seed(cited_titles=[], angles=["auto phrase one", "auto phrase two"]),
                        max_angles=3, extra_angles=["phenotypic niching lexicase"])
        self.assertEqual(self.queries[0], "phenotypic niching lexicase")
        self.assertEqual(len(self.queries), 3)

    def test_supplied_angles_alone_fill_the_budget(self):
        traverse.expand(Seed(cited_titles=[], angles=["auto"]), max_angles=2,
                        extra_angles=["q1", "q2", "q3"])
        self.assertEqual(self.queries, ["q1", "q2"])


class TestCouplingRank(unittest.TestCase):
    def test_paper_reached_from_many_seeds_beats_one_matching_an_angle(self):
        from survey.traverse import Candidate
        many = Candidate(title="Unrelated Wording Entirely", year=2024, cited_by_count=10,
                         paths=["backward:S1", "forward:S2", "related:S3", "backward:S4"])
        # THREAT under the default ranking: matches an angle and was reached twice
        angle = Candidate(title="Symbolic regression with gradients", year=2024, cited_by_count=10,
                          paths=["topical:symbolic regression", "topical:regression gradients"])
        seed = Seed(cited_titles=[], angles=["symbolic regression", "regression gradients"])
        cands = {"m": many, "a": angle}
        self.assertEqual(rank(cands, seed)[0][0].title, angle.title)          # default: grade first
        self.assertEqual(rank(cands, seed, mode="coupling")[0][0].title, many.title)

    def test_distinct_seeds_not_paths_are_counted(self):
        from survey.rank import seed_links
        c = traverse.Candidate(title="x", paths=["backward:S1", "forward:S1", "related:S2", "topical:q"])
        self.assertEqual(seed_links(c), 2)


if __name__ == "__main__":
    unittest.main()
