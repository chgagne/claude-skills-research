"""Aligned plain-text columns as one ``rich.text.Text`` (no table borders),
for the per-cluster sections of the Usage and Storage tabs."""
from __future__ import annotations

import re

from rich.text import Text

GAP = "  "


def grid(rows: list[list[Text]], right=(), indent: int = 0) -> Text:
    """Pad each column to its widest cell; columns in ``right`` align right.
    Rows may be shorter than the widest row."""
    right = set(right)
    ncol = max((len(r) for r in rows), default=0)
    widths = [max((r[i].cell_len for r in rows if i < len(r)), default=0)
              for i in range(ncol)]
    out = Text()
    for n, r in enumerate(rows):
        if n:
            out.append("\n")
        out.append(" " * indent)
        for i, cell in enumerate(r):
            pad = " " * (widths[i] - cell.cell_len)
            if i:
                out.append(GAP)
            if i in right:
                out.append(pad)
                out.append_text(cell)
            else:
                out.append_text(cell)
                if i < len(r) - 1:
                    out.append(pad)
    return out


def wid(prefix: str, name: str) -> str:
    """A widget id for a cluster name (ids allow letters, digits, - and _)."""
    return f"{prefix}-{re.sub(r'[^A-Za-z0-9_-]', '_', name)}"
