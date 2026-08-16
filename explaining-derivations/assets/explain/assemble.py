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
    "local-result": lambda v: r"\texttt{%s} of this paper" % _esc(v),
    "not-established": lambda v: (
        r"\textbf{nothing in the paper establishes this move}"),
}


def _esc(text):
    """Escape prose for LaTeX. Never applied to mathematics."""
    s = str(text if text is not None else "")
    for a, b in _ESCAPES:
        s = s.replace(a, b)
    return s


#: Accents, which are the one class of control sequence that turns up in prose.
#: `It\^o` and `Gr\"onwall` came back from a real expansion and were escaped into
#: `It\textbackslash{}\^{}o`, which is unreadable in a way that reads as a bug in
#: the expander rather than in the renderer.
_ACCENT = re.compile(r"\\[\^\"'`~=.uvHtcdb](?:\{[A-Za-z]\}|[A-Za-z])")


def _prose(text):
    """Prose that may contain inline `$...$` or an accent, which survive."""
    parts = re.split(r"(\$[^$]*\$|" + _ACCENT.pattern + r")", str(text or ""))
    return "".join(
        p if (p.startswith("$") and p.endswith("$") and len(p) > 1)
        or _ACCENT.fullmatch(p) else _esc(p)
        for p in parts)


def _checked_cell(checked):
    checked = checked or {}
    verdict = checked.get("verdict") or "not run"
    if verdict == "not run":
        return r"\emph{not run} --- no mechanical check was applied to this step"
    engine = checked.get("engine")
    if not engine:
        # `UNVERIFIED by ?` was what a step no engine could reach rendered as.
        # The question mark reads like missing data; the honest reading is that
        # the checker ran and reached nothing, which is itself the finding.
        return (r"\texttt{%s} --- no engine could run on this step"
                % _esc(verdict))
    script = checked.get("script")
    tail = (r" (\texttt{%s})" % _esc(script)) if script else ""
    return r"\texttt{%s} by \texttt{%s}%s" % (_esc(verdict), _esc(engine), tail)


def _step_number(row, ordinal):
    """The paper's step number, not the row's position in the fragment.

    Steps the checker skipped as narration never reach the expander, so the
    fragment's fifth row can be the paper's seventh step. Numbering blocks by
    position then leaves the gap ledger -- which keys on step ids -- pointing at
    numbers that appear nowhere in the document.
    """
    m = re.search(r"/s(\d+)$", str(row.get("step_id") or ""))
    return str(int(m.group(1))) if m else str(ordinal)


def _step_block(i, row):
    lic = row.get("licensed_by") or {}
    render = _LICENCE_RENDER.get(lic.get("kind"),
                                 lambda v: r"\textbf{unrecognised licence}")
    # `expanded_into` is the sub-steps `registers.md` asks the expander for: "a
    # step that takes three moves to justify gets three sub-steps". The contract
    # carried the field, the validator accepted it, and nothing rendered it --
    # so the instruction produced output that was thrown away. Both real
    # dispatches filled it in; on the second, roughly a third of what the
    # expander wrote never reached the page.
    unpacked = "".join(r"\item %s" % _prose(s)
                       for s in (row.get("expanded_into") or []) if s)
    return r"\stepblock{%s}{%s}{%s}{%s}{%s}{%s}{%s}{%s}{%s}" % (
        _step_number(row, i),
        row.get("before_tex") or r"\text{---}",
        row.get("after_tex") or r"\text{---}",
        _esc(row.get("move") or ""),
        render(lic.get("value")),
        _prose(row.get("breaks_if") or "not stated"),
        _checked_cell(row.get("checked")),
        _prose(row.get("gloss") or ""),
        unpacked)


def _short_step(step_id):
    """`proof/lem:long_label/s07` as `Step 7`. The label is in the title."""
    m = re.search(r"/s(\d+)$", str(step_id or ""))
    return "Step %d" % int(m.group(1)) if m else _esc(step_id or "--")


def _gap_block(gap):
    """A gap where the step would have been.

    `BLOCKING` and `SUBSTANTIVE` are not the same event and must not look the
    same. A SUBSTANTIVE gap sits beside a step that *was* expanded, so rendering
    it in the BLOCKING red under the heading `could not be made explicit`
    contradicts the block immediately above it.
    """
    macro = r"\stepgap" if gap["severity"] == "BLOCKING" else r"\stepcaveat"
    return r"%s{%s}{%s}{%s}" % (
        macro, _short_step(gap.get("step_id")),
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
            # Said once above the table rather than on every row. On a paper
            # that declares nothing this sentence was repeated verbatim in
            # every row, which reads as filler and buries the rows that differ.
            where = r"\textbf{never stated}"
        out.append(r"$%s$ & %s & %s \\" % (s["symbol"], _esc(s.get("domain")),
                                           where))
    out += [r"\bottomrule", r"\end{longtable}"]
    if any((s.get("domain_provenance") not in
            ("declared", "inferred", "user-supplied")) for s in syms):
        out.append(r"\noindent{\footnotesize A symbol marked \textbf{never "
                   r"stated} has no range anywhere in the paper. No step "
                   r"involving it can be mechanically refuted, because sampling "
                   r"outside a range the author meant but never wrote down is "
                   r"how a checker manufactures an error against correct "
                   r"mathematics.}")
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


_DISPLAY = re.compile(
    r"\\begin\{(align|align\*|equation|equation\*|gather|gather\*|multline|"
    r"multline\*|displaymath|eqnarray)\}.*?\\end\{\1\}|\\\[.*?\\\]", re.S)


def _clause(text):
    r"""A hypothesis or conclusion, as the paper wrote it.

    Emitted unescaped exactly as `statement_tex` is: passing it through the
    prose escaper turned a displayed `align` in the conclusion into a paragraph
    of `\textbackslash{}sqrt\{...\}` -- unreadable, and 104pt past the right
    margin because the result is one unbreakable token.

    Displays are replaced rather than repeated. The full statement is printed
    directly above this gloss, so re-emitting its `align` blocks set the same
    mathematics twice and gave it two different equation numbers.
    """
    out = _DISPLAY.sub(r"\\emph{(the display in the statement above)}",
                       str(text or ""))
    return re.sub(r"^[\s,;:]+", "", out)


def _statement_gloss(claim):
    hyps = claim.get("hypotheses") or []
    if not hyps:
        return (r"The statement was not split into hypotheses and conclusion: "
                r"nothing in its wording marked the boundary, and guessing one "
                r"would invent a hypothesis the paper does not carry.")
    out = [r"\noindent\textbf{What must hold going in:}",
           r"\begin{itemize}[nosep]"]
    out += [r"\item %s" % _clause(h) for h in hyps]
    out += [r"\end{itemize}",
            r"\noindent\textbf{What comes out:} %s"
            % _clause(claim.get("conclusion"))]
    return "\n".join(out)


def _gap_section(gap_rows, all_gaps=False):
    shown = _gaps.reportable(gap_rows, all_gaps=all_gaps)
    if not gap_rows:
        return (r"\textbf{No gaps.} Every step above was made explicit with a "
                r"stated licence. That is a statement about this expansion, not "
                r"a proof that the theorem is true.")
    # Two columns, not four. The first version put `What is missing` and `What
    # would close it` in narrow neighbouring `p{}` columns; a gap whose text
    # carries a long inline formula -- which is most of them -- overran by up to
    # 29pt even after the step id was shortened, because inline mathematics does
    # not break. One wide column removes the failure mode rather than tuning it,
    # which is the same lesson the step block already carries.
    out = [r"\begin{longtable}{@{}p{0.17\textwidth} p{0.77\textwidth}@{}}",
           r"\toprule",
           r"Step & What is missing, and what would close it \\",
           r"\midrule", r"\endhead"]
    for g in shown:
        # `SUBSTANTIVE` set in bold at body size is itself wider than a narrow
        # first column, so the severity is the one thing here that must be set
        # small: the longest word in the table is a fixed vocabulary item.
        out.append(r"%s\newline{\footnotesize\textbf{%s}} & %s\newline"
                   r"\emph{Closed by:} %s \\[4pt]" % (
                       _short_step(g.get("step_id")), _esc(g["severity"]),
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


def document(claim, rows, gaps, notation, meta, all_gaps=False, tex_fragment=""):
    """One standalone `.tex` for one derivation."""
    with open(os.path.join(_TEMPLATES, "derivation.tex.in"), encoding="utf-8") as fh:
        tpl = fh.read()

    if rows:
        blocks = []
        # The expander's framing paragraph. It was validated for forbidden tokens
        # and then dropped: `Result.tex_fragment` was set and never read.
        if (tex_fragment or "").strip():
            blocks.append(r"\noindent %s" % tex_fragment.strip())
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
