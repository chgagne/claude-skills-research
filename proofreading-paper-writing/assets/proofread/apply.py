"""Turn kept ledger rows into markup in the tex, degrading to comments when an edit is unsafe."""
from dataclasses import dataclass
from .anchors import find_all, find_normalised, forbidden_context, paragraph_start, whole_token
from .ledger import COMMENT_ONLY
from .markup import render_edit, render_comment


@dataclass
class Applied:
    tex: str
    rows: list
    applied: int = 0
    degraded: int = 0
    unanchored: int = 0


def _locate(tex, anchor):
    """(spans, how): exact spans if any, else whitespace-normalised spans."""
    exact = [(p, p + len(anchor)) for p in find_all(tex, anchor)]
    if exact:
        return exact, "exact"
    return find_normalised(tex, anchor), "normalised"


def _overlaps(a, b):
    return a[0] < b[1] and b[0] < a[1]


def apply_ledger(tex, rows, levels=None):
    selected = [r for r in rows if r.status == "kept" and (levels is None or r.level in levels)]
    edits = []          # (start, end, text, row) replacing tex[start:end]
    inserts = []        # (pos, text, row) inserted at pos
    taken = []          # (start, end, id) spans already claimed by edits
    result = Applied(tex=tex, rows=rows)

    for r in selected:
        spans, how = _locate(tex, r.anchor)
        if not spans:
            r.status, r.cut_reason = "unanchored", "anchor not found"
            result.unanchored += 1
            continue
        start, end = spans[0]
        comment_only = r.level in COMMENT_ONLY or r.replacement is None
        reason = None
        if not comment_only:
            if len(spans) != 1:
                reason = f"ambiguous anchor ({len(spans)} matches)"
            elif (ctx := forbidden_context(tex, start, end)):
                reason = f"inside {ctx}"
            elif not whole_token(tex, start, end):
                reason = "not a whole token"
            else:
                clash = next((t for t in taken if _overlaps((start, end), t[:2])), None)
                if clash:
                    reason = f"overlaps {clash[2]}"
        if comment_only or reason:
            pos = paragraph_start(tex, start)
            suffix = "; see report" if reason else ""
            inserts.append((pos, render_comment(r, suffix), r))
            if reason:
                r.status, r.cut_reason = "degraded", reason
                result.degraded += 1
            else:
                r.status = "applied"
                result.applied += 1
            continue
        edits.append((start, end, render_edit(r), r))
        taken.append((start, end, r.id))
        r.status = "applied"
        result.applied += 1

    # apply from the end so earlier offsets stay valid; inserts at a position come before edits there
    ops = [(s, 1, e, t) for s, e, t, _ in edits] + [(p, 0, p, t) for p, t, _ in inserts]
    ops.sort(key=lambda o: (o[0], o[1]), reverse=True)
    out = tex
    for start, _, end, text in ops:
        out = out[:start] + text + out[end:]
    result.tex = out
    return result
