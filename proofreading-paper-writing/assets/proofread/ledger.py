"""Ledger rows: one JSON object per line, one writing proposal per row."""
import json
from dataclasses import dataclass, asdict, fields
from typing import Optional

LEVELS = ("mechanics", "style", "flow", "framing")
STATUSES = ("proposed", "kept", "cut", "applied", "degraded", "unanchored")
COMMENT_ONLY = ("flow", "framing")
MAX_COMMENT_WORDS = 15


@dataclass
class Row:
    id: str
    level: str
    section: str
    para: int
    anchor: str
    replacement: Optional[str]
    comment: str
    rationale: str
    rule: str
    confidence: float
    status: str = "proposed"
    cut_reason: Optional[str] = None


_REQUIRED = {"id", "level", "section", "para", "anchor", "replacement",
             "comment", "rationale", "rule", "confidence"}


def parse_line(s):
    d = json.loads(s)
    missing = _REQUIRED - set(d)
    if missing:
        raise ValueError("missing fields: " + ", ".join(sorted(missing)))
    known = {f.name for f in fields(Row)}
    return Row(**{k: v for k, v in d.items() if k in known})


def validate(row):
    errs = []
    if not isinstance(row.id, str) or not row.id.startswith("W") or not row.id[1:].isdigit():
        errs.append(f"{row.id}: id must look like W12")
    if row.level not in LEVELS:
        errs.append(f"{row.id}: level {row.level!r} not in {LEVELS}")
    if row.status not in STATUSES:
        errs.append(f"{row.id}: status {row.status!r} not in {STATUSES}")
    if not row.anchor or not row.anchor.strip():
        errs.append(f"{row.id}: empty anchor")
    if row.level in COMMENT_ONLY and row.replacement is not None:
        errs.append(f"{row.id}: {row.level} rows are comment-only; replacement must be null")
    if row.level == "style" and not (row.rule or "").strip():
        errs.append(f"{row.id}: style rows need a rule")
    if row.level != "mechanics":
        words = (row.comment or "").split()
        if not words:
            errs.append(f"{row.id}: {row.level} rows need a comment")
        elif len(words) > MAX_COMMENT_WORDS + 1:      # +1 for the W<n>: tag
            errs.append(f"{row.id}: comment over 15 words")
        elif not words[0].startswith(row.id):
            errs.append(f"{row.id}: comment must start with {row.id}:")
    try:
        c = float(row.confidence)
        if not 0.0 <= c <= 1.0:
            raise ValueError
    except (TypeError, ValueError):
        errs.append(f"{row.id}: confidence must be in [0,1]")
    return errs


RENDER_OUTCOMES = ("applied", "degraded", "unanchored")


def reset_render_outcome(row):
    """Restore a previous render's outcome to the gate's decision.

    render-ledger.py writes statuses back into the ledger, and apply_ledger selects
    only rows still marked 'kept'. Without this, a second run over the same ledger
    applies nothing while printing the first run's counts: it reports success and
    leaves the output tex without markup.
    """
    if row.status in RENDER_OUTCOMES:
        row.status, row.cut_reason = "kept", None
    return row


def load_ledger(path):
    rows, errs = [], []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                row = parse_line(line)
            except (ValueError, TypeError) as exc:
                errs.append(f"line {n}: {exc}")
                continue
            for e in validate(row):
                errs.append(f"line {n}: {e}")
            rows.append(reset_render_outcome(row))
    if errs:
        raise ValueError("ledger invalid:\n  " + "\n  ".join(errs))
    return rows


def dump_ledger(rows, path):
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
