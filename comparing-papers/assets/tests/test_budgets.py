"""Offline tests for compare.budgets: budget statements converted to examples seen."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.expanduser("~/.claude/skills/_shared"))

from compare.budgets import find_budgets, ratios  # noqa: E402
from compare.fulltext import Document  # noqa: E402


def _doc(*sections):
    return Document(sections=list(sections))


def _values(doc, unit="examples"):
    return sorted(round(b.value) for b in find_budgets(doc) if b.unit == unit)


def test_steps_times_batch_in_one_sentence():
    d = _doc(("Setup", "We train for 20k steps with a global batch size of 64."))
    assert 1_280_000 in _values(d)


def test_epochs_times_dataset_across_sentences():
    d = _doc(("Training data", "The corpus consists of 1.3 million samples. "
                               "Each model is trained for 10 epochs."))
    assert 13_000_000 in _values(d)


def test_epochs_times_per_epoch_size():
    d = _doc(("Setup", "One epoch contains 20k samples. We train for 100 epochs with Adam."))
    assert 2_000_000 in _values(d)


def test_batches_of():
    d = _doc(("Baselines", "The adapter was trained for 20 batches of 32 images."))
    assert 640 in _values(d)


def test_stated_total_seen():
    d = _doc(("Method", "The head is trained offline on 3.6 million samples seen."))
    assert 3_600_000 in _values(d)


def test_hyperparameter_table_per_round():
    tab = ("\\begin{tabular}{ll}Prompts / responses per round & 32 / 1 \\\\"
           " Rollout rounds & 30 \\\\ \\end{tabular}")
    d = _doc(("Hyperparameters", tab))
    assert 960 in _values(d)


def test_multicolumn_cell_is_unwrapped():
    tab = "\\begin{tabular}{ll}Training steps & \\multicolumn{2}{c}{375} \\\\ \\end{tabular}"
    assert 375 in _values(_doc(("H", tab)), unit="steps")


def test_sampling_steps_are_not_training():
    d = _doc(("Inference", "We generate with 4 denoising steps per block at inference."))
    assert _values(d, unit="steps") == []


def test_caption_budget_is_read():
    body = ("\\begin{table}\\caption{All baselines are retrained for 500 steps with batch size 16.}"
            "\\begin{tabular}{ll}a & 1 \\\\ \\end{tabular}\\end{table}")
    assert 8_000 in _values(_doc(("Results", body)))


def test_ratios_same_unit_only():
    d = find_budgets(_doc(("S", "We train for 1k steps with a batch size of 10.")))
    o = find_budgets(_doc(("S", "We train for 10k steps with a batch size of 10.")))
    rows = ratios(d, o)
    assert rows and abs(rows[0][0] - 0.1) < 1e-9


def test_nothing_invented():
    assert find_budgets(_doc(("Intro", "Large models are expensive to train."))) == []
