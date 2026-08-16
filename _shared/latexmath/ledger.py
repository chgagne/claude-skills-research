"""Step-ledger assembly. Stdlib only. The interchange format both skills read.

Flat entity lists with stable ids, cross-linked. Hierarchical would force the
explainer (which wants per-claim subtrees) and the verifier (which wants a flat
step stream) into different traversals of the same data.

Two properties are worth more than the rest of the schema put together:

- **`coverage` is not bookkeeping.** The histogram heads every report and is
  frequently the finding: *of 41 inference steps in the proof of Theorem 2, six
  were mechanically checkable*. A tool that hides how little it checked is
  worse than one that checks nothing.
- **`content_hash` is identity.** An explanation produced from one version of a
  step must be refused, not silently reattached, when the step changes. The hash
  ignores whitespace and notices tokens, which is exactly the distinction between
  reformatting a proof and editing it.
"""
import hashlib
import json
import os
import re

from scholarly import latex as _slatex

from . import chains as _chains
from . import environments as _env
from . import refs as _refs
from . import segment as _seg
from . import sideconds as _sc
from . import symbols as _sym
from .macros import MacroTable
from .tokenize import DISPLAY_ENVS, blank_comments, find_env_spans
from .tokenize import balanced as _balanced

SCHEMA = "latexmath-ledger/1"

#: The closed set of reasons a step cannot be mechanised. A controlled vocabulary
#: is what makes the coverage histogram comparable across papers and the gap
#: ledger in `explaining-derivations` writable in one language.
OPACITY_VOCABULARY = (
    "undefined-operator",
    "unbound-index",
    "expectation-over-unspecified-measure",
    "asymptotic",
    "probabilistic-quantifier",
    "matrix-shape-unknown",
    "references-external-result",
    "natural-language-only",
    "macro-unexpandable",
)

_ASYMPTOTIC = re.compile(r"\\mathcal\s*\{\s*O\s*\}|\\Theta\b|\\Omega\s*\(|"
                         r"(?<![A-Za-z])[Oo]\s*\(|\\text\{poly\}|\\tilde\s*\{?O")
_BARE_EXPECT = re.compile(r"\\(?:mathbb\s*\{\s*E\s*\}|mathbf\s*\{\s*E\s*\}|E)"
                          r"(?!\s*_)(?![A-Za-z])")
_PROB_QUANT = re.compile(r"with\s+probability\s+at\s+least|w\.h\.p|"
                         r"\\Pr\b|\\mathbb\s*\{\s*P\s*\}", re.I)
_OPERATOR = re.compile(r"\\operatorname\*?\s*(?=\{)")

#: Bodies that name a standard quantity rather than an unmodellable operator.
#: `\DeclareMathOperator{\E}{\mathbb{E}}` expands to `\operatorname{\mathbb{E}}`,
#: which is the expectation -- already reported under its own reason -- not an
#: operator nobody has heard of. Measured: 54 spurious reasons on arXiv:1509.01240.
_OPERATOR_ALIASES = re.compile(
    r"^\\?(?:mathbb|mathbf|mathrm|mathcal|text|operatorname)?\s*\{?\s*"
    r"([A-Za-z]{1,3})\s*\}?$")
_STANDARD_ALIASES = frozenset(("E", "P", "V", "Var", "Cov", "Pr", "R", "N", "I"))

#: Operators a checker can model. Anything else named is genuinely opaque.
KNOWN_OPERATORS = frozenset((
    "exp", "log", "ln", "sin", "cos", "tan", "sinh", "cosh", "tanh", "min",
    "max", "inf", "sup", "argmin", "argmax", "arg min", "arg max", "det", "tr",
    "diag", "sign", "abs", "id", "softmax", "relu", "var", "cov", "rank"))


def content_hash(step):
    """Identity of a step: its tokens, not its layout."""
    parts = []
    for field in ("kind", "prose_tex", "math_tex"):
        parts.append(re.sub(r"\s+", " ", str(getattr(step, field, "") or "")).strip())
    for f in getattr(step, "claim_forms", []) or []:
        parts.append("|".join(
            re.sub(r"\s+", " ", str(f.get(k, "") or "")).strip()
            for k in ("form", "lhs_tex", "relation", "rhs_tex")))
    return hashlib.blake2b("\x1f".join(parts).encode("utf-8"),
                           digest_size=8).hexdigest()


def _opacity(step, symbols, unexpanded):
    """Why this step cannot be handed to a checker. Controlled vocabulary only."""
    reasons = []
    tex = (step.math_tex or "") + " " + (step.prose_tex or "")
    if not step.math_tex and step.kind == "prose-move":
        reasons.append("natural-language-only")
    if _ASYMPTOTIC.search(step.math_tex or ""):
        reasons.append("asymptotic")
    if _BARE_EXPECT.search(step.math_tex or ""):
        reasons.append("expectation-over-unspecified-measure")
    if _PROB_QUANT.search(tex):
        reasons.append("probabilistic-quantifier")
    math = step.math_tex or ""
    for m in _OPERATOR.finditer(math):
        body, _ = _balanced(math, m.end())
        if body is None:
            continue
        name = body.strip()
        if name.lower() in KNOWN_OPERATORS:
            continue
        alias = _OPERATOR_ALIASES.match(name)
        if alias and alias.group(1) in _STANDARD_ALIASES:
            continue
        reasons.append("undefined-operator:%s" % name)
    for name in sorted(unexpanded or ()):
        if ("\\" + name) in (step.math_tex or ""):
            reasons.append("macro-unexpandable:%s" % name)
    if step.justification and step.justification.get("cites"):
        reasons.append("references-external-result")
    return sorted(set(reasons))


def _file_map(main_path):
    """Concatenated sources plus (start, end, path) so an offset names a file."""
    text, spans = "", []
    for path in _slatex.tex_sources(main_path):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                body = fh.read()
        except OSError:
            continue
        spans.append((len(text), len(text) + len(body), path))
        text += body + "\n"
    return text, spans


def _locate(spans, offset, root):
    """Which file an offset falls in, and where **in that file**.

    `offset` was the position in the concatenated document, reported under a key
    that sits next to `file` and therefore reads as a position in that file. It
    is not, on any paper built from more than one `.tex`: a reader handed
    "dimfree2.tex at offset 90959" opens a 72888-byte file and finds nothing.
    Measured when an expansion subagent tried to navigate by it and fell back to
    grepping the source.

    **It cannot be turned into a file position, and this says so rather than
    pretending.** Offsets are into the macro-*expanded* concatenation, while the
    file map is of the raw source; `\cX` becoming `\mathcal{X}` shifts every
    position after it. Subtracting the file's start looks right and lands
    thousands of characters away, which was tried and measured. `coordinates`
    names the system so a consumer can tell what it has, and `file` is the file
    the expanded position falls in -- reliable enough to say where to look, not
    to say where to point.
    """
    for a, b, path in spans:
        if a <= offset < b:
            return {"file": os.path.relpath(path, os.path.dirname(root)),
                    "line": None, "offset": offset,
                    "coordinates": "macro-expanded document, not this file"}
    return {"file": None, "line": None, "offset": offset,
            "coordinates": "macro-expanded document"}


def _located(rec, spans, root):
    """Keep the raw span and add the file it falls in."""
    src = rec.get("source") or {}
    if "start" in src:
        rec["source"] = dict(src, **_locate(spans, src["start"], root))
        rec["source"]["start"] = src["start"]
        rec["source"]["end"] = src.get("end")
    return rec


def build_ledger(main_tex, user_domains=None):
    """Parse a document into the interchange ledger both skills consume."""
    root = os.path.abspath(main_tex)
    raw, spans = _file_map(root)
    macros = MacroTable.from_sources(root)
    text, unexpanded = macros.expand(raw)
    scan = blank_comments(text)

    registry = _env.theorem_registry(text)
    claims = _env.dedupe_restatements(_env.extract_claims(text, registry))
    proofs, diagnostics = _env.attach_proofs(claims, text)

    inv = _sym.inventory(text)
    if user_domains:
        inv = _sym.apply_user_domains(inv, user_domains)
    sym_by_name = {s.symbol: s for s in inv}

    equations, eq_by_start = [], {}
    for nm in DISPLAY_ENVS:
        for name in (nm, nm + "*"):
            for sp in find_env_spans(scan, [name], scan=scan):
                eid = "eq/%d" % sp.start
                eq = _chains.parse_display(scan[sp.start:sp.end], eid=eid)
                rec = eq.as_dict()
                rec["source"] = _locate(spans, sp.start, root)
                equations.append(rec)
                eq_by_start[sp.start] = eid
    equations.sort(key=lambda e: e["source"]["offset"])

    claim_by_id = {c.id: c for c in claims}
    steps, captured = [], []
    for pr in proofs:
        body = pr.body_tex
        # Domains as the *enclosing proof* declares them, statement included: a
        # hypothesis is a declaration, and it is the one in scope at the step.
        claim = claim_by_id.get(pr.claim_id)
        scope_start = min(pr.source["start"],
                          claim.source["start"] if claim else pr.source["start"])
        scope = _sym.scope_table(sym_by_name, text, scope_start, pr.source["end"])
        st = _seg.segment_proof(body, macros=macros, proof_id=pr.id,
                                base_offset=pr.source["start"])
        captured.append(_seg.captured_fraction(body, [
            _rebase(s, -pr.source["start"]) for s in st]))
        for s in st:
            local_syms = _sym.resolve_at(sym_by_name, scope, text, s.source["end"])
            s.symbols_used = sorted(
                {t for t in re.findall(r"\\[A-Za-z]+|[A-Za-z]", s.math_tex or "")
                 if t in sym_by_name})
            s.side_conditions = _sc.conditions(s.math_tex or "", local_syms)
            s.assumptions_in_scope = [
                c.id for c in claims
                if c.kind == "assumption" and c.source["end"] <= pr.source["start"]]
            s.quantifiers_in_scope = _quantifiers(s.math_tex or "")
            s.container = _container(eq_by_start, s.source["start"],
                                     s.source["end"])
            reasons = _opacity(s, local_syms, unexpanded)
            if s.checkable != "structural":
                s.checkable = "opaque" if reasons else s.checkable
            s.opacity_reasons = reasons
            s.content_hash = content_hash(s)
            rec = s.as_dict()
            # Carried on the step, not only in the global table, so that anything
            # deciding whether this step may be refuted reads the domain that was
            # in scope where the step was written. Added to the record rather than
            # to `Step`, because `content_hash` must keep meaning "the step's
            # mathematics" and nothing else.
            rec["domains"] = {
                name: {"domain": local_syms[name].domain_hint,
                       "provenance": local_syms[name].domain_provenance}
                for name in s.symbols_used
                if name in local_syms
                and (local_syms[name].domain_hint
                     != sym_by_name[name].domain_hint
                     or local_syms[name].domain_provenance
                     != sym_by_name[name].domain_provenance)}
            rec["source"] = _locate(spans, s.source["start"], root)
            rec["source"]["end"] = s.source["end"]
            steps.append(rec)

    refs = _refs.build_refs(text, claims, proofs)

    led = {
        "schema": SCHEMA,
        "source": {"root": root, "files": [os.path.relpath(p, os.path.dirname(root))
                                           for _, _, p in spans]},
        "macros": [{"name": n, "nargs": d["nargs"], "body": d["body"],
                    "is_math": macros.is_math_macro(n)}
                   for n, d in sorted(macros.defs.items())],
        "macros_unexpandable": sorted(unexpanded),
        "theorem_envs": {k: {"counter": v.counter, "printed": v.printed}
                         for k, v in sorted(registry.items())},
        # Located to a file, like steps already were. A claim's raw span is an
        # offset into the *concatenated* document, and anything handed that span
        # -- an expansion request, a reviewer following a finding -- tries to
        # open a file at a position past its end. Measured on a multi-file
        # monograph, where a claim reported offset 90959 in a 72888-byte file
        # and the reader fell back to grep. Same shape as the step offsets that
        # were proof-local in a global field.
        "claims": [_located(c.as_dict(), spans, root) for c in claims],
        "proofs": [_located(p.as_dict(), spans, root) for p in proofs],
        "steps": steps,
        "equations": equations,
        "refs": refs,
        "symbols": [s.as_dict() for s in inv],
        "diagnostics": list(diagnostics),
    }
    led["coverage"] = _coverage(led, captured)
    led["diagnostics"] = validate(led)
    return led


class _Rebased:
    """A step's span shifted into proof-local coordinates, without touching it.

    `captured_fraction` measures coverage against the proof body, so it needs
    local offsets; everything else needs the document-global ones the segmenter
    recorded. Shifting the steps in place to satisfy the first reader left every
    later reader with local offsets in a global field -- `_locate` then resolved
    them against the file map and reported steps as belonging to whichever file
    happens to contain that offset, which on a multi-file paper is the wrong one.
    """
    __slots__ = ("source",)

    def __init__(self, step, delta):
        self.source = {"start": step.source["start"] + delta,
                       "end": step.source["end"] + delta}


def _rebase(step, delta):
    return _Rebased(step, delta)


def _container(eq_by_start, a, b):
    for start, eid in eq_by_start.items():
        if a <= start < b:
            return eid
    return None


_QUANT = re.compile(r"\\(sum|prod|int|iint|oint|forall|exists|lim)"
                    r"\s*_?\s*\{?\s*(\\?[A-Za-z]+)?")


def _quantifiers(tex):
    out = []
    for m in _QUANT.finditer(tex or ""):
        out.append({"binder": "\\" + m.group(1), "var": m.group(2)})
    return out


def _coverage(led, captured):
    by_kind = {}
    for s in led["steps"]:
        by_kind[s["kind"]] = by_kind.get(s["kind"], 0) + 1
    hist = {}
    for s in led["steps"]:
        for r in s["opacity_reasons"]:
            hist[r] = hist.get(r, 0) + 1
    check = {"candidate": 0, "opaque": 0, "structural": 0}
    for s in led["steps"]:
        check[s["checkable"]] = check.get(s["checkable"], 0) + 1
    return {
        "claims": len(led["claims"]),
        "proofs": len(led["proofs"]),
        "steps": len(led["steps"]),
        "steps_by_kind": by_kind,
        "inference_steps": sum(by_kind.get(k, 0) for k in _seg.INFERENCE_KINDS),
        "checkable_candidates": check["candidate"],
        "opaque": check["opaque"],
        "structural": check["structural"],
        "opacity_histogram": dict(sorted(hist.items(), key=lambda kv: -kv[1])),
        "proof_text_captured_pct": round(
            100.0 * (sum(captured) / len(captured) if captured else 1.0), 1),
        "macros_unexpandable": len(led["macros_unexpandable"]),
        "symbols_with_unknown_domain": sum(
            1 for s in led["symbols"] if s["domain_provenance"] == "unknown"),
    }


def validate(led):
    """Diagnostics about the *ledger*, not about the mathematics.

    A ledger that dropped a third of a proof produces verdicts about a document
    that is not the one in the paper, so `low-text-capture` is an error rather
    than a note.
    """
    out = [d for d in led.get("diagnostics", [])
           if d.get("code") not in ("dangling-ref", "claim-cycle",
                                    "low-text-capture", "macro-unexpandable")]
    for ref in led["refs"]["dangling"]:
        out.append({"code": "dangling-ref", "severity": "warn",
                    "message": "\\%s{%s} in %s resolves to nothing"
                               % (ref["cmd"], ref["label"], ref["from"]),
                    "source": None})
    for cyc in led["refs"]["cycles"]:
        out.append({"code": "claim-cycle", "severity": "error",
                    "message": "circular dependency: " + " -> ".join(cyc),
                    "source": None})
    pct = led["coverage"]["proof_text_captured_pct"]
    if pct < 90.0 and led["coverage"]["proofs"]:
        out.append({"code": "low-text-capture", "severity": "error",
                    "message": "only %.1f%% of proof text was segmented; verdicts "
                               "computed on this ledger describe a different "
                               "document" % pct, "source": None})
    if led["macros_unexpandable"]:
        out.append({"code": "macro-unexpandable", "severity": "warn",
                    "message": "macros left unexpanded: %s"
                               % ", ".join(led["macros_unexpandable"]),
                    "source": None})
    return out


def write(led, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(led, fh, indent=1, sort_keys=False)
    return path


def read(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
