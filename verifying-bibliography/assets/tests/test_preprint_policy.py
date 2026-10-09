"""Policy: when a paper has both a venue of record and a preprint, the .bib must
cite the published version. The preprint may be kept as a supplementary field."""
import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bibcheck.bibparse import Entry
from bibcheck.sources import Record
from bibcheck.compare import check_entry


def sev(findings, field):
    return [f.severity for f in findings if f.field == field]


PUBLISHED = Record(title="Symbolic regression via MDLformer-guided search",
                   authors=["Zihan Yu"], venue="ICLR", year=2025,
                   source="dblp", strong=False)
PREPRINT = Record(title="Symbolic regression via MDLformer-guided search",
                  authors=["Zihan Yu"], venue="arXiv", year=2024,
                  source="arxiv", strong=True)


class TestPreprintPolicy(unittest.TestCase):
    def test_arxiv_entry_with_published_version_is_flagged(self):
        e = Entry("someref", "article", {
            "title": "Symbolic regression via MDLformer-guided search",
            "author": "Yu, Zihan", "journal": "arXiv preprint arXiv:2405.12345",
            "year": "2024"})
        f = check_entry(e, [PREPRINT, PUBLISHED])
        self.assertEqual(sev(f, "preprint"), ["MINOR"])
        self.assertIn("ICLR", [x.in_record for x in f if x.field == "preprint"][0])

    def test_venue_plus_eprint_is_the_desired_state(self):
        """booktitle=ICLR with eprint kept as a supplementary field is correct."""
        e = Entry("meidani2024snip", "inproceedings", {
            "title": "Symbolic regression via MDLformer-guided search",
            "author": "Yu, Zihan",
            "booktitle": "International Conference on Learning Representations",
            "eprint": "2405.12345", "archiveprefix": "arXiv", "year": "2025"})
        self.assertEqual(sev(check_entry(e, [PUBLISHED]), "preprint"), [])

    def test_openalex_match_alone_does_not_claim_a_published_version(self):
        """OpenAlex offered 'Int. J. Neural Syst.' for the InfoNCE preprint."""
        e = Entry("oord2018infonce", "article", {
            "title": "Representation learning with contrastive predictive coding",
            "author": "van den Oord, Aaron",
            "journal": "arXiv preprint arXiv:1807.03748", "year": "2018"})
        bogus = Record(title="Representation learning with contrastive predictive coding",
                       authors=["Aaron van den Oord"], venue="Int. J. Neural Syst.",
                       year=2023, source="openalex", strong=False)
        self.assertEqual(sev(check_entry(e, [bogus]), "preprint"), [])

    def test_different_paper_from_a_trusted_source_is_not_the_published_version(self):
        """DBLP answered the InfoNCE preprint with an EEG paper of a similar name."""
        e = Entry("oord2018infonce", "article", {
            "title": "Representation Learning with Contrastive Predictive Coding",
            "author": "van den Oord, Aaron",
            "journal": "arXiv preprint arXiv:1807.03748", "year": "2018"})
        preprint = Record(title="Representation Learning with Contrastive Predictive Coding",
                          authors=["Aaron van den Oord"], venue="arXiv", year=2018,
                          source="arxiv", strong=True)
        other = Record(title="Self-Supervised EEG Representation Learning with "
                             "Contrastive Predictive Coding",
                       authors=["Someone Else"], venue="Int. J. Neural Syst.",
                       year=2023, source="dblp", strong=False)
        self.assertEqual(sev(check_entry(e, [preprint, other]), "preprint"), [])

    def test_misc_arxiv_entry_is_not_skipped(self):
        """An @misc arXiv preprint is a paper, not a web resource."""
        e = Entry("someref", "misc", {
            "title": "Symbolic regression via MDLformer-guided search",
            "author": "Yu, Zihan", "eprint": "2405.12345",
            "archiveprefix": "arXiv", "year": "2024"})
        f = check_entry(e, [PREPRINT, PUBLISHED])
        self.assertNotIn("SKIP", [x.severity for x in f])
        self.assertEqual(sev(f, "preprint"), ["MINOR"])

    def test_entry_already_citing_the_venue_is_clean(self):
        e = Entry("someref", "inproceedings", {
            "title": "Symbolic regression via MDLformer-guided search",
            "author": "Yu, Zihan",
            "booktitle": "International Conference on Learning Representations",
            "year": "2025"})
        self.assertEqual(sev(check_entry(e, [PUBLISHED]), "preprint"), [])

    def test_preprint_with_no_published_version_is_not_flagged(self):
        e = Entry("someref", "article", {
            "title": "Symbolic regression via MDLformer-guided search",
            "author": "Yu, Zihan", "journal": "arXiv preprint arXiv:2405.12345",
            "year": "2024"})
        self.assertEqual(sev(check_entry(e, [PREPRINT]), "preprint"), [])

    def test_web_resource_misc_entry_still_skipped(self):
        """anthropic2024agents is a blog post: no arXiv id, no DOI."""
        e = Entry("anthropic2024agents", "misc", {
            "title": "Building Effective Agents", "author": "Anthropic",
            "year": "2024", "url": "https://www.anthropic.com/engineering/"})
        self.assertEqual([x.severity for x in check_entry(e, [])], ["SKIP"])


    def test_published_title_that_adds_a_subtitle_is_the_published_version(self):
        """arXiv 'Batch Tournament Selection for Genetic Programming' became the GECCO
        paper '...: the quality of lexicase, the speed of tournament'."""
        e = Entry("melo2019batch", "article", {
            "title": "Batch Tournament Selection for Genetic Programming",
            "author": "Melo, Vinicius V. and Vargas, Danilo Vasconcellos and Banzhaf, Wolfgang",
            "journal": "arXiv preprint arXiv:1904.08658", "year": "2019"})
        gecco = Record(title="Batch tournament selection for genetic programming: the quality "
                             "of lexicase, the speed of tournament",
                       authors=["Vinícius Veloso de Melo", "Danilo Vasconcellos Vargas", "Wolfgang Banzhaf"],
                       venue="GECCO", year=2019, source="dblp", strong=False)
        arx = Record(title="Batch Tournament Selection for Genetic Programming",
                     authors=["Vinicius V. Melo"], venue="arXiv", year=2019, source="arxiv", strong=True)
        self.assertEqual(sev(check_entry(e, [arx, gecco]), "preprint"), ["MINOR"])

    def test_subtitle_extension_needs_the_same_first_author(self):
        e = Entry("x2020", "article", {
            "title": "Neural Architecture Search for Tabular Data",
            "author": "Ivanova, Maria", "journal": "arXiv preprint arXiv:2001.00001", "year": "2020"})
        other = Record(title="Neural Architecture Search for Tabular Data: a benchmark",
                       authors=["Kenji Sato"], venue="NeurIPS", year=2021, source="dblp", strong=False)
        arx = Record(title="Neural Architecture Search for Tabular Data", authors=["Maria Ivanova"],
                     venue="arXiv", year=2020, source="arxiv", strong=True)
        self.assertEqual(sev(check_entry(e, [arx, other]), "preprint"), [])

    def test_short_generic_title_is_not_extended(self):
        e = Entry("y2015", "article", {
            "title": "Deep Learning", "author": "LeCun, Yann",
            "journal": "arXiv preprint arXiv:1501.00001", "year": "2015"})
        other = Record(title="Deep Learning: methods and applications", authors=["Yann LeCun"],
                       venue="Some Journal", year=2016, source="dblp", strong=False)
        arx = Record(title="Deep Learning", authors=["Yann LeCun"], venue="arXiv", year=2015,
                     source="arxiv", strong=True)
        self.assertEqual(sev(check_entry(e, [arx, other]), "preprint"), [])


if __name__ == "__main__":
    unittest.main()
