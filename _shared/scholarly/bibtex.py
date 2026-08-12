"""BibTeX parsing shared by every scholarly skill. Stdlib only."""
import re
from dataclasses import dataclass, field

from .textnorm import latex_to_unicode  # noqa: F401



@dataclass
class Entry:
    key: str
    etype: str
    fields: dict = field(default_factory=dict)


def _read_balanced(text: str, i: int) -> tuple:
    """Read a {...} group starting at text[i] == '{'. Return (content, next_index)."""
    depth, start = 0, i
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i], i + 1
        i += 1
    return text[start + 1:], len(text)


def _clean(value: str) -> str:
    value = re.sub(r"\s*\n\s*", " ", value).strip()
    return latex_to_unicode(value)


def parse_bib(text: str) -> list:
    entries, i = [], 0
    while True:
        at = text.find("@", i)
        if at == -1:
            return entries
        m = re.match(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text[at:])
        if not m:                          # @string, @comment, or stray '@'
            i = at + 1
            continue
        etype, key = m.group(1).lower(), m.group(2)
        j = at + m.end()
        e = Entry(key=key, etype=etype)
        while j < len(text):
            fm = re.match(r"\s*([A-Za-z][\w-]*)\s*=\s*", text[j:])
            if not fm:
                break
            name = fm.group(1).lower()
            j += fm.end()
            if text[j] == "{":
                raw, j = _read_balanced(text, j)
            elif text[j] == '"':
                k = text.find('"', j + 1)
                raw, j = text[j + 1:k], k + 1
            else:
                k = j
                while k < len(text) and text[k] not in ",}":
                    k += 1
                raw, j = text[j:k], k
            e.fields[name] = _clean(raw)
            while j < len(text) and text[j] in " \t\r\n,":
                j += 1
            if j < len(text) and text[j] == "}":
                j += 1
                break
        entries.append(e)
        i = j
