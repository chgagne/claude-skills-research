"""Emit changes.sty markup for the LG author. Recipe rules from
reviewing-paper-sources/reference/annotating-with-changes.md are encoded here:
comments go BEFORE a replacement, never inside; multi-key cites get \\mbox."""
import re
from .ledger import COMMENT_ONLY

AUTHOR = "LG"
_CITE = re.compile(r"(\\cite[pt]?\*?(?:\[[^\]]*\]){0,2}\{[^}]*\})")
_SPECIAL = {"%": r"\%", "&": r"\&", "_": r"\_", "#": r"\#", "{": r"\{", "}": r"\}", "$": r"\$"}


def wrap_cites(s):
    return _CITE.sub(r"\\mbox{\1}", s)


def escape_comment(s):
    return "".join(_SPECIAL.get(c, c) for c in s or "")


def comment(text, author=AUTHOR):
    return r"\chcomment[id=%s]{%s}" % (author, escape_comment(text))


def replaced(new, old, author=AUTHOR):
    return r"\chreplaced[id=%s]{%s}{%s}" % (author, wrap_cites(new), wrap_cites(old))


def deleted(old, author=AUTHOR):
    return r"\chdeleted[id=%s]{%s}" % (author, wrap_cites(old))


def render_edit(row):
    if row.level in COMMENT_ONLY or row.replacement is None:
        raise ValueError(f"{row.id}: comment-only row cannot be rendered as an edit")
    body = deleted(row.anchor) if row.replacement == "" else replaced(row.replacement, row.anchor)
    if row.level == "style" and row.comment:
        return comment(row.comment) + body
    return body


def render_comment(row, suffix=""):
    return comment((row.comment or f"{row.id}: see report") + suffix)
