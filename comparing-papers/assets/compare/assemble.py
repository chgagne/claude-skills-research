"""Put the draft and each prior paper side by side, axis by axis.

The hard rule here is about what the tool is allowed to say. It computes a note
only where a relation is arithmetic and unambiguous:

* `training_scale` -- a ratio between two counts
* `seeds` -- how many training runs a sentence states

Everywhere else the row holds two quotes and nothing more. "These protocols
differ" reads like a finding but is a judgement, and a tool that makes it will
eventually make it wrongly, in a document a reviewer signs their name to.
"""
import re
from dataclasses import dataclass, field

from .axes import AXES, Evidence, extract, parse_count

# Axes where a note may be computed. Everything else stays empty by design.
_COMPUTED = ("training_scale", "seeds")

_WORD_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
             "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


@dataclass
class Row:
    axis: str
    draft: Evidence
    others: dict = field(default_factory=dict)
    note: str = ""


def _leading_count(value):
    """First magnitude in a value string: '6.4M examples (...)' -> 6400000."""
    m = re.match(r"\s*([\d.,]+\s*(?:[KMB]\b|thousand|million|billion)?)", value or "",
                 re.I)
    return parse_count(m.group(1)) if m else None


def _short(value):
    m = re.match(r"\s*([\d.,]+\s*(?:[KMB]\b|thousand|million|billion)?)", value or "",
                 re.I)
    return m.group(1).strip() if m else (value or "")


def ratio_note(draft_ev, other_ev):
    """State the scale relation between two training budgets, or say nothing."""
    if not (draft_ev.found and other_ev.found):
        return ""
    a, b = _leading_count(draft_ev.value), _leading_count(other_ev.value)
    if not a or not b:
        return ""
    pct = round(100 * a / b)
    return (f"{_short(draft_ev.value)} vs {_short(other_ev.value)} — "
            f"about {pct}% of the other paper's scale")


def seed_note(seeds_ev):
    """How many training runs the sentence states, when it states one."""
    if not seeds_ev.found:
        return ""
    q = (seeds_ev.quote or "").lower()

    m = re.search(r"\b(\d+|" + "|".join(_WORD_NUM) + r")\s+seeds\b", q)
    if m:
        n = _WORD_NUM.get(m.group(1), None)
        n = n if n is not None else int(m.group(1))
        return f"{n} training seed(s) reported"

    if re.search(r"\b(?:training|random)\s+seed\s*\d+\b", q) or \
       re.search(r"\bseed\s*0\b", q) or "one training run" in q:
        return ("single training seed — confidence intervals cannot describe "
                "training variance")
    return ""


def build(draft_doc, others):
    """[Row] over every axis, for the draft against each named paper."""
    draft_ev = extract(draft_doc)
    other_ev = {name: extract(doc) for name, doc in others.items()}

    rows = []
    for axis in AXES:
        row = Row(axis=axis, draft=draft_ev[axis],
                  others={n: ev[axis] for n, ev in other_ev.items()})
        if axis in _COMPUTED:
            if axis == "training_scale":
                notes = [f"{n}: {ratio_note(row.draft, ev)}"
                         for n, ev in row.others.items()
                         if ratio_note(row.draft, ev)]
                row.note = "; ".join(notes)
            elif axis == "seeds":
                row.note = seed_note(row.draft)
        rows.append(row)
    return rows
