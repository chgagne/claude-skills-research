"""Pair an assertion in the abstract with the sentence in the results that bears
on it.

Pairing is where this goes wrong, so it is deliberately conservative: two
sentences pair only when they share `min_shared` content tokens. An abstract
claim with no partner is reported with an empty results cell rather than matched
to the nearest thing available -- "no matching results sentence" is honest and
occasionally the finding itself, whereas a wrong pairing manufactures a rung
difference against correct writing.

Abstract sentences that assert nothing on the scale are dropped, not carried
with rung 0: "we release the code" is not a claim whose strength can drift.
"""
import re
from dataclasses import dataclass, field

from .scale import Assertion, classify

_ABSTRACT = re.compile(r"\\begin\{abstract\}(.*?)\\end\{abstract\}",
                       re.DOTALL | re.IGNORECASE)

# IEEE/VGTC and several ACM classes take \abstract{...} instead of the
# environment. Supporting only the environment made one real paper report "no
# abstract environment found" and contribute nothing to the probe -- a silent
# zero, which is the worst way for a check to fail.
_ABSTRACT_CMD = re.compile(r"\\abstract\s*\{", re.IGNORECASE)

_RESULTS_HEADING = re.compile(
    r"\b(results?|evaluation|experiments?|findings|empirical)\b", re.IGNORECASE)

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "with",
    "that", "this", "these", "those", "is", "are", "was", "were", "be", "been",
    "it", "its", "we", "our", "us", "they", "their", "as", "at", "by", "from",
    "which", "than", "then", "when", "while", "also", "both", "each", "more",
    "most", "such", "can", "may", "might", "could", "does", "do", "not", "no",
}


@dataclass
class Pairing:
    abstract: str
    results: str = ""
    shared: int = 0
    abstract_rung: Assertion = field(default_factory=Assertion)
    results_rung: Assertion = field(default_factory=Assertion)
    delta: int = 0


def _balanced(text, open_at):
    """Text between a '{' at open_at and its matching '}'. Escaped braces skipped."""
    depth, out, i = 0, [], open_at
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            out.append(text[i:i + 2])
            i += 2
            continue
        if ch == "{":
            depth += 1
            if depth == 1:
                i += 1
                continue
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return "".join(out)
        out.append(ch)
        i += 1
    return "".join(out)


def abstract_text(full_tex):
    """The abstract body, from either \\begin{abstract} or \\abstract{...}."""
    text = full_tex or ""
    m = _ABSTRACT.search(text)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    m = _ABSTRACT_CMD.search(text)
    if m:
        body = _balanced(text, m.end() - 1)
        return re.sub(r"\s+", " ", body).strip()
    return ""


def results_bodies(sections):
    """[(heading, body)] for headings naming results, evaluation or experiments."""
    return [(h, b) for h, b in (sections or []) if _RESULTS_HEADING.search(h or "")]


def sentences(text):
    """Split on terminal punctuation followed by a capital. A decimal never splits."""
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z(])", text)
    return [p.strip() for p in parts if p.strip()]


def content_tokens(sentence):
    """Lowercase word-ish tokens of 3+ chars that are not stopwords, plus numbers."""
    raw = re.findall(r"[A-Za-z][A-Za-z-]{2,}|\d+(?:\.\d+)?", (sentence or "").lower())
    return {t for t in raw if t not in _STOPWORDS}


def pair(abstract_sents, results_sents, min_shared=3):
    """One Pairing per asserting abstract sentence, best-matching results sentence."""
    out = []
    for a in abstract_sents or []:
        a_rung = classify(a)
        if not a_rung.found:
            continue
        a_tok = content_tokens(a)
        best, best_shared = "", 0
        for r in results_sents or []:
            n = len(a_tok & content_tokens(r))
            if n > best_shared:
                best, best_shared = r, n
        if best_shared < min_shared:
            out.append(Pairing(abstract=a, abstract_rung=a_rung))
            continue
        r_rung = classify(best)
        out.append(Pairing(
            abstract=a, results=best, shared=best_shared,
            abstract_rung=a_rung, results_rung=r_rung,
            delta=max(0, a_rung.level - r_rung.level),
        ))
    return out
