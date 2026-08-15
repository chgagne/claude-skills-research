"""Validation of one per-theorem subagent's returned fragment. Stdlib only.

The dispatcher owns all I/O; a subagent returns one JSON object and writes
nothing. That is what makes assembly deterministic and notation collisions
detectable — and it is what makes this module the place where an expansion is
kept honest.

Two rules carry almost all of the weight.

**`licensed_by` is a closed set of four shapes.** A free-text justification field
is exactly the affordance that lets a plausible-sounding reason through for a step
nobody checked, and the `expert-shorthand` register actively invites one. The four
shapes are: a labelled equation in this paper, a cited result with its bib key, an
entry from the move vocabulary, or the literal `not-established`. That last one is
a first-class answer, not a failure.

**The expander may not write a mechanical verdict it did not receive.** With no
checker results in hand, every `checked` cell reads `not run`. A fragment claiming
a verdict the dispatcher never passed in is refused, because inventing evidence
inverts the purpose of the skill.

A fragment is a *body*, not a document: `\\usepackage`, `\\documentclass`,
`\\newcommand` and friends are refused. `macros_requested` is the sanctioned
channel, and the dispatcher regenerates one preamble for every document rather
than letting fragments drift apart.
"""
import re

CONTRACT = "explain-fragment/1"
REQUEST_CONTRACT = "explain-request/1"

#: The only shapes a justification may take.
LICENCE_KINDS = ("equation", "citation", "named-result", "not-established")

#: Gap severities. `BLOCKING` is the thesis in operation: a step nobody could make
#: explicit is a hole in the proof until someone supplies what closes it.
GAP_SEVERITIES = ("BLOCKING", "SUBSTANTIVE", "NOTATIONAL", "COSMETIC")

#: Tokens that make a fragment a document rather than a body.
_FORBIDDEN = (r"\documentclass", r"\usepackage", r"\begin{document}",
              r"\end{document}", r"\newcommand", r"\renewcommand",
              r"\providecommand", r"\def", r"\DeclareMathOperator",
              r"\input", r"\include", r"\bibliography")

#: The controlled move vocabulary. An off-vocabulary move is flagged, not dropped:
#: losing the row would lose the explanation, and the point is to notice drift.
MOVES = (
    "substitute-definition", "algebraic-rearrangement", "expand-product",
    "factor", "collect-terms", "cancel-common-factor", "add-and-subtract",
    "multiply-by-one", "change-of-variable", "reindex-sum", "split-sum",
    "swap-sum-order", "linearity-of-expectation", "linearity-of-integral",
    "apply-named-inequality", "apply-monotone-function", "take-limits",
    "interchange-limit-and-sum", "interchange-limit-and-integral",
    "differentiate-both-sides", "integrate-both-sides", "apply-hypothesis",
    "apply-previous-result", "case-split", "induction-hypothesis",
    "bound-term-above", "bound-term-below", "triangle-inequality-split",
    "conditioning", "tower-property", "union-bound", "definition-unfolding",
)


class Result:
    __slots__ = ("ok", "rows", "gaps", "tex_fragment", "macros_requested",
                 "symbols_introduced", "problems", "warnings", "request_id")

    def __init__(self, **kw):
        for s in self.__slots__:
            setattr(self, s, kw.get(s))
        self.rows = self.rows or []
        self.gaps = self.gaps or []
        self.problems = self.problems or []
        self.warnings = self.warnings or []
        self.macros_requested = self.macros_requested or []
        self.symbols_introduced = self.symbols_introduced or []

    def __repr__(self):
        return "Result(ok=%s, %d rows, %d gaps, %d problems)" % (
            self.ok, len(self.rows), len(self.gaps), len(self.problems))


def _move_base(move):
    return (move or "").split(":", 1)[0]


def validate(fragment, steps, verdicts, level="grad-ml"):
    """Check a returned fragment against the ledger and the verdicts we passed in.

    Returns a `Result`. `ok` false means the fragment must not be assembled;
    `warnings` are things worth reporting that do not invalidate it.
    """
    problems, warnings = [], []
    verdicts = verdicts or {}

    if fragment.get("contract") != CONTRACT:
        problems.append("contract is %r, expected %r"
                        % (fragment.get("contract"), CONTRACT))

    tex = fragment.get("tex_fragment") or ""
    for tok in _FORBIDDEN:
        if tok in tex:
            problems.append(
                "fragment contains %s: a fragment is a body, not a document. "
                "Use macros_requested to ask for a new macro." % tok)

    rows = []
    for i, row in enumerate(fragment.get("rows") or []):
        sid = row.get("step_id")
        step = steps.get(sid)
        if step is None:
            problems.append("row %d names step %r, which is not in the ledger"
                            % (i, sid))
            continue
        if not row.get("content_hash"):
            problems.append("row %d for %s carries no content hash" % (i, sid))
            continue
        if row["content_hash"] != step.get("content_hash"):
            problems.append(
                "row %d for %s has a stale content hash (%s, ledger says %s): the "
                "step changed after this explanation was written"
                % (i, sid, row["content_hash"], step.get("content_hash")))
            continue

        lb = row.get("licensed_by")
        if not isinstance(lb, dict) or lb.get("kind") not in LICENCE_KINDS:
            problems.append(
                "row %d for %s: licensed_by must be one of %s, not %r. Free text "
                "here is how an unchecked step acquires a plausible reason."
                % (i, sid, ", ".join(LICENCE_KINDS), lb))
            continue

        row = dict(row)
        row["checked"] = _reconcile_verdict(sid, row.get("checked"), verdicts,
                                            problems)
        if _move_base(row.get("move")) not in MOVES:
            warnings.append(
                "row %d for %s uses the off-vocabulary move %r; kept, but add it "
                "to reference/move-vocabulary.md or rename it"
                % (i, sid, row.get("move")))
        if not (row.get("breaks_if") or "").strip():
            warnings.append("row %d for %s says nothing about what would break it"
                            % (i, sid))
        rows.append(row)

    gaps = []
    for i, gap in enumerate(fragment.get("gaps") or []):
        sev = gap.get("severity")
        if sev not in GAP_SEVERITIES:
            problems.append("gap %d has severity %r, expected one of %s"
                            % (i, sev, ", ".join(GAP_SEVERITIES)))
            continue
        if sev in ("BLOCKING", "SUBSTANTIVE") and not (
                gap.get("what_would_close_it") or "").strip():
            problems.append(
                "gap %d is %s but does not say what would close it; a gap that "
                "names no remedy cannot be acted on" % (i, sev))
            continue
        gaps.append(gap)

    macros = []
    for m in fragment.get("macros_requested") or []:
        if not m.get("name") or not m.get("body"):
            warnings.append("a requested macro is missing a name or a body")
            continue
        macros.append(m)

    return Result(ok=not problems, rows=rows, gaps=gaps, tex_fragment=tex,
                  macros_requested=macros,
                  symbols_introduced=fragment.get("symbols_introduced") or [],
                  problems=problems, warnings=warnings,
                  request_id=fragment.get("request_id"))


def _reconcile_verdict(step_id, claimed, verdicts, problems):
    """The expander reports what the checker said, or that it did not run."""
    actual = verdicts.get(step_id)
    if actual is None:
        if claimed and claimed.get("verdict") not in (None, "", "not run"):
            problems.append(
                "row for %s reports the verdict %r, but no checker result was "
                "supplied for that step. The expander may not write a mechanical "
                "verdict it did not receive."
                % (step_id, claimed.get("verdict")))
        return {"verdict": "not run", "engine": None, "script": None}
    if claimed and claimed.get("verdict") not in (None, "", actual.get("verdict")):
        problems.append(
            "row for %s reports the verdict %r, but the checker said %r"
            % (step_id, claimed.get("verdict"), actual.get("verdict")))
    return {"verdict": actual.get("verdict"), "engine": actual.get("engine"),
            "script": actual.get("script")}


def request(claim, proof, steps, notation, context, verdicts, level="grad-ml",
            budget=None):
    """The object handed to a per-theorem subagent."""
    return {
        "request_id": claim["id"], "contract": REQUEST_CONTRACT, "level": level,
        "claim": claim, "proof": proof, "steps": steps,
        "notation": dict(notation, forbidden_new_macros=True),
        "context": context, "verdicts": verdicts or {},
        "move_vocabulary": list(MOVES),
        "budget": budget or {"max_tool_calls": 40, "wall_clock_s": 600},
        "output_contract": CONTRACT,
    }
