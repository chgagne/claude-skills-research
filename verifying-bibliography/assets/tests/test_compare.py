import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bibcheck.bibparse import Entry
from bibcheck.sources import Record
from bibcheck.compare import check_entry


def sev(findings, field):
    return [f.severity for f in findings if f.field == field]


class TestCompare(unittest.TestCase):
    def test_draco_fabricated_title_is_critical(self):
        e = Entry("moritz2019draco", "article", {
            "title": "Draco: An Approach to Generating Visualizations with a "
                     "Computational Design Process",
            "author": "Moritz, Dominik and Wang, Chenglong",
            "volume": "26", "number": "1", "pages": "661--671", "year": "2019",
            "doi": "10.1109/TVCG.2018.2865240"})
        r = Record(title="Formalizing Visualization Design Knowledge as Constraints: "
                         "Actionable and Extensible Models in Draco",
                   authors=["Dominik Moritz", "Chenglong Wang"],
                   volume="25", issue="1", pages="438-448", year=2019,
                   source="crossref", strong=True)
        f = check_entry(e, [r])
        self.assertIn("CRITICAL", sev(f, "title"))
        self.assertIn("MAJOR", sev(f, "volume"))
        self.assertIn("MAJOR", sev(f, "pages"))

    def test_voyager_wrong_doi_points_at_other_paper(self):
        e = Entry("wongsuphasawat2016voyager", "article", {
            "title": "Voyager: Exploratory Visual-Analysis by Recommendation",
            "author": "Wongsuphasawat, Kanit and Bach, Bill and Dragicevic, Pierre",
            "pages": "114--123", "year": "2016", "doi": "10.1109/TVCG.2015.2467251"})
        r = Record(title="High-Quality Ultra-Compact Grid Layout of Grouped Networks",
                   authors=["Vahan Yoghourdjian", "Tim Dwyer"],
                   volume="22", issue="1", pages="339-348", year=2016,
                   source="crossref", strong=True)
        f = check_entry(e, [r])
        self.assertIn("CRITICAL", sev(f, "title"))
        self.assertIn("CRITICAL", sev(f, "author"))

    def test_misc_entry_is_skipped_not_matched(self):
        e = Entry("anthropic2024agents", "misc", {
            "title": "Building Effective Agents", "author": "Anthropic",
            "year": "2024", "url": "https://www.anthropic.com/engineering/"})
        f = check_entry(e, [])
        self.assertEqual([x.severity for x in f], ["SKIP"])

    def test_preprint_vs_published_year_is_not_a_finding(self):
        e = Entry("matsubara2024rethinking", "inproceedings", {
            "title": "Rethinking Symbolic Regression Datasets and Benchmarks",
            "author": "Matsubara, Yoshitomo", "year": "2024"})
        pub = Record(title="Rethinking Symbolic Regression Datasets and Benchmarks",
                     authors=["Yoshitomo Matsubara"], year=2024,
                     source="dblp", strong=False)
        pre = Record(title="Rethinking Symbolic Regression Datasets and Benchmarks",
                     authors=["Yoshitomo Matsubara"], year=2022,
                     source="arxiv", strong=True)
        self.assertEqual(sev(check_entry(e, [pub, pre]), "year"), [])

    def test_book_year_difference_is_minor(self):
        e = Entry("strogatz1994nonlinear", "book", {
            "title": "Nonlinear Dynamics and Chaos", "author": "Strogatz, Steven H",
            "year": "1994"})
        r = Record(title="Nonlinear Dynamics and Chaos", authors=["Steven H Strogatz"],
                   venue="Westview Press", year=2024, doi="10.1201/9780429492563",
                   source="crossref", strong=True)
        self.assertEqual(sev(check_entry(e, [r]), "year"), ["MINOR"])

    def test_no_record_is_unverified(self):
        e = Entry("ghost2020", "article", {"title": "A Paper", "author": "X, Y",
                                           "year": "2020"})
        self.assertEqual([x.severity for x in check_entry(e, [])], ["UNVERIFIED"])

    def test_clean_entry_produces_no_findings(self):
        e = Entry("dibia2023lida", "inproceedings", {
            "title": "LIDA: A Tool for Automatic Generation of Grammar-Agnostic "
                     "Visualizations and Infographics using Large Language Models",
            "author": "Dibia, Victor", "year": "2023", "pages": "113--126",
            "doi": "10.18653/v1/2023.acl-demo.11"})
        r = Record(title="LIDA: A Tool for Automatic Generation of Grammar-Agnostic "
                         "Visualizations and Infographics using Large Language Models",
                   authors=["Victor Dibia"], year=2023, pages="113-126",
                   source="acl/crossref", strong=True)
        self.assertEqual(check_entry(e, [r]), [])

    # --- rules added after the Task 3 live run ---
    def test_dblp_corr_pseudo_volume_is_ignored(self):
        """DBLP puts 'abs/2604.08324' in volume for CoRR entries."""
        e = Entry("someref", "article", {
            "title": "Structured Representations for Program Synthesis",
            "author": "Dupré, B.", "volume": "12", "year": "2026"})
        r = Record(title="Structured Representations for Program Synthesis",
                   authors=["Benoit Dupré"], volume="abs/2604.08324", year=2026,
                   source="dblp", strong=False)
        self.assertEqual(sev(check_entry(e, [r]), "volume"), [])

    def test_given_name_mismatch_is_minor(self):
        """hu2018vizml: 'Bakker, Alex' for Michiel A. Bakker, 'Li, Ma' for Stephen Li."""
        e = Entry("hu2018vizml", "article", {
            "title": "VizML: A Machine Learning Approach to Visualization Recommendation",
            "author": "Hu, Kevin and Bakker, Alex and Li, Ma", "year": "2019",
            "doi": "10.1145/3290605.3300358"})
        r = Record(title="VizML: A Machine Learning Approach to Visualization Recommendation",
                   authors=["Kevin Zeng Hu", "Michiel A. Bakker", "Stephen Li"],
                   year=2019, source="crossref", strong=True)
        f = check_entry(e, [r])
        self.assertEqual(sev(f, "author-name-form"), ["MINOR"])
        names = [x.in_bib for x in f if x.field == "author-name-form"][0]
        self.assertIn("Bakker", names)
        self.assertIn("Li", names)


    # --- rules added after the Task 4 live preview ---
    def test_inproceedings_with_url_is_not_skipped(self):
        """SKIP is for @misc/@online only, not any DOI-less entry with a URL."""
        e = Entry("li2026gensr", "inproceedings", {
            "title": "GenSR: Symbolic regression based on equation generative space",
            "author": "Qian Li", "year": "2026",
            "url": "https://openreview.net/forum?id=8emIjwUQZg"})
        r = Record(title="GenSR: Symbolic regression based on equation generative space",
                   authors=["Qian Li"], year=2026, source="openalex", strong=False)
        self.assertNotIn("SKIP", [x.severity for x in check_entry(e, [r])])

    def test_preprint_only_records_do_not_fire_year(self):
        """Bib cites the published version; only preprint records exist."""
        e = Entry("matsubara2024rethinking", "article", {
            "title": "Rethinking Symbolic Regression Datasets and Benchmarks",
            "author": "Matsubara, Yoshitomo",
            "journal": "Journal of Data-centric Machine Learning Research (DMLR)",
            "year": "2024"})
        recs = [Record(title="Rethinking Symbolic Regression Datasets and Benchmarks",
                       authors=["Yoshitomo Matsubara"], venue="CoRR", year=2022,
                       volume="abs/2206.10540", source="dblp", strong=False),
                Record(title="Rethinking Symbolic Regression Datasets and Benchmarks",
                       authors=["Yoshitomo Matsubara"], venue="arXiv (Cornell University)",
                       year=2022, source="openalex", strong=False),
                # Semantic Scholar reports the published venue with the preprint year.
                Record(title="Rethinking Symbolic Regression Datasets and Benchmarks",
                       authors=["Yoshitomo Matsubara"],
                       venue="J. Data-centric Mach. Learn. Res.", year=2022,
                       source="s2", strong=False)]
        self.assertEqual(sev(check_entry(e, recs), "year"), [])

    def test_conference_entry_with_spurious_volume_is_minor(self):
        """ICLR has no volumes; 'volume={2025}' is a Scholar-export artifact."""
        e = Entry("yu2024mdlformer", "inproceedings", {
            "title": "Symbolic regression via MDLformer-guided search",
            "author": "Yu, Zihan", "booktitle": "International Conference on "
                                                "Learning Representations",
            "volume": "2025", "year": "2025"})
        r = Record(title="Symbolic regression via MDLformer-guided search",
                   authors=["Zihan Yu"], venue="ICLR", year=2025, volume=None,
                   source="dblp", strong=False)
        self.assertEqual(sev(check_entry(e, [r]), "volume"), ["MINOR"])

    def test_two_authors_sharing_a_family_name_do_not_false_alarm(self):
        """zhang2025rag has both Hengzhe Zhang and Mengjie Zhang."""
        e = Entry("zhang2025rag", "inproceedings", {
            "title": "RAG-SR: Retrieval-augmented generation for neural symbolic regression",
            "author": "Zhang, Hengzhe and Chen, Qi and Zhang, Mengjie", "year": "2025"})
        r = Record(title="RAG-SR: Retrieval-augmented generation for neural symbolic regression",
                   authors=["Hengzhe Zhang", "Qi Chen", "Mengjie Zhang"],
                   venue="ICLR", year=2025, source="dblp", strong=False)
        self.assertEqual(sev(check_entry(e, [r]), "author-name-form"), [])

    # --- rules added after the Task 5 CLI checkpoint ---
    def test_venue_not_compared_against_preprint_record(self):
        """An arXiv record's venue is always 'arXiv'; that is not a venue error."""
        e = Entry("chen2026coda", "inproceedings", {
            "title": "CoDA", "author": "Chen, X",
            "booktitle": "International Conference on Learning Representations",
            "year": "2026"})
        r = Record(title="CoDA", authors=["X Chen"], venue="arXiv", year=2026,
                   source="arxiv", strong=True)
        self.assertEqual(sev(check_entry(e, [r]), "venue"), [])

    def test_venue_punctuation_is_ignored(self):
        e = Entry("yang2024matplotagent", "inproceedings", {
            "title": "MatPlotAgent", "author": "Yang, Z",
            "booktitle": "Findings of the Association for Computational "
                         "Linguistics: ACL 2024", "year": "2024"})
        r = Record(title="MatPlotAgent", authors=["Zhiyu Yang"],
                   venue="Findings of the Association for Computational "
                         "Linguistics ACL 2024",
                   year=2024, source="acl/crossref", strong=True)
        self.assertEqual(sev(check_entry(e, [r]), "venue"), [])

    def test_numbered_series_volume_is_legitimate(self):
        """Advances in NeurIPS 2022 really is volume 35 -- must not fire."""
        e = Entry("kamienny2022e2e", "inproceedings", {
            "title": "End-to-end symbolic regression with transformers",
            "author": "Kamienny, Pierre-Alexandre",
            "booktitle": "Advances in Neural Information Processing Systems",
            "volume": "35", "year": "2022"})
        r = Record(title="End-to-end symbolic regression with transformers",
                   authors=["Pierre-Alexandre Kamienny"], venue="NeurIPS",
                   year=2022, volume=None, source="dblp", strong=False)
        self.assertEqual(sev(check_entry(e, [r]), "volume"), [])

    def test_year_as_volume_is_an_artifact(self):
        """'volume={2025}' on a 2025 ICLR paper is the year leaking in."""
        e = Entry("zhang2025rag", "inproceedings", {
            "title": "RAG-SR", "author": "Zhang, Hengzhe",
            "booktitle": "International Conference on Learning Representations",
            "volume": "2025", "year": "2025"})
        r = Record(title="RAG-SR", authors=["Hengzhe Zhang"], venue="ICLR",
                   year=2025, volume=None, source="dblp", strong=False)
        self.assertEqual(sev(check_entry(e, [r]), "volume"), ["MINOR"])

    def test_title_mismatch_on_weak_record_stops_all_comparison(self):
        """moraglio2015semantic: title search returned two different papers.

        Without identity, no other field can be compared -- the year difference
        would be reported as a defect in an entry that is correct.
        """
        e = Entry("moraglio2015semantic", "inproceedings", {
            "title": "Semantic genetic programming",
            "author": "Moraglio, Alberto and Krawiec, Krzysztof",
            "booktitle": "Proceedings of the Companion Publication of the 2015 "
                         "Annual Conference on Genetic and Evolutionary Computation",
            "pages": "603--627", "year": "2015"})
        recs = [Record(title="Cartesian Genetic Programming as an Optimizer of "
                             "Programs Evolved with Geometric Semantic GP",
                       authors=["Someone Else"], venue="EuroGP", year=2019,
                       source="dblp", strong=False),
                Record(title="Geometric Semantic Genetic Programming",
                       authors=["Alberto Moraglio"], venue="LNCS", year=2012,
                       source="openalex", strong=False)]
        f = check_entry(e, recs)
        self.assertEqual(sev(f, "year"), [])
        self.assertEqual([x.severity for x in f], ["WEAK"])

    def test_no_volume_or_pages_comparison_against_weak_record(self):
        """A title-search match does not establish the same publication instance."""
        e = Entry("strogatz1995nonlinear", "article", {
            "title": "Nonlinear Dynamics and Chaos", "author": "Strogatz, Steven H",
            "journal": "Physics Today", "volume": "48", "number": "3",
            "pages": "93", "year": "1995"})
        r = Record(title="Nonlinear Dynamics and Chaos", authors=["Steven H Strogatz"],
                   venue="SIAM Rev.", year=1995, volume="37", pages="280-281",
                   source="dblp", strong=False)
        f = check_entry(e, [r])
        self.assertEqual(sev(f, "volume"), [])
        self.assertEqual(sev(f, "pages"), [])
        self.assertEqual(sev(f, "issue"), [])


if __name__ == "__main__":
    unittest.main()
