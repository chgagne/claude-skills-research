"""Turn an Antidote pass over a copy of the tex into mechanics rows for the ledger.

Antidote fixes words well but edits LaTeX blindly: it unescapes \\%, drops the space
before \\cite, pastes fragments of citation keys into prose and reflows lines. So the
corrected copy is never used directly. It is diffed against the original token by token
(whitespace, ~ and no-break spaces are separators, so reflow and spacing vanish), and
each change becomes either a mechanics row anchored in the original, or a review item
with the reason it was refused.
"""
import difflib, re, unicodedata
from .anchors import find_normalised, forbidden_context, whole_token
from .ledger import Row

_SEP = re.compile(r"[^\s~\u00a0\u202f]+")
_KEYS = re.compile(r"\\(?:cite[a-zA-Z]*|ref|eqref|autoref|[cC]ref|label)\*?(?:\[[^\]]*\])*\{([^}]*)\}")
_COMMENT = re.compile(r"(?<!\\)%.*")
_UNESCAPED_PCT = re.compile(r"(?<!\\)%")
_CS = re.compile(r"\\(?:[A-Za-z]+|.)")
_PUNCT = ".,;:!?()«»\"'’"
_SECTION = re.compile(r"\\(sub)?section\*?\s*(?:\[[^\]]*\])?\{")
_ABSTRACT = re.compile(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", re.S)
_BLANK = re.compile(r"\n[ \t]*\n")
MAX_REWRITE_TOKENS = 3      # an unequal hunk longer than this is a rewrite, not a fix
MIN_SIMILARITY = 0.5
MAX_CONTEXT = 8


def _tokens(tex):
    return [(m.group(0), m.start(), m.end()) for m in _SEP.finditer(tex)]


def _fold(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def _similar(old, new):
    return difflib.SequenceMatcher(None, _fold(" ".join(old)), _fold(" ".join(new))).ratio()


def _comment_spans(tex):
    return [(m.start(), m.end()) for m in _COMMENT.finditer(tex)]


def _refusal(old, new, keys):
    """Why this change may not become a row, or None."""
    joined_old, joined_new = " ".join(old), " ".join(new)
    if _UNESCAPED_PCT.search(joined_new) and not _UNESCAPED_PCT.search(joined_old):
        return "unescaped % (the rest of the line would become a comment)"
    if set(_CS.findall(joined_old)) - set(_CS.findall(joined_new)):
        return "drops a LaTeX escape or command"
    if any(ch in tok for tok in old + new for ch in "\\{}$"):
        return "touches LaTeX markup"
    cores = {t.strip(_PUNCT) for t in new} - {t.strip(_PUNCT) for t in old}
    if cores & keys:
        return "copies a citation key or label into prose (garbled)"
    if _similar(old, new) < MIN_SIMILARITY:
        return "low similarity: a rewrite or a garble, review by hand"
    return None


def _section_of(tex, pos):
    for m in _ABSTRACT.finditer(tex):
        if m.start() <= pos < m.end():
            return "Abstract", m.start(1)
    sec = sub = 0
    head_end = 0
    for m in _SECTION.finditer(tex, 0, pos):
        if m.group(1):
            sub += 1
        else:
            sec, sub = sec + 1, 0
        close = tex.find("}", m.end())
        head_end = close + 1 if close != -1 else m.end()
    label = f"{sec}.{sub}" if sub else str(sec)
    return label, head_end


def _para_of(tex, start_of_section, pos):
    chunks = _BLANK.split(tex[start_of_section:pos + 1])
    return max(1, sum(1 for c in chunks if c.strip()))


def _anchor(orig, toks, i, j):
    """Smallest unique whole-token span of orig tokens [i', j') containing [i, j)."""
    lo, hi = i, j
    for step in range(2 * MAX_CONTEXT + 1):
        s, e = toks[lo][1], toks[hi - 1][2]
        if whole_token(orig, s, e) and len(find_normalised(orig, orig[s:e])) == 1:
            return lo, hi
        grow_left = step % 2 == 0
        if grow_left and lo > 0 and "\\" not in toks[lo - 1][0]:
            lo -= 1
        elif hi < len(toks) and "\\" not in toks[hi][0]:
            hi += 1
        elif lo > 0 and "\\" not in toks[lo - 1][0]:
            lo -= 1
        else:
            break
    return None


def _hunks(ot, nt):
    """Diff opcodes, split as finely as the tokens allow: equal-length replacements into
    1:1 pairs, and unequal ones re-aligned on accent- and case-folded tokens, so "a 92,1\\%"
    -> "à 92,1~%" yields the fix a -> à apart from the damaged number."""
    sm = difflib.SequenceMatcher(None, [t[0] for t in ot], [t[0] for t in nt], autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace" and i2 - i1 == j2 - j1:
            for k in range(i2 - i1):
                if ot[i1 + k][0] != nt[j1 + k][0]:
                    yield i1 + k, i1 + k + 1, j1 + k, j1 + k + 1, True
            continue
        fold = difflib.SequenceMatcher(None, [_fold(t[0]) for t in ot[i1:i2]],
                                       [_fold(t[0]) for t in nt[j1:j2]], autojunk=False)
        for t2, a1, a2, b1, b2 in fold.get_opcodes():
            if t2 == "equal":
                for k in range(a2 - a1):
                    if ot[i1 + a1 + k][0] != nt[j1 + b1 + k][0]:
                        yield i1 + a1 + k, i1 + a1 + k + 1, j1 + b1 + k, j1 + b1 + k + 1, True
            else:
                yield i1 + a1, i1 + a2, j1 + b1, j1 + b2, False


def antidote_rows(orig, corrected, start, existing=()):
    """(rows, rejected). rows are mechanics Rows anchored in orig, ids from W<start>;
    rejected are dicts {line, before, after, reason} for a human or the agent to review."""
    ot, nt = _tokens(orig), _tokens(corrected)
    keys = {k.strip() for m in _KEYS.finditer(orig) for k in m.group(1).split(",")}
    comments = _comment_spans(orig)
    taken = []
    for r in existing:
        for s, e in find_normalised(orig, r.anchor):
            taken.append((s, e, r.id))

    items = []      # (i1, i2, j1, j2, paired, reason)
    for i1, i2, j1, j2, paired in _hunks(ot, nt):
        old = [t[0] for t in ot[i1:i2]]
        new = [t[0] for t in nt[j1:j2]]
        pos = ot[i1][1] if i1 < len(ot) else len(orig)
        reason = "inside a LaTeX comment" if any(s <= pos < e for s, e in comments) else None
        reason = reason or _refusal(old, new, keys)
        if reason is None and not paired and max(len(old), len(new)) > MAX_REWRITE_TOKENS:
            reason = "rewrite, not a mechanics fix: review by hand"
        if reason is None and i1 < i2 and (ctx := forbidden_context(orig, ot[i1][1], ot[i2 - 1][2])):
            reason = f"inside {ctx}"
        items.append([i1, i2, j1, j2, paired, reason])

    # a pair next to a garbled pair is part of the garble: refuse it too
    for a, b in zip(items, items[1:]):
        if a[4] and b[4] and a[1] == b[0]:
            if a[5] and "garble" in a[5] and not b[5]:
                b[5] = "next to a garbled span"
            if b[5] and "garble" in b[5] and not a[5]:
                a[5] = "next to a garbled span"

    rows, rejected = [], []
    n = start
    for i1, i2, j1, j2, paired, reason in items:
        before = orig[ot[i1][1]:ot[i2 - 1][2]] if i1 < i2 else ""
        after = corrected[nt[j1][1]:nt[j2 - 1][2]] if j1 < j2 else ""
        line = orig.count("\n", 0, ot[min(i1, len(ot) - 1)][1]) + 1
        if reason is None:
            # insertions and deletions anchor on the token before them
            ai, aj = (i1, i2) if i1 < i2 else (max(i1 - 1, 0), max(i1, 1))
            span = _anchor(orig, ot, ai, aj)
            if span is None:
                reason = "no unique anchor"
        if reason is None:
            lo, hi = span
            s, e = ot[lo][1], ot[hi - 1][2]
            hs = ot[i1][1] if i1 < i2 else ot[aj - 1][2]
            he = ot[i2 - 1][2] if i1 < i2 else ot[aj - 1][2]
            glue = " " if i1 == i2 and after else ""
            new_text = after.replace("\u00a0", "~").replace("\u202f", "~")
            replacement = orig[s:hs] + glue + new_text + orig[he:e]
            if i1 < i2 and not after:
                replacement = re.sub(r"[ \t]+", " ", replacement).strip()
            clash = next((t for t in taken if t[0] < e and s < t[1]), None)
            if clash:
                reason = f"duplicate of {clash[2]}"
        if reason is not None:
            if rejected and rejected[-1]["_end"] == i1:
                prev = rejected[-1]
                prev["before"] = orig[prev["_start"]:ot[i2 - 1][2]] if i1 < i2 else prev["before"]
                prev["after"] = (prev["after"] + " " + after).strip()
                prev["_end"] = i2
                if reason not in prev["reason"]:
                    prev["reason"] += "; " + reason
            else:
                rejected.append({"line": line, "before": before, "after": after, "reason": reason,
                                 "_start": ot[i1][1] if i1 < len(ot) else len(orig), "_end": i2})
            continue
        section, sec_start = _section_of(orig, s)
        rows.append(Row(id=f"W{n}", level="mechanics", section=section,
                        para=_para_of(orig, sec_start, s), anchor=orig[s:e],
                        replacement=replacement, comment="",
                        rationale=f"Antidote: «{before or orig[s:e]}» → «{after}».",
                        rule="tool:antidote", confidence=0.8))
        taken.append((s, e, f"W{n}"))
        n += 1
    for x in rejected:
        x.pop("_start", None); x.pop("_end", None)
    return rows, rejected
