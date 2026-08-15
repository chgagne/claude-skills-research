"""Symbol inventory with domain provenance. Stdlib only.

This module decides whether a refutation may exist at all.

A random-point checker that does not know $x > 0$ will happily evaluate a step at
$x = -11/5$, find the two sides differ, and report a counterexample against
correct mathematics. No amount of sampling cleverness fixes that; the fix is to
know that the domain was never established and refuse to refute. Hence
`can_refute`, which the severity ladder is built on.

Three provenances, and the distinction is load-bearing:

- **declared** -- the paper says so, near first use, and the quote is kept so a
  reader can check the tool's reading against the sentence.
- **inferred** -- the tool worked it out (`\\sum_{i=1}^n` makes $i$ an integer).
  Honest, usable, and never promoted to `declared`.
- **unknown** -- the default. Reported as a gap, never guessed, never refuting.

Declared patterns fire *near first use only*. A paper that says `$\\beta > 0$` on
page 9 has not told the reader anything about the $\\beta$ on page 2, and a tool
that pretends otherwise is inventing a hypothesis.
"""
import re

from .tokenize import math_spans

#: How far after first use a declaration may sit and still be about it.
DECLARATION_WINDOW = 240

_GREEK = (r"alpha|beta|gamma|delta|epsilon|varepsilon|zeta|eta|theta|vartheta|"
          r"iota|kappa|lambda|mu|nu|xi|pi|varpi|rho|varrho|sigma|varsigma|tau|"
          r"upsilon|phi|varphi|chi|psi|omega|Gamma|Delta|Theta|Lambda|Xi|Pi|"
          r"Sigma|Upsilon|Phi|Psi|Omega|ell|hbar|imath|jmath")

# Control sequences that are operators, delimiters or decoration -- never the
# name of a quantity. Without this the inventory fills with \sum, \left and \!.
_NOT_SYMBOLS = re.compile(
    r"^\\(?:" + r"sum|prod|int|iint|oint|lim|limsup|liminf|inf|sup|max|min|"
    r"arg|argmin|argmax|log|ln|exp|sin|cos|tan|sinh|cosh|tanh|det|tr|rank|"
    r"dim|ker|deg|gcd|lcm|Pr|mathbb|mathcal|mathrm|mathbf|mathsf|mathfrak|"
    r"mathit|text|textbf|textit|operatorname|left|right|big|Big|bigg|Bigg|"
    r"bigl|bigr|Bigl|Bigr|frac|dfrac|tfrac|cdot|cdots|ldots|dots|vdots|ddots|"
    r"quad|qquad|,|;|!|:|space|hspace|vspace|label|nonumber|notag|begin|end|"
    r"partial|nabla|infty|to|mapsto|in|notin|subset|subseteq|forall|exists|"
    r"leq|geq|le|ge|ne|neq|approx|sim|simeq|equiv|propto|times|div|pm|mp|"
    r"circ|otimes|oplus|wedge|vee|cap|cup|setminus|emptyset|langle|rangle|"
    r"lVert|rVert|lvert|rvert|Vert|vert|norm|abs|hat|tilde|bar|vec|dot|ddot|"
    r"overline|underline|widehat|widetilde|mathop|colon|mid|land|lor|neg|"
    r"triangleq|doteq|coloneqq|prime|star|ast|dagger|top|bot|perp|angle|"
    r"binom|choose|sqrt|overset|underset|stackrel|substack|nolimits|limits|"
    # Notation supplied by common packages. These are never expanded, because
    # the macro table reads \newcommand from the source and not from a package,
    # so without this they enter the inventory as unknown-domain quantities and
    # block refutation on every step they touch. Measured on a draft using
    # `\usepackage{physics}`, where `\dd` alone blocked 108 of 470 steps.
    r"dd|dv|pdv|fdv|qty|pqty|bqty|vqty|absolutevalue|ev|expval|"
    r"Tr|tr|grad|divergence|curl|laplacian|order|eval|"
    r"differential|derivative|va|vb|vu|vv"
    r")$")

_TOKEN = re.compile(r"\\[A-Za-z]+|[A-Za-z]")

_INT_DIFFERENTIAL = re.compile(r"(?:\\[,;!]|\s)*d\s*(?=[A-Za-z\\])")

# --- declared-domain patterns -------------------------------------------------
# Each is high precision by construction: it names a set or an order relation.
_DECLARED = [
    ("unit-interval-half-open", r"\\in\s*\[\s*0\s*,\s*1\s*\)"),
    ("unit-interval-half-open", r"\\in\s*\(\s*0\s*,\s*1\s*\]"),
    ("unit-interval", r"\\in\s*\[\s*0\s*,\s*1\s*\]"),
    ("open-unit-interval", r"\\in\s*\(\s*0\s*,\s*1\s*\)"),
    ("natural", r"\\in\s*\\mathbb\s*\{?\s*N\s*\}?"),
    ("natural", r"\\in\s*\\mathbb\s*\{?\s*Z\s*\}?_?\{?\s*\+"),
    ("integer", r"\\in\s*\\mathbb\s*\{?\s*Z\s*\}?"),
    ("real-vector", r"\\in\s*\\mathbb\s*\{?\s*R\s*\}?\s*\^"),
    ("real", r"\\in\s*\\mathbb\s*\{?\s*R\s*\}?"),
    ("complex", r"\\in\s*\\mathbb\s*\{?\s*C\s*\}?"),
    ("positive-definite", r"\\succ\s*0"),
    ("positive-semidefinite", r"\\succeq\s*0"),
    ("positive", r">\s*0"),
    ("negative", r"<\s*0"),
    ("nonnegative", r"\\geq?\s*0|\\ge\s*0"),
    ("nonpositive", r"\\leq?\s*0|\\le\s*0"),
]
_DECLARED = [(k, re.compile(p)) for k, p in _DECLARED]

# Prose declarations. `%s` is the symbol, escaped, as it appears in the source.
_PROSE_DECLARED = [
    ("probability-distribution",
     r"%s\$?\s+(?:be|is|denotes?)\s+(?:a|the)\s+"
     r"(?:probability\s+(?:distribution|measure|density)|density|distribution)"),
    ("probability-distribution", r"%s\$?\s+(?:be|is)\s+a\s+probability"),
    ("convex", r"%s\$?\s+(?:be|is)\s+(?:a\s+)?convex"),
    ("positive", r"%s\$?\s+(?:be|is|denotes?)\s+(?:a\s+|the\s+)?"
                 r"(?:positive|strictly\s+positive)"),
    ("matrix", r"%s\$?\s+(?:be|is|denotes?)\s+(?:a|the)\s+"
               r"(?:\w+\s+){0,2}matrix"),
]

_ROLE_BY_DOMAIN = {
    "real-vector": "vector", "positive-definite": "matrix",
    "positive-semidefinite": "matrix", "invertible": "matrix", "matrix": "matrix",
    "probability-distribution": "function",
}

#: Provenances that may license a refutation. `unknown` is deliberately absent.
REFUTING_PROVENANCE = ("declared", "inferred", "user-supplied")


class Symbol:
    __slots__ = ("symbol", "normalized", "first_use", "defined_at", "role_hint",
                 "domain_hint", "domain_provenance", "domain_evidence",
                 "occurrences", "scopes")

    def __init__(self, **kw):
        for s in self.__slots__:
            setattr(self, s, kw.get(s))
        self.domain_evidence = self.domain_evidence or []
        self.scopes = self.scopes or []

    def as_dict(self):
        return {s: getattr(self, s) for s in self.__slots__}

    def __repr__(self):
        return "Symbol(%r, %s/%s)" % (self.symbol, self.domain_hint,
                                      self.domain_provenance)


def can_refute(sym):
    """May a failing check on this symbol be reported as a counterexample?

    Not when the domain is unknown. Sampling outside a domain the paper meant but
    never wrote produces a counterexample against correct mathematics, and one of
    those teaches a reader to disregard every finding that follows.
    """
    return sym.domain_provenance in REFUTING_PROVENANCE


def _is_symbol(tok):
    if tok.startswith("\\"):
        if _NOT_SYMBOLS.match(tok):
            return False
        return bool(re.match(r"^\\(?:%s)$" % _GREEK, tok)) or len(tok) <= 4
    return tok.isalpha()


def _differential_positions(body):
    """Offsets of the `d` in `dx`, `\\,dz` -- an integration mark, not a symbol."""
    out = set()
    for m in re.finditer(r"\\int|\\iint|\\oint", body):
        for dm in re.finditer(r"(?:\\[,;!]\s*|\s)d(?=[A-Za-z\\])", body[m.end():]):
            out.add(m.end() + dm.end() - 1)
    return out


def inventory(text, claims=None, steps=None, macros=None):
    """Every quantity named in mathematics, with a domain and its provenance."""
    text = text or ""
    if macros is not None:
        pass  # callers expand before slicing; kept for interface symmetry
    seen = {}
    for sp in math_spans(text):
        body = sp.body
        skip = _differential_positions(body)
        for m in _TOKEN.finditer(body):
            if m.start() in skip:
                continue
            tok = m.group(0)
            if not _is_symbol(tok):
                continue
            pos = sp.inner_start + m.start()
            s = seen.get(tok)
            if s is None:
                seen[tok] = Symbol(
                    symbol=tok, normalized=tok.lstrip("\\"),
                    first_use={"start": pos, "end": pos + len(tok)},
                    defined_at=None, role_hint="scalar", domain_hint=None,
                    domain_provenance="unknown", domain_evidence=[],
                    occurrences=1, scopes=[])
            else:
                s.occurrences += 1
    for sym in seen.values():
        _assign_domain(text, sym)
    return sorted(seen.values(), key=lambda s: s.first_use["start"])


def _window(text, sym):
    a = sym.first_use["start"]
    return text[a:a + DECLARATION_WINDOW], a


def _assign_domain(text, sym):
    win, base = _window(text, sym)
    esc = re.escape(sym.symbol)

    # Declared: a set membership or order relation attached to this symbol.
    for kind, pat in _DECLARED:
        m = re.search(esc + r"\s*(?:\$?\s*)?" + pat.pattern, win)
        if m:
            _set(sym, kind, "declared", text, base + m.start(), base + m.end())
            return

    for kind, tmpl in _PROSE_DECLARED:
        m = re.search(tmpl % esc, win, re.I)
        if m:
            _set(sym, kind, "declared", text, base + m.start(), base + m.end())
            return

    # Inferred: the surrounding notation forces the domain.
    m = re.search(r"\\(?:sum|prod|bigcup|bigcap)\s*_\s*\{?\s*" + esc
                  + r"\s*(?:=|\\in)", text)
    if m:
        _set(sym, "natural", "inferred", text, m.start(), m.end(),
             inference="summation-index")
        return
    m = re.search(esc + r"\s*\^\s*\{?\s*-\s*1", text)
    if m:
        _set(sym, "invertible", "inferred", text, m.start(), m.end(),
             inference="negative-exponent")
        return


def _set(sym, kind, provenance, text, a, b, inference=None):
    """Record a domain and, for inferences, *what construct* implied it.

    The construct matters: a domain inferred from `\\sum_{t=1}^{T}` is a fact the
    paper wrote down and may discharge an obligation about $t$. A domain inferred
    from `A^{-1}` merely restates the obligation, and letting it discharge itself
    would be circular. `sideconds` keys on this.
    """
    sym.domain_hint = kind
    sym.domain_provenance = provenance
    # An inference drawn *from* `A^{-1}` must not also decide that `A` is a
    # matrix: that would let the guess about the obligation answer the question
    # the obligation asks. Measured on arXiv:2003.04706, where `\rho^{-1}` on a
    # scalar step size was reported as "needs $\rho$ to be invertible".
    if inference != "negative-exponent":
        sym.role_hint = _ROLE_BY_DOMAIN.get(kind, sym.role_hint)
    sym.domain_evidence = [{"kind": provenance, "quote": text[a:b].strip(),
                            "inference": inference,
                            "source": {"start": a, "end": b}}]
    if provenance == "declared":
        sym.defined_at = {"start": a, "end": b}


def undefined_symbols(inv):
    """Symbols whose first use precedes anything that defines them.

    A `MINOR` in its own right, and the reason a later step is often opaque: a
    checker cannot pick a sample point for a quantity the paper never introduced.
    """
    out = []
    for s in inv:
        if s.defined_at is None:
            out.append(s)
        elif s.defined_at["start"] > s.first_use["end"]:
            out.append(s)
    return out


def apply_user_domains(inv, table):
    """Overlay a user-supplied symbol table, marked `user-supplied`.

    One minute of a reader's time is worth more than any amount of inference, and
    it is the same "ask, don't guess" move the orchestrator makes in phase 0.
    """
    for s in inv:
        for key in (s.symbol, s.normalized):
            if key in (table or {}):
                s.domain_hint = table[key]
                s.domain_provenance = "user-supplied"
                s.role_hint = _ROLE_BY_DOMAIN.get(table[key], s.role_hint)
                s.domain_evidence = [{"kind": "user-supplied",
                                      "quote": "%s: %s" % (key, table[key]),
                                      "source": None}]
                break
    return inv
