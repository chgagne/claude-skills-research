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

That is the document-wide reading. `scope_table` and `resolve_at` give the
reading **at a position**: the declarations inside one proof and its statement,
in source order, with the last one before the step winning. Both are needed. A
long document reuses its letters, and a monograph that declares
`$\\alpha \\in [0,1]$` on page 12 for a convex combination and opens a proof on
page 300 with *"for any `$\\alpha \\in (0,1)$`"* means the second one there.
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

#: The zero in these bounds must be the whole number. Without it
#: `\varepsilon \leq 0.006` matches `\leq 0` and declares $\varepsilon$
#: non-positive -- measured on Bubeck's monograph, where it put one MAJOR back on
#: the most heavily vetted document in the corpus. `< 0.5` reading as "negative"
#: is the same shape and the same severity of wrong.
_ZERO_END = r"(?![.,]?\d)"
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
    ("positive-definite", r"\\succ\s*0" + _ZERO_END),
    ("positive-semidefinite", r"\\succeq\s*0" + _ZERO_END),
    ("positive", r">\s*0" + _ZERO_END),
    ("negative", r"<\s*0" + _ZERO_END),
    ("nonnegative", r"\\geq?\s*0" + _ZERO_END + r"|\\ge\s*0" + _ZERO_END),
    ("nonpositive", r"\\leq?\s*0" + _ZERO_END + r"|\\le\s*0" + _ZERO_END),
]
# Wrapped, because these are composed onto a symbol prefix and two of them carry
# a top-level `|`. Unwrapped, `t` + `\geq?\s*0|\ge\s*0` parses as
# *(t followed by >= 0)* OR *(any `\ge 0` anywhere at all)*, so a single
# `x \ge 0` in a proof declared every symbol in that proof nonnegative. Measured
# on an online-learning monograph, where one such line gave seven symbols --
# including two indices and a probability -- the domain `nonnegative`, provenance
# `declared`, which is a refuting provenance.
_DECLARED = [(k, re.compile("(?:%s)" % p)) for k, p in _DECLARED]

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

#: Every domain name this codebase understands, in one place because it used to
#: be in four: the patterns above, `_ROLE_BY_DOMAIN`, the `_NONZERO`/`_POSITIVE`/
#: `_NONNEG`/`_INVERTIBLE` sets in `sideconds`, and the sampling pools in the
#: engines. A name outside this tuple discharges nothing anywhere, so a reader
#: who mistypes one gets silence rather than an error -- see `apply_user_domains`.
DOMAINS = (
    "real", "integer", "natural", "integer-positive", "complex",
    "positive", "negative", "nonnegative", "nonpositive",
    "unit-interval", "unit-interval-half-open", "open-unit-interval",
    "real-vector", "matrix", "invertible",
    "positive-definite", "positive-semidefinite",
    "probability-distribution", "convex",
)


def validate_domains(table):
    """Names in a user-supplied symbol table that this codebase cannot use.

    Returns `[(symbol, value, nearest_legal_or_None)]`, empty when all are fine.

    This exists because the failure mode is silence. `apply_user_domains` set
    `domain_hint` to whatever string it was handed, and a value like
    `unit_interval` then matched nothing in any of the sets that discharge an
    obligation -- so a reader's minute of work bought nothing and said nothing.
    The whole argument for `--symbols` is that one minute of a reader's time is
    worth more than any amount of inference, and a typo that fails quietly
    destroys exactly that.

    A key beginning with `_` is an annotation, not a symbol, and is ignored.
    A supplied domain is evidence about the paper, and evidence with no
    provenance beside it cannot be audited or corrected later -- but JSON has no
    comments and no LaTeX symbol starts with an underscore, so this is the seam
    where the reason a domain was chosen can be written down and kept with it.
    """
    import difflib
    bad = []
    for sym, value in sorted((table or {}).items()):
        if sym.startswith("_"):
            continue                      # an annotation, not a symbol
        if value in ("", None):
            continue                      # an unfilled template row, not an error
        if value not in DOMAINS:
            near = difflib.get_close_matches(str(value), DOMAINS, n=1, cutoff=0.6)
            bad.append((sym, value, near[0] if near else None))
    return bad


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
                    # Not "scalar". A role is only known once a domain says so,
                    # and defaulting to scalar asserted it about every symbol
                    # the paper never typed -- 77 of 81 on one paper, with the
                    # ambient set, the objective function and a projection
                    # operator all reported as scalars to an expander that had
                    # to work out otherwise. Unknown is the honest value and it
                    # is what `_ROLE_BY_DOMAIN` overwrites when there is
                    # evidence.
                    defined_at=None, role_hint=None, domain_hint=None,
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


#: The symbol must start a token. Without this, `y_t \in [0,1]` -- which declares
#: `y` -- is read as declaring `t`, because the search for `t \in ...` matches the
#: subscript. Measured on a 250-page online-learning monograph, where nearly every
#: quantity is subscripted by the round index: `t` was recorded as
#: `unit-interval`, `declared`, across 9147 occurrences of an integer index. A
#: *wrong* declared domain is worse than an unknown one, because `declared` is a
#: refuting provenance -- the tool would have been entitled to sample $t=1/2$ and
#: report a counterexample against correct mathematics.
_TOKEN_START = r"(?<![A-Za-z0-9_^\\])"

#: Decoration between the symbol and the relation. `y_t \in [0,1]` declares $y$,
#: and without this it declares nothing at all.
_DECORATION = r"(?:_\{[^{}]*\}|_[A-Za-z0-9]|\^\{[^{}]*\}|\^[A-Za-z0-9]|')*"

#: `a, b \geq 0` declares both. Matching only the symbol adjacent to the relation
#: left $a$ with no domain at all, so it fell through to an unrelated earlier
#: declaration and the step's own stated side condition reported as unmet --
#: the tool contradicting the sentence it is reading, measured on Tropp's
#: matrix-concentration monograph. Bounded at four, because a longer list before
#: a relation is more likely to be an expression than a declaration.
_COMPANIONS = r"(?:\s*,\s*\$?\s*\\?[A-Za-z]+" + _DECORATION + r"\$?){0,4}\s*"


def _find_declaration(text, symbol, start, end):
    """A declaration of `symbol` between `start` and `end`, or `None`.

    Searched against the full text with a bounded window rather than against a
    sliced copy: the token-start guard is a lookbehind, and a lookbehind on a
    slice cannot see the character before the slice. With `t` first used inside
    `\\alpha_t \\in [0,1]`, the window begins at that very `t` and the guard has
    nothing to look behind at, so the subscript is read as the declared symbol
    again -- the exact bug the guard exists to stop.
    """
    esc = _TOKEN_START + re.escape(symbol) + _DECORATION + _COMPANIONS
    for kind, pat in _DECLARED:
        m = re.compile(esc + r"\s*(?:\$?\s*)?" + pat.pattern).search(text, start, end)
        if m:
            return kind, m.start(), m.end()
    for kind, tmpl in _PROSE_DECLARED:
        m = re.compile(tmpl % esc, re.I).search(text, start, end)
        if m:
            return kind, m.start(), m.end()
    return None


def declarations_in(text, symbol, start, end):
    """Every declaration of `symbol` in `[start, end)`, in source order."""
    esc = _TOKEN_START + re.escape(symbol) + _DECORATION + _COMPANIONS
    out = []
    for kind, pat in _DECLARED:
        for m in re.compile(esc + r"\s*(?:\$?\s*)?"
                            + pat.pattern).finditer(text, start, end):
            out.append((m.start(), kind, m.start(), m.end()))
    for kind, tmpl in _PROSE_DECLARED:
        for m in re.compile(tmpl % esc, re.I).finditer(text, start, end):
            out.append((m.start(), kind, m.start(), m.end()))
    out.sort()
    return out


def scope_table(inv, text, start, end):
    r"""Declarations available inside one passage, ready to resolve per position.

    Domains are otherwise global and first-use wins, which is wrong in exactly
    the place it matters most. Measured on a 250-page online-learning monograph:
    $\alpha \in [0,1]$ is declared once, early, for a convex combination; three
    hundred pages later a proof opens *"for any $\alpha \in (0,1)$"* and divides
    by $\alpha$. The open interval never reached the step, and every such
    division reported as unlicensed -- `MAJOR` findings against correct
    mathematics, which is the cry-wolf failure this module exists to prevent.

    `start`/`end` should span the claim statement as well as the proof body: that
    is where hypotheses live, and a hypothesis is a declaration.
    """
    return {name: declarations_in(text, sym.symbol, start, end)
            for name, sym in inv.items()}


def resolve_at(inv, table, text, position):
    r"""The symbol table as it reads at one point in the source.

    The *last* declaration before the position wins, not the first in the
    passage. Scoping to the whole proof and taking the first match was tried and
    was not enough: a proof that uses $t$ as a round index for thirty steps and
    then writes $t \in [0,1]$ in a convex-combination argument at step thirty-one
    had the interval applied to all thirty. A declaration governs what comes
    after it, which is the ordinary reading of mathematical prose.

    A symbol the passage says nothing about keeps whatever the document
    established, and a local declaration is one the paper wrote down, so the
    provenance stays `declared`.
    """
    out = {}
    for name, sym in inv.items():
        prior = [d for d in table.get(name, ()) if d[3] <= position]
        if not prior:
            out[name] = sym
            continue
        _, kind, a, b = prior[-1]
        if kind == sym.domain_hint and sym.domain_provenance == "declared":
            out[name] = sym
            continue
        local = Symbol(**sym.as_dict())
        _set(local, kind, "declared", text, a, b)
        local.scopes = list(sym.scopes or []) + [
            {"at": position, "domain": kind, "overrides": sym.domain_hint}]
        out[name] = local
    return out


def _assign_domain(text, sym):
    """Find a declaration near this symbol's first use."""
    _, base = _window(text, sym)
    end = base + DECLARATION_WINDOW
    found = _find_declaration(text, sym.symbol, base, end)
    if found:
        kind, a, b = found
        _set(sym, kind, "declared", text, a, b)
        return

    # Inferred: the surrounding notation forces the domain. No companion list
    # here -- an inference is about this symbol's own surroundings.
    esc = _TOKEN_START + re.escape(sym.symbol) + _DECORATION
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
    bad = validate_domains(table)
    if bad:
        raise ValueError(
            "unusable domain%s in the symbol table: %s. Legal values: %s"
            % ("" if len(bad) == 1 else "s",
               "; ".join("%s = %r%s" % (s, v, " (did you mean %r?)" % n if n else "")
                         for s, v, n in bad),
               ", ".join(DOMAINS)))
    for s in inv:
        for key in (s.symbol, s.normalized):
            if key in (table or {}) and table[key] not in ("", None):
                s.domain_hint = table[key]
                s.domain_provenance = "user-supplied"
                s.role_hint = _ROLE_BY_DOMAIN.get(table[key], s.role_hint)
                s.domain_evidence = [{"kind": "user-supplied",
                                      "quote": "%s: %s" % (key, table[key]),
                                      "source": None}]
                break
    return inv
