"""User macro table and bounded expansion. Stdlib only.

A real ML appendix is written in the author's own vocabulary -- `\\encS`, `\\D`,
`\\fstar`, `\\argmin` -- and an unexpanded ledger records symbols that do not
exist while missing the ones that do. Expansion happens once, at ingest, and
everything downstream sees `\\mathrm{enc}_S` rather than a macro name.

Two rules that look fussy and are not:

- **Longest-name matching.** `\\encS` is not `\\enc` followed by `S`. Expanding it
  as one silently rewrites a different symbol.
- **Bounded depth.** `\\def\\x{\\x y}` is legal and would not terminate. Depth is
  capped and every macro still present afterwards is *reported*, because a macro
  the ledger could not expand is a step it cannot check.
"""
import re

from .tokenize import balanced, blank_comments, _bracketed

# A macro whose body reaches for one of these is a cross-reference or citation
# helper, not mathematics. Without this, `\secref{sec:proofs}` puts "Section"
# into the symbol inventory of every proof that navigates.
_NON_MATH = re.compile(
    r"\\(?:ref|cref|Cref|autoref|pageref|eqref|nameref|cite[A-Za-z]*|label"
    r"|url|href|footnote|caption|textcite|citet|citep)\b")

_DEF = re.compile(r"\\(newcommand|renewcommand|providecommand"
                  r"|DeclareMathOperator|def)(\*?)")

_CALL = re.compile(r"\\([A-Za-z@]+)")


def _macro_name_at(text, k):
    """Read a macro name written either as `{\\name}` or bare as `\\name`."""
    while k < len(text) and text[k] in " \t\n":
        k += 1
    if k < len(text) and text[k] == "{":
        body, end = balanced(text, k)
        if body is None:
            return None, k
        m = re.match(r"\s*\\([A-Za-z@]+)\s*$", body)
        return (m.group(1) if m else None), end
    m = re.match(r"\\([A-Za-z@]+)", text[k:])
    if m:
        return m.group(1), k + m.end()
    return None, k


def _subst(body, args):
    """Replace `#1`..`#9` in a macro body. `##` is a literal `#`."""
    out, i, n = [], 0, len(body)
    while i < n:
        c = body[i]
        if c == "#" and i + 1 < n:
            nxt = body[i + 1]
            if nxt == "#":
                out.append("#")
                i += 2
                continue
            if nxt.isdigit():
                k = int(nxt)
                out.append(args[k - 1] if 1 <= k <= len(args) else "")
                i += 2
                continue
        out.append(c)
        i += 1
    return "".join(out)


class MacroTable:
    """Name -> definition, with transitive expansion capped at `depth`."""

    def __init__(self, defs=None):
        self.defs = dict(defs or {})

    # ---- construction ----------------------------------------------------

    @classmethod
    def from_text(cls, text):
        t = cls()
        t.ingest(text)
        return t

    @classmethod
    def from_sources(cls, main_path):
        """Read a document and everything it `\\input`s, in document order."""
        from scholarly import latex as _slatex
        t = cls()
        for path in _slatex.tex_sources(main_path):
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    t.ingest(fh.read())
            except OSError:
                continue
        return t

    def ingest(self, text):
        """Read every definition in `text`. Later definitions win, as in LaTeX."""
        scan = blank_comments(text or "")
        for m in _DEF.finditer(scan):
            cmd, star = m.group(1), m.group(2)
            if cmd == "def":
                self._read_def(scan, m.end())
            elif cmd == "DeclareMathOperator":
                self._read_operator(scan, m.end(), star)
            else:
                self._read_newcommand(scan, m.end(), cmd)

    def _read_newcommand(self, scan, k, cmd):
        name, k = _macro_name_at(scan, k)
        if name is None:
            return
        nargs, default = 0, None
        opt = re.match(r"\s*\[", scan[k:])
        if opt:
            body, end = _bracketed(scan, k + opt.end() - 1)
            if end > 0 and body is not None and body.strip().isdigit():
                nargs, k = int(body.strip()), end
                opt2 = re.match(r"\s*\[", scan[k:])
                if opt2:
                    body2, end2 = _bracketed(scan, k + opt2.end() - 1)
                    if end2 > 0:
                        default, k = body2, end2
        while k < len(scan) and scan[k] in " \t\n":
            k += 1
        body, end = balanced(scan, k)
        if body is None:
            return
        if cmd == "providecommand" and name in self.defs:
            return
        self.defs[name] = {"nargs": nargs, "default": default, "body": body}

    def _read_operator(self, scan, k, star):
        name, k = _macro_name_at(scan, k)
        if name is None:
            return
        while k < len(scan) and scan[k] in " \t\n":
            k += 1
        body, end = balanced(scan, k)
        if body is None:
            return
        self.defs[name] = {"nargs": 0, "default": None,
                           "body": "\\operatorname%s{%s}" % (star, body)}

    def _read_def(self, scan, k):
        m = re.match(r"\\([A-Za-z@]+)", scan[k:])
        if not m:
            return
        name, k = m.group(1), k + m.end()
        params = ""
        while k < len(scan) and scan[k] != "{":
            params += scan[k]
            k += 1
        body, end = balanced(scan, k)
        if body is None:
            return
        self.defs[name] = {"nargs": len(re.findall(r"#\d", params)),
                           "default": None, "body": body}

    # ---- use -------------------------------------------------------------

    def is_math_macro(self, name):
        """False for cross-reference and citation helpers, whose bodies are prose."""
        d = self.defs.get(name)
        return bool(d) and not _NON_MATH.search(d["body"])

    def _grab_arg(self, text, k):
        """One macro argument: a brace group, a control sequence, or a single token."""
        while k < len(text) and text[k] in " \t\n":
            k += 1
        if k >= len(text):
            return "", k
        if text[k] == "{":
            body, end = balanced(text, k)
            if body is not None:
                return body, end
            return "", k
        m = re.match(r"\\[A-Za-z@]+", text[k:])
        if m:
            return m.group(0), k + m.end()
        return text[k], k + 1

    def _expand_once(self, text):
        out, i, n, changed = [], 0, len(text), False
        while i < n:
            m = _CALL.match(text, i)
            if not m:
                out.append(text[i])
                i += 1
                continue
            name = m.group(1)
            d = self.defs.get(name)
            if d is None:
                out.append(m.group(0))
                i = m.end()
                continue
            k, args = m.end(), []
            if d["default"] is not None:
                opt = re.match(r"\s*\[", text[k:])
                if opt:
                    body, end = _bracketed(text, k + opt.end() - 1)
                    args.append(body if body is not None else d["default"])
                    if end > 0:
                        k = end
                else:
                    args.append(d["default"])
            while len(args) < d["nargs"]:
                a, k = self._grab_arg(text, k)
                args.append(a)
            out.append(_subst(d["body"], args))
            i = k
            changed = True
        return "".join(out), changed

    def expand(self, tex, depth=8):
        """Expanded text, plus the names of macros that survived the depth cap."""
        cur, unexpanded = tex or "", set()
        for _ in range(depth):
            nxt, changed = self._expand_once(cur)
            cur = nxt
            if not changed:
                return cur, unexpanded
        for m in _CALL.finditer(cur):
            if m.group(1) in self.defs:
                unexpanded.add(m.group(1))
        return cur, unexpanded
