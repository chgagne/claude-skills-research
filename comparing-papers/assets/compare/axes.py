"""Extract per-axis evidence, with the sentence and section it came from.

Every axis here is something a reviewer attacks. `training_scale` exists because
"the baseline was retrained at a fraction of its published scale" is the single
most common way a headline result turns out to be an artifact, and checking it
by hand means reading two appendices and doing a multiplication.

Two rules the whole module obeys:

* **Never invent.** An axis with no matching sentence is reported `found=False`
  with empty value and quote, not guessed from context.
* **Never assert without provenance.** A number with no quote and no section is
  unusable in a review, because the first question is always "where is that from".
"""
import re
from dataclasses import dataclass

AXES = ("problem", "data", "training_scale", "checkpoint", "seeds",
        "metrics", "results", "compute")


@dataclass
class Evidence:
    axis: str
    value: str = ""
    quote: str = ""
    section: str = ""
    found: bool = False


_MAGNITUDE = {"k": 1_000, "thousand": 1_000, "m": 1_000_000, "million": 1_000_000,
              "b": 1_000_000_000, "billion": 1_000_000_000}

_NUM = r"\d[\d,.]*"


def parse_count(text):
    """'10^5' -> 100000, '1,000' -> 1000, '60 million' -> 60000000."""
    if not text:
        return None
    s = text.strip().lower().replace("{,}", ",")

    m = re.fullmatch(r"(\d+)\s*\^\s*\{?(\d+)\}?", s)
    if m:
        return int(m.group(1)) ** int(m.group(2))

    m = re.fullmatch(rf"({_NUM})\s*({'|'.join(_MAGNITUDE)})\b\.?", s)
    if m:
        try:
            return int(float(m.group(1).replace(",", "")) * _MAGNITUDE[m.group(2)])
        except ValueError:
            return None

    try:
        return int(float(s.replace(",", "")))
    except ValueError:
        return None


def _fmt(n):
    if n is None:
        return ""
    for suffix, size in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if n >= size:
            v = n / size
            return f"{v:.6g}{suffix}"
    return str(n)


def _sentences(body):
    out = []
    for s in re.split(r"(?<=[.!?])\s+", body or ""):
        s = _clean_sentence(s)
        if s and not _LEADING_JUNK.match(s):
            out.append(s)
    return out


# A sentence starting with \ref or \cref is a fragment: splitting on "Fig." cut
# a real sentence in half. \item is a list bullet, not the start of prose.
_LEADING_JUNK = re.compile(r"^\\(?:ref|cref|autoref|eqref|figref|tabref)\b")
_LEADING_TRIM = re.compile(
    r"^\\(?:item|noindent|bigskip|medskip|smallskip|par|centering|small|"
    r"footnotesize|normalsize)\b\s*"
    r"|^\\(?:vspace|hspace|vskip|hskip)\*?\s*\{[^}]*\}\s*")


def _clean_sentence(sent):
    """Strip layout commands that lead a sentence without being part of it."""
    s = (sent or "").strip()
    prev = None
    while prev != s:                 # \vspace{..}\noindent We ... needs two passes
        prev = s
        s = _LEADING_TRIM.sub("", s).strip()
    return s


def _is_markup(sent):
    """Float, algorithm and table blocks are markup, not prose about the work."""
    if not sent:
        return True
    symbols = sum(sent.count(c) for c in "\\{}$&")
    return symbols > max(4, len(sent) / 12)


# (axis, [regexes]) — first sentence matching any regex wins.
_PATTERNS = {
    "problem": [r"\bwe (?:present|propose|introduce)\b", r"\bthis paper\b"],
    "data": [r"\b(?:evaluate|train|test)\w*\s+on\s+[^.]{0,40}\b(?:dataset|benchmark|corpus)",
             r"\bbenchmark[s]?\b", r"\bdataset[s]?\b", r"\bcorpus\b"],
    "checkpoint": [r"\brelease[sd]?\b.{0,60}\bcheckpoint\b",
                   r"\bcheckpoint\b.{0,60}\b(?:public|available|release)",
                   r"\bpre-?trained (?:model|weights)\b.{0,40}\bavailable\b"],
    "seeds": [r"\b(?:training|random)\s+seed[s]?\s*\d", r"\bseed[s]?\s*\d",
              r"\b(?:three|five|ten|\d+)\s+seeds\b",
              r"\b(?:training|random) seed[s]?\b"],
    "metrics": [r"\b(?:we (?:report|measure)|evaluated? (?:with|using)|metric[s]?)\b"],
    "results": [r"\b(?:accuracy|percentile rank|F1|BLEU|R\^?2|score)\b.{0,40}\d"],
    "compute": [r"\bGPU[s]?\b", r"\bGPU-hours\b", r"\bA100\b|\bH100\b|\bV100\b"],
}

# training_scale is computed, not merely matched.
_STATED = re.compile(
    rf"(?:pre-?train(?:ed|ing)?|train(?:ed|ing)?)\b[^.]*?\b(?:on|of)\s+"
    rf"(?:approximately|about|~)?\s*({_NUM}\s*(?:{'|'.join(_MAGNITUDE)})\b)"
    rf"[^.]*?\b(?:examples|samples|pairs?|instances)", re.I)
_UPDATES = re.compile(rf"total of\s+({_NUM}(?:\s*\^\s*\{{?\d+\}}?)?)\s+(?:updates|steps)",
                      re.I)
_BATCH = re.compile(rf"(?:global\s+)?batch(?:\s+size)?\s+of\s+({_NUM})", re.I)


def _training_scale(doc):
    """Prefer a stated total; otherwise multiply updates by batch size."""
    for heading, body in doc.sections:
        for sent in _sentences(body):
            m = _STATED.search(sent)
            if m:
                n = parse_count(m.group(1))
                if n:
                    return Evidence("training_scale", f"{_fmt(n)} examples (stated)",
                                    sent, heading, True)

    updates = batch = None
    up_sent = up_head = ""
    for heading, body in doc.sections:
        for sent in _sentences(body):
            if updates is None:
                m = _UPDATES.search(sent)
                if m:
                    updates = parse_count(m.group(1))
                    up_sent, up_head = sent, heading
            if batch is None:
                m = _BATCH.search(sent)
                if m:
                    batch = parse_count(m.group(1))
                    if not up_sent:
                        up_sent, up_head = sent, heading
    if updates and batch:
        total = updates * batch
        return Evidence("training_scale",
                        f"{_fmt(total)} examples ({_fmt(updates)} updates x {batch} batch)",
                        up_sent, up_head, True)
    return Evidence("training_scale")


def extract(doc):
    """{axis: Evidence} for every axis in AXES, found or not."""
    out = {"training_scale": _training_scale(doc)}

    for axis, patterns in _PATTERNS.items():
        ev = Evidence(axis)
        # Patterns are ordered most-specific first, and each is tried across the
        # whole document before the next. Scanning section by section instead
        # lets an early vague mention beat a later precise one -- document order
        # is not relevance order.
        for pattern in patterns:
            for heading, body in doc.sections:
                for sent in _sentences(body):
                    if _is_markup(sent):
                        continue
                    if re.search(pattern, sent, re.I):
                        ev = Evidence(axis, value=sent[:160], quote=sent,
                                      section=heading, found=True)
                        break
                if ev.found:
                    break
            if ev.found:
                break
        out[axis] = ev

    return out
