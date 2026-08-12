import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from survey import traverse
from survey.seeds import Seed


class TestTraverse(unittest.TestCase):
    def setUp(self):
        self.seed = Seed(cited_keys={"a"}, cited_titles=["LIDA: A Tool"],
                         contributions=[], angles=[])
        self.orig = (traverse._lookup_refs, traverse._lookup_citers,
                     traverse._lookup_related)
        traverse._lookup_refs = lambda t, n: [
            {"title": "Chat2VIS: Generating Data Visualisations via NL",
             "year": 2023, "cited_by_count": 120, "doi": "10.1/x"}]
        traverse._lookup_citers = lambda t, n: [
            {"title": "ChartGPT: Leveraging LLMs", "year": 2024,
             "cited_by_count": 40, "doi": "10.1/y"}]
        traverse._lookup_related = lambda t, n: [
            {"title": "LIDA: A Tool", "year": 2023, "cited_by_count": 900}]

    def tearDown(self):
        (traverse._lookup_refs, traverse._lookup_citers,
         traverse._lookup_related) = self.orig

    def test_collects_from_all_three_directions(self):
        got = traverse.expand(self.seed)
        titles = sorted(c.title for c in got.values())
        self.assertIn("Chat2VIS: Generating Data Visualisations via NL", titles)
        self.assertIn("ChartGPT: Leveraging LLMs", titles)

    def test_drops_papers_the_draft_already_cites(self):
        got = traverse.expand(self.seed)
        self.assertNotIn("lida a tool", got)

    def test_records_how_each_candidate_was_reached(self):
        got = traverse.expand(self.seed)
        c = got["chat2vis generating data visualisations via nl"]
        self.assertIn("backward:LIDA: A Tool", c.paths)

    def test_merges_duplicates_across_paths(self):
        traverse._lookup_citers = lambda t, n: [
            {"title": "Chat2VIS: Generating Data Visualisations via NL",
             "year": 2023, "cited_by_count": 120}]
        got = traverse.expand(self.seed)
        c = got["chat2vis generating data visualisations via nl"]
        self.assertEqual(len(c.paths), 2, "one candidate, two discovery paths")

    def test_unknown_count_is_upgraded_when_another_engine_knows_it(self):
        """arXiv finds it first with no count; S2 finds it later with 120."""
        traverse._lookup_refs = lambda t, n: [
            {"title": "Chat2VIS", "year": 2023, "cited_by_count": None}]
        traverse._lookup_citers = lambda t, n: [
            {"title": "Chat2VIS", "year": 2023, "cited_by_count": 120}]
        traverse._lookup_related = lambda t, n: []
        got = traverse.expand(self.seed)
        self.assertEqual(got["chat2vis"].cited_by_count, 120)

    def test_unknown_stays_unknown_when_no_engine_reports_one(self):
        traverse._lookup_refs = lambda t, n: [
            {"title": "Only On arXiv", "year": 2026, "cited_by_count": None}]
        traverse._lookup_citers = lambda t, n: []
        traverse._lookup_related = lambda t, n: []
        got = traverse.expand(self.seed)
        self.assertIsNone(got["only on arxiv"].cited_by_count)

    def test_untitled_results_are_ignored(self):
        traverse._lookup_refs = lambda t, n: [{"title": None, "year": 2020},
                                              {"title": "", "year": 2020}]
        got = traverse.expand(self.seed)
        self.assertNotIn("", got)
        self.assertTrue(all(c.title for c in got.values()))

    def test_max_per_seed_is_passed_through(self):
        seen = {}
        traverse._lookup_refs = lambda t, n: seen.setdefault("n", n) and [] or []
        traverse.expand(self.seed, max_per_seed=7)
        self.assertEqual(seen["n"], 7)

    def test_unresolvable_seeds_are_recorded_not_swallowed(self):
        """Anonymous artifacts and blog posts cannot be resolved by any index."""
        traverse._lookup_refs = lambda t, n: []
        traverse._lookup_citers = lambda t, n: []
        traverse._lookup_related = lambda t, n: []
        seed = Seed(cited_keys=set(), cited_titles=["Building Effective Agents"],
                    contributions=[], angles=[])
        traverse.expand(seed)
        self.assertEqual(traverse.UNRESOLVED_SEEDS, ["Building Effective Agents"])

    def test_resolved_seeds_are_not_listed_as_unresolved(self):
        traverse.expand(self.seed)
        self.assertEqual(traverse.UNRESOLVED_SEEDS, [])

    def test_no_seed_titles_yields_nothing(self):
        empty = Seed(cited_keys=set(), cited_titles=[], contributions=[], angles=[])
        self.assertEqual(traverse.expand(empty), {})


class TestTopicalSearch(unittest.TestCase):
    """Graph traversal only reaches what the draft already cites. A thin related
    work section -- the exact failure being detected -- gives a thin neighbourhood,
    so parallel work must also be found by searching the contribution directly."""

    def setUp(self):
        self.orig = (traverse._lookup_refs, traverse._lookup_citers,
                     traverse._lookup_related, traverse._lookup_topical)
        traverse._lookup_refs = lambda t, n: []
        traverse._lookup_citers = lambda t, n: []
        traverse._lookup_related = lambda t, n: []
        traverse._lookup_topical = lambda q, n: [
            {"title": f"Chat2VIS for {q}", "year": 2023, "cited_by_count": 90}]
        self.seed = Seed(cited_keys=set(), cited_titles=["LIDA: A Tool"],
                         contributions=["natural language visualisation"],
                         angles=["natural language visualisation", "language visualisation"])

    def tearDown(self):
        (traverse._lookup_refs, traverse._lookup_citers,
         traverse._lookup_related, traverse._lookup_topical) = self.orig

    def test_topical_hits_are_added_with_their_own_path_label(self):
        got = traverse.expand(self.seed, max_angles=1)
        self.assertTrue(got, "topical search found nothing")
        c = list(got.values())[0]
        self.assertTrue(any(p.startswith("topical:") for p in c.paths), c.paths)

    def test_max_angles_bounds_the_number_of_searches(self):
        seen = []
        traverse._lookup_topical = lambda q, n: seen.append(q) or []
        traverse.expand(self.seed, max_angles=1)
        self.assertEqual(len(seen), 1)

    def test_three_word_angles_are_preferred_over_longer_ones(self):
        """The 4-gram returns nothing; the 3-gram puts the target in the top five."""
        seen = []
        traverse._lookup_topical = lambda q, n: seen.append(q) or []
        seed = Seed(cited_keys=set(), cited_titles=["LIDA: A Tool"], contributions=[],
                    angles=["natural language visualization code",
                            "natural language visualization",
                            "language visualization"])
        traverse.expand(seed, max_angles=1)
        self.assertEqual(seen[0], "natural language visualization")

    def test_shorter_angles_are_not_deleted_for_being_subsumed(self):
        seen = []
        traverse._lookup_topical = lambda q, n: seen.append(q) or []
        seed = Seed(cited_keys=set(), cited_titles=["LIDA: A Tool"], contributions=[],
                    angles=["natural language visualization code",
                            "natural language visualization"])
        traverse.expand(seed, max_angles=2)
        self.assertIn("natural language visualization", seen)

    def test_topical_results_already_cited_are_dropped(self):
        traverse._lookup_topical = lambda q, n: [{"title": "LIDA: A Tool"}]
        self.assertEqual(traverse.expand(self.seed, max_angles=1), {})

    def test_seed_with_no_angles_does_no_topical_search(self):
        seen = []
        traverse._lookup_topical = lambda q, n: seen.append(q) or []
        bare = Seed(cited_keys=set(), cited_titles=["LIDA: A Tool"],
                    contributions=[], angles=[])
        traverse.expand(bare)
        self.assertEqual(seen, [])


class TestSearchEngines(unittest.TestCase):
    """Keyword lookup is a search problem, not a citation-graph problem.
    S2 and OpenAlex are graph APIs whose relevance ranking is idiosyncratic;
    arXiv, Crossref and DBLP are genuinely different retrieval systems."""

    def setUp(self):
        self.orig = list(traverse._TOPICAL_ENGINES)

    def tearDown(self):
        traverse._TOPICAL_ENGINES[:] = self.orig

    def test_all_five_engines_are_consulted(self):
        seen = []
        traverse._TOPICAL_ENGINES[:] = [
            (name, (lambda n: (lambda q, k: seen.append(n) or []))(name))
            for name in ("s2", "openalex", "arxiv", "crossref", "dblp")]
        traverse._lookup_topical("x", 5)
        self.assertEqual(sorted(seen),
                         ["arxiv", "crossref", "dblp", "openalex", "s2"])

    def test_results_from_every_engine_are_unioned(self):
        traverse._TOPICAL_ENGINES[:] = [
            ("a", lambda q, n: [{"title": "From A"}]),
            ("b", lambda q, n: [{"title": "From B"}]),
        ]
        got = sorted(r["title"] for r in traverse._lookup_topical("x", 5))
        self.assertEqual(got, ["From A", "From B"])

    def test_one_engine_failing_does_not_lose_the_others(self):
        def boom(q, n):
            raise RuntimeError("engine down")
        traverse._TOPICAL_ENGINES[:] = [
            ("bad", boom), ("good", lambda q, n: [{"title": "Survivor"}])]
        self.assertEqual([r["title"] for r in traverse._lookup_topical("x", 5)],
                         ["Survivor"])

    def test_duplicates_across_engines_collapse(self):
        traverse._TOPICAL_ENGINES[:] = [
            ("a", lambda q, n: [{"title": "Chat2VIS: A Tool"}]),
            ("b", lambda q, n: [{"title": "Chat2VIS: A Tool."}]),
        ]
        self.assertEqual(len(traverse._lookup_topical("x", 5)), 1)

    def test_arxiv_atom_is_parsed(self):
        xml = b'''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
        <entry><title>Chat2VIS: Generating Data
        Visualisations</title><published>2023-02-04T00:00:00Z</published>
        <author><name>P Maddigan</name></author>
        <id>http://arxiv.org/abs/2302.02094v1</id></entry></feed>'''
        got = traverse._parse_arxiv_atom(xml)
        self.assertEqual(got[0]["title"],
                         "Chat2VIS: Generating Data Visualisations")
        self.assertEqual(got[0]["year"], 2023)
        self.assertEqual(got[0]["authors"], ["P Maddigan"])
        self.assertEqual(got[0]["venue"], "arXiv")

    def test_crossref_payload_is_mapped(self):
        payload = {"message": {"items": [{
            "title": ["LLM4Vis: Explainable Visualization Recommendation"],
            "author": [{"given": "Lei", "family": "Wang"}],
            "container-title": ["EMNLP"], "DOI": "10.1/z",
            "issued": {"date-parts": [[2023, 10]]},
            "is-referenced-by-count": 42}]}}
        got = traverse._crossref_to_dicts(payload)
        self.assertEqual(got[0]["title"],
                         "LLM4Vis: Explainable Visualization Recommendation")
        self.assertEqual(got[0]["year"], 2023)
        self.assertEqual(got[0]["venue"], "EMNLP")
        self.assertEqual(got[0]["cited_by_count"], 42)
        self.assertEqual(got[0]["authors"], ["Lei Wang"])


class TestS2Fallback(unittest.TestCase):
    """OpenAlex alone is a single point of failure: when its breaker trips, the
    whole sweep degrades to nothing and a benchmark measures uptime, not recall."""

    def setUp(self):
        self.orig = (traverse._oa_refs, traverse._oa_citers, traverse._oa_related,
                     traverse._s2_refs, traverse._s2_citers, traverse._s2_related,
                     traverse._s2_search, traverse._oa_search)

    def tearDown(self):
        (traverse._oa_refs, traverse._oa_citers, traverse._oa_related,
         traverse._s2_refs, traverse._s2_citers, traverse._s2_related,
         traverse._s2_search, traverse._oa_search) = self.orig

    def test_s2_leads_because_openalex_is_budget_capped(self):
        """OpenAlex charges $0.001/search against a small daily allowance."""
        traverse._oa_refs = lambda t, n: [{"title": "From OpenAlex"}]
        traverse._s2_refs = lambda t, n: [{"title": "From S2"}]
        self.assertEqual([r["title"] for r in traverse._lookup_refs("x", 5)],
                         ["From S2"])

    def test_openalex_is_used_when_s2_returns_nothing(self):
        traverse._s2_refs = lambda t, n: []
        traverse._oa_refs = lambda t, n: [{"title": "From OpenAlex"}]
        self.assertEqual([r["title"] for r in traverse._lookup_refs("x", 5)],
                         ["From OpenAlex"])

    def test_fallback_applies_to_citers_and_related_too(self):
        traverse._s2_citers = lambda t, n: []
        traverse._oa_citers = lambda t, n: [{"title": "OA citer"}]
        traverse._s2_related = lambda t, n: []
        traverse._oa_related = lambda t, n: [{"title": "OA related"}]
        self.assertEqual([r["title"] for r in traverse._lookup_citers("x", 5)],
                         ["OA citer"])
        self.assertEqual([r["title"] for r in traverse._lookup_related("x", 5)],
                         ["OA related"])

    def test_s2_reference_payload_is_mapped(self):
        payload = {"data": [{"citedPaper": {
            "title": "Chat2VIS", "year": 2023, "venue": "IEEE Access",
            "citationCount": 120, "externalIds": {"DOI": "10.1/x"},
            "authors": [{"name": "P Maddigan"}]}}]}
        got = traverse._s2_papers(payload, "citedPaper")
        self.assertEqual(got[0]["title"], "Chat2VIS")
        self.assertEqual(got[0]["year"], 2023)
        self.assertEqual(got[0]["cited_by_count"], 120)
        self.assertEqual(got[0]["doi"], "10.1/x")
        self.assertEqual(got[0]["authors"], ["P Maddigan"])

    def test_s2_payload_tolerates_missing_fields(self):
        payload = {"data": [{"citedPaper": None}, {"citedPaper": {"title": "T"}}]}
        got = traverse._s2_papers(payload, "citedPaper")
        self.assertEqual([g["title"] for g in got], ["T"])


if __name__ == "__main__":
    unittest.main()
