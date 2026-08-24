"""Text extraction and reflowing."""

from __future__ import annotations

import re
import shutil
import subprocess


class PdftotextMissing(RuntimeError):
    pass


def _pdftotext(pdf: str, *args: str) -> str:
    exe = shutil.which("pdftotext")
    if exe is None:
        raise PdftotextMissing(
            "pdftotext not found. It ships with poppler "
            "(brew install poppler / apt install poppler-utils). "
            "Ask before installing."
        )
    out = subprocess.run(
        [exe, *args, pdf, "-"], capture_output=True, text=True, check=False
    )
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or "pdftotext failed")
    return out.stdout


def extract_text(pdf: str, layout: bool = False, first: int | None = None,
                 last: int | None = None) -> str:
    """Raw text. `layout` preserves column geometry, which helps for tables and
    hurts for prose."""
    args = []
    if layout:
        args.append("-layout")
    if first is not None:
        args += ["-f", str(first)]
    if last is not None:
        args += ["-l", str(last)]
    return _pdftotext(pdf, *args)


def page_count(pdf: str) -> int:
    exe = shutil.which("pdfinfo")
    if exe is None:
        # Fall back to counting form feeds in the text layer.
        return extract_text(pdf).count("\f") or 1
    out = subprocess.run([exe, pdf], capture_output=True, text=True, check=False)
    m = re.search(r"^Pages:\s+(\d+)", out.stdout, re.M)
    return int(m.group(1)) if m else 1


def pages(pdf: str, layout: bool = False) -> list[str]:
    """Text split per page. pdftotext emits a form feed between pages."""
    raw = extract_text(pdf, layout=layout)
    parts = raw.split("\f")
    if parts and not parts[-1].strip():
        parts.pop()
    return parts


def flow(text: str) -> str:
    """Undo hard wrapping so multi-word phrases become searchable.

    pdftotext hard-wraps at the typeset line break. Two substitutions recover
    running prose: rejoin words split across a line by a hyphen, then join a
    line to the next when the next begins lowercase (i.e. is a continuation).

    Known blind spot: a phrase straddling a break before a capitalised token
    ("...in in\\nEq. 3") survives unjoined, because the second rule keys on a
    lowercase successor. Search the raw text as well as the flowed text.
    """
    text = re.sub(r"-\n(?=[a-z])", "", text)
    text = re.sub(r"\n(?=[a-z(])", " ", text)
    return text


_REFS_HEADING = re.compile(r"^\s*(References|REFERENCES|Bibliography)\s*$", re.M)


def split_at_references(text: str) -> tuple[str, str]:
    """(body, references). Returns ('', text) if no heading is found.

    Uses the LAST heading match, since an appendix commonly carries a second
    reference list and the later one is the one a naive split would miss.
    """
    matches = list(_REFS_HEADING.finditer(text))
    if not matches:
        return text, ""
    m = matches[0]
    return text[: m.start()], text[m.end():]


def reference_sections(text: str) -> list[str]:
    """Every reference list in the document, in order.

    A paper can carry more than one: a main bibliography and a separate list of
    dataset or resource citations in the appendix. Auditing only the first is
    how uncited baselines survive review.
    """
    matches = list(_REFS_HEADING.finditer(text))
    out = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append(text[m.end():end])
    return out
