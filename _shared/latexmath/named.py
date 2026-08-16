r"""Hypotheses of results invoked by name, and the few that can be checked.

`segment.NAMED_RESULTS` normalises *"by Jensen's inequality"* into `jensen`, and
its own comment says what was missing: **an entry nobody checks the hypotheses of
is decoration.** This module is the checker, and it is deliberately small.

Two rules shape it, both inherited from `sideconds`:

1. **A hypothesis this module cannot read is not a finding.** Most named results
   need something no parser sees -- that a norm is finite, that a dominating
   summable bound exists, that the events are the ones the conclusion quantifies
   over. Those entries emit nothing at all. Emitting `undetermined` for every
   hypothesis of every named result would have added roughly 120 rows on one
   monograph, and a report nobody finishes reading is worse than no report.
2. **`unstated` is claimed only when a domain was actually read.** The paper
   declaring $f$ convex and then using Jensen the wrong way round is a finding.
   The paper declaring nothing is a gap in the paper's writing, not in its
   mathematics, and it comes out as `undetermined`.

What is checkable, and therefore what is here:

| Result | Checked |
|---|---|
| `jensen` | the **direction**: with $f$ declared convex, $\mathbb{E}[f(X)]$ is the larger side |
| `markov`, `chebyshev` | non-negativity of the quantity bounded |
| `am-gm` | non-negativity of the terms |

Everything else in the catalogue is listed in `UNCHECKED` with the reason, so a
reader can see the difference between "checked and fine" and "not looked at".
"""
import re

#: Named results whose hypotheses nothing here can read, and why. Listed rather
#: than omitted: the distinction between a silent pass and an unexamined step is
#: the whole reason this file has a docstring.
UNCHECKED = {
    "cauchy-schwarz": "both norms must be finite, which no parser sees",
    "holder": "conjugate exponents and finiteness of both norms",
    "minkowski": "finiteness of both norms",
    "triangle": "finiteness of each piece",
    "union-bound": "the events must be the ones the conclusion quantifies over",
    "fatou": "non-negativity of the sequence, which is rarely written down",
    "dominated-convergence": "existence of a dominating integrable bound",
    "monotone-convergence": "monotonicity of the sequence",
    "fubini": "absolute integrability on the product space",
    "taylor": "differentiability to the order used, on the whole interval",
    "mean-value": "continuity on the closed interval, differentiability inside",
    "bayes": "the conditioning event must have positive probability",
    "chain-rule": "differentiability of both factors at the point",
    "tower": "integrability of the inner expectation",
    "total-probability": "the partition must be exhaustive and disjoint",
    "hoeffding": "independence and a bounded range per term",
    "bernstein": "independence and a variance bound",
    "mcdiarmid": "the bounded-difference constant per coordinate",
    "azuma": "the martingale property and bounded increments",
    "borel-cantelli": "summability of the probabilities",
    "gronwall": "non-negativity and integrability of the kernel",
    "pinsker": "both arguments must be probability measures",
    "lipschitz": "the constant must be uniform on the set in play",
    "banach-fixed-point": "completeness of the space and a contraction factor",
}

_EXPECTATION = r"(?:\\mathbb\s*\{\s*E\s*\}|\\mathbb E|\\operatorname\s*\{\s*E\s*\}|\\E(?![A-Za-z]))"

#: `E[ f(...) ]` -- an expectation whose argument applies something to something.
_E_OF_F = re.compile(_EXPECTATION + r"\s*(?:_\s*(?:\{[^{}]*\}|\S))?\s*"
                     r"[\[\(\{]\s*\\?[A-Za-z]+\s*[\(\[]")
#: `f( E[...] )` -- a function applied to an expectation.
_F_OF_E = re.compile(r"\\?[A-Za-z]+\s*[\(\[]\s*" + _EXPECTATION)

#: Order relations, and whether the left side is claimed to be the larger one.
_LEFT_IS_GREATER = {r"\ge": True, r"\geq": True, r"\geqslant": True, ">": True,
                    r"\le": False, r"\leq": False, r"\leqslant": False, "<": False}


def _side_shapes(form):
    """(has E[f] , has f(E)) for each side of a claim form."""
    lhs, rhs = form.get("lhs_tex") or "", form.get("rhs_tex") or ""
    return ((bool(_E_OF_F.search(lhs)), bool(_F_OF_E.search(lhs))),
            (bool(_E_OF_F.search(rhs)), bool(_F_OF_E.search(rhs))))


def _jensen(step, symbols):
    r"""Jensen's direction, which is the whole content of the inequality.

    For convex $f$, $\mathbb{E}[f(X)] \ge f(\mathbb{E}[X])$; for concave $f$ it
    reverses. A step that names Jensen, declares its function convex, and then
    puts $f(\mathbb{E}[X])$ on the larger side has applied it backwards -- and
    that is one of the defects the seeded-error benchmark lists as unreachable
    without this engine.

    Nothing is claimed unless the paper declared the function convex or concave.
    Without that the direction is unknowable from the source, and saying so is
    the honest answer.
    """
    convex = sorted(n for n, s in symbols.items()
                    if (s.get("domain_hint") if isinstance(s, dict)
                        else s.domain_hint) == "convex")
    for form in step.get("claim_forms") or []:
        rel = (form.get("relation") or "").strip()
        if rel not in _LEFT_IS_GREATER:
            continue
        (l_ef, l_fe), (r_ef, r_fe) = _side_shapes(form)
        if not ((l_ef and r_fe) or (r_ef and l_fe)):
            continue
        left_greater = _LEFT_IS_GREATER[rel]
        e_of_f_on_left = l_ef
        # Convex: E[f] is the larger side. The claim is right when the side
        # carrying E[f] is the side the relation calls larger.
        correct = (e_of_f_on_left == left_greater)
        if not convex:
            return {"kind": "jensen-direction",
                    "expr_tex": (form.get("lhs_tex") or "")[:60],
                    "status": "undetermined", "established": False, "by": None,
                    "detail": "Jensen is invoked and no function here is declared "
                              "convex or concave, so the direction cannot be "
                              "checked"}
        return {"kind": "jensen-direction",
                "expr_tex": (form.get("lhs_tex") or "")[:60],
                "status": "established" if correct else "unstated",
                "established": bool(correct),
                "by": ("$%s$ declared convex" % convex[0]) if correct else None,
                "detail": None if correct else
                          "with $%s$ declared convex, $E[f(X)]$ is the larger "
                          "side; this step puts it on the smaller one"
                          % convex[0]}
    return None


_NONNEG_DOMAINS = ("nonnegative", "positive", "natural", "unit-interval",
                   "unit-interval-half-open", "open-unit-interval",
                   "probability-distribution", "positive-definite")


def _nonnegative_subject(step, symbols, result):
    """Markov and Chebyshev bound a *non-negative* quantity."""
    used = [n for n in step.get("symbols_used") or [] if n in symbols]
    if not used:
        return None
    known = []
    for n in used:
        s = symbols[n]
        dom = s.get("domain_hint") if isinstance(s, dict) else s.domain_hint
        prov = (s.get("domain_provenance") if isinstance(s, dict)
                else s.domain_provenance)
        if prov in ("declared", "user-supplied"):
            known.append((n, dom))
    if not known:
        return {"kind": "%s-nonnegative" % result, "expr_tex": used[0],
                "status": "undetermined", "established": False, "by": None,
                "detail": "%s needs the quantity it bounds to be non-negative, "
                          "and no domain here was stated" % result}
    ok = [n for n, d in known if d in _NONNEG_DOMAINS]
    if ok:
        return {"kind": "%s-nonnegative" % result, "expr_tex": ok[0],
                "status": "established", "established": True,
                "by": "declared domain", "detail": None}
    return {"kind": "%s-nonnegative" % result, "expr_tex": known[0][0],
            "status": "unstated", "established": False, "by": None,
            "detail": "%s needs a non-negative quantity; $%s$ is declared %s"
                      % (result, known[0][0], known[0][1])}


_CHECKS = {
    "jensen": _jensen,
    "markov": lambda s, y: _nonnegative_subject(s, y, "markov"),
    "chebyshev": lambda s, y: _nonnegative_subject(s, y, "chebyshev"),
    "am-gm": lambda s, y: _nonnegative_subject(s, y, "am-gm"),
}


def conditions(step, symbols):
    """Side conditions from the named result this step invokes, if any."""
    just = step.get("justification") or {}
    if just.get("kind") != "named-result":
        return []
    name = just.get("name")
    check = _CHECKS.get(name)
    if check is None:
        return []
    got = check(step, symbols or {})
    return [got] if got else []
