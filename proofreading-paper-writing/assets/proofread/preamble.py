"""Make a tex file ready for LG markup: changes preamble, second author, known clashes."""
import re

LG_AUTHOR_LINE = r"\definechangesauthor[name={Claude (writing)}, color=green!50!black]{LG}"
ULEM_WORKAROUND = (
    "% LG: review copy only -- NEVER submit. Clears ulem's marker so a class that forbids it still builds.\n"
    "\\makeatletter\n"
    "\\expandafter\\let\\csname ver@ulem.sty\\endcsname\\@undefined\n"
    "\\makeatother\n")

_CHANGES = re.compile(r"^[ \t]*\\usepackage(\[[^\]]*\])?\{changes\}.*$", re.M)
_AUTHOR = re.compile(r"\\definechangesauthor(\[[^\]]*\])?\{(?P<id>[A-Za-z]+)\}")
_USEPACKAGE = re.compile(r"^[ \t]*\\(?:usepackage|RequirePackage)(\[[^\]]*\])?\{[^}]*\}.*$", re.M)
_DOCCLASS = re.compile(r"^[ \t]*\\documentclass(\[[^\]]*\])?\{[^}]*\}.*$", re.M)
_TODO_DEF = re.compile(r"^[ \t]*\\(?:newcommand\*?|renewcommand\*?|def|providecommand\*?)\s*\{?\\todo\}?.*$", re.M)
_BEGIN_DOC = re.compile(r"^[ \t]*\\begin\{document\}", re.M)


def has_changes(tex):
    return _CHANGES.search(tex) is not None


def has_author(tex, author="LG"):
    return any(m.group("id") == author for m in _AUTHOR.finditer(tex))


def todo_definition(tex):
    return _TODO_DEF.search(tex)


def _insertion_point(tex):
    """End of the last \\usepackage line before \\begin{document}, else after \\documentclass."""
    begin = _BEGIN_DOC.search(tex)
    limit = begin.start() if begin else len(tex)
    last = None
    for m in _USEPACKAGE.finditer(tex, 0, limit):
        last = m
    if last is None:
        last = _DOCCLASS.search(tex)
    if last is None:
        return 0
    return last.end()


def ensure_changes(tex, preamble_text, forbid_ulem=False):
    out = tex
    if not has_changes(out):
        pos = _insertion_point(out)
        block = "\n" + preamble_text.rstrip("\n") + "\n"
        tdef = todo_definition(out)
        if tdef and tdef.start() < pos:
            block = "\n\\let\\todo\\relax" + block
        out = out[:pos] + block + out[pos:]
    changes_line = _CHANGES.search(out)
    # a \todo defined after the changes load would clash with todonotes: comment it out
    for m in list(_TODO_DEF.finditer(out)):
        if m.start() > changes_line.end():
            out = out[:m.start()] + "% LG: freed for todonotes -- " + m.group(0).lstrip() + out[m.end():]
            changes_line = _CHANGES.search(out)
    if forbid_ulem and ULEM_WORKAROUND.strip() not in out:
        out = out[:changes_line.end()] + "\n" + ULEM_WORKAROUND.rstrip("\n") + out[changes_line.end():]
        changes_line = _CHANGES.search(out)
    if not has_author(out):
        authors = [m for m in _AUTHOR.finditer(out)]
        anchor_end = authors[-1].end() if authors else changes_line.end()
        # end of that line
        eol = out.find("\n", anchor_end)
        eol = len(out) if eol == -1 else eol
        out = out[:eol] + "\n" + LG_AUTHOR_LINE + out[eol:]
    return out
