"""DBLP through sparql.dblp.org. dblp.org itself now disallows every robot (robots.txt
'User-agent: * / Disallow: /') and answers scripts with a proof-of-work page; the SPARQL
host allows /sparql with a 10 s crawl delay."""
import unittest, sys, pathlib, json, tempfile, urllib.parse, os
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bibcheck import sources


def _b(v): return {"type": "literal", "value": v}


def _row(pub, title, venue, year, typ, ordinal, name, doi=None, pages=None, volume=None):
    r = {"p": {"type": "uri", "value": pub}, "t": _b(title), "venue": _b(venue), "year": _b(year),
         "type": {"type": "uri", "value": "https://dblp.org/rdf/schema#" + typ},
         "ord": _b(str(ordinal)), "name": _b(name)}
    if doi: r["doi"] = {"type": "uri", "value": "https://doi.org/" + doi}
    if pages: r["pages"] = _b(pages)
    if volume: r["volume"] = _b(volume)
    return r


GECCO = "https://dblp.org/rec/conf/gecco/MeloVB19"
CORR = "https://dblp.org/rec/journals/corr/abs-1904-08658"
TITLE_GECCO = ("Batch tournament selection for genetic programming: the quality of lexicase, "
               "the speed of tournament.")
BATCH = {"head": {"vars": []}, "results": {"bindings": [
    _row(CORR, "Batch Tournament Selection for Genetic Programming.", "CoRR", "2019", "Informal", 2, "Danilo Vasconcellos Vargas", "10.48550/ARXIV.1904.08658"),
    _row(CORR, "Batch Tournament Selection for Genetic Programming.", "CoRR", "2019", "Informal", 1, "Vinícius Veloso de Melo", "10.48550/ARXIV.1904.08658"),
    _row(CORR, "Batch Tournament Selection for Genetic Programming.", "CoRR", "2019", "Informal", 3, "Wolfgang Banzhaf", "10.48550/ARXIV.1904.08658"),
    _row(GECCO, TITLE_GECCO, "GECCO", "2019", "Inproceedings", 3, "Wolfgang Banzhaf", "10.1145/3321707.3321793", "994-1002"),
    _row(GECCO, TITLE_GECCO, "GECCO", "2019", "Inproceedings", 1, "Vinícius Veloso de Melo", "10.1145/3321707.3321793", "994-1002"),
    _row(GECCO, TITLE_GECCO, "GECCO", "2019", "Inproceedings", 2, "Danilo Vasconcellos Vargas 0001", "10.1145/3321707.3321793", "994-1002"),
]}}
CHALLENGE = (b"<!doctype html><html lang=\"en\"><head><title>Making sure you&#39;re "
             b"not a bot!</title></head></html>")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        sources.set_cache_dir(self.tmp)
        sources.reset_breaker()
        sources.reset_dblp()
        self.urls = []
        self._orig = sources._raw_get
        self._sleep = sources.time.sleep
        sources.time.sleep = lambda s: None

    def tearDown(self):
        sources._raw_get = self._orig
        sources.time.sleep = self._sleep

    def serve(self, payload):
        def fake(url, extra_headers=None):
            self.urls.append((url, extra_headers))
            return payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        sources._raw_get = fake


class TestDblpSparql(Base):
    def test_never_calls_the_disallowed_host(self):
        self.serve(BATCH)
        sources.search_dblp("Batch Tournament Selection for Genetic Programming")
        hosts = {urllib.parse.urlparse(u).netloc for u, _ in self.urls}
        self.assertEqual(hosts, {"sparql.dblp.org"})
        self.assertEqual(self.urls[0][1].get("Accept"), "application/sparql-results+json")

    def test_sparql_gets_a_long_enough_timeout(self):
        # a scan takes 6-12 s server-side; the default 15 s timed out three times in a row
        self.assertGreaterEqual(sources._HOST_TIMEOUT["sparql.dblp.org"], 30)

    def test_keyword_search_filters_the_remaining_words_locally(self):
        self.serve(BATCH)
        recs = sources.dblp_keyword_search("batch tournament lexicase", 10)
        self.assertEqual([r.venue for r in recs], ["GECCO"])   # only GECCO's title has "lexicase"

    def test_crawl_delay_is_ten_seconds(self):
        self.assertGreaterEqual(sources._HOST_DELAY["sparql.dblp.org"], 10.0)
        self.assertNotIn("dblp.org", sources._HOST_DELAY)

    def test_rows_become_records_with_ordered_authors(self):
        self.serve(BATCH)
        recs = sources.dblp_records("Batch tournament selection for genetic programming")
        by_venue = {r.venue: r for r in recs}
        g = by_venue["GECCO"]
        self.assertEqual(g.authors, ["Vinícius Veloso de Melo", "Danilo Vasconcellos Vargas", "Wolfgang Banzhaf"])
        self.assertEqual((g.year, g.pages, g.doi, g.source, g.strong), (2019, "994-1002", "10.1145/3321707.3321793", "dblp", False))
        self.assertFalse(g.title.endswith("."))
        self.assertTrue(sources.is_preprint(by_venue["CoRR"]))

    def test_search_prefers_the_published_version_of_the_same_title(self):
        self.serve(BATCH)
        r = sources.search_dblp("Batch Tournament Selection for Genetic Programming: "
                                "the quality of lexicase, the speed of tournament")
        self.assertEqual(r.venue, "GECCO")

    def test_preprint_title_finds_the_published_version(self):
        # the arXiv title is a prefix of the published one; the published record must win
        self.serve(BATCH)
        r = sources.search_dblp("Batch Tournament Selection for Genetic Programming")
        self.assertEqual(r.venue, "GECCO")

    def test_unrelated_title_returns_none(self):
        self.serve({"head": {"vars": []}, "results": {"bindings": []}})
        self.assertIsNone(sources.search_dblp("A title nobody wrote"))

    def test_prefetch_batches_titles_into_one_request(self):
        self.serve(BATCH)
        titles = ["Batch Tournament Selection for Genetic Programming",
                  "CMA-ES with Adaptive Reevaluation for Multiplicative Noise",
                  "Solving the {Exponential} Growth of Symbolic Regression Trees"]
        sources.prefetch_dblp(titles)
        self.assertEqual(len(self.urls), 1)
        for t in titles:
            sources.search_dblp(t)
        self.assertEqual(len(self.urls), 1, "prefetched titles must not be queried again")

    def test_prefetch_chunks_long_lists(self):
        self.serve({"head": {"vars": []}, "results": {"bindings": []}})
        sources.prefetch_dblp([f"Some distinct title number {i} about evolution" for i in range(45)])
        self.assertEqual(len(self.urls), 3)

    def test_regex_metacharacters_and_latex_are_neutralised(self):
        self.serve({"head": {"vars": []}, "results": {"bindings": []}})
        sources.search_dblp(r"{CMA-ES} (and) $\mu$+[lambda]* \emph{Strategies}?")
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.urls[0][0]).query)["query"][0]
        self.assertIn("REGEX", q)
        for bad in ("(and)", "[lambda]", "\\emph", "$"):
            self.assertNotIn(bad, q)

    def test_keyword_search_returns_records(self):
        self.serve(BATCH)
        recs = sources.dblp_keyword_search("batch tournament selection", 10)
        self.assertEqual({r.venue for r in recs}, {"GECCO", "CoRR"})
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.urls[0][0]).query)["query"][0]
        self.assertIn("LIMIT", q)


class TestNonJsonIsAFailureNotACacheEntry(Base):
    def test_challenge_page_is_not_cached_and_counts_as_failure(self):
        self.serve(CHALLENGE)
        self.assertIsNone(sources.get_json("https://sparql.dblp.org/sparql?query=x"))
        self.assertEqual(os.listdir(self.tmp), [], "a non-JSON body must not stay in the cache")
        self.assertIn("sparql.dblp.org", sources.SOURCE_FAILURES)

    def test_poisoned_cache_entry_is_discarded_and_refetched(self):
        url = "https://api.crossref.org/works/10.1/x"
        with open(sources._cache_path(url), "wb") as fh:
            fh.write(CHALLENGE)
        self.serve({"message": {"title": ["T"]}})
        self.assertEqual(sources.get_json(url), {"message": {"title": ["T"]}})
        self.assertEqual(len(self.urls), 1)


if __name__ == "__main__":
    unittest.main()
