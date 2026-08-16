"""Side conditions a step requires, and whether anything establishes them.

The highest-value engine in the design, and it needs no computer algebra: a step
that divides by a quantity nobody proved non-zero is a real gap whether or not
the algebra checks out. It is also the engine most likely to destroy the tool's
credibility, because *every paper ever written* divides by $n$ without saying
$n \\neq 0$.

So this module is mostly suppression, and the suppression list is the feature.
Each entry states the standard practice it protects:

- `\\frac{1}{n}\\sum_{i=1}^n` -- dividing by the bound of the sum you are averaging
- `\\sqrt{x^2}`, `\\sqrt{\\|x\\|^2}` -- an even root of something manifestly non-negative
- numeric denominators and numeric log arguments
- `\\lim` over a *finite* sum, where interchange is unconditional
- `2^{-1}`, a numeric reciprocal that is not a matrix inverse

`established` is only ever set from a *declared* or *user-supplied* domain with a
quote attached. An inferred domain narrows sampling but does not discharge an
obligation the paper still failed to state.
"""
import re

from .tokenize import balanced

#: Symbol names conventionally used for a count. Dividing by one of these while
#: summing over it is averaging, not an unguarded division.
COUNT_NAMES = ("n", "N", "m", "M", "T", "B", "K", "k", "d", "D", "L", "S")

_NUMERIC = re.compile(r"^[\s0-9.+\-*/()]*$")

#: Mathematical constants that are just numbers wearing a backslash.
_CONSTANTS = re.compile(r"\\pi\b|\\mathrm\s*\{\s*e\s*\}|\\e(?![A-Za-z])|\\cdot")

#: `\lim` but not `\limits`, which is a spacing directive. Measured: 10 of 10
#: limit-interchange hits on arXiv:1810.02054 came from `\lim\limits_{...}`.
#: `\b` will not do here: the character after `\liminf` is usually `_`, which is
#: a word character, so `\liminf\b` never matches `\liminf_{n}`.
_LIMIT = re.compile(r"\\liminf(?![a-zA-Z])|\\limsup(?![a-zA-Z])"
                    r"|\\lim(?![a-zA-Z])")


#: A derivative operator immediately applied to an integral. The gap between the
#: two may hold only spacing, delimiters and grouping -- not another term.
_DIFF_OF_INTEGRAL = re.compile(
    r"(?:\\frac\s*\{\s*(?:\\partial|d|\\mathrm\s*\{\s*d\s*\})[^{}]*\}"
    r"\s*\{[^{}]*\}"
    r"|\\nabla(?:\s*_\s*(?:\{[^{}]*\}|\\[A-Za-z]+|\S))?"
    r"|\\partial(?:\s*_\s*(?:\{[^{}]*\}|\\[A-Za-z]+|\S))?)"
    r"(?:\s|\\[,;!:]|\\left|\\big[lr]?|\{|\()*"
    r"\\i?int")


def _delimited_arg(tex, k):
    """The argument beginning at `k`: a group, a delimited expression, or a token.

    `\\log\\left(x\\right)` reported its argument as `\\left` before this existed.
    """
    n = len(tex)
    while k < n and tex[k] in " \t\n":
        k += 1
    if k >= n:
        return None
    if tex.startswith(r"\left", k):
        j = k + 5
        while j < n and tex[j] in " \t\n":
            j += 1
        depth, start = 0, j
        while j < n:
            if tex.startswith(r"\left", j):
                depth += 1
                j += 5
                continue
            if tex.startswith(r"\right", j):
                if depth == 0:
                    return tex[start + 1:j].strip()
                depth -= 1
                j += 6
                continue
            j += 1
        return tex[start + 1:].strip()
    if tex[k] == "{":
        body, _ = balanced(tex, k)
        return None if body is None else body.strip()
    if tex[k] == "(":
        depth = 0
        for j in range(k, n):
            if tex[j] == "(":
                depth += 1
            elif tex[j] == ")":
                depth -= 1
                if depth == 0:
                    return tex[k + 1:j].strip()
        return tex[k + 1:].strip()
    m = re.match(r"\\[A-Za-z]+|[0-9.]+|[A-Za-z]", tex[k:])
    return m.group(0) if m else None


def _manifestly_nonnegative(expr):
    """Radicands that cannot be negative, so an even root needs no condition.

    Measured on arXiv:1810.02054, which produced 55 `even-root-nonnegative`
    reports, almost all of them `\\sqrt{2\\pi}`, `\\sqrt{m}` and friends. Constants
    and counts are stripped and what remains must be arithmetic.
    """
    e = (expr or "").strip()
    if re.search(r"\^\s*\{?\s*2\s*\}?\s*$", e):
        return True
    if r"\|" in e or r"\lVert" in e or r"\Vert" in e:
        return True
    stripped = _CONSTANTS.sub(" ", e)
    stripped = re.sub(r"\b(?:%s)\b" % "|".join(COUNT_NAMES), " ", stripped)
    return bool(_NUMERIC.match(stripped))

# Domains that make a quantity provably non-zero / positive / non-negative.
#
# `natural` means $\ge 1$ here. That is not a reading imposed on the corpus: both
# engines already assume it -- `smt.py` asserts `var >= 1` for a natural, and
# `rational.py` samples a natural from 2, 3, 5, ... -- while this table alone
# treated it as possibly zero. The disagreement was silent and it fired: on a
# 250-page online-learning monograph every `1/t` and `\ln t` outside a summation
# reported "nothing establishes that $t$ is admissible" about a round index the
# paper had bounded below by 1 in the summation that introduced it.
#: `open-unit-interval` is $(0,1)$, which excludes zero by construction. It was
#: in `_POSITIVE` and not here, so a proof opening "for any $\alpha \in (0,1)$"
#: and then dividing by $\alpha$ still reported that nothing established the
#: denominator. Scoping declarations to the enclosing proof made no difference
#: until this was fixed, because the correctly-scoped domain landed in a set that
#: did not discharge the obligation.
_NONZERO = {"positive", "negative", "positive-definite",
            "probability-distribution", "natural", "open-unit-interval"}
_POSITIVE = {"positive", "positive-definite", "probability-distribution",
             "open-unit-interval", "natural"}
_NONNEG = _POSITIVE | {"nonnegative", "unit-interval", "unit-interval-half-open",
                       "positive-semidefinite"}
_INVERTIBLE = {"positive-definite", "invertible"}

#: Provenances that discharge an obligation outright.
_DISCHARGING = ("declared", "user-supplied")

#: Inferences that also discharge, because they are facts the paper wrote down
#: rather than guesses. `\sum_{t=1}^{T} 1/\sqrt{t}` states the range of $t$; a
#: rule that ignores it turns every `\alpha/\sqrt{t}` learning rate into a MAJOR,
#: which is what happened on every optimization paper in the evaluation corpus.
#:
#: `negative-exponent` is deliberately absent: it is inferred *from* `A^{-1}`,
#: which is the very obligation being raised, and letting it discharge itself
#: would be circular.
_DISCHARGING_INFERENCES = frozenset(("summation-index",))


def _sym_domain(expr, symbols):
    """(domain, evidence, known) for the single symbol an expression consists of.

    `known` distinguishes "the paper states a domain that does not discharge this"
    from "the tool could not read a domain at all". Only the first is a finding.
    """
    tok = (expr or "").strip()
    s = symbols.get(tok)
    if s is None:
        return None, None, False
    ev = s.domain_evidence[0] if s.domain_evidence else {}
    if s.domain_provenance == "inferred":
        if ev.get("inference") in _DISCHARGING_INFERENCES:
            return s.domain_hint, "inferred: %s" % ev.get("quote", ""), True
        # The only thing known about this symbol was inferred from the very
        # construct raising the obligation, so nothing is actually known.
        return None, None, False
    if s.domain_provenance not in _DISCHARGING:
        return None, None, False
    return s.domain_hint, ev.get("quote") or s.domain_hint, True


#: A single uppercase Latin letter, or a bold symbol, is a matrix by convention
#: in this literature. Greek lowercase and lowercase Latin are scalars. Used only
#: when the paper declared nothing -- a declaration always wins.
_MATRIXISH = re.compile(r"^(?:\\math(?:bf|bb|cal)\s*\{?\s*)?[A-Z]\}?$")


def _looks_like_matrix(name, sym):
    """Is `X` in `X^{-1}` a matrix, or a scalar being reciprocated?

    `\\rho^{-1}` on a step size asks for $\\rho \\ne 0$; `A^{-1}` asks for
    invertibility. Reporting the first in matrix language is a category error and
    was measured on arXiv:2003.04706 and arXiv:1509.01240.
    """
    if sym is not None and sym.role_hint == "matrix" and \
            sym.domain_provenance in _DISCHARGING:
        return True
    return bool(_MATRIXISH.match((name or "").strip()))


def _positive_form(expr, symbols):
    """Is `expr` non-vanishing because every symbol in it is known positive?

    Only for forms that cannot cancel: no top-level subtraction. This is what
    makes `\\frac{\\|g_t\\|}{\\sqrt{t}}` silent inside `\\sum_{t=1}^{T}` -- the
    radicand is the sum's own index, so the denominator is positive and the paper
    said so by writing the sum.
    """
    e = (expr or "").strip()
    if not e or re.search(r"(?<![\^_{(])-", e):
        return None, None
    names = set(re.findall(r"\\[A-Za-z]+|[A-Za-z]", e))
    names = {n for n in names if n in symbols}
    if not names:
        return None, None
    quotes = []
    for n in names:
        dom, why, _ = _sym_domain(n, symbols)
        if dom not in _POSITIVE and dom != "natural":
            return None, None
        quotes.append(why or dom)
    return True, "; ".join(q for q in quotes if q)


def _one_minus_pattern(expr, symbols):
    """`1 - x` with x confined below 1 is non-zero. The discount-factor case."""
    m = re.match(r"^\s*1\s*-\s*(\\?[A-Za-z]+)\s*$", expr or "")
    if not m:
        return None, None
    dom, quote, _ = _sym_domain(m.group(1), symbols)
    if dom in ("unit-interval-half-open", "open-unit-interval"):
        return True, quote
    return None, None


def _cond(kind, expr, established, by, known=True):
    """One obligation, in one of the three states."""
    if established:
        status = "established"
    elif known:
        status = "unstated"
    else:
        status = "undetermined"
    return {"kind": kind, "expr_tex": expr, "status": status,
            "established": bool(established), "by": by if established else None}


def _find_command_args(tex, name, nargs=1):
    """Every `\\name{...}` occurrence with its argument bodies and span."""
    out = []
    for m in re.finditer(r"\\" + name + r"\s*(?=\{)", tex):
        args, k = [], m.end()
        ok = True
        for _ in range(nargs):
            body, end = balanced(tex, k)
            if body is None:
                ok = False
                break
            args.append(body)
            k = end
        if ok:
            out.append((args, m.start(), k))
    return out


def _sum_bounds(tex):
    """Upper bounds of every `\\sum`/`\\prod` in the expression."""
    out = set()
    for m in re.finditer(r"\\(?:sum|prod)\s*(_\s*(?:\{[^}]*\}|\S))?"
                         r"\s*(\^\s*(?:\{[^}]*\}|\S))?", tex):
        sup = m.group(2) or ""
        sup = sup.lstrip("^").strip().strip("{}").strip()
        if sup:
            out.add(sup)
    return out


def conditions(math_tex, symbols=None, context_tex=""):
    """Side conditions the expression requires, minus everything standard.

    Each dict carries `status`, which is the field that matters:

    - `established` -- a stated domain discharges it, and `by` quotes the sentence
    - `unstated` -- the domain is known and does *not* discharge it. A finding:
      the algebra may be right and the licence still missing.
    - `undetermined` -- no domain could be read, so no claim is made either way.

    Measured on three real papers, which produced 84, 98 and 97 conditions with
    100% "unestablished" before this distinction existed. In one of them 54 of 61
    symbols had an unreadable domain. Alleging a missing licence on those would be
    the same error as sampling outside a domain nobody wrote down.
    """
    tex = math_tex or ""
    symbols = symbols or {}
    bounds = _sum_bounds(tex)
    out = []

    # --- division -------------------------------------------------------------
    for args, a, b in _find_command_args(tex, r"[dt]?frac", nargs=2):
        den = args[1].strip()
        if _NUMERIC.match(den):
            continue
        if den in bounds or (den in COUNT_NAMES and bounds):
            continue                       # averaging over the sum's own bound
        if den in COUNT_NAMES:
            continue        # dividing by a count is averaging, sum in sight or not
        est, why = _one_minus_pattern(den, symbols)
        if not est:
            est, why = _positive_form(den, symbols)
        if est:
            out.append(_cond("nonzero-denominator", den, True, why))
            continue
        dom, why, known = _sym_domain(den, symbols)
        out.append(_cond("nonzero-denominator", den, dom in _NONZERO, why, known))

    # --- logarithms -----------------------------------------------------------
    for m in re.finditer(r"\\(?:log|ln)\s*(?:_\s*(?:\{[^}]*\}|\S))?", tex):
        arg = _delimited_arg(tex, m.end())
        if not arg or _NUMERIC.match(_CONSTANTS.sub(" ", arg)):
            continue
        dom, why, known = _sym_domain(arg, symbols)
        out.append(_cond("log-argument-positive", arg, dom in _POSITIVE, why, known))

    # --- even roots -----------------------------------------------------------
    for m in re.finditer(r"\\sqrt\s*(?:\[[^\]]*\])?", tex):
        arg = _delimited_arg(tex, m.end())
        if not arg or _manifestly_nonnegative(arg):
            continue
        dom, why, known = _sym_domain(arg, symbols)
        out.append(_cond("even-root-nonnegative", arg, dom in _NONNEG, why, known))

    # --- inverses -------------------------------------------------------------
    for m in re.finditer(r"(\\?[A-Za-z]+)\s*\^\s*\{?\s*-\s*1\s*\}?", tex):
        base = m.group(1)
        if base.isdigit():
            continue
        sym = symbols.get(base)
        dom, why, known = _sym_domain(base, symbols)
        # `\rho^{-1}` on a scalar asks for non-vanishing, not for a matrix
        # inverse. Measured on arXiv:2003.04706 and 1509.01240, where the
        # finding read "needs $\rho$ to be invertible" about a step size.
        is_matrix = _looks_like_matrix(base, sym)
        if is_matrix:
            out.append(_cond("invertible", base, dom in _INVERTIBLE, why, known))
        else:
            out.append(_cond("nonzero-denominator", base, dom in _NONZERO, why,
                             known))

    # --- interchange of a limit with a sum or integral ------------------------
    lm = _LIMIT.search(tex)
    if lm:
        after = tex[lm.end():]
        # `\lim\limits_{r \to 0+}` is the common idiom. Quoting the expression
        # from just after `\lim` makes the finding open with `\limits_`, which
        # reads as a parser artifact and costs the reader's trust in the finding.
        after = re.sub(r"^\s*\\limits", "", after)
        after = re.sub(r"^\s*(?:_\s*(?:\{[^}]*\}|\S))?"
                       r"\s*(?:\^\s*(?:\{[^}]*\}|\S))?", "", after)
        infinite_sum = re.search(r"\\sum[^\\]*\\infty|\\sum\s*_\s*\{[^}]*\}\s*\^\s*"
                                 r"\{?\s*\\infty", after)
        integral = re.search(r"\\i?int", after)
        if infinite_sum or integral:
            out.append(_cond("limit-interchange", after.strip()[:80],
                             False, None, known=True))

    # --- differentiating under an integral ------------------------------------
    # The derivative must be applied *to* the integral, not merely appear before
    # it. Measured on arXiv:1405.4980: Taylor with integral remainder puts a
    # gradient on the left and an integral on the right, interchanges nothing,
    # and produced three MAJORs on a reference monograph.
    m = _DIFF_OF_INTEGRAL.search(tex)
    if m:
        out.append(_cond("differentiate-under-integral", m.group(0).strip()[:80],
                         False, None, known=True))

    return _dedupe(out)


def _dedupe(conds):
    """The same obligation stated twice in one step is one obligation.

    A chain that divides by $\\mu(B_r)$ in four consecutive rows owes one
    non-vanishing condition, not four, and four is what makes a report unreadable.
    """
    seen, out = set(), []
    for c in conds:
        key = (c["kind"], re.sub(r"\s+", "", c["expr_tex"] or ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def findings(conds):
    """The subset that is a finding: domain known, and it does not discharge.

    `undetermined` is deliberately excluded. It belongs in the report as a gap to
    check by hand, and reporting it as a defect is how a reader learns to skim.
    """
    return [c for c in conds or [] if c["status"] == "unstated"]


def undetermined(conds):
    """Obligations whose domain could not be read. Report, never allege."""
    return [c for c in conds or [] if c["status"] == "undetermined"]


def unestablished(conds):
    """Everything not discharged, of either kind. For coverage counting only."""
    return [c for c in conds or [] if not c["established"]]
