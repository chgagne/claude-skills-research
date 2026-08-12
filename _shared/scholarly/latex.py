"""LaTeX source handling shared by every scholarly skill. Stdlib only.

Both the gap sweep and the head-to-head comparison must read `.tex`: one to learn
what a draft cites and claims, the other to quote a paper's appendix back at a
reviewer. One copy means a fix lands everywhere at once -- and both fixes here
were earned. Globbing `**/*.tex` swept a template's sample file into one sweep
(7 phantom cite keys) and turned 74 sections into 605 in the other, so
`tex_sources` follows `\\input` instead. Numbers hide inside math delimiters
(`$60$ million`, `$10^5$ updates`), so `demath` runs before any extraction.
"""
import os
import re

# Literal strings, not regexes: as a pattern, "\\approx" means the BEL character
# followed by "pprox" and silently matches nothing.
_MATH_CMD = [("\\approx", "~"), ("\\sim", "~"), ("\\times", " x "),
             ("\\!", ""), ("\\,", " "), ("\\;", " ")]

_SECTION = re.compile(
    r"\\(?:sub)*(?:section|paragraph|chapter)\*?\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}")

_INPUT = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")


def demath(text):
    """Strip math delimiters and common spacing commands so numbers are readable."""
    for cmd, repl in _MATH_CMD:
        text = text.replace(cmd, repl)
    text = re.sub(r"\\mathrm\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\text(?:bf|it|rm|sf)?\{([^}]*)\}", r"\1", text)
    return text.replace("{,}", ",").replace("$", "")


def strip_comments(text):
    """Drop LaTeX comments. An escaped \\% is not a comment."""
    out = []
    for line in (text or "").splitlines():
        cut = None
        for i, ch in enumerate(line):
            if ch == "%" and (i == 0 or line[i - 1] != "\\"):
                cut = i
                break
        out.append(line if cut is None else line[:cut])
    return "\n".join(out)


def tex_sources(main_path):
    """main.tex plus everything it \\input/\\include, transitively.

    Globbing instead picks up template samples, annotated copies and superseded
    drafts -- files the document never includes.
    """
    main_path = os.path.abspath(main_path)
    root = os.path.dirname(main_path)
    seen, order, queue = set(), [], [main_path]
    while queue:
        path = queue.pop(0)
        if path in seen or not os.path.exists(path):
            continue
        seen.add(path)
        order.append(path)
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                body = strip_comments(fh.read())
        except OSError:
            continue
        for rel in _INPUT.findall(body):
            cand = os.path.normpath(os.path.join(root, rel.strip()))
            for p in (cand, cand + ".tex"):
                if os.path.exists(p):
                    queue.append(p)
                    break
    return order


def read_sources(main_path):
    """Concatenated text of a document and everything it includes."""
    text = ""
    for f in tex_sources(main_path):
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                text += fh.read() + "\n"
        except OSError:
            continue
    return text


def split_sections(text):
    """[(heading, body)] with headings verbatim. Text before the first heading kept."""
    text = strip_comments(text or "")
    marks = list(_SECTION.finditer(text))
    if not marks:
        body = re.sub(r"\s+", " ", demath(text)).strip()
        return [("(body)", body)] if body else []

    out = []
    lead = re.sub(r"\s+", " ", demath(text[:marks[0].start()])).strip()
    if lead:
        out.append(("(preamble)", lead))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = re.sub(r"\s+", " ", demath(text[m.end():end])).strip()
        # \paragraph{Optimization.} headings carry their trailing punctuation.
        out.append((m.group(1).strip().rstrip(".:"), body))
    return out
