"""Z3, as an escape hatch. Stdlib only in the harness; Z3 only in the script.

**Not a rung in the ladder.** Z3 is not installed by default, and putting it in
the routine path would make a first run demand an install from a skill whose
siblings advertise no dependencies. It is also a poor match for the corpus: the
quantified claims in ML papers are asymptotic ($\\forall \\epsilon > 0\\ \\exists N$),
which Z3 cannot decide either.

Route a *specific* step here when it is a concrete inequality over reals or
integers with explicit bounds — the shape Z3 is genuinely strong on, and the only
engine that can **confirm** an inequality rather than merely fail to refute it.

The method is assertion of the negation:

- `unsat` — no counterexample exists in the stated domain, so the claim holds
  there. This confirms.
- `sat` — Z3 produced a counterexample. Reported with the model, which is a
  concrete point a reader can substitute back into the paper.
- `unknown` — Z3 gave up. `UNVERIFIED`, never a refutation.

Domain assumptions are **mandatory** and are asserted before the negation. A
counterexample outside the domain the paper meant is the same fabricated finding
the rational engine's sampling rules exist to prevent, and here it is prevented by
constraining the solver rather than the sampler.
"""

HARNESS = r'''
# --- z3 harness (inlined; runs only inside the generated script) ------------
import z3


class Untranslatable(Exception):
    """Raised by build() when the step cannot be faithfully modelled."""


#: Domain hints from the ledger, as constraints on a declared variable.
def constrain(solver, var, domain):
    """Assert what the paper says about `var`. Unknown domains constrain nothing.

    A symbol with no stated domain is left free -- and the composer refuses to
    turn a refutation involving one into a finding, exactly as it does for the
    sampling engine.
    """
    if domain in ("positive", "positive-definite"):
        solver.add(var > 0)
    elif domain == "negative":
        solver.add(var < 0)
    elif domain == "nonnegative":
        solver.add(var >= 0)
    elif domain == "unit-interval":
        solver.add(var >= 0, var <= 1)
    elif domain == "unit-interval-half-open":
        solver.add(var >= 0, var < 1)
    elif domain == "open-unit-interval":
        solver.add(var > 0, var < 1)
    elif domain == "natural":
        solver.add(var >= 1)
    elif domain == "probability-distribution":
        solver.add(var >= 0, var <= 1)


def check(claim, variables, domains, step_id, timeout_ms=8000):
    """Assert the negation of `claim` under the stated domains.

    `claim` is a z3 boolean expression; `variables` maps names to z3 constants.
    """
    solver = z3.Solver()
    solver.set("timeout", timeout_ms)
    for name, var in variables.items():
        constrain(solver, var, domains.get(name))

    domain_note = ", ".join("%s: %s" % (n, domains.get(n) or "not stated")
                            for n in sorted(variables))

    # A symbol with no stated domain leaves this solver free to pick anything --
    # including the point where the expression is undefined -- and the answer
    # comes back as a counterexample. The composer refuses to turn that into a
    # finding, but an engine that has to be saved downstream is one gate away
    # from a fabricated CRITICAL. It declines here as well: sampling engines have
    # always done so, and this one should not be the exception.
    unstated = sorted(n for n in variables if not domains.get(n))
    if unstated:
        return {"step_id": step_id, "engine": "smt", "outcome": "unverified",
                "detail": "no domain is stated for %s, so no point is known to "
                          "be admissible and nothing is concluded either way. "
                          "Supply them with --symbols."
                          % ", ".join("$%s$" % n for n in unstated),
                "counterexample": None}
    solver.add(z3.Not(claim))
    result = solver.check()

    if result == z3.unsat:
        return {"step_id": step_id, "engine": "smt", "outcome": "confirmed",
                "detail": "no counterexample exists under the stated domains "
                          "(%s)" % domain_note,
                "counterexample": None}
    if result == z3.sat:
        model = solver.model()
        # Every *constant* in the model, not only the declared ones. Z3 also
        # carries its interpretation of partial functions -- `/0 = [(1, 1) ->
        # 1, else -> 0]` for division -- and a finding that prints that reads as
        # a parser artifact, which costs the reader's trust in the finding
        # itself. Those are declarations of arity > 0, so they drop out here
        # while genuine constants stay.
        #
        # Restricting the point to `variables` was the earlier rule, and it was
        # wrong for a reason only a real translation showed: a translator that
        # introduces an auxiliary (a second gradient entry, a named square root)
        # produces a counterexample whose printed coordinates are incomplete, so
        # the reader cannot reproduce it. An unreproducible counterexample is
        # worth no more than none at all.
        point = {n: str(model[var]) for n, var in sorted(variables.items())
                 if model[var] is not None}
        declared = set(str(v) for v in variables.values())
        extra = {}
        for decl in model.decls():
            if decl.arity() or str(decl) in declared:
                continue
            extra[str(decl)] = str(model[decl])
        shown = ", ".join("%s = %s" % kv for kv in sorted(point.items()))
        if extra:
            shown += "; auxiliaries introduced by the translation: %s" % (
                ", ".join("%s = %s" % kv for kv in sorted(extra.items())))
        return {"step_id": step_id, "engine": "smt", "outcome": "refuted",
                "detail": "counterexample inside the stated domains (%s): %s"
                          % (domain_note, shown),
                "counterexample": point, "auxiliaries": extra}
    return {"step_id": step_id, "engine": "smt", "outcome": "unverified",
            "detail": "Z3 returned unknown (%s); no conclusion is drawn"
                      % solver.reason_unknown(),
            "counterexample": None}
# --- end harness ------------------------------------------------------------
'''
