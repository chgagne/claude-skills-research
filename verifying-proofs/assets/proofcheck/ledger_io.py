"""Build a ledger from sources, or load one that was built earlier. Stdlib only.

Splitting this out means the report and the engines never touch the filesystem
layout, and `--ledger-only` is a one-line CLI path rather than a special case.
"""
import json
import os
import sys

sys.path.insert(0, os.path.expanduser("~/.claude/skills/_shared"))

from latexmath import ledger as _ledger  # noqa: E402
from latexmath import symbols as _symbols  # noqa: E402


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


def symbols_template(led):
    """A `--symbols` skeleton plus the evidence needed to fill it in.

    Returns `(table, notes)`: a dict ready to be written as JSON in exactly the
    shape `--symbols` consumes, and a Markdown sidecar. JSON has no comments and
    the table has to stay directly usable, so the evidence goes beside it rather
    than inside it.

    **Ordered by what each symbol unblocks, not by how often it appears.** The
    obvious sort is by occurrence count; the useful one is by the number of
    unmet side conditions the symbol stands in, because that is the quantity
    `--symbols` actually buys. A symbol used 900 times in steps that are already
    settled is worth less than one used twice in the denominator of a bound.

    Only `unknown`-provenance symbols are listed. A domain the paper *declared*
    is not the reader's to override here, and inviting that would produce
    exactly the wrong-domain-recorded-as-declared failure that false-alarm
    classes 14, 17 and 18 are all instances of.
    """
    blocks, needs = {}, {}
    for step in led.get("steps", []):
        unmet = [c for c in step.get("side_conditions") or []
                 if c.get("status") != "established"]
        if not unmet:
            continue
        for name in step.get("symbols_used") or []:
            for c in unmet:
                if name in (c.get("expr_tex") or ""):
                    blocks.setdefault(name, []).append(step["id"])
                    needs.setdefault(name, set()).add(c["kind"])

    rows = []
    for s in led.get("symbols", []):
        if s.get("domain_provenance") != "unknown":
            continue
        steps = blocks.get(s["symbol"], [])
        rows.append((len(steps), s.get("occurrences", 0), s["symbol"], s, steps))
    rows.sort(key=lambda r: (-r[0], -r[1], r[2]))

    table = {sym: "" for _, _, sym, _, _ in rows}
    notes = [
        "# Symbol domains to supply",
        "",
        "Fill in `symbols-template.json` and pass it with `--symbols`. A symbol",
        "whose domain the paper never states can never produce a counterexample,",
        "so every row here is a step the tool declined to decide rather than one",
        "it decided in your favour.",
        "",
        "Ordered by how many unmet side conditions each symbol stands in, which",
        "is what supplying it actually buys — not by how often it appears.",
        "",
        "Legal values: `" + "`, `".join(_symbols.DOMAINS) + "`.",
        "Leave a row empty to say nothing about it; an empty value is ignored,",
        "and a value outside the list above is refused rather than accepted",
        "silently.",
        "",
        "| Symbol | Blocks | Uses | The obligations it stands in |",
        "|---|---|---|---|",
    ]
    for nblock, occ, sym, s, steps in rows:
        # What the symbol blocks, not where it first appeared. An unknown-domain
        # symbol has no domain evidence by definition -- that is what makes it a
        # row here -- so a "first use" column is empty for every entry. The kind
        # of obligation is what tells the reader which value to write.
        kinds = ", ".join("`%s`" % k for k in sorted(needs.get(sym, ()))) or "--"
        notes.append("| `%s` | %d | %d | %s |" % (sym, nblock, occ, kinds))
    notes.append("")
    if rows and rows[0][0] == 0:
        notes.append("No symbol here stands in an unmet side condition: supplying")
        notes.append("domains will widen what the engines may sample, but nothing")
        notes.append("in this run is waiting on one.")
    return table, "\n".join(notes) + "\n"
