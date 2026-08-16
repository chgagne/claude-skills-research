"""Theorem-like environments, proof attachment, and restatement dedupe. Stdlib only.

Three decisions here carry the most weight downstream.

**A hypothesis split is never guessed.** `unsplit` is a supported outcome and the
common one. A guessed split lets a later pass report "hypothesis never used"
about a clause that was never a hypothesis, which is a fabricated finding -- the
one thing this project treats as unrecoverable.

**`\\begin{proof}[Proof of Theorem 2]` binds by its argument, not by adjacency.**
Appendices reorder proofs relative to statements constantly. Adjacency is the
fallback, and it is recorded as such so the report can say which it used.

**A restatement that drops a hypothesis is a finding.** `restatable` puts the
statement in the body and the proof in the appendix, and the appendix copy is
retyped by hand often enough that the two versions diverge.
"""
import difflib
import re

from .tokenize import (Span, blank_comments, find_env_spans, mask, math_spans,
                       strip_labels)

# Venue classes predefine these, so a paper need not declare them and most do not.
_DEFAULT_ENVS = {
    "theorem": "Theorem", "thm": "Theorem", "lemma": "Lemma", "lem": "Lemma",
    "proposition": "Proposition", "prop": "Proposition",
    "corollary": "Corollary", "cor": "Corollary",
    "definition": "Definition", "defn": "Definition", "def": "Definition",
    "assumption": "Assumption", "assum": "Assumption", "asm": "Assumption",
    "claim": "Claim", "fact": "Fact", "remark": "Remark", "rem": "Remark",
    "conjecture": "Conjecture", "example": "Example", "observation": "Observation",
}

# Kinds that assert something a proof can discharge. A proof following a
# definition belongs to whatever claim preceded the definition.
PROVABLE = ("theorem", "lemma", "proposition", "corollary", "claim", "fact",
            "conjecture", "observation")

_NEWTHEOREM = re.compile(
    r"\\newtheorem\*?\s*\{([A-Za-z@*]+)\}\s*(?:\[([A-Za-z@]+)\])?\s*"
    r"\{([^}]*)\}\s*(?:\[([A-Za-z@]+)\])?")
_DECLARETHEOREM = re.compile(
    r"\\declaretheorem\s*(?:\[([^\]]*)\])?\s*\{([A-Za-z@]+)\}")
_LABEL = re.compile(r"\\label\s*\{([^}]*)\}")

_HEDGE = re.compile(
    r"\b(clearly|obviously|evidently|trivially|straightforward(?:ly)?|"
    r"it is easy to see|it is well known|one can easily|readily (?:see|verify)|"
    r"immediate(?:ly)?|of course)\b", re.I)

_INDUCTION = re.compile(r"\b(by|on|using|proceed(?:s|ing)? by|argue by)\s+"
                        r"(strong\s+|structural\s+)?induction\b", re.I)

# An explicit marker settles it, whatever the variable is called.
_BASE_MARKER = re.compile(
    r"\\(?:textbf|textit|emph|paragraph|textsc)\s*\{\s*base\s+case[^}]*\}"
    r"|\bbase\s+case\b|\binitial\s+case\b|\bbase\s+step\b", re.I)

# "induction on the depth $L$", "induction on $n$", "induction over $k$".
_IND_VAR = re.compile(
    r"induction\s+(?:on|over|in)\s+(?:the\s+)?(?:[a-z]+\s+){0,3}?"
    r"\$?\\?([A-Za-z])\b", re.I)

# "When $L=1$", "For $d = 0$", "The case $k=1$", "If $L = 1$".
_BASE_AT = (r"(?:\bwhen\b|\bfor\b|\bif\b|\bthe\s+case\b|\bsuppose\b|\bin\s+case\b|"
            r"\bconsider\b|\btake\b|\bat\b|\bwith\b)"
            r"[^.$]{0,24}\$?\s*\\?%s\s*=\s*(?:0|1|2)\b")

# The induction hypothesis, which is *not* a base case however it is phrased.
_IND_HYP = re.compile(
    r"\b(?:assume|suppose|hypothesis)\b[^.]{0,80}\bholds?\b"
    r"|\binduction\s+hypothesis\b|\binductive\s+hypothesis\b", re.I)
_CASE = re.compile(r"(?:\\textbf|\\textit|\\emph)\s*\{\s*(Case[^}]*)\}"
                   r"|\\paragraph\s*\{\s*(Case[^}]*)\}", re.I)


class ThmEnv:
    __slots__ = ("name", "counter", "printed", "parent")

    def __init__(self, name, counter, printed, parent=None):
        self.name = name
        self.counter = counter
        self.printed = printed
        self.parent = parent

    def __repr__(self):
        return "ThmEnv(%r, counter=%r, printed=%r)" % (
            self.name, self.counter, self.printed)


class Claim:
    __slots__ = ("id", "kind", "env", "label", "number", "title", "statement_tex",
                 "hypotheses", "conclusion", "split_method", "split_confidence",
                 "duplicate_of", "hypotheses_diff", "source")

    def __init__(self, **kw):
        for s in self.__slots__:
            setattr(self, s, kw.get(s))
        self.hypotheses = self.hypotheses or []
        self.hypotheses_diff = self.hypotheses_diff or []

    def as_dict(self):
        return {s: getattr(self, s) for s in self.__slots__}

    def __repr__(self):
        return "Claim(%r, %r)" % (self.id, self.kind)


class Proof:
    __slots__ = ("id", "claim_id", "attachment", "body_tex", "structure", "source")

    def __init__(self, **kw):
        for s in self.__slots__:
            setattr(self, s, kw.get(s))

    def as_dict(self):
        return {s: getattr(self, s) for s in self.__slots__}

    def __repr__(self):
        return "Proof(%r -> %r, %s)" % (self.id, self.claim_id, self.attachment)


def theorem_registry(text):
    """Declared theorem environments, plus the ones venue classes predefine."""
    reg = {}
    for name, printed in _DEFAULT_ENVS.items():
        reg[name] = ThmEnv(name, name, printed)
    scan = blank_comments(text or "")
    for m in _NEWTHEOREM.finditer(scan):
        name, shared, printed, parent = m.groups()
        reg[name] = ThmEnv(name, shared or name, printed.strip(), parent)
    for m in _DECLARETHEOREM.finditer(scan):
        opts, name = m.group(1) or "", m.group(2)
        nm = re.search(r"name\s*=\s*([^,\]]+)", opts)
        sh = re.search(r"(?:numberlike|sibling)\s*=\s*([A-Za-z@]+)", opts)
        reg[name] = ThmEnv(name, (sh.group(1) if sh else name),
                           (nm.group(1).strip() if nm else name.capitalize()))
    return reg


def _outside_math(text):
    """`text` with every math body blanked, so prose patterns cannot match inside it."""
    return mask(text, math_spans(text))


def _sentences(text):
    """Split prose into sentences without breaking inside mathematics."""
    blind = _outside_math(text)
    out, start = [], 0
    for m in re.finditer(r"[.;]\s+|\.\s*$", blind):
        out.append(text[start:m.end()])
        start = m.end()
    tail = text[start:]
    if tail.strip():
        out.append(tail)
    return [s for s in out if s.strip()]


_HYP_LEAD = re.compile(r"^\s*(let|suppose|assume|consider|fix|given|define)\b", re.I)


def _split_statement(stmt):
    """(hypotheses, conclusion, method, confidence). Never guesses."""
    blind = _outside_math(stmt)

    m = re.search(r"(?:^|[.;]\s+|,\s*)[Tt]hen\b", blind)
    if m:
        head, tail = stmt[:m.start()], stmt[m.end():]
        hyps = [s.strip() for s in _sentences(head) if s.strip()]
        if hyps and any(_HYP_LEAD.match(h) for h in hyps):
            method = "if-then" if re.match(r"^\s*[Ii]f\b", blind) else "then"
            return hyps, tail.strip(), method, "high"
        if re.match(r"^\s*[Ii]f\b", blind):
            return [head.strip().rstrip(",")], tail.strip(), "if-then", "high"

    m = re.match(r"\s*[Ii]f\b(.*?),\s*then\b(.*)$", blind, re.S)
    if m:
        return ([stmt[m.start(1):m.end(1)].strip()],
                stmt[m.start(2):m.end(2)].strip(), "if-then", "high")

    return [], stmt.strip(), "unsplit", "high"


def _claim_id(label, kind, ordinal):
    return "claim/%s" % (label if label else "%s%d" % (kind[:3], ordinal))


def extract_claims(text, registry):
    """Every theorem-like unit in document order, numbered by its counter."""
    scan = blank_comments(text or "")
    names = sorted(set(list(registry) + [n + "*" for n in registry]
                       + ["restatable"]))
    spans = []
    for nm in names:
        spans.extend(find_env_spans(scan, [nm], scan=scan))
    spans.sort(key=lambda s: s.start)

    counters, out, ordinal = {}, [], 0
    for sp in spans:
        env, title, body = sp.name, sp.arg, sp.body
        if env == "restatable":
            # \begin{restatable}[Title]{thm}{MacroName}
            m = re.match(r"\s*\{([A-Za-z@]+)\}\s*(?:\{[A-Za-z@]*\})?", body)
            if not m:
                continue
            env, body = m.group(1), body[m.end():]
        base = env.rstrip("*")
        ent = registry.get(base)
        if ent is None:
            continue
        starred = env.endswith("*")
        number = None
        if not starred:
            counters[ent.counter] = counters.get(ent.counter, 0) + 1
            number = str(counters[ent.counter])
        lab = _LABEL.search(body)
        label = lab.group(1) if lab else None
        stmt = strip_labels(body).strip()
        ordinal += 1
        hyps, concl, method, conf = _split_statement(stmt)
        kind = ent.printed.lower()
        out.append(Claim(
            id=_claim_id(label, kind, ordinal), kind=kind, env=env, label=label,
            number=number, title=title, statement_tex=stmt, hypotheses=hyps,
            conclusion=concl, split_method=method, split_confidence=conf,
            duplicate_of=None, hypotheses_diff=[],
            source={"start": sp.start, "end": sp.end}))
    return out


_PROOF_OF = re.compile(
    r"proof\s+of\s+(?:the\s+)?([A-Za-z]+)?\s*~?\s*"
    r"(?:\\(?:eq|c|C|auto)?ref\s*\{([^}]*)\}|([0-9]+(?:\.[0-9]+)*))", re.I)


def _base_case(body, is_induction):
    """Locate an induction's base case without assuming what the variable is called.

    Measured false alarm: all four induction proofs in arXiv:1806.07572 were
    reported as having no base case. They induct on network depth $L$ and open
    with "When $L=1$, ...", which a detector hard-coding $n$ cannot see. Four
    fabricated CRITICALs on a correct paper.

    So the variable is read out of the induction phrase first, and when it cannot
    be read the verdict is `unknown` -- a thing for a human to check -- rather
    than an accusation. Only `not-found` escalates, and only when there was a
    named variable to look for.
    """
    if not is_induction:
        return {"verdict": "n/a", "offset": None, "variable": None,
                "evidence": None}

    prose = _outside_math(body)
    m = _BASE_MARKER.search(prose)
    if m:
        return {"verdict": "found", "offset": m.start(), "variable": None,
                "evidence": "explicit-marker"}

    # Math is masked in `prose`, so match the raw body for `$L = 1$` forms.
    var = None
    vm = _IND_VAR.search(prose) or _IND_VAR.search(body)
    if vm:
        var = vm.group(1)

    candidates = [var] if var else []
    for v in candidates:
        m = re.search(_BASE_AT % re.escape(v), body, re.I | re.S)
        if m:
            return {"verdict": "found", "offset": m.start(), "variable": var,
                    "evidence": "base-value-of-induction-variable"}

    # No variable named, or named but no base value found: look for any
    # "When $X = 0/1/2$" opener that is not the induction hypothesis.
    generic = re.search(_BASE_AT % r"([A-Za-z])", body, re.I | re.S)
    if generic and not _IND_HYP.match(generic.group(0)):
        return {"verdict": "found", "offset": generic.start(),
                "variable": var or generic.group(1), "evidence": "base-value"}

    if var is None:
        return {"verdict": "unknown", "offset": None, "variable": None,
                "evidence": "induction variable not named"}
    return {"verdict": "not-found", "offset": None, "variable": var,
            "evidence": "no base value of $%s$ found" % var}


def _structure(body):
    ind = _INDUCTION.search(_outside_math(body))
    base = _base_case(body, bool(ind))
    cases = [(m.group(1) or m.group(2)).strip() for m in _CASE.finditer(body)]
    return {
        "is_induction": bool(ind),
        "base_case": base,
        "base_case_offset": base["offset"],
        "cases": cases,
        "qed_present": bool(re.search(r"\\qed(?:here|symbol)?\b|\\square\b", body)),
        "hedges": sorted({m.group(0).lower()
                          for m in _HEDGE.finditer(_outside_math(body))}),
    }


def attach_proofs(claims, text):
    """(proofs, diagnostics). Explicit argument beats adjacency; orphans are reported."""
    scan = blank_comments(text or "")
    spans = find_env_spans(scan, ["proof"], scan=scan)
    spans += find_env_spans(scan, ["proof*"], scan=scan)
    spans.sort(key=lambda s: s.start)

    by_label = {c.label: c for c in claims if c.label}
    by_num = {}
    seen_pids = {}
    for c in claims:
        if c.number:
            by_num[(c.kind, c.number)] = c

    proofs, diags = [], []
    for i, sp in enumerate(spans):
        claim, how = None, None
        if sp.arg:
            m = _PROOF_OF.search(sp.arg)
            if m:
                printed, ref, num = m.group(1), m.group(2), m.group(3)
                if ref and ref in by_label:
                    claim, how = by_label[ref], "explicit-arg"
                elif num:
                    key = ((printed or "").lower(), num)
                    if key in by_num:
                        claim, how = by_num[key], "explicit-arg"
                    else:
                        hits = [c for (k, n), c in by_num.items() if n == num]
                        if len(hits) == 1:
                            claim, how = hits[0], "explicit-arg"
        if claim is None:
            prior = [c for c in claims
                     if c.source["end"] <= sp.start and c.kind in PROVABLE]
            if prior:
                claim = max(prior, key=lambda c: c.source["end"])
                how = "adjacent"
        if claim is None:
            how = "none"
            diags.append({"code": "orphan-proof", "severity": "warn",
                          "message": "proof at offset %d has no claim to attach to"
                                     % sp.start,
                          "source": {"start": sp.start, "end": sp.end}})
        # A claim may be proved more than once -- a second proof, a proof of the
        # converse, a proof deferred to an appendix and restated. Naming the
        # proof after the claim alone gave those the same id, and therefore gave
        # their steps the same ids: measured on a 2692-step monograph, 158 step
        # ids collided, with 24 on another and 16 on a third that had been in the
        # corpus from the beginning.
        #
        # This is not cosmetic. Everything downstream keys on the step id --
        # verdicts, generated check-script filenames, the fragment binding in
        # `explaining-derivations` -- and a dict keyed by id silently keeps one
        # of the two. A verdict computed on one proof was reported against a step
        # in another.
        stem = claim.id.split("/", 1)[1] if claim else "orphan%d" % i
        pid = "proof/%s" % stem
        if pid in seen_pids:
            seen_pids[pid] += 1
            pid = "proof/%s#%d" % (stem, seen_pids["proof/%s" % stem])
        else:
            seen_pids[pid] = 1
        proofs.append(Proof(id=pid, claim_id=(claim.id if claim else None),
                            attachment=how, body_tex=sp.body,
                            structure=_structure(sp.body),
                            source={"start": sp.inner_start, "end": sp.inner_end}))
    return proofs, diags


def _norm(s):
    s = re.sub(r"\\label\s*\{[^}]*\}", " ", s or "")
    s = re.sub(r"\\(?:,|;|!|quad|qquad)", " ", s)
    return re.sub(r"\s+", " ", s).strip().lower()


_RESTATED = re.compile(r"restat|recall(?:ed|ing)?\s+(?:from|that)|repeated\s+from",
                       re.I)


#: Label suffixes authors use to mark an appendix copy of a body statement.
_RESTATE_SUFFIX = re.compile(r"[_-](?:restated|restatement|appendix|app|full)$",
                             re.I)


def _explicit_restatement(claim):
    """Did the author say this is a restatement?"""
    if (claim.env or "").startswith("restatable"):
        return True
    return bool(_RESTATED.search(claim.title or ""))


def _label_stem(claim):
    """The body label an appendix copy names, by convention, or None.

    `thm:foo_restated` names `thm:foo`. This is the author speaking, and it beats
    any text heuristic: measured on a real draft where
    `thm:generalization_radius_scaling_restated` was matched by similarity to
    `thm:memorization_radius_scaling` -- a sibling scaling law with near-identical
    shape that happened to come first.
    """
    label = claim.label or ""
    stem = _RESTATE_SUFFIX.sub("", label)
    return stem if stem and stem != label else None


def dedupe_restatements(claims, threshold=0.70, conclusion_threshold=0.90):
    """Link a restatement to its original and diff the hypotheses.

    A restatement is only ever linked to an *earlier* claim of the same kind, so
    the body version stays authoritative and the appendix copy is the one that
    carries `duplicate_of`.

    **A restatement must reach the same conclusion.** Measured on arXiv:1405.4980
    (Bubeck's monograph), where four pairs of genuinely *different* theorems were
    linked and their differing hypotheses reported as drift: gradient descent
    versus *projected* gradient descent, Nesterov for convex versus for strongly
    convex. Any family of results reads as near-identical text with differing
    hypotheses -- which is exactly the shape of real drift, except that a sibling
    theorem also states a different bound. Comparing conclusions separates them;
    similarity alone cannot.

    The **conclusion match is the primary signal**, not an extra gate on top of
    text similarity: a restatement that drops a hypothesis necessarily has
    *lower* whole-statement similarity, precisely because it dropped the text
    that is the finding. So the statement threshold stays loose and the
    conclusion threshold is what decides.

    An explicit marker (`restatable`, or a title saying so) overrides both,
    because then the author has told us.
    """
    for i, c in enumerate(claims):
        if c.duplicate_of:
            continue
        explicit = _explicit_restatement(c)

        # The author's own naming convention wins outright.
        stem = _label_stem(c)
        if stem:
            target = next((p for p in claims[:i] if p.label == stem), None)
            if target is not None:
                c.duplicate_of = target.id
                if "unsplit" not in (target.split_method, c.split_method):
                    a = {_norm(h) for h in target.hypotheses}
                    b = {_norm(h) for h in c.hypotheses}
                    c.hypotheses_diff = (["-" + h for h in sorted(a - b)]
                                         + ["+" + h for h in sorted(b - a)])
                continue

        best, score = None, 0.0
        for prev in claims[:i]:
            if prev.kind != c.kind or prev.duplicate_of:
                continue
            r = difflib.SequenceMatcher(
                None, _norm(prev.statement_tex), _norm(c.statement_tex)).ratio()
            if r > score:
                best, score = prev, r
        if best is None:
            continue
        if not explicit:
            if score < threshold:
                continue
            concl = difflib.SequenceMatcher(
                None, _norm(best.conclusion), _norm(c.conclusion)).ratio()
            if concl < conclusion_threshold:
                continue          # a sibling theorem, not a restatement
        c.duplicate_of = best.id
        # An empty hypothesis list from `unsplit` means *not parsed*, not *none
        # stated*. Diffing against it reports every hypothesis of the restatement
        # as newly added -- which is the same error as guessing a split, and this
        # module refuses to guess a split everywhere else. Measured on a real
        # draft, where it produced a MAJOR on a theorem whose body statement
        # simply had no "Let ... Then ..." shape.
        if "unsplit" in (best.split_method, c.split_method):
            continue
        a = {_norm(h) for h in best.hypotheses}
        b = {_norm(h) for h in c.hypotheses}
        c.hypotheses_diff = (
            ["-" + h for h in sorted(a - b)] + ["+" + h for h in sorted(b - a)])
    return claims
