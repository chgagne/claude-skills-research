"""Build a ledger from sources, or load one that was built earlier. Stdlib only.

Splitting this out means the report and the engines never touch the filesystem
layout, and `--ledger-only` is a one-line CLI path rather than a special case.
"""
import json
import os
import sys

sys.path.insert(0, os.path.expanduser("~/.claude/skills/_shared"))

from latexmath import ledger as _ledger  # noqa: E402


def build(main_tex, symbols_path=None):
    """Ledger for a document, with an optional user-supplied symbol table."""
    return _ledger.build_ledger(main_tex, user_domains=load_symbols(symbols_path))


def load(path):
    with open(path, encoding="utf-8") as fh:
        led = json.load(fh)
    if led.get("schema") != _ledger.SCHEMA:
        raise ValueError("ledger schema is %r, expected %r"
                         % (led.get("schema"), _ledger.SCHEMA))
    return led


def save(led, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(led, fh, indent=1)
    return path


def load_symbols(path):
    """`{"\\\\gamma": "unit-interval-half-open", ...}` supplied by the reader.

    One minute of a reader's time beats any amount of inference: 54 of 61 symbols
    in one real paper had a domain the parser could not read, and every one of
    those blocks a refutation.
    """
    if not path:
        return None
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("--symbols must be a JSON object of symbol -> domain")
    return data


def select_claims(led, wanted):
    """Restrict a ledger to named claims, keeping their proofs and steps."""
    if not wanted:
        return led
    keep = set()
    for c in led["claims"]:
        if c["id"] in wanted or c.get("label") in wanted:
            keep.add(c["id"])
    proofs = [p for p in led["proofs"] if p.get("claim_id") in keep]
    pids = {p["id"] for p in proofs}
    out = dict(led)
    out["claims"] = [c for c in led["claims"] if c["id"] in keep]
    out["proofs"] = proofs
    out["steps"] = [s for s in led["steps"] if s.get("proof_id") in pids]
    return out
