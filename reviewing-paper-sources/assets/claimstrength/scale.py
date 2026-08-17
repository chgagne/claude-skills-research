"""Where a sentence sits on the strength scale -- and nothing more.

The scale orders assertions by how much evidence each requires. A paper whose
abstract asserts a higher rung than its own results section is the shape this
looks for, but the judgement stays with the reader: this module reports a rung
and the phrase that produced it, never a verdict. "This overclaims" is a
judgement, and a tool that makes it will eventually make it wrongly in a
document someone signs.

The lexicon is the risk, not the scale. `verifying-proofs` accumulated 21
false-alarm classes against a far more constrained problem, and a verb list will
do the same faster. `reference/claim-strength.md` carries the false alarms found
so far; add to it rather than silently widening a pattern here.
"""
import re
from dataclasses import dataclass

RUNGS = (
    (1, "consistent-with", (r"consistent with", r"compatible with", r"in line with")),
    (2, "associated-with", (r"associated with", r"correlates? with", r"correlated with")),
    (3, "predicts", (r"predicts?", r"predictive of")),
    (4, "contributes-to", (r"contributes? to", r"plays? a role in")),
    (5, "improves", (r"improves?", r"outperforms?")),
    (6, "causes", (r"causes?", r"leads? to", r"results? in", r"drives?")),
)

HEDGES = (r"may", r"might", r"could", r"appears? to", r"suggests?",
          r"we hypothesi[sz]e", r"seems? to")


@dataclass
class Assertion:
    level: int = 0
    label: str = "none"
    phrase: str = ""
    hedged: bool = False
    found: bool = False


def _search(sentence, patterns):
    for pat in patterns:
        m = re.search(rf"\b{pat}\b", sentence, re.IGNORECASE)
        if m:
            return m.group(0)
    return None


def classify(sentence):
    """The highest rung whose phrase appears, demoted one rung if hedged."""
    sentence = sentence or ""
    best = Assertion()
    for level, label, patterns in RUNGS:
        phrase = _search(sentence, patterns)
        if phrase and level > best.level:
            best = Assertion(level=level, label=label, phrase=phrase, found=True)
    if not best.found:
        return best
    if _search(sentence, HEDGES):
        best.hedged = True
        best.level = max(1, best.level - 1)
    return best
