"""Engine registry: name -> the harness inlined into a generated check script.

Kept in one place so `stubs.py` cannot silently fall back to the wrong harness
when an engine is requested. A script emitted with the rational harness but asked
to model a derivative would report `untranslatable` forever, and the run would
look like a coverage problem rather than a wiring bug.
"""
from . import gradient, rational, smt, symbolic

#: Every engine that emits a check script, and the harness it inlines.
HARNESSES = {
    "rational": rational.HARNESS,
    "symbolic": symbolic.HARNESS,
    "gradient": gradient.HARNESS,
    "smt": smt.HARNESS,
}

#: The external checker each needs, if any. Absent means stdlib-only.
CHECKERS = {"symbolic": "sympy", "smt": "z3"}

#: Engines routed to by default. `sideconds` needs no script at all, and `named`
#: is template matching over the ledger rather than a generated script.
SCRIPTED = ("rational", "symbolic", "gradient", "smt")


def harness_for(engine):
    """The harness source for `engine`, or None if it emits no script."""
    return HARNESSES.get(engine)
