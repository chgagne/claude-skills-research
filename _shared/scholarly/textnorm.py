"""Text normalisation shared by every scholarly skill. No I/O."""
import html
import re
import unicodedata


_ACCENTS = {
    "'": "\u0301", "`": "\u0300", '"': "\u0308", "^": "\u0302",
    "~": "\u0303", "v": "\u030C", "c": "\u0327", "H": "\u030B",
    "u": "\u0306", ".": "\u0307", "=": "\u0304",
}
_SPECIALS = {r"\ss": "ß", r"\o": "ø", r"\O": "Ø", r"\aa": "å", r"\AA": "Å",
             r"\ae": "æ", r"\AE": "Æ", r"\l": "ł", r"\L": "Ł"}


def latex_to_unicode(s: str) -> str:
    """Convert LaTeX accent commands to composed Unicode, then drop braces."""
    for k, v in _SPECIALS.items():
        s = s.replace(k, v)
    # dotless i/j carry the accent on the base letter
    s = s.replace(r"\i", "i").replace(r"\j", "j")

    def repl(m):
        acc, ch = m.group(1), m.group(2)
        comb = _ACCENTS.get(acc)
        if not comb:
            return m.group(0)
        return unicodedata.normalize("NFC", ch + comb)

    pattern = r"\\([\'`\"^~vcHu.=])\s*\{?([A-Za-z])\}?"
    prev = None
    while prev != s:                      # nested braces need repeated passes
        prev = s
        s = re.sub(pattern, repl, s)
    s = s.replace("{", "").replace("}", "")
    return s

# DBLP returns HTML-escaped names (O&apos;Reilly) while .bib files use either an
# ASCII or a typographic apostrophe. Both must fold to the same thing.
_QUOTES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'",
                         "`": "'", "´": "'"})


def strip_dblp_suffix(name: str) -> str:
    """DBLP appends ' 0001' to disambiguate homonyms."""
    return re.sub(r"\s+\d{4}$", "", name).strip()


def fold(s: str) -> str:
    s = html.unescape(latex_to_unicode(s)).translate(_QUOTES)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.casefold().strip()


def norm_title(s: str) -> str:
    s = fold(s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def split_authors(value: str) -> list:
    parts = re.split(r"\s+and\s+", value.strip())
    return [p.strip().rstrip(",") for p in parts if p.strip()]


def family_key(name: str) -> str:
    """Family name, folded. Handles 'Last, First', 'First Last', 'M Vastl'.

    Keyed on the final token of the family part so a compound surname matches
    across name orders: 'Molina Leon, Gabriela' and 'Gabriela Molina Leon' both
    key on 'leon'. Without this, the comma form keys on the full compound and
    the natural order keys on the last word, and they never match.
    """
    name = strip_dblp_suffix(latex_to_unicode(name)).strip()
    if "," in name:
        family = name.split(",", 1)[0]
    else:
        tokens = [t for t in name.split() if t]
        family = tokens[-1] if tokens else name
    parts = [p for p in fold(family).split() if p]
    return parts[-1] if parts else fold(family)


def given_initial(name: str) -> str:
    """First initial of the given name(s). Empty when there is no given part.

    Deliberately separate from family_key: family matching must ignore given
    names (that is what kills the initials-only false alarms), so given-name
    checking is a distinct, lower-severity signal.
    """
    name = strip_dblp_suffix(latex_to_unicode(name)).strip()
    if "," in name:
        given = name.split(",", 1)[1]
    else:
        tokens = [t for t in name.split() if t]
        given = " ".join(tokens[:-1])
    for ch in fold(given):
        if ch.isalpha():
            return ch
    return ""


def author_diff(bib: list, rec: list) -> tuple:
    """Compare on family name. Returns (only_in_bib, only_in_record)."""
    bib_map, rec_map = {}, {}
    for n in bib:
        bib_map.setdefault(family_key(n), []).append(n)
    for n in rec:
        rec_map.setdefault(family_key(n), []).append(n)
    only_bib, only_rec = [], []
    for k, names in bib_map.items():
        if k not in rec_map:
            only_bib.extend(names)
    for k, names in rec_map.items():
        if k not in bib_map:
            only_rec.extend(names)
    return only_bib, only_rec
