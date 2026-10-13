import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))
from survey import lookup


def cr(title, year=2024, venue="Proc. GECCO", doi="10.1/x"):
    return {"title": title, "year": year, "venue": venue, "doi": doi, "authors": ["Ana Ruiz"]}


def ax(title, ident="http://arxiv.org/abs/2501.01234v2", year=2025):
    return {"id": ident, "title": title, "year": year, "venue": "arXiv", "doi": None, "authors": ["Bo Li"]}


class TestLookup(unittest.TestCase):
    def setUp(self):
        self.orig = dict(lookup.ENGINES)

    def tearDown(self):
        lookup.ENGINES.clear(); lookup.ENGINES.update(self.orig)

    def use(self, crossref=None, arxiv=None):
        lookup.ENGINES.clear()
        lookup.ENGINES["crossref"] = lambda t: crossref(t) if callable(crossref) else (crossref or [])
        lookup.ENGINES["arxiv"] = lambda t: arxiv(t) if callable(arxiv) else (arxiv or [])

    def test_published_record_gives_doi_year_venue(self):
        self.use(crossref=[cr("Deep Generative Approaches for Oversampling")])
        r = lookup.resolve("Deep generative approaches for oversampling")
        self.assertTrue(r["found"])
        self.assertEqual((r["doi"], r["year"], r["venue"]), ("10.1/x", 2024, "Proc. GECCO"))

    def test_punctuation_and_case_do_not_matter(self):
        self.use(crossref=[cr("PromptFE: Automated Feature Engineering by Prompting")])
        self.assertTrue(lookup.resolve("PromptFE - automated feature engineering by prompting")["found"])

    def test_unrelated_top_hit_is_not_a_match(self):
        self.use(crossref=[cr("A Survey of Evolutionary Computation")], arxiv=[ax("Something Else Entirely Here")])
        r = lookup.resolve("Optimal mutation rates for the (1+1) EA on OneMax")
        self.assertFalse(r["found"])

    def test_preprint_only_gives_arxiv_id_without_version(self):
        self.use(arxiv=[ax("SE-Search: Self-Evolving Search Agent via Memory and Dense Reward")])
        r = lookup.resolve("SE-Search: Self-Evolving Search Agent via Memory and Dense Reward")
        self.assertTrue(r["found"])
        self.assertEqual(r["arxiv"], "2501.01234")
        self.assertIsNone(r["doi"])

    def test_published_and_preprint_are_both_reported(self):
        t = "Kolmogorov-Arnold Network for Transistor Compact Modeling"
        self.use(crossref=[cr(t, doi="10.2/k")], arxiv=[ax(t)])
        r = lookup.resolve(t)
        self.assertEqual((r["doi"], r["arxiv"]), ("10.2/k", "2501.01234"))

    def test_subtitle_added_by_published_version_still_matches(self):
        self.use(crossref=[cr("Evolving Comprehensive Proxies for Zero-Shot Neural Architecture Search: A Study")])
        self.assertTrue(lookup.resolve("Evolving Comprehensive Proxies for Zero-Shot Neural Architecture Search")["found"])

    def test_supplementary_file_record_is_skipped_for_the_article(self):
        t = "Deep Reinforcement Learning for Dynamic Algorithm Selection: A Proof-of-Principle Study on Differential Evolution"
        self.use(crossref=[cr(t + "_supp1-3374889.pdf", doi="10.1109/tsmc.2024.3374889/mm1", venue=""),
                           cr(t, doi="10.1109/tsmc.2024.3374889", venue="IEEE Trans. SMC")])
        r = lookup.resolve(t)
        self.assertEqual((r["doi"], r["venue"]), ("10.1109/tsmc.2024.3374889", "IEEE Trans. SMC"))

    def test_exact_title_preferred_over_a_longer_prefix_match(self):
        t = "Evolving Comprehensive Proxies for Zero-Shot Neural Architecture Search"
        self.use(crossref=[cr(t + ": Extended Version With Proofs", doi="10.9/long"), cr(t, doi="10.9/exact")])
        self.assertEqual(lookup.resolve(t)["doi"], "10.9/exact")

    def test_a_failing_engine_does_not_stop_the_others(self):
        def boom(t):
            raise OSError("down")
        self.use(crossref=boom, arxiv=[ax("Agentic Bayesian Optimization through Surrogates")])
        self.assertTrue(lookup.resolve("Agentic Bayesian Optimization through Surrogates")["found"])

    def test_resolve_all_keeps_input_order(self):
        self.use(crossref=lambda t: [cr(t)])
        out = lookup.resolve_all(["Beta paper title here", "Alpha paper title here"])
        self.assertEqual([r["query"] for r in out], ["Beta paper title here", "Alpha paper title here"])


if __name__ == "__main__":
    unittest.main()
