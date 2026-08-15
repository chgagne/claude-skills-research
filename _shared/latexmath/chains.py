"""Multi-row displays reconstructed into checkable claims. Stdlib only.

An `align` chain is not a list of equations. Row 3 reads `&= \\int q(z)\\ldots`
and means "the previous right-hand side equals this". Two readings matter and
both are produced:

- **adjacent** -- `rhs_{k-1} REL rhs_k`, the actual inference the author made
- **anchored** -- `lhs_1 REL* rhs_k`, the cumulative claim, where `REL*` is the
  composition of every relation so far

Composition is not cosmetic. A chain that goes `=` then `\\ge` then `=` proves
`lhs_1 \\ge rhs_k`, and a chain that goes `\\le` then `\\ge` proves *nothing*
about its endpoints -- so no anchored form is emitted for it. Emitting one would
manufacture a claim the paper never made, and then check it.
"""
import re

from .tokenize import DISPLAY_ENVS, balanced, blank_comments, find_env_spans

_LABEL = re.compile(r"\\label\s*\{([^}]*)\}")
_NOTAG = re.compile(r"\\(?:nonumber|notag)\b")
_ROWSEP = re.compile(r"\\\\\*?(?:\s*\[[^\]]*\])?")
_INTERTEXT = re.compile(r"\\(short)?intertext\s*\{")

# Longest first: `\leq` must win over `\le`, and `\le\b` must not fire inside
# `\leftarrow`.
_RELS = [r"\\coloneqq", r"\\Longrightarrow", r"\\Leftrightarrow", r"\\Rightarrow",
         r"\\leqslant", r"\\geqslant", r"\\lesssim", r"\\gtrsim", r"\\preceq",
         r"\\succeq", r"\\subseteq", r"\\supseteq", r"\\equiv", r"\\approx",
         r"\\simeq", r"\\propto", r"\\mapsto", r"\\subset", r"\\supset",
         r"\\notin\b", r"\\neq\b", r"\\leq\b", r"\\geq\b", r"\\sim\b", r"\\iff\b",
         r"\\le\b", r"\\ge\b", r"\\ne\b", r"\\in\b", r"\\to\b", r"\\ll\b",
         r"\\gg\b", r"\\prec\b", r"\\succ\b", r"\\doteq\b", r"\\triangleq\b",
         r":=", r"=", r"<", r">"]
_REL = re.compile("|".join(_RELS))

# Which relations may be chained with which. `=` is transparent; two relations
# leaning the same way compose; anything else yields no cumulative claim.
_LE = {r"\le", r"\leq", r"\leqslant", "<", r"\ll", r"\lesssim", r"\prec",
       r"\preceq", r"\subseteq", r"\subset"}
_GE = {r"\ge", r"\geq", r"\geqslant", ">", r"\gg", r"\gtrsim", r"\succ",
       r"\succeq", r"\supseteq", r"\supset"}
_EQ = {"=", r"\equiv", r":=", r"\coloneqq", r"\doteq", r"\triangleq"}


def compose(a, b):
    """Cumulative relation of `a` then `b`, or None if they do not compose."""
    if a is None:
        return b
    if b is None:
        return a
    if a in _EQ:
        return b
    if b in _EQ:
        return a
    if a in _LE and b in _LE:
        return a if a == b else r"\le"
    if a in _GE and b in _GE:
        return a if a == b else r"\ge"
    return None


class Row:
    __slots__ = ("index", "raw", "tex", "cells", "label", "numbered",
                 "lead_relation", "intertext")

    def __init__(self, **kw):
        for s in self.__slots__:
            setattr(self, s, kw.get(s))

    def __repr__(self):
        return "Row(%d, %r)" % (self.index, self.tex[:40])


class Equation:
    __slots__ = ("id", "env", "starred", "labels", "row_labels", "numbered_rows",
                 "notag_rows", "raw_tex", "expanded_tex", "alignment_columns",
                 "intertext", "rows", "source")

    def __init__(self, **kw):
        for s in self.__slots__:
            setattr(self, s, kw.get(s))

    def as_dict(self):
        d = {s: getattr(self, s) for s in self.__slots__}
        d["rows"] = [{k: getattr(r, k) for k in Row.__slots__} for r in self.rows]
        return d

    def __repr__(self):
        return "Equation(%r, %d rows)" % (self.env, len(self.rows or []))


def split_rows(body):
    """Split on `\\\\` at brace depth 0 and outside any nested environment."""
    out, start, i, n = [], 0, 0, len(body)
    depth = envd = 0
    while i < n:
        c = body[i]
        if c == "\\":
            if body.startswith(r"\begin", i):
                envd += 1
                i += 6
                continue
            if body.startswith(r"\end", i):
                envd -= 1
                i += 4
                continue
            m = _ROWSEP.match(body, i)
            if m and depth == 0 and envd == 0:
                out.append(body[start:i])
                start = i = m.end()
                continue
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    out.append(body[start:])
    return out


def _angle_ranges(tex):
    """Offsets of `<` and `>` that bracket an inner product rather than relate.

    Papers write `\\langle a, b\\rangle`, and papers also write `<a, b>`. Read as
    relations the bare form truncates the claim: on arXiv:1806.07572 the step
    `\\partial_t W = \\frac{1}{\\sqrt{n}}<\\alpha, d>` became
    `\\partial_t W = \\frac{1}{\\sqrt{n}}`, a claim the authors never made.

    The signature of the bracket form is a matching `>` at the same depth with a
    top-level comma between. `x < 1` and `0 < x < 1` have no such pairing and are
    left alone.
    """
    out, stack, depth = [], [], 0
    i, n = 0, len(tex)
    while i < n:
        c = tex[i]
        if c == "\\":
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif c == "<":
            stack.append((i, depth))
        elif c == ">" and stack:
            start, d = stack[-1]
            if d == depth and "," in tex[start + 1:i]:
                stack.pop()
                out.append((start, i))
        i += 1
    return out


def _angle_delimiters(tex):
    """Flat offsets of the `<`/`>` characters that bracket an inner product."""
    out = set()
    for a, b in _angle_ranges(tex):
        out.add(a)
        out.add(b)
    return out


def top_relations(tex):
    """(start, end, symbol) for every relation at brace depth 0."""
    angles = _angle_delimiters(tex)
    out, i, n, depth = [], 0, len(tex), 0
    while i < n:
        c = tex[i]
        if c == "{":
            depth += 1
            i += 1
            continue
        if c == "}":
            depth -= 1
            i += 1
            continue
        if i in angles:
            i += 1
            continue
        m = _REL.match(tex, i) if depth == 0 else None
        if m:
            out.append((m.start(), m.end(), m.group(0)))
            i = m.end()
            continue
        i += 2 if c == "\\" else 1
    return out


def split_clauses(tex):
    """Split a row into independent relational statements at top-level commas.

    Earned from a real paper: `C_0 = \\{c_{i0}\\}_{i=1}^{B}, O_0 = \\{o_{i0}\\}`
    packs two definitions into one row. Read as a transitive chain it produces the
    left-hand side `\\{c_{i0}\\}_{i=1}^{B}, O_0`, which is not an expression --
    and a checker handed that reports on a claim the paper never made.

    A comma only separates clauses when *both* sides carry a top-level relation.
    That keeps `f(x, y) = z` and `S = 1, 2, \\ldots, n` whole. Parentheses and
    brackets count toward depth here, unlike elsewhere, because the false split
    this guards against lives inside function arguments.
    """
    angles = _angle_ranges(tex)
    cuts, depth, paren, brack, i, n = [], 0, 0, 0, 0, len(tex)
    while i < n:
        c = tex[i]
        if c == "\\":
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif c == "(":
            paren += 1
        elif c == ")":
            paren -= 1
        elif c == "[":
            brack += 1
        elif c == "]":
            brack -= 1
        elif (c in ",;" and depth == paren == brack == 0
              and not any(a < i < b for a, b in angles)):
            cuts.append(i)
        i += 1
    if not cuts:
        return [tex]
    out, prev = [], 0
    for cut in cuts:
        if top_relations(tex[prev:cut]) and top_relations(tex[cut + 1:]):
            out.append(tex[prev:cut])
            prev = cut + 1
    out.append(tex[prev:])
    return [p.strip() for p in out if p.strip()]


def _pull_intertext(row_tex):
    """(row without its leading intertext, intertext body or None)."""
    m = _INTERTEXT.search(row_tex)
    if not m:
        return row_tex, None
    body, end = balanced(row_tex, m.end() - 1)
    if body is None:
        return row_tex, None
    return (row_tex[:m.start()] + row_tex[end:]), body.strip()


def _split_cells(tex):
    """Alignment cells: split on `&` at brace depth 0."""
    cells, start, depth, i, n = [], 0, 0, 0, len(tex)
    while i < n:
        c = tex[i]
        if c == "\\":
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif c == "&" and depth == 0:
            cells.append(tex[start:i])
            start = i + 1
        i += 1
    cells.append(tex[start:])
    return cells


def parse_display(tex, eid=None, macros=None, source=None):
    """One display environment (or a bare body) as an `Equation`."""
    scan = blank_comments(tex or "")
    env, starred, body = "display", False, scan
    m = re.match(r"\s*\\begin\s*\{([A-Za-z@]+\*?)\}", scan)
    if m:
        name = m.group(1)
        spans = find_env_spans(scan, [name], scan=scan)
        if spans:
            env, body = name.rstrip("*"), spans[0].body
            starred = name.endswith("*")
    if env == "display" and env not in DISPLAY_ENVS:
        env = "display"

    raw_rows = split_rows(body)
    rows, intertext, labels, row_labels = [], [], [], {}
    numbered_rows, notag_rows, ncols = [], [], 1
    for k, raw in enumerate(raw_rows, start=1):
        cleaned, itx = _pull_intertext(raw)
        if itx is not None:
            intertext.append({"after_row": k - 1, "tex": itx})
        lab = _LABEL.search(cleaned)
        label = lab.group(1) if lab else None
        tagged = not (_NOTAG.search(cleaned) or starred)
        text = _NOTAG.sub("", _LABEL.sub("", cleaned)).strip()
        cells = _split_cells(text)
        ncols = max(ncols, len(cells))
        joined = " ".join(c.strip() for c in cells if c.strip())
        rels = top_relations(joined)
        lead = None
        if rels and joined.lstrip().startswith(rels[0][2]):
            lead = rels[0][2]
        if label:
            labels.append(label)
            row_labels[k] = label
        (numbered_rows if tagged else notag_rows).append(k)
        rows.append(Row(index=k, raw=raw, tex=joined, cells=cells, label=label,
                        numbered=tagged, lead_relation=lead, intertext=itx))

    return Equation(id=eid, env=env, starred=starred, labels=labels,
                    row_labels=row_labels, numbered_rows=numbered_rows,
                    notag_rows=notag_rows, raw_tex=tex,
                    expanded_tex=(macros.expand(tex)[0] if macros else tex),
                    alignment_columns=ncols, intertext=intertext, rows=rows,
                    source=source)


def rows_to_claims(eq):
    """Every row of a display as one or more `{relation, claim_forms}` records.

    A row containing two top-level relations (`a \\le b = c`) becomes two claims
    sharing a row index, marked `derived_from: "relation-chain"`.
    """
    out, anchor, prev_rhs, cumulative = [], None, None, None
    for row in eq.rows:
        tex = row.tex.strip()
        if not tex:
            continue
        clauses = split_clauses(tex)
        for ci, clause in enumerate(clauses):
            rels = top_relations(clause)
            if not rels:
                continue

            independent = ci > 0
            carried = bool(row.lead_relation) and not independent
            pieces, last = [], 0
            for (s, e, sym) in rels:
                pieces.append((clause[last:s].strip(), sym))
                last = e
            pieces.append((clause[last:].strip(), None))

            # A carried row opens with its relation, so its first piece is empty
            # and the left-hand side comes from the row above.
            left = prev_rhs if carried else pieces[0][0]
            if not carried and anchor is None and not independent:
                anchor = pieces[0][0]

            segments = []
            for idx in range(len(pieces) - 1):
                sym = pieces[idx][1]
                right = pieces[idx + 1][0]
                segments.append((left, sym, right))
                left = right

            for j, (lhs, sym, rhs) in enumerate(segments):
                if not independent:
                    cumulative = compose(cumulative, sym)
                forms = [{"form": "adjacent", "lhs_tex": lhs, "relation": sym,
                          "rhs_tex": rhs}]
                if (not independent and anchor is not None
                        and cumulative is not None and lhs != anchor):
                    forms.append({"form": "anchored", "lhs_tex": anchor,
                                  "relation": cumulative, "rhs_tex": rhs})
                derived = ("comma-list" if independent
                           else "relation-chain" if len(segments) > 1 else "row")
                out.append({
                    "equation_id": eq.id, "row": row.index,
                    "of_rows": len(eq.rows), "segment": j, "relation": sym,
                    "carried": carried,
                    "anchor_tex": None if independent else anchor,
                    "label": row.label, "numbered": row.numbered,
                    "derived_from": derived, "claim_forms": forms,
                    "tex": clause if independent else row.tex,
                })
            if not independent:
                prev_rhs = segments[-1][2] if segments else prev_rhs

        # Several statements on one row breaks the chain: nothing after it may
        # carry a left-hand side, because which one it would carry is a guess.
        if len(clauses) > 1:
            anchor = prev_rhs = cumulative = None
    return out
