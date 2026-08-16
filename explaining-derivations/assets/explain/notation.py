"""Frozen notation, and collision detection across independently produced
fragments. Stdlib only.

Fragments are produced by separate subagents that never see each other's output.
Four things keep them reading as one document, and this module owns two of them:
a preamble computed **before** dispatch and passed read-only, and a symbol
registry checked **after** every fragment returns.

A collision is never resolved silently. Two expansions that both introduce
`\\tilde{q}` with different meanings produce a `NOTATIONAL` gap and a rename,
because the alternative is a document in which one symbol quietly means two
things — the single most confusing thing a piece of mathematical writing can do,
and precisely what this skill exists to prevent.
"""

import os
import re

_UNKNOWN = "not stated in the paper"

_USEPACKAGE = re.compile(r"^\s*\\usepackage(?:\[[^\]]*\])?\{([^}]*)\}", re.M)

_PREAMBLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "templates", "preamble.tex")


def preamble_packages(path=None):
    """What the frozen preamble loads, read from the preamble itself.

    The macro table holds what the *paper* defines with `\\newcommand`; it says
    nothing about what the paper's macros are built on. A paper using
    `\\usepackage{physics}` writes `\\dd t` in every step of an SDE proof, no
    `\\newcommand` records it, and a fragment that copies the step verbatim
    produces a document that dies on `Undefined control sequence` — after the
    expansion, which is the expensive part, has already been paid for.

    So the request tells the subagent what it may rely on. Read from the file
    rather than hard-coded, because a list that drifts from the preamble is a
    list that lies.
    """
    try:
        with open(path or _PREAMBLE, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return []
    out = []
    for m in _USEPACKAGE.finditer(text):
        for name in m.group(1).split(","):
            name = name.strip()
            if name and name not in out:
                out.append(name)
    return out


def freeze(ledger):
    """The macro table and symbol glossary, computed once and passed read-only."""
    macros = {}
    for m in ledger.get("macros", []):
        if not m.get("is_math"):
            continue          # a cross-reference helper is not notation
        macros[m["name"]] = {"nargs": m.get("nargs", 0), "body": m.get("body", "")}

    symbols = []
    for s in ledger.get("symbols", []):
        quote = ""
        if s.get("domain_evidence"):
            quote = s["domain_evidence"][0].get("quote", "")
        symbols.append({
            "symbol": s["symbol"],
            "normalized": s.get("normalized"),
            "domain": s.get("domain_hint") or _UNKNOWN,
            "domain_provenance": s.get("domain_provenance"),
            "quote": quote,
            "role": s.get("role_hint"),
            "occurrences": s.get("occurrences", 0),
        })
    symbols.sort(key=lambda s: (-s["occurrences"], s["symbol"]))
    return {"macros": macros, "symbols": symbols,
            "preamble_packages": preamble_packages()}


def glossary(notation, used=None):
    """The rows of the notation table for one document.

    Restricted to symbols the expansion actually uses when `used` is given: a
    glossary listing sixty symbols for a four-symbol proof is furniture.
    """
    rows = notation["symbols"]
    if used:
        keep = set(used)
        rows = [s for s in rows if s["symbol"] in keep or s["normalized"] in keep]
    return rows


def collisions(fragments, notation):
    """Symbols two fragments define differently, or that shadow the paper's own.

    Returned as gap rows so they travel with every other finding rather than
    living in a separate error channel nobody reads.
    """
    existing = {s["symbol"] for s in notation["symbols"]}
    seen, out = {}, []
    for frag in fragments:
        rid = frag.get("request_id")
        for intro in frag.get("symbols_introduced") or []:
            sym, why = intro.get("symbol"), (intro.get("why") or "").strip()
            if not sym:
                continue
            if sym in existing:
                out.append(_gap(
                    rid, sym,
                    "%s already denotes something in the paper; the expansion of "
                    "%s reuses it for %r" % (sym, rid, why),
                    "rename the symbol introduced by the expansion"))
                continue
            prior = seen.get(sym)
            if prior is None:
                seen[sym] = (rid, why)
                continue
            if prior[1].lower() != why.lower():
                out.append(_gap(
                    rid, sym,
                    "%s means %r in the expansion of %s and %r in %s"
                    % (sym, prior[1], prior[0], why, rid),
                    "rename one of them, or state the shared meaning once"))
    return out


def _gap(request_id, symbol, what, remedy):
    return {"step_id": None, "claim_id": request_id, "severity": "NOTATIONAL",
            "kind": "symbol-collision",
            "what_is_missing": "%s: %s" % (symbol, what),
            "what_would_close_it": remedy, "quote": ""}


def merge_requested_macros(notation, fragments):
    """Grant requested macros, or report the ones that clash.

    The dispatcher regenerates one preamble for every document rather than
    letting fragments carry their own, so a granted macro is granted everywhere.
    """
    granted, refused = dict(notation["macros"]), []
    for frag in fragments:
        for m in frag.get("macros_requested") or []:
            name, body = m.get("name"), m.get("body")
            if name in granted and granted[name].get("body") != body:
                refused.append(m)
                continue
            granted[name] = {"nargs": m.get("nargs", 0), "body": body,
                             "requested_by": frag.get("request_id"),
                             "why": m.get("why", "")}
    return granted, refused
