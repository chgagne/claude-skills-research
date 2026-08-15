"""SymPy equivalence, with the guards that keep a translation bug from becoming
a mathematics finding.

This is the only engine that may **confirm** an equality, and it will do so far
less often than one expects: `simplify` on an expression containing opaque
function symbols returns something non-zero much more readily than it proves
zero. Most of its verdicts are `UNVERIFIED`, and that is the honest answer.

Two guards run before any refutation is allowed to become a finding:

- **Round-trip display.** `sympy.latex()` of what was actually parsed is printed
  beside the source LaTeX, so a dropped subscript is visible in two seconds
  rather than being argued about.
- **Symbol coverage.** Every symbol the ledger says the step uses must appear in
  the expression or in `IGNORED_SYMBOLS`. A translation that silently dropped
  `\\sum_{i=1}^n` fails this and is downgraded to
  `UNVERIFIED (translation incomplete)` rather than being believed.

The harness lives here as source text because generated scripts run under an
import allowlist and may not import this package.
"""

HARNESS = r'''
# --- sympy harness (inlined; runs only inside the generated script) ---------
import sympy


class Untranslatable(Exception):
    """Raised by build() when the step cannot be faithfully modelled."""


_EQ = ("=", r"\equiv", ":=", r"\coloneqq", r"\doteq", r"\triangleq")

#: Order relations, and the sign the *slack* `rhs - lhs` must carry for the claim
#: to hold. Inequalities are most of what optimization papers prove, so declining
#: them left three papers with documented proof errors reporting nothing at all.
_ORDER = {r"\le": "nonneg", r"\leq": "nonneg", r"\leqslant": "nonneg",
          "<": "pos", r"\ge": "nonpos", r"\geq": "nonpos",
          r"\geqslant": "nonpos", ">": "neg"}


def _decide_order(lhs, rhs, relation, step_id, roundtrip):
    """Decide an inequality by the sign of the slack, exactly.

    SymPy settles a concrete comparison exactly -- including irrationals such as
    `sqrt(2) + sqrt(3) <= 3` -- and settles a symbolic one whenever the
    assumptions carried on the symbols are enough. When they are not, the answer
    is `unverified`: a slack whose sign SymPy cannot determine says nothing about
    the claim in either direction.
    """
    want = _ORDER[relation]
    try:
        slack = sympy.simplify(rhs - lhs)
    except Exception as exc:                      # noqa: BLE001
        return {"step_id": step_id, "engine": "symbolic", "outcome": "unverified",
                "detail": "could not simplify the slack: %s" % exc,
                "counterexample": None, "roundtrip_latex": roundtrip}

    holds = {"nonneg": slack.is_nonnegative, "pos": slack.is_positive,
             "nonpos": slack.is_nonpositive, "neg": slack.is_negative}[want]
    fails = {"nonneg": slack.is_negative, "pos": slack.is_nonpositive,
             "nonpos": slack.is_positive, "neg": slack.is_nonnegative}[want]

    if holds is True:
        return {"step_id": step_id, "engine": "symbolic", "outcome": "confirmed",
                "detail": "rhs - lhs = %s, whose sign settles the inequality"
                          % slack,
                "counterexample": None, "roundtrip_latex": roundtrip}
    if fails is True:
        return {"step_id": step_id, "engine": "symbolic", "outcome": "refuted",
                "detail": "rhs - lhs = %s (approximately %s), so the stated "
                          "inequality points the wrong way"
                          % (slack, _approx(slack)),
                "counterexample": None, "roundtrip_latex": roundtrip}
    return {"step_id": step_id, "engine": "symbolic", "outcome": "unverified",
            "detail": "rhs - lhs = %s; SymPy could not determine its sign from "
                      "the assumptions available, so the inequality is neither "
                      "confirmed nor refuted" % slack,
            "counterexample": None, "roundtrip_latex": roundtrip}


def _approx(expr):
    try:
        return sympy.N(expr, 8)
    except Exception:                             # noqa: BLE001
        return "?"


def _normalise(name):
    return str(name).lstrip("\\")


def check(lhs, rhs, relation, declared, ignored, step_id):
    """Decide the step, or say why it could not be decided."""
    try:
        free = set()
        for e in (lhs, rhs):
            free |= {_normalise(s) for s in getattr(e, "free_symbols", set())}
        roundtrip = "%s %s %s" % (sympy.latex(lhs), relation, sympy.latex(rhs))
    except Exception as exc:                      # noqa: BLE001 - report, never raise
        return {"step_id": step_id, "engine": "symbolic", "outcome": "unverified",
                "detail": "could not render the translation: %s" % exc,
                "counterexample": None, "roundtrip_latex": None}

    ignored_n = {_normalise(s) for s in (ignored or [])}
    missing = [s for s in (declared or [])
               if _normalise(s) not in free and _normalise(s) not in ignored_n]
    if missing:
        return {"step_id": step_id, "engine": "symbolic", "outcome": "unverified",
                "detail": "translation incomplete: %s appear in the step but not "
                          "in the model, and were not declared ignored"
                          % ", ".join(sorted(missing)),
                "counterexample": None, "roundtrip_latex": roundtrip}

    if relation in _ORDER:
        return _decide_order(lhs, rhs, relation, step_id, roundtrip)

    if relation not in _EQ:
        return {"step_id": step_id, "engine": "symbolic", "outcome": "unverified",
                "detail": "no symbolic rule for the relation %r" % relation,
                "counterexample": None, "roundtrip_latex": roundtrip}

    try:
        diff = sympy.simplify(sympy.expand(lhs - rhs))
    except Exception as exc:                      # noqa: BLE001
        return {"step_id": step_id, "engine": "symbolic", "outcome": "unverified",
                "detail": "simplify failed: %s" % exc,
                "counterexample": None, "roundtrip_latex": roundtrip}

    if diff == 0 or diff.is_zero is True:
        return {"step_id": step_id, "engine": "symbolic", "outcome": "confirmed",
                "detail": "simplify(lhs - rhs) = 0",
                "counterexample": None, "roundtrip_latex": roundtrip}

    if diff.is_zero is False:
        point = None
        try:
            syms = sorted(diff.free_symbols, key=lambda s: str(s))
            if syms:
                sub = {s: sympy.Rational(2 + i, 3) for i, s in enumerate(syms)}
                if sympy.simplify(diff.subs(sub)) != 0:
                    point = {str(k): str(v) for k, v in sub.items()}
        except Exception:                          # noqa: BLE001
            point = None
        return {"step_id": step_id, "engine": "symbolic", "outcome": "refuted",
                "detail": "simplify(lhs - rhs) = %s, which is not zero" % diff,
                "counterexample": point, "roundtrip_latex": roundtrip}

    return {"step_id": step_id, "engine": "symbolic", "outcome": "unverified",
            "detail": "simplify(lhs - rhs) = %s; SymPy could not decide whether "
                      "this is zero, so the step is neither confirmed nor "
                      "refuted" % diff,
            "counterexample": None, "roundtrip_latex": roundtrip}
# --- end harness ------------------------------------------------------------
'''
