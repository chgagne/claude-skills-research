"""Framing of the remote script's output (stdlib only).

Frame: ``@@dracmon begin <name>\\n<raw output>\\n@@dracmon end <name> rc=<int>\\n``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

BEGIN = re.compile(r"^@@dracmon begin (\S+)$")
END = re.compile(r"^@@dracmon end (\S+) rc=(-?\d+)$")


@dataclass
class Section:
    name: str
    rc: int | None
    body: str
    complete: bool


def parse_frames(text: str) -> dict[str, Section]:
    """Parse framed output. Text outside frames is ignored; a section whose
    end marker is missing (truncated stream) is returned incomplete."""
    sections: dict[str, Section] = {}
    cur: str | None = None
    lines: list[str] = []

    def close_open() -> None:
        if cur is not None:
            sections[cur] = Section(cur, None, "".join(lines), False)

    for line in text.splitlines():
        m = BEGIN.match(line)
        if m:
            close_open()
            cur, lines = m.group(1), []
            continue
        m = END.match(line)
        if m and cur is not None and m.group(1) == cur:
            sections[cur] = Section(cur, int(m.group(2)), "".join(lines), True)
            cur, lines = None, []
            continue
        if cur is not None:
            lines.append(line + "\n")
    close_open()
    return sections


def render_frames(sections) -> str:
    """Inverse of parse_frames for complete sections (incomplete ones are skipped)."""
    out = []
    for s in sections:
        if not s.complete:
            continue
        body = s.body if (not s.body or s.body.endswith("\n")) else s.body + "\n"
        out.append(f"@@dracmon begin {s.name}\n{body}@@dracmon end {s.name} rc={s.rc}\n")
    return "".join(out)
