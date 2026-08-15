"""Fragments plus frozen notation into one standalone document. Stdlib only.

One document per theorem, self-contained: it restates the notation, restates the
claim, and then walks the proof. Nothing is assumed from the paper, because a
reader who could already follow the paper's own version does not need this.

The preamble is **copied** next to the `.tex` so the artifact still builds after
this skill is gone — the same rule `_shared/md2pdf` states about its own
single-file design.

A gap is rendered **inline, where the step would have been**, as well as in the
ledger at the end. A gap relegated to an appendix reads as an afterthought; a red
block in the middle of the derivation reads as what it is.
"""
import datetime
import os
import re
import shutil

from . import gaps as _gaps

_TEMPLATES = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "templates")

#: Characters that are LaTeX syntax in prose. Mathematics is never passed here.
_ESCAPES = [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
            ("$", r"\$"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"),
            ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}")]

_LICENCE_RENDER = {
    "equation": lambda v: r"equation~\texttt{%s} of the paper" % _esc(v),
    "citation": lambda v: r"the cited result \texttt{%s}" % _esc(v),
    "named-result": lambda v: r"\emph{%s}" % _esc(str(v).replace("-", " ")),
    "not-established": lambda v: (
        r"\textbf{nothing in the paper establishes this move}"),
}


def _esc(text):
    """Escape prose for LaTeX. Never applied to mathematics."""
    s = str(text if text is not None else "")
    for a, b in _ESCAPES:
        s = s.replace(a, b)
    return s


def _prose(text):
    """Prose that may contain inline `$...$`, which must survive unescaped."""
    parts = re.split(r"(\$[^$]*\$)", str(text or ""))
    return "".join(p if p.startswith("$") and p.endswith("$") and len(p) > 1
                   else _esc(p) for p in parts)


def _checked_cell(checked):
    checked = checked or {}
    verdict = checked.get("verdict") or "not run"
    if verdict == "not run":
        return r"\emph{not run} --- no mechanical check was applied to this step"
    engine = checked.get("engine") or "?"
    script = checked.get("script")
    tail = (r" (\texttt{%s})" % _esc(script)) if script else ""
    return r"\texttt{%s} by \texttt{%s}%s" % (_esc(verdict), _esc(engine), tail)


def _step_block(i, row):
    lic = row.get("licensed_by") or {}
    render = _LICENCE_RENDER.get(lic.get("kind"),
                                 lambda v: r"\textbf{unrecognised licence}")
    return r"\stepblock{%d}{%s}{%s}{%s}{%s}{%s}{%s}{%s}" % (
        i,
        row.get("before_tex") or r"\text{---}",
        row.get("after_tex") or r"\text{---}",
        _esc(row.get("move") or ""),
        render(lic.get("value")),
        _prose(row.get("breaks_if") or "not stated"),
        _checked_cell(row.get("checked")),
        _prose(row.get("gloss") or ""))


def _gap_block(gap):
    return r"\stepgap{%s}{%s}{%s}" % (
        _esc(gap.get("step_id") or "a step"),
        _prose(gap.get("what_is_missing") or ""),
        _prose(gap.get("what_would_close_it") or "not stated"))


def _notation_table(notation, rows=None):
    syms = notation.get("symbols") or []
    if not syms:
        return "No symbols were resolved for this derivation."
    out = [r"\begin{longtable}{@{}l l p{0.5\textwidth}@{}}",
           r"\toprule",
           r"Symbol & Range & Where that comes from \\",
           r"\midrule", r"\endhead"]
    for s in syms:
        prov = s.get("domain_provenance")
        if prov == "declared" and s.get("quote"):
            where = r"stated in the paper: %s" % _prose(s["quote"])
        elif prov == "inferred":
            where = r"\emph{inferred} from the surrounding notation, not stated"
        elif prov == "user-supplied":
            where = r"supplied by the reader"
        else:
            where = (r"\textbf{never stated.} Steps involving it cannot be "
                     r"mechanically refuted")
        out.append(r"$%s$ & %s & %s \\" % (s["symbol"], _esc(s.get("domain")),
                                           where))
    out += [r"\bottomrule", r"\end{longtable}"]
    return "\n".join(out)


def _statement(claim):
    body = [r"\begin{quote}", r"\emph{%s.}" % _esc(
        (claim.get("kind") or "Claim").capitalize()
        + (" " + claim["number"] if claim.get("number") else "")), ""]
    if claim.get("title"):
        body.append(r"\textbf{%s.}" % _esc(claim["title"]))
    body.append(claim.get("statement_tex") or "")
    body.append(r"\end{quote}")
    return "\n".join(body)


def _statement_gloss(claim):
    hyps = claim.get("hypotheses") or []
    if not hyps:
        return (r"The statement was not split into hypotheses and conclusion: "
                r"nothing in its wording marked the boundary, and guessing one "
                r"would invent a hypothesis the paper does not carry.")
    out = [r"\noindent\textbf{What must hold going in:}",
           r"\begin{itemize}[nosep]"]
    out += [r"\item %s" % _prose(h) for h in hyps]
    out += [r"\end{itemize}",
            r"\noindent\textbf{What comes out:} %s"
            % _prose(claim.get("conclusion") or "")]
    return "\n".join(out)


def _gap_section(gap_rows, all_gaps=False):
    shown = _gaps.reportable(gap_rows, all_gaps=all_gaps)
    if not gap_rows:
        return (r"\textbf{No gaps.} Every step above was made explicit with a "
                r"stated licence. That is a statement about this expansion, not "
                r"a proof that the theorem is true.")
    out = [r"\begin{longtable}{@{}l l p{0.34\textwidth} p{0.30\textwidth}@{}}",
           r"\toprule",
           r"Step & Severity & What is missing & What would close it \\",
           r"\midrule", r"\endhead"]
    for g in shown:
        out.append(r"\texttt{%s} & \textbf{%s} & %s & %s \\" % (
            _esc(g.get("step_id") or "--"), _esc(g["severity"]),
            _prose(g.get("what_is_missing")),
            _prose(g.get("what_would_close_it") or "not stated")))
    out += [r"\bottomrule", r"\end{longtable}"]
    hidden = len(gap_rows) - len(shown)
    if hidden > 0:
        out.append(r"\noindent{\footnotesize %d further gap%s of lower severity "
                   r"%s not shown; rerun with \texttt{--all-gaps}.}"
                   % (hidden, "" if hidden == 1 else "s",
                      "is" if hidden == 1 else "are"))
    return "\n".join(out)


def document(claim, rows, gaps, notation, meta, all_gaps=False):
    """One standalone `.tex` for one derivation."""
    with open(os.path.join(_TEMPLATES, "derivation.tex.in"), encoding="utf-8") as fh:
        tpl = fh.read()

    if rows:
        blocks = []
        gap_by_step = {g.get("step_id"): g for g in gaps or []}
        seen = set()
        for i, row in enumerate(rows, start=1):
            blocks.append(_step_block(i, row))
            g = gap_by_step.get(row.get("step_id"))
            if g and g["severity"] in ("BLOCKING", "SUBSTANTIVE"):
                blocks.append(_gap_block(g))
                seen.add(g.get("step_id"))
        for g in gaps or []:
            if g["severity"] == "BLOCKING" and g.get("step_id") not in seen:
                blocks.append(_gap_block(g))
        steps_tex = "\n\n".join(blocks)
        failure = ""
    else:
        steps_tex = (r"\subsection*{This derivation could not be expanded}"
                     "\n\n"
                     r"No step of this proof was made explicit. The gap ledger "
                     r"below is the whole result, and an expansion that could "
                     r"not be started is itself evidence about the derivation.")
        failure = (r" \textbf{This expansion did not complete}; see the gap "
                   r"ledger.")

    title = "Expanded derivation: %s%s" % (
        (claim.get("kind") or "claim").capitalize(),
        " " + claim["number"] if claim.get("number") else "")

    subs = {
        "TITLE": _esc(title),
        "AUTHORLINE": _esc(meta.get("paper") or meta.get("source_file") or ""),
        "DATE": meta.get("date") or datetime.date.today().isoformat(),
        "FAILURENOTE": failure,
        "NOTATION": _notation_table(notation, rows),
        "STATEMENT": _statement(claim),
        "STATEMENTGLOSS": _statement_gloss(claim),
        "STEPS": steps_tex,
        "GAPS": _gap_section(gaps or [], all_gaps),
        "LEVEL": _esc(meta.get("level") or "grad-ml"),
        "SOURCEFILE": _esc(meta.get("source_file") or "?"),
        "LEDGERHASH": _esc(meta.get("ledger_hash") or "?"),
        "PROVENANCE": _esc(meta.get("provenance") or ""),
    }
    for key, val in subs.items():
        tpl = tpl.replace("@@%s@@" % key, val)
    leftover = re.findall(r"@@[A-Z]+@@", tpl)
    if leftover:
        raise ValueError("template placeholders never substituted: %s"
                         % ", ".join(sorted(set(leftover))))
    return tpl


def write_document(outdir, name, text):
    """Write the `.tex` and copy the preamble beside it."""
    os.makedirs(outdir, exist_ok=True)
    shutil.copyfile(os.path.join(_TEMPLATES, "preamble.tex"),
                    os.path.join(outdir, "preamble.tex"))
    path = os.path.join(outdir, "%s.tex" % name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path
