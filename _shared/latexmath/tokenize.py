"""Offset-preserving LaTeX scanner. Stdlib only.

Everything downstream slices the source by offset -- a step records the byte span
it came from so a reader can open the file at the right line, and so a fragment
written weeks later can be refused when the span no longer hashes the same. That
rules out `strip_comments`, which is correct but shortens the text. Here comments
are *blanked* instead: replaced by spaces, same length, same line breaks.

Three things must be got right before any proof can be read, and each was chosen
because getting it wrong is silent rather than loud:

- **Comments.** Authors comment out whole `aligned` blocks and leave them in the
  appendix. Scanning them produces steps that are not in the paper.
- **Verbatim.** `$` inside `\\verb|...|` or a listing is a dollar sign. Treating it
  as math opens a span that swallows the rest of the section.
- **Nesting.** `\\begin{align}` inside `\\begin{align}` must yield one span, not two
  half-open ones.
"""
import re

_BEGIN = re.compile(r"\\begin\s*\{([A-Za-z@]+\*?)\}")

_VERB_ENVS = ("verbatim", "Verbatim", "lstlisting", "minted", "alltt", "comment")

# Environments whose contents are mathematics. `cases`, `pmatrix` and friends are
# absent on purpose: they only ever occur *inside* one of these.
DISPLAY_ENVS = ("equation", "displaymath", "math", "align", "aligned", "alignat",
                "flalign", "gather", "gathered", "multline", "eqnarray", "split",
                "IEEEeqnarray", "dmath", "empheq")

# A `\label` that owns its whole line, taken with the newline that follows it.
_LABEL_LINE = re.compile(r"(?m)^[ \t]*\\label\s*\{[^}]*\}[ \t]*\r?\n")
_LABEL_INLINE = re.compile(r"\\label\s*\{[^}]*\}")


def strip_labels(text):
    r"""Remove `\label{...}` without leaving a blank line behind.

    Deleting the command alone turns a line that held only a label into an empty
    line, and an empty line inside `align` is a `\par`: the extracted statement
    then fails to compile with `Paragraph ended before \align was complete`.
    Authors put labels on their own line as a matter of course, so this is the
    common case rather than an exotic one -- and the failure surfaces only when
    something re-typesets the extracted text, which is long after extraction.
    """
    return _LABEL_INLINE.sub("", _LABEL_LINE.sub("", text or ""))


class Span:
    """A region of the source, with both its outer and its inner extent.

    `start`/`end` bound the whole construct including delimiters; `inner_start`/
    `inner_end` bound the body. Masking uses the inner pair so the delimiters
    survive and a later pass can still see that mathematics was here.
    """

    __slots__ = ("name", "start", "end", "body", "arg", "inner_start", "inner_end")

    def __init__(self, name, start, end, body, arg, inner_start, inner_end):
        self.name = name
        self.start = start
        self.end = end
        self.body = body
        self.arg = arg
        self.inner_start = inner_start
        self.inner_end = inner_end

    def __repr__(self):
        return "Span(%r, %d, %d)" % (self.name, self.start, self.end)


def balanced(text, i):
    """Body and end offset of the brace group opening at `i`. (None, -1) if unbalanced."""
    if i >= len(text) or text[i] != "{":
        return None, -1
    depth, j, n = 0, i, len(text)
    while j < n:
        c = text[j]
        if c == "\\":
            j += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1:j], j + 1
        j += 1
    return None, -1


def _bracketed(text, i):
    """Body and end offset of the optional-argument group opening at `i`."""
    if i >= len(text) or text[i] != "[":
        return None, -1
    depth, j, n = 0, i, len(text)
    while j < n:
        c = text[j]
        if c == "\\":
            j += 2
            continue
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return text[i + 1:j], j + 1
        j += 1
    return None, -1


def protected_spans(text):
    """Regions where LaTeX special characters carry no meaning."""
    out = []
    for nm in _VERB_ENVS:
        pat = re.compile(r"\\begin\s*\{" + nm + r"\*?\}")
        endpat = re.compile(r"\\end\s*\{" + nm + r"\*?\}")
        for m in pat.finditer(text):
            e = endpat.search(text, m.end())
            out.append((m.start(), e.end() if e else len(text)))
    for m in re.finditer(r"\\verb\*?(.)", text):
        j = text.find(m.group(1), m.end())
        out.append((m.start(), j + 1 if j >= 0 else len(text)))
    return sorted(out)


def _covered(spans, i):
    for a, b in spans:
        if a <= i < b:
            return b
    return 0


def blank_comments(text, protected=None):
    """Replace comment characters with spaces, preserving every offset.

    An escaped `\\%` is not a comment. Comments inside verbatim are not comments.
    """
    prot = protected_spans(text) if protected is None else protected
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        skip = _covered(prot, i)
        if skip:
            i = skip
            continue
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == "%":
            j = i
            while j < n and text[j] != "\n":
                out[j] = " "
                j += 1
            i = j
            continue
        i += 1
    return "".join(out)


def find_env_spans(text, names, scan=None):
    """Outermost `\\begin{name}...\\end{name}` spans, comment-blanked, nesting-aware."""
    scan = blank_comments(text) if scan is None else scan
    wanted = set(names)
    out, pos = [], 0
    for m in _BEGIN.finditer(scan):
        if m.start() < pos or m.group(1) not in wanted:
            continue
        name = m.group(1)
        k, arg = m.end(), None
        opt = re.match(r"\s*\[", scan[k:])
        if opt:
            body, e = _bracketed(scan, k + opt.end() - 1)
            if e > 0:
                arg, k = body, e
        inner_start = k
        tok = re.compile(r"\\(begin|end)\s*\{" + re.escape(name) + r"\}")
        depth, cur, closing = 1, inner_start, None
        while True:
            t = tok.search(scan, cur)
            if t is None:
                break
            depth += 1 if t.group(1) == "begin" else -1
            cur = t.end()
            if depth == 0:
                closing = t
                break
        if closing is None:
            continue  # unterminated environment; ledger.validate reports it
        out.append(Span(name, m.start(), closing.end(),
                        scan[inner_start:closing.start()], arg,
                        inner_start, closing.start()))
        pos = closing.end()
    return out


def math_spans(text, scan=None):
    """Every mathematics region, in source order: `$`, `$$`, `\\(`, `\\[`, display envs."""
    scan = blank_comments(text) if scan is None else scan
    prot = protected_spans(text)

    envs = {}
    for m in _BEGIN.finditer(scan):
        if m.group(1).rstrip("*") in DISPLAY_ENVS:
            for s in find_env_spans(scan, [m.group(1)], scan=scan):
                envs.setdefault(s.start, s)

    out, i, n = [], 0, len(scan)
    while i < n:
        skip = _covered(prot, i)
        if skip:
            i = skip
            continue
        if i in envs:
            s = envs[i]
            out.append(s)
            i = s.end
            continue
        c = scan[i]
        if c == "\\":
            nxt = scan[i + 1:i + 2]
            if nxt in ("(", "["):
                close = "\\)" if nxt == "(" else "\\]"
                j = scan.find(close, i + 2)
                if j < 0:
                    break
                out.append(Span("inline" if nxt == "(" else "display",
                                i, j + 2, scan[i + 2:j], None, i + 2, j))
                i = j + 2
                continue
            i += 2
            continue
        if c == "$":
            delim = "$$" if scan.startswith("$$", i) else "$"
            j = i + len(delim)
            while j < n:
                if scan[j] == "\\":
                    j += 2
                    continue
                if scan.startswith(delim, j):
                    break
                j += 1
            if j >= n:
                break
            out.append(Span("display" if delim == "$$" else "inline",
                            i, j + len(delim), scan[i + len(delim):j], None,
                            i + len(delim), j))
            i = j + len(delim)
            continue
        i += 1
    return out


def mask(text, spans, fill=" "):
    """Blank the *bodies* of `spans`, preserving length so offsets still resolve."""
    out = list(text)
    for s in spans:
        for k in range(s.inner_start, min(s.inner_end, len(out))):
            if out[k] != "\n":
                out[k] = fill
    return "".join(out)
