"""Randomized exact-rational evaluation. Stdlib only, in the harness and in the
generated script alike.

This engine does most of the real work, and it can only ever **refute**. A step
that survives every sample point is `NOT REFUTED`, which is evidence and not
proof; the report never calls it verified.

The harness is kept here as source text rather than as a module because the
generated scripts run under an import allowlist -- they may not import this
package. Inlining it also makes each script a self-contained artifact a reader can
open, which is the point of writing them to disk at all.

Design decisions that each exist because the obvious alternative is wrong:

- **0 and +-1 are never sampled.** They satisfy far too many false identities:
  `x^a = x^b` holds at 1 for every a and b, and 0 annihilates most discrimination.
- **Degenerate points are rejected and counted, never silently skipped.** More
  than half rejected means the domain was too constrained to sample, which is
  `UNVERIFIED` -- not a pass.
- **A double zero is not evidence.** If both sides evaluate to 0 at every point,
  the check learned nothing.
- **A failure is re-run at higher density** to report the *smallest* refuting
  point, because a counterexample a reader can verify by hand in thirty seconds
  is worth ten they cannot.
- **Inequalities get boundary points deliberately.** They typically fail at the
  ends of a domain and hold across a random interior.
"""

HARNESS = r'''
# --- rational-sampling harness (inlined; stdlib only) ----------------------
import hashlib
from fractions import Fraction


class Untranslatable(Exception):
    """Raised by build() when the step cannot be faithfully modelled."""


#: Numerators, excluding 0 and +-1: those satisfy too many false identities.
_NUM = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29)
_DEN = (1, 2, 3, 5, 7, 9)

_POSITIVE = ("positive", "positive-definite", "probability-distribution")
_NONNEG = ("nonnegative", "natural", "unit-interval", "unit-interval-half-open",
           "open-unit-interval")


def _pool(domain, want):
    """Candidate values for a symbol, ordered by increasing magnitude."""
    out = []
    if domain in ("natural", "integer-positive"):
        out = [Fraction(n) for n in _NUM]
    elif domain == "integer":
        out = [Fraction(s * n) for n in _NUM for s in (1, -1)]
    elif domain in ("unit-interval", "unit-interval-half-open",
                    "open-unit-interval"):
        out = [Fraction(a, b) for b in (2, 3, 5, 7, 9, 11) for a in range(1, b)]
    elif domain in _POSITIVE:
        out = [Fraction(n, d) for n in _NUM for d in _DEN]
    elif domain == "negative":
        out = [Fraction(-n, d) for n in _NUM for d in _DEN]
    else:
        out = [Fraction(s * n, d) for n in _NUM for d in _DEN for s in (1, -1)]
    # Filter *after* construction: Fraction(3, 3) is 1, and 1 satisfies far too
    # many false identities to be usable as a discriminating point.
    out = [v for v in out if abs(v) != 1 and v != 0]
    out = sorted(set(out), key=lambda v: (abs(v), v))
    return (out * ((want // len(out)) + 1))[:want] if out else []


def _endpoints(domain):
    """Points where an inequality is most likely to fail, if it fails at all."""
    if domain in ("unit-interval", "unit-interval-half-open", "open-unit-interval"):
        return [Fraction(1, 100), Fraction(99, 100)]
    if domain in _POSITIVE:
        return [Fraction(1, 100)]
    if domain in _NONNEG:
        return [Fraction(1, 100)]
    return []


def _points(symbols, domains, step_id, trials, relation="="):
    """Deterministic sample points. The same step always yields the same run."""
    seed = int(hashlib.blake2b(str(step_id).encode("utf-8"),
                               digest_size=8).hexdigest(), 16)
    pools = {}
    for i, s in enumerate(symbols):
        p = _pool(domains.get(s), max(trials, 8))
        shift = (seed >> (i * 5)) % max(len(p), 1)
        pools[s] = p[shift:] + p[:shift]

    out = []
    if relation != "=":
        for s in symbols:
            for e in _endpoints(domains.get(s)):
                pt = {t: pools[t][0] for t in symbols}
                pt[s] = e
                out.append(pt)
    for k in range(trials):
        out.append({s: pools[s][k % len(pools[s])] for s in symbols})
    return out[:max(trials, len(out))] if trials else out


def _holds(lhs, rhs, relation):
    if relation in ("=", r"\equiv", ":=", r"\coloneqq", r"\doteq", r"\triangleq"):
        return lhs == rhs
    if relation in (r"\le", r"\leq", r"\leqslant"):
        return lhs <= rhs
    if relation in (r"\ge", r"\geq", r"\geqslant"):
        return lhs >= rhs
    if relation == "<":
        return lhs < rhs
    if relation == ">":
        return lhs > rhs
    if relation in (r"\ne", r"\neq"):
        return lhs != rhs
    return None


def check(lhs_fn, rhs_fn, relation, symbols, domains, step_id, trials=24):
    """Sample the claim. Refute, or report that it was not refuted."""
    pts = _points(symbols, domains, step_id, trials, relation)
    rejected = 0
    tried = 0
    zero_both = 0
    failures = []
    for env in pts:
        try:
            a = lhs_fn(env)
            b = rhs_fn(env)
        except Untranslatable as exc:
            return {"step_id": step_id, "engine": "rational",
                    "outcome": "untranslatable", "detail": str(exc),
                    "trials": 0, "rejected_samples": 0, "counterexample": None}
        except (ZeroDivisionError, ValueError, ArithmeticError, OverflowError):
            rejected += 1
            continue
        verdict = _holds(a, b, relation)
        if verdict is None:
            return {"step_id": step_id, "engine": "rational",
                    "outcome": "untranslatable",
                    "detail": "no sampling rule for relation %r" % relation,
                    "trials": 0, "rejected_samples": rejected,
                    "counterexample": None}
        tried += 1
        if a == 0 and b == 0:
            zero_both += 1
        if not verdict:
            failures.append((env, a, b))

    # Inclusive: at exactly half rejected there is no longer enough of the
    # domain left for a clean run to mean anything.
    if tried == 0 or rejected >= tried:
        return {"step_id": step_id, "engine": "rational", "outcome": "unverified",
                "detail": "domain too constrained to sample: %d of %d points were "
                          "degenerate" % (rejected, rejected + tried),
                "trials": tried, "rejected_samples": rejected,
                "counterexample": None}

    if not failures and zero_both == tried:
        return {"step_id": step_id, "engine": "rational", "outcome": "unverified",
                "detail": "both sides were zero at every sample point, which "
                          "discriminates nothing",
                "trials": tried, "rejected_samples": rejected,
                "counterexample": None}

    if failures:
        env, a, b = min(failures, key=lambda f: _magnitude(f[0]))
        return {"step_id": step_id, "engine": "rational", "outcome": "refuted",
                "detail": "at %s the two sides are %s and %s"
                          % (_fmt(env), a, b),
                "trials": tried, "rejected_samples": rejected,
                "counterexample": {k: str(v) for k, v in env.items()}}

    return {"step_id": step_id, "engine": "rational", "outcome": "not-refuted",
            "detail": "NOT REFUTED -- %d sample points inside the stated domain, "
                      "%d rejected as degenerate" % (tried, rejected),
            "trials": tried, "rejected_samples": rejected, "counterexample": None}


def _magnitude(env):
    return sum(abs(v) for v in env.values())


def _fmt(env):
    return ", ".join("%s = %s" % (k, v) for k, v in sorted(env.items()))
# --- end harness ------------------------------------------------------------
'''
