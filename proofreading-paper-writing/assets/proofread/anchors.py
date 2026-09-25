"""Locate ledger anchors in LaTeX and decide whether a span may be edited."""
import re

_WORD = re.compile(r"\w")
_BLANK = re.compile(r"\n[ \t]*\n")
_HEADING_LINE = re.compile(r"\\(?:sub)*section\*?\s*(?:\[[^\]]*\])?\{[^}]*\}(?:\s*\\label\{[^}]*\})?[ \t]*\n")

# Commands whose brace arguments may not be edited. Order matters only for the label.
_CMD_GROUPS = {
    "cite": re.compile(r"\\cite[pt]?\*?(?:\[[^\]]*\]){0,2}\{"),
    "resizebox": re.compile(r"\\resizebox\*?\{"),
    "footnote": re.compile(r"\\footnote(?:\[[^\]]*\])?\{"),
    "CL-markup": re.compile(r"\\ch(?:replaced|added|deleted|comment|highlight)(?:\[[^\]]*\])?\{"),
}
_ENVS = {
    "tabular": re.compile(r"\\begin\{(tabular[xy*]?|longtable|array)\}"),
    "math": re.compile(r"\\begin\{(equation\*?|align\*?|gather\*?|multline\*?|eqnarray\*?|displaymath)\}"),
}
_INLINE_MATH = re.compile(r"(?<!\\)\$\$?|\\\[|\\\]|\\\(|\\\)")


def _brace_groups_end(tex, open_pos, n_groups):
    """Position just after the n_groups consecutive {...} groups starting at open_pos."""
    i = open_pos
    for _ in range(n_groups):
        if i >= len(tex) or tex[i] != "{":
            break
        depth = 0
        while i < len(tex):
            c = tex[i]
            if c == "\\":
                i += 2
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1
        # skip whitespace between consecutive groups
        j = i
        while j < len(tex) and tex[j] in " \t":
            j += 1
        if j < len(tex) and tex[j] == "{":
            i = j
    return i


def spans(tex):
    """Forbidden regions as (start, end, kind). Inner regions are listed after outer ones."""
    out = []
    for kind, rx in _CMD_GROUPS.items():
        n = 3 if kind == "resizebox" else 2 if kind == "CL-markup" else 1
        for m in rx.finditer(tex):
            open_pos = m.end() - 1
            end = _brace_groups_end(tex, open_pos, n)
            out.append((m.start(), end, kind))
    for kind, rx in _ENVS.items():
        for m in rx.finditer(tex):
            close = re.compile(r"\\end\{" + re.escape(m.group(1)) + r"\}").search(tex, m.end())
            end = close.end() if close else len(tex)
            out.append((m.start(), end, kind))
    # inline math: pair delimiters left to right
    opened = None
    for m in _INLINE_MATH.finditer(tex):
        tok = m.group(0)
        if opened is None:
            if tok in ("$", "$$", r"\[", r"\("):
                opened = (m.start(), tok)
        else:
            want = {"$": "$", "$$": "$$", r"\[": r"\]", r"\(": r"\)"}[opened[1]]
            if tok == want:
                out.append((opened[0], m.end(), "math"))
                opened = None
    # sort outer-first so the innermost is the last containing span
    out.sort(key=lambda t: (t[0], -t[1]))
    return out


def forbidden_context(tex, start, end):
    """Kind of the innermost forbidden span containing [start, end), or None."""
    hit = None
    for s, e, kind in spans(tex):
        if s <= start and end <= e:
            hit = kind
    return hit


def find_all(tex, anchor):
    out, i = [], tex.find(anchor)
    while i != -1:
        out.append(i)
        i = tex.find(anchor, i + 1)
    return out


def find_normalised(tex, anchor):
    """Match with any whitespace run in the anchor standing for any whitespace run in the tex."""
    parts = [re.escape(p) for p in anchor.split()]
    if not parts:
        return []
    rx = re.compile(r"\s+".join(parts))
    return [(m.start(), m.end()) for m in rx.finditer(tex)]


def whole_token(tex, start, end):
    before = tex[start - 1] if start > 0 else " "
    after = tex[end] if end < len(tex) else " "
    return not _WORD.match(before) and not _WORD.match(after)


def paragraph_start(tex, pos):
    """Start of the prose paragraph containing pos: after the last blank line or heading line."""
    cands = [0]
    for m in _BLANK.finditer(tex, 0, pos):
        cands.append(m.end())
    for m in _HEADING_LINE.finditer(tex, 0, pos):
        cands.append(m.end())
    start = max(c for c in cands if c <= pos)
    while start < len(tex) and tex[start] in " \t\n":
        start += 1
    return start
