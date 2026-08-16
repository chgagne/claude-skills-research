"""Proof body -> steps. Stdlib only. The crux of the whole ledger.

A proof is prose with mathematics embedded in it, and the unit a checker needs --
one inference -- does not correspond to any single LaTeX construct. Getting the
boundary wrong is not a cosmetic failure:

- **Over-fragment** and the report fills with `UNVERIFIED: "Recall the setting of
  Section 3"`. A reader who sees three of those stops reading the fourth, and the
  real finding two screens down is lost. This is why narration merges forward.
- **Under-fragment** and two inferences share one verdict, so a refutation cannot
  be pointed at the move that caused it.

The ordering of the rules below matters and is not arbitrary. Displays attach
*backwards* because "By Jensen's inequality," followed by a display is one
inference written across two lines, and treating the prose as its own step
produces a step with no mathematics and the display as a step with no
justification -- two unverifiable halves in place of one checkable whole.
"""
import re

from . import chains as _chains
from .tokenize import blank_comments, mask, math_spans

# Sentence-ending periods that are not sentence endings. Every entry here has
# appeared in a real proof; `Eq.`, `Fig.` and `i.e.` are near-universal.
_ABBR = re.compile(
    r"\b(?:i\.e|e\.g|w\.l\.o\.g|a\.s|i\.i\.d|s\.t|et\s+al|cf|resp|etc|vs|viz"
    r"|Eqs?|Figs?|Secs?|Apps?|Thms?|Lems?|Props?|Cors?|Defs?|Defns?|Chs?|Algs?"
    r"|Tabs?|Refs?|no|approx|Ex|Prob)\.", re.I)

HEDGE = re.compile(
    r"\b(clearly|obviously|evidently|trivially|straightforward(?:ly)?|"
    r"it is easy to see|it is well known|one can easily|readily (?:see|verify)|"
    r"of course)\b", re.I)

# A sentence opening with one of these is asserting a *move*, not describing the
# scene. `recall`, `note` and `consider` are deliberately absent: they set up.
_DISCOURSE = re.compile(
    r"^\s*(?:\\[a-zA-Z]+\s*(?:\{[^}]*\})?\s*)?"
    r"(hence|thus|therefore|so|consequently|it follows|we (?:obtain|get|have|"
    r"conclude|deduce|find)|combining|since|by|applying|apply|substituting|"
    r"substitute|plugging|using|rearranging|taking|summing|integrating|"
    r"multiplying|dividing|expanding|from this|this gives|this yields|"
    r"which gives|which yields|adding|subtracting)\b", re.I)

_QED = re.compile(
    r"\\(?:qed|qedhere|square|blacksquare|Box)\b"
    r"|\b(?:this (?:completes|concludes|proves)|which (?:completes|concludes|"
    r"proves)|as (?:claimed|required|desired)|the (?:claim|result|lemma|theorem)"
    r" follows|completing the proof)\b", re.I)

_CASE = re.compile(
    r"(?:\\(?:textbf|textit|emph|paragraph|textsc)\s*\{\s*("
    r"(?:Case|Base case|Inductive step|Induction step)[^}]*)\}"
    r"|^\s*((?:Case\s+\d+|Base case|Inductive step)\s*[.:])"
    r"|^\s*(Suppose first|Assume first))", re.I | re.M)

_REF = re.compile(r"\\(?:eq|c|C|auto|name|page)?ref\s*\{([^}]*)\}")
_CITE = re.compile(r"\\cite[a-zA-Z]*\s*(?:\[[^\]]*\])*\s*\{([^}]*)\}")
_ASSUMPTION = re.compile(r"\b(?:by|under|from)\s+(?:the\s+)?assumptions?\b", re.I)
_DEFINITION = re.compile(r"\bby\s+(?:the\s+)?definition\b", re.I)

# Results invoked by name. The catalogue is short on purpose: each entry is a
# result whose *hypotheses* a later engine can look for, and an entry nobody
# checks the hypotheses of is decoration.
NAMED_RESULTS = [
    ("jensen", r"Jensen"),
    ("cauchy-schwarz", r"Cauchy[-\u2013\u2014\s]*Schwarz"),
    ("markov", r"Markov(?:'s)?\s+inequality"),
    ("chebyshev", r"Chebyshev"),
    ("holder", r"H[o\u00f6]lder"),
    ("minkowski", r"Minkowski"),
    ("triangle", r"triangle\s+inequality"),
    ("union-bound", r"union\s+bound|Boole(?:'s)?\s+inequality"),
    ("fatou", r"Fatou"),
    ("dominated-convergence", r"dominated\s+convergence"),
    ("monotone-convergence", r"monotone\s+convergence"),
    ("fubini", r"Fubini|Tonelli"),
    ("taylor", r"Taylor(?:'s)?\s+(?:theorem|expansion|series)"),
    ("mean-value", r"mean\s+value\s+theorem"),
    ("bayes", r"Bayes(?:'|'s)?\s+(?:rule|theorem)"),
    ("chain-rule", r"chain\s+rule"),
    ("tower", r"tower\s+(?:rule|property)|law\s+of\s+total\s+expectation"),
    ("total-probability", r"law\s+of\s+total\s+probability"),
    ("am-gm", r"AM[-\u2013]GM|arithmetic[-\s]geometric\s+mean"),
    ("hoeffding", r"Hoeffding"),
    ("bernstein", r"Bernstein(?:'s)?\s+inequality"),
    ("mcdiarmid", r"McDiarmid"),
    ("azuma", r"Azuma"),
    ("borel-cantelli", r"Borel[-\u2013]Cantelli"),
    ("gronwall", r"Gr[o\u00f6]nwall"),
    ("pinsker", r"Pinsker"),
    ("lipschitz", r"Lipschitz"),
    ("banach-fixed-point", r"Banach\s+fixed[-\s]point|contraction\s+mapping"),
]
_NAMED = [(k, re.compile(p, re.I)) for k, p in NAMED_RESULTS]

INFERENCE_KINDS = ("chain-row", "display", "inline-assert", "prose-move")
_MERGE_TARGETS = ("inline-assert", "prose-move")


class Step:
    __slots__ = ("id", "proof_id", "ordinal", "kind", "chain", "container",
                 "case_path", "prose_tex", "math_tex", "claim_forms",
                 "justification", "derived_from", "symbols_used",
                 "assumptions_in_scope", "quantifiers_in_scope", "side_conditions",
                 "checkable", "opacity_reasons", "content_hash", "source")

    def __init__(self, **kw):
        for s in self.__slots__:
            setattr(self, s, kw.get(s))
        self.case_path = self.case_path or []
        self.claim_forms = self.claim_forms or []
        self.symbols_used = self.symbols_used or []
        self.assumptions_in_scope = self.assumptions_in_scope or []
        self.quantifiers_in_scope = self.quantifiers_in_scope or []
        self.side_conditions = self.side_conditions or []
        self.opacity_reasons = self.opacity_reasons or []
        self.prose_tex = self.prose_tex or ""
        self.math_tex = self.math_tex or ""

    def as_dict(self):
        return {s: getattr(self, s) for s in self.__slots__}

    def __repr__(self):
        return "Step(%s, %s, %r)" % (self.ordinal, self.kind,
                                     (self.prose_tex or self.math_tex)[:36])


def _blind(text):
    """Math bodies blanked and abbreviation periods neutralised, offsets intact."""
    out = mask(text, math_spans(text))
    chars = list(out)
    for m in _ABBR.finditer(out):
        for k in range(m.start(), m.end()):
            if chars[k] == ".":
                chars[k] = "\x00"
    return "".join(chars)


def sentence_spans(text):
    """(start, end) per sentence, splitting only where prose really ends."""
    blind = _blind(text)
    n = len(blind)
    spans, start = [], 0
    for m in re.finditer(r"[.!?]", blind):
        k = m.end()
        while k < n and blind[k] in " \t\r\n":
            k += 1
        if k >= n or blind[k] in "\\$" or blind[k].isupper():
            if text[start:k].strip():
                spans.append((start, k))
            start = k
    if text[start:].strip():
        spans.append((start, len(text)))
    return spans


def sentences(text):
    return [text[a:b] for a, b in sentence_spans(text)]


def _attaches_back(sentence):
    """Does a display belong to the sentence before it?

    Yes when the sentence is unfinished -- it ends in a colon, a comma, or no
    terminal punctuation at all. "By Jensen's inequality," is one inference with
    the display that follows it; "We recall the setting of Section 3." is not.
    """
    s = (sentence or "").strip()
    if not s:
        return False
    if s[-1] in ":,;":
        return True
    return s[-1] not in ".!?"


def _named_result(text):
    for key, pat in _NAMED:
        if pat.search(text):
            return key
    return None


def justification_of(prose, math_tex=""):
    """What the step says licenses it. `kind: "none"` is a finding, not a blank."""
    text = prose or ""
    refs = [r.strip() for g in _REF.findall(text) for r in g.split(",") if r.strip()]
    cites = [c.strip() for g in _CITE.findall(text) for c in g.split(",") if c.strip()]
    hedges = sorted({m.group(0).lower() for m in HEDGE.finditer(text)})
    name = _named_result(text)
    if name:
        kind = "named-result"
    elif refs:
        kind = "internal-ref"
    elif cites:
        kind = "citation"
    elif _ASSUMPTION.search(text):
        kind = "assumption"
    elif _DEFINITION.search(text):
        kind = "definition"
    else:
        kind = "none"
    return {"tex": text.strip(), "kind": kind, "name": name,
            "refs": refs, "cites": cites, "hedges": hedges}


def _case_label(text):
    m = _CASE.search(text)
    if not m:
        return None
    return (m.group(1) or m.group(2) or m.group(3) or "").strip()


def _classify(sentence):
    blind = _blind(sentence)
    if _QED.search(blind) or _QED.search(sentence):
        return "qed"
    if _case_label(sentence):
        return "case-open"
    if _DISCOURSE.search(blind):
        return "prose-move"
    for sp in math_spans(sentence):
        if _chains.top_relations(sp.body):
            return "inline-assert"
    return "narration"


def _display_steps(text, span, prose, case_path, source):
    """One display -> chain-row steps (multi-row) or a single display step."""
    inner = text[span.start:span.end] if span.name not in ("display",) else span.body
    eq = _chains.parse_display(inner)
    claims = _chains.rows_to_claims(eq)
    multi = len(eq.rows) > 1
    out = []
    if not claims:
        return [Step(kind="display", prose_tex=prose, math_tex=span.body.strip(),
                     case_path=list(case_path), justification=justification_of(prose),
                     derived_from="row", checkable="candidate", source=source)]
    for i, c in enumerate(claims):
        row = eq.rows[c["row"] - 1]
        out.append(Step(
            kind="chain-row" if multi else "display",
            chain={"row": c["row"], "of_rows": c["of_rows"],
                   "anchor_tex": c["anchor_tex"], "carried": c["carried"],
                   "label": c["label"], "numbered": c["numbered"]},
            prose_tex=(prose if i == 0 else ""),
            math_tex=row.tex.strip(),
            claim_forms=c["claim_forms"],
            justification=justification_of(prose if i == 0 else "", row.tex),
            derived_from=c["derived_from"], case_path=list(case_path),
            checkable="candidate", source=source))
    for itx in eq.intertext:
        idx = min(itx["after_row"], len(out) - 1)
        if 0 <= idx < len(out):
            out[idx].prose_tex = (out[idx].prose_tex + " " + itx["tex"]).strip()
    return out


def segment_proof(proof_tex, macros=None, proof_id="proof", base_offset=0):
    """A proof body as an ordered list of steps.

    `base_offset` is added to every recorded span so a step can be resolved back
    to a byte offset in the original file, not merely in the proof body.
    """
    text = blank_comments(proof_tex or "")
    displays = [s for s in math_spans(text) if s.name != "inline"]

    raw, cursor, pending_prose = [], 0, None
    for sp in displays + [None]:
        end = sp.start if sp else len(text)
        region = text[cursor:end]
        sents = [(cursor + a, cursor + b) for a, b in sentence_spans(region)]
        prose_for_display = ""
        if sp is not None and sents and _attaches_back(text[sents[-1][0]:sents[-1][1]]):
            a, b = sents.pop()
            prose_for_display = text[a:b].strip()
            pending_prose = (a, b)
        for a, b in sents:
            raw.append(("sentence", text[a:b], a, b))
        if sp is not None:
            start = pending_prose[0] if pending_prose else sp.start
            raw.append(("display", (sp, prose_for_display), start, sp.end))
            pending_prose = None
            cursor = sp.end
    del cursor

    steps, case_path = [], []
    for kind, payload, a, b in raw:
        source = {"start": base_offset + a, "end": base_offset + b}
        if kind == "display":
            sp, prose = payload
            lbl = _case_label(prose)
            if lbl:
                case_path = [lbl]
            steps.extend(_display_steps(text, sp, prose, case_path, source))
            continue
        sentence = payload
        cls = _classify(sentence)
        if cls == "case-open":
            case_path = [_case_label(sentence)]
        math = " ".join(s.body.strip() for s in math_spans(sentence))
        steps.append(Step(
            kind=cls, prose_tex=sentence.strip(), math_tex=math,
            claim_forms=_inline_claims(sentence),
            justification=justification_of(sentence, math),
            derived_from="sentence", case_path=list(case_path),
            checkable=("candidate" if cls == "inline-assert" else
                       "structural" if cls in ("narration", "case-open", "qed")
                       else "opaque"),
            opacity_reasons=([] if cls != "prose-move" else
                             ["natural-language-only"] if not math else []),
            source=source))

    steps = _merge_narration(steps)
    steps = _attach_trailing_justification(steps)
    for i, s in enumerate(steps, start=1):
        s.ordinal = i
        s.proof_id = proof_id
        s.id = "%s/s%02d" % (proof_id, i)
    return steps


def _inline_claims(sentence):
    out = []
    for sp in math_spans(sentence):
        eq = _chains.parse_display(sp.body)
        for c in _chains.rows_to_claims(eq):
            out.extend(c["claim_forms"])
    return out


#: A clause that continues the sentence the display interrupted. "which follows
#: from Lemma 3" after a display licenses *that display*, and English puts it
#: after because the display is the object of the sentence.
_CONTINUATION = re.compile(
    r"^\s*(?:which|where|whence|by|since|because|using|owing\s+to|thanks\s+to)\b",
    re.I)


def _attach_trailing_justification(steps):
    r"""Give an inference the licence stated *after* it.

    A step's justification is read from the prose in front of it, which is the
    common shape but not the only one. `\[ ... \] which follows from Lemma 3.`
    puts the licence behind the display, and it was landing in a `narration` step
    of its own -- where nothing looks for it, and which the expander never sees
    because narration is not an inference.

    Measured on two papers by two independent expansions: on Bubeck the load-
    bearing projection lemma reached no step at all, and the subagent recovered
    it only by opening the source. The narration step is kept -- it is real text
    and deleting it would cost coverage -- but the inference in front of it now
    carries the reference.

    Only backwards, only over one step, and only when the trailing clause states
    something the preceding step's own prose did not: this must not overwrite a
    justification the author actually wrote in front.
    """
    for prev, s in zip(steps, steps[1:]):
        if s.kind != "narration" or prev.kind not in INFERENCE_KINDS:
            continue
        if not _CONTINUATION.match(s.prose_tex or ""):
            continue
        trailing = justification_of(s.prose_tex or "")
        if trailing.get("kind") in (None, "none"):
            continue
        own = prev.justification or {}
        if own.get("kind") not in (None, "none"):
            continue                      # the author licensed it in front
        merged = dict(own)
        merged["kind"] = trailing["kind"]
        merged["name"] = trailing.get("name")
        merged["refs"] = sorted(set(own.get("refs") or []) | set(trailing.get("refs") or []))
        merged["cites"] = sorted(set(own.get("cites") or []) | set(trailing.get("cites") or []))
        merged["tex"] = ("%s %s" % (own.get("tex") or "", s.prose_tex or "")).strip()
        merged["trailing"] = True
        prev.justification = merged
    return steps


def _merge_narration(steps):
    """Fold scene-setting into the inference it introduces.

    Only into an `inline-assert` or a `prose-move`: a display the author ended
    the previous sentence before is a step in its own right, and swallowing the
    narration into it would undo the attachment rule that put it there.
    """
    out = []
    for s in steps:
        if (out and out[-1].kind == "narration" and s.kind in _MERGE_TARGETS):
            prev = out.pop()
            s.prose_tex = (prev.prose_tex + " " + s.prose_tex).strip()
            s.justification = justification_of(s.prose_tex, s.math_tex)
            s.source = {"start": min(prev.source["start"], s.source["start"]),
                        "end": max(prev.source["end"], s.source["end"])}
            if not s.case_path:
                s.case_path = prev.case_path
        out.append(s)
    return out


def captured_fraction(proof_tex, steps):
    """Share of the proof's non-whitespace characters that some step covers.

    Below ~0.9 the segmenter is dropping content, and every verdict computed on
    the result describes a proof that is not the one in the paper.
    """
    text = proof_tex or ""
    total = sum(1 for c in text if not c.isspace())
    if not total:
        return 1.0
    covered = bytearray(len(text))
    for s in steps:
        a = max(0, s.source["start"])
        b = min(len(text), s.source["end"])
        for k in range(a, b):
            covered[k] = 1
    hit = sum(1 for k, c in enumerate(text) if covered[k] and not c.isspace())
    return hit / total
