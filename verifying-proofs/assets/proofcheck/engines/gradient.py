"""Derivative claims, by central finite differences. Stdlib only.

For the claims ML papers actually make about gradients, Jacobians and update
rules. It can refute a stated derivative; it can never confirm one.

**No JAX.** Central differences at 50-digit `decimal` precision do the same job
for the scalar and small-vector expressions that appear in papers, with zero
install and no tracing-failure mode that returns `UNVERIFIED` instead of an
answer. Add JAX only if this engine is measured failing on real cases.

The rule that makes it usable is the **Richardson order-of-accuracy check**. A
central difference has error $O(h^2)$, so halving $h$ should quarter the error.
If the observed discrepancy does not shrink at that rate, the disagreement is
numerical — cancellation, an ill-conditioned point, a kink — and **not**
mathematical. Reporting those as refutations would make this the noisiest engine
in the set instead of a usable one.
"""

HARNESS = r'''
# --- finite-difference harness (inlined; stdlib only) ----------------------
from decimal import Decimal, getcontext

getcontext().prec = 50


class Untranslatable(Exception):
    """Raised by build() when the step cannot be faithfully modelled."""


#: Step sizes, each half the last, so Richardson has a sequence to work with.
_STEPS = (Decimal("1e-6"), Decimal("5e-7"), Decimal("2.5e-7"))

#: A ratio near 4 means the error is shrinking like h^2, as it should.
_ORDER_LO, _ORDER_HI = Decimal("2.0"), Decimal("8.0")

#: Below this the claim and the difference agree to the precision available.
_TOL = Decimal("1e-12")


def _central(f, point, var, h):
    up = dict(point)
    dn = dict(point)
    up[var] = point[var] + h
    dn[var] = point[var] - h
    return (f(up) - f(dn)) / (2 * h)


def check(f, claimed, point, var, step_id, engine="gradient"):
    """Is `claimed` the derivative of `f` with respect to `var` at `point`?

    `f` and `claimed` take a dict of Decimals and return a Decimal.
    """
    point = {k: Decimal(str(v)) for k, v in point.items()}
    try:
        target = Decimal(str(claimed(point)))
        approx = [_central(f, point, var, h) for h in _STEPS]
    except Untranslatable as exc:
        return {"step_id": step_id, "engine": engine, "outcome": "untranslatable",
                "detail": str(exc), "counterexample": None}
    except (ZeroDivisionError, ArithmeticError, ValueError, OverflowError) as exc:
        return {"step_id": step_id, "engine": engine, "outcome": "unverified",
                "detail": "the expression could not be evaluated near the test "
                          "point: %s" % exc, "counterexample": None}

    errs = [abs(a - target) for a in approx]
    scale = max(abs(target), Decimal(1))
    if errs[-1] / scale < _TOL:
        return {"step_id": step_id, "engine": engine, "outcome": "not-refuted",
                "detail": "NOT REFUTED -- the central difference agrees with the "
                          "stated derivative to %s relative at h=%s"
                          % (_TOL, _STEPS[-1]),
                "counterexample": None}

    # Richardson: with a correct derivative the residual is O(h^2), so halving h
    # should quarter it. A residual that stays put is a genuine disagreement; one
    # that shrinks at the wrong rate is numerical noise, not mathematics.
    ratios = []
    for a, b in zip(errs, errs[1:]):
        if b == 0:
            ratios.append(None)
        else:
            ratios.append(a / b)
    converging = [r for r in ratios if r is not None
                  and _ORDER_LO <= r <= _ORDER_HI]
    if converging:
        return {"step_id": step_id, "engine": engine, "outcome": "unverified",
                "detail": "the residual shrinks like h^2 (ratios %s), so the "
                          "discrepancy is numerical rather than mathematical"
                          % ", ".join("%.2f" % float(r) for r in ratios
                                      if r is not None),
                "counterexample": None}

    stable = all(r is not None and r < _ORDER_LO for r in ratios)
    if not stable:
        return {"step_id": step_id, "engine": engine, "outcome": "unverified",
                "detail": "the finite-difference estimate did not settle "
                          "(residual ratios %s); no conclusion is drawn"
                          % ", ".join("%.2f" % float(r) if r is not None else "inf"
                                      for r in ratios),
                "counterexample": None}

    return {"step_id": step_id, "engine": engine, "outcome": "refuted",
            "detail": "at %s the stated derivative is %s but the central "
                      "difference converges to %s, and the gap does not shrink "
                      "with h"
                      % (", ".join("%s = %s" % kv for kv in sorted(point.items())),
                         target, approx[-1]),
            "counterexample": {k: str(v) for k, v in point.items()}}
# --- end harness ------------------------------------------------------------
'''
