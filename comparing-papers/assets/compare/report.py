"""Render a comparison. Pure formatting."""
import json

DRAFT = "(draft)"


def _cell(v):
    return str(v if v is not None else "").replace("|", "\\|").replace("\n", " ")


def _value(evidence):
    return _cell(evidence.value) if evidence.found else "—"


def _label(name, refs):
    ref = refs.get(name)
    if not ref:
        return name
    bits = [b for b in (str(ref.year) if ref.year else "", ref.venue) if b]
    ident = ref.arxiv_id or ref.doi
    if ident:
        bits.append(ident)
    return f"{name} ({', '.join(bits)})" if bits else name


def to_markdown(rows, refs, sources):
    names = []
    for r in rows:
        for n in r.others:
            if n not in names:
                names.append(n)

    lines = ["# Head-to-head comparison", ""]

    if refs or sources:
        lines += ["| Paper | Identity | Text source |", "|---|---|---|",
                  f"| **This draft** | — | {_cell(sources.get(DRAFT, ('local', False))[0])} |"]
        for n in names:
            src = sources.get(n, ("unknown", True))[0]
            lines.append(f"| {_cell(n)} | {_cell(_label(n, refs))} | {_cell(src)} |")
        lines.append("")

    degraded = [n for n, (_s, d) in sources.items() if d]
    if degraded:
        lines += [f"> **Coverage degraded.** No full text was reachable for "
                  f"{', '.join(_cell(n) for n in degraded)}; only the abstract was "
                  f"used. Axes such as training scale, seeds and compute live in "
                  f"appendices and will read as *not found* rather than as absent "
                  f"from the paper.", ""]

    for r in rows:
        lines += [f"## {r.axis}", ""]
        if r.note:
            lines += [f"**{_cell(r.note)}**", ""]
        lines += ["| Paper | Value | Section |", "|---|---|---|",
                  f"| **This draft** | {_value(r.draft)} | "
                  f"{_cell(r.draft.section) if r.draft.found else '—'} |"]
        for n in names:
            e = r.others.get(n)
            if e is None:
                lines.append(f"| {_cell(n)} | — | — |")
            else:
                lines.append(f"| {_cell(n)} | {_value(e)} | "
                             f"{_cell(e.section) if e.found else '—'} |")
        lines.append("")

        quotes = []
        if r.draft.found:
            quotes.append(f"> **This draft** — {_cell(r.draft.quote)}")
        for n in names:
            e = r.others.get(n)
            if e is not None and e.found:
                quotes.append(f"> **{_cell(n)}** — {_cell(e.quote)}")
        if quotes:
            lines += quotes + [""]

    lines += ["## How to read this", "",
              "Every cell is a quoted sentence with the section it came from; "
              "nothing here is paraphrased. Notes are computed only where the "
              "relation is arithmetic — a scale ratio, a seed count. On every "
              "other axis the table shows two passages and stops, because "
              "whether two protocols are genuinely comparable is a judgement "
              "for you to make, not one a regular expression can reach.", "",
              "`—` means no sentence matched that axis. That is not the same as "
              "the paper not doing it: check the source before reporting an "
              "absence."]
    return "\n".join(lines)


def _ev_json(e):
    return {"value": e.value, "quote": e.quote, "section": e.section,
            "found": e.found}


def to_json(rows):
    return json.dumps([
        {"axis": r.axis, "note": r.note, "draft": _ev_json(r.draft),
         "others": {n: _ev_json(e) for n, e in r.others.items()}}
        for r in rows], indent=2)
