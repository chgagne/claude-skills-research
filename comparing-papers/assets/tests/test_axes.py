import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))
from compare.axes import AXES, extract, parse_count
from compare.fulltext import Document

# Sentences taken verbatim from the two real papers.
SNIPPP = Document(sections=[
    ("Optimization", "Each model is trained for 100 epochs with 1,000 optimizer "
                     "updates per epoch, for a total of 10^5 updates. "
                     "We train on four NVIDIA H100-80GB GPUs with a global batch "
                     "size of 64."),
    ("Hyperparameter selection", "All variants are trained from scratch with "
                                 "training seed 0."),
    ("Results", "SNIP++ reaches percentile rank .73 for f->y, against .48 for SNIP."),
], source="arxiv-latex")

SNIP = Document(sections=[
    ("Pre-training", "In total, SNIP is pre-trained on approximately 60 million "
                     "synthetic paired examples."),
    ("Training Details", "Our model undergoes training for a total of ~220 epochs, "
                         "with each epoch comprising 1,000 steps. For training, we "
                         "utilize 4 GPUs, each equipped with 48GB of memory."),
    ("Release", "We release the SNIP-10dmax checkpoint publicly at github.com/x."),
], source="arxiv-latex")


class TestParseCount(unittest.TestCase):
    def test_scientific_notation(self):
        self.assertEqual(parse_count("10^5"), 100000)

    def test_thousands_separator(self):
        self.assertEqual(parse_count("1,000"), 1000)

    def test_magnitude_suffixes(self):
        self.assertEqual(parse_count("60 million"), 60_000_000)
        self.assertEqual(parse_count("6.4M"), 6_400_000)
        self.assertEqual(parse_count("10K"), 10_000)

    def test_unparseable_is_none(self):
        self.assertIsNone(parse_count("several"))


class TestAxes(unittest.TestCase):
    def test_training_scale_computed_from_updates_and_batch(self):
        ev = extract(SNIPPP)["training_scale"]
        self.assertTrue(ev.found)
        self.assertIn("6.4M", ev.value)
        self.assertIn("Optimization", ev.section)
        self.assertIn("10^5", ev.quote)

    def test_training_scale_reads_a_stated_example_count(self):
        ev = extract(SNIP)["training_scale"]
        self.assertTrue(ev.found)
        self.assertIn("60M", ev.value)
        self.assertIn("Pre-training", ev.section)

    def test_stated_count_wins_over_derived_arithmetic(self):
        """A paper that says its total outright is more reliable than a product."""
        doc = Document(sections=[
            ("A", "a total of 10^5 updates with a global batch size of 64."),
            ("B", "In total we pre-train on approximately 60 million examples."),
        ], source="arxiv-latex")
        self.assertIn("60M", extract(doc)["training_scale"].value)

    def test_seed_count_is_found_with_its_quote(self):
        ev = extract(SNIPPP)["seeds"]
        self.assertTrue(ev.found)
        self.assertIn("seed 0", ev.quote)

    def test_released_checkpoint_is_detected(self):
        self.assertTrue(extract(SNIP)["checkpoint"].found)
        self.assertFalse(extract(SNIPPP)["checkpoint"].found)

    def test_compute_is_found(self):
        ev = extract(SNIPPP)["compute"]
        self.assertTrue(ev.found)
        self.assertIn("H100", ev.quote)

    def test_missing_axis_is_reported_not_invented(self):
        ev = extract(SNIP)["seeds"]
        self.assertFalse(ev.found)
        self.assertEqual(ev.value, "")
        self.assertEqual(ev.quote, "")

    def test_every_axis_is_always_present(self):
        self.assertEqual(sorted(extract(SNIPPP)), sorted(AXES))

    def test_found_evidence_always_carries_provenance(self):
        for ev in list(extract(SNIPPP).values()) + list(extract(SNIP).values()):
            if ev.found:
                self.assertTrue(ev.section, f"{ev.axis} has no section")
                self.assertTrue(ev.quote, f"{ev.axis} has no quote")

    def test_most_specific_pattern_wins_over_document_order(self):
        """Document order is not relevance order: an early vague mention of
        "seed" must not beat a later "trained with training seed 0"."""
        doc = Document(sections=[
            ("Data", "Unless stated otherwise, expressions are sampled from the "
                     "same random seed pool."),
            ("Hyperparameters", "All variants are trained from scratch with "
                                "training seed 0."),
        ], source="arxiv-latex")
        ev = extract(doc)["seeds"]
        self.assertIn("seed 0", ev.quote)
        self.assertEqual(ev.section, "Hyperparameters")

    def test_markup_heavy_sentences_are_skipped(self):
        """LaTeX float and algorithm blocks are not prose about the dataset."""
        doc = Document(sections=[
            ("Figures", r"{ \centering \begin{minipage}{0.9\linewidth} "
                        r"\begin{algorithm}[H] \fontsize{9}{9} dataset."),
            ("Setup", "We evaluate on the SRBench benchmark dataset."),
        ], source="arxiv-latex")
        ev = extract(doc)["data"]
        self.assertIn("SRBench", ev.quote)

    def test_fragments_starting_with_a_ref_are_rejected(self):
        """Splitting on "Fig." cuts a sentence in half; the tail is not prose."""
        doc = Document(sections=[
            ("Feynman", r"\ref{fig:grid} (middle), we present a comparative analysis."),
            ("Intro", "We present a compositional alignment method."),
        ], source="arxiv-latex")
        ev = extract(doc)["problem"]
        self.assertIn("compositional alignment", ev.quote)

    def test_item_bullets_are_trimmed_not_quoted_raw(self):
        doc = Document(sections=[
            ("Setup", r"\item We evaluate on the SRBench benchmark dataset.")],
            source="arxiv-latex")
        ev = extract(doc)["data"]
        self.assertTrue(ev.found)
        self.assertFalse(ev.quote.startswith("\\item"), ev.quote)

    def test_leading_layout_commands_are_stripped(self):
        doc = Document(sections=[
            ("Intro", r"\vspace{-0.3em} \noindent In this work, we present a method.")],
            source="arxiv-latex")
        ev = extract(doc)["problem"]
        self.assertTrue(ev.found)
        self.assertTrue(ev.quote.startswith("In this work"), ev.quote)

    def test_empty_document_yields_all_not_found(self):
        got = extract(Document(sections=[], source="none", degraded=True))
        self.assertTrue(all(not ev.found for ev in got.values()))


if __name__ == "__main__":
    unittest.main()
