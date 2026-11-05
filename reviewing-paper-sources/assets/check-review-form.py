#!/usr/bin/env python3
"""Check that a review follows the fixed form of reference/review-template.md.

    python3 check-review-form.py review.md

Prints one line per problem and exits 1, or prints OK and exits 0. Checks: the twelve level-2
headings, verbatim (numbering punctuation and case tolerated), in order, none extra, none empty;
the 14-row coverage checklist with a status (done / issue / n.a.) and evidence in every row; the
§2 recommendation line and the disqualifying line (or the two-line gate of an early draft).
Stdlib only.
"""
import re
import sys

HEADINGS = [
    "1. Summary of the submission",
    "2. Overall assessment",
    "2a. Coverage checklist",
    "3. Strengths",
    "4. Major concerns",
    "4a. Not written yet",
    "5. Bibliography audit",
    "6. Figures and tables",
    "7. Detailed comments by section",
    "8. Writing, formatting, and mechanics",
    "9. Action plan",
    "10. Questions for the authors",
]
CHECKLIST = [
    "Contribution stated in the reviewer's own words",
    "Main claims supported by the results",
    "Experimental protocol (baselines, datasets, splits)",
    "Statistical uncertainty (seeds, variance, significance)",
    "Reproducibility (code, data, hyperparameters, compute)",
    "Positioning against prior work",
    "Clarity and presentation",
    "Limitations and threats to validity",
    "Overall recommendation and prioritised actions",
    "Headline numbers checked against tables, derived numbers recomputed",
    "Appendix checked against claims in the main text",
    "Ablations of the claimed mechanism",
    "Figures (legibility, unexplained series, figure vs table)",
    "Build (compiles, unresolved references, leftover notes)",
]
STATUSES = {"done", "issue", "n.a."}


def key(h):
    h = h.strip().lower()
    h = re.sub(r"^(\d+[a-z]?)[\.\):]?\s+", r"\1 ", h)
    return re.sub(r"[^a-z0-9 ]", "", h).strip()


def sections(text):
    out, cur = [], None
    for line in text.splitlines():
        m = re.match(r"^##\s+(.*?)\s*#*\s*$", line)
        if m and not line.startswith("###"):
            cur = [m.group(1), []]
            out.append(cur)
        elif cur is not None:
            cur[1].append(line)
    return [(h, "\n".join(b)) for h, b in out]


def check(text):
    probs = []
    secs = sections(text)
    want = {key(h): h for h in HEADINGS}
    found = [key(h) for h, _ in secs]
    for h, _ in secs:
        if key(h) not in want:
            probs.append(f"extra level-2 heading not in the form: '{h}' (use ### inside a section)")
    for h in HEADINGS:
        if key(h) not in found:
            probs.append(f"missing heading: '## {h}'")
    order = [k for k in found if k in want]
    if order != [key(h) for h in HEADINGS if key(h) in order]:
        probs.append("headings out of order: expected " + " / ".join(h.split(" ", 1)[0] for h in HEADINGS))
    body = {key(h): b for h, b in secs}
    for h in HEADINGS:
        b = body.get(key(h))
        if b is not None and not b.strip():
            probs.append(f"section '{h}' is empty: keep it and say in one line why there is nothing")
    s2 = body.get(key(HEADINGS[1]), "")
    if s2 and not re.search(r"\*\*Recommendation:", s2):
        probs.append("§2 has no '**Recommendation: <verdict>.**' line")
    if s2 and not (re.search(r"\*\*Disqualifying findings:\*\*", s2)
                   or re.search(r"\*\*Findings that gate the science:\*\*", s2)):
        probs.append("§2 has no '**Disqualifying findings:**' line (or the two-line gate of an early draft)")
    s2a = body.get(key(HEADINGS[2]))
    if s2a is not None:
        rows = {}
        for line in s2a.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if line.strip().startswith("|") and cells and re.fullmatch(r"\d+", cells[0]):
                rows[int(cells[0])] = cells
        for i in range(1, len(CHECKLIST) + 1):
            c = rows.get(i)
            if c is None:
                probs.append(f"checklist row {i} missing ({CHECKLIST[i - 1]})")
                continue
            if len(c) < 4 or c[2].lower() not in STATUSES:
                probs.append(f"checklist row {i}: status must be one of done / issue / n.a.")
            if len(c) < 4 or not c[3]:
                probs.append(f"checklist row {i}: evidence is empty (say what was checked, or why n.a.)")
    return probs


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    probs = check(open(sys.argv[1], encoding="utf-8").read())
    for p in probs:
        print(p)
    if probs:
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
