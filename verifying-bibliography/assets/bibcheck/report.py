"""Pure formatting. No I/O beyond returning strings."""
import csv
import io

ORDER = ["CRITICAL", "MAJOR", "MINOR", "WEAK", "UNVERIFIED", "SKIP"]

BLURB = {
    "CRITICAL": "Wrong title under a resolved identifier, an author in the .bib who is "
                "not on the record, or a DOI that does not resolve. Treat as fabrication "
                "until shown otherwise.",
    "MAJOR": "Metadata disagrees with a record reached by a stable identifier.",
    "MINOR": "Name form, punctuation, or a field the venue does not use.",
    "WEAK": "Matched by title search only. Not verified — a human must check these.",
    "UNVERIFIED": "No source returned a record. This is a finding, not a pass.",
    "SKIP": "Non-paper entry (blog, web page, artifact). Check the URL by hand.",
}


def _cell(v):
    return str(v or "").replace("|", "\\|").replace("\n", " ")


def to_markdown(findings, total, checked):
    lines = ["# Bibliography verification report", "",
             f"Entries in file: {total}. Entries checked: {checked}.", ""]
    for sev in ORDER:
        group = [f for f in findings if f.severity == sev]
        if not group:
            continue
        lines += [f"## {sev} ({len(group)})", "", BLURB[sev], "",
                  "| Key | Field | In .bib | In record | Source |",
                  "|---|---|---|---|---|"]
        for f in group:
            lines.append(f"| `{f.key}` | {_cell(f.field)} | {_cell(f.in_bib)} "
                         f"| {_cell(f.in_record)} | {_cell(f.source)} |")
        lines.append("")
    if not findings:
        lines.append("No findings.")
    return "\n".join(lines)


def to_csv(findings):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["key", "field", "in_bib", "in_record", "source", "severity"])
    for f in findings:
        w.writerow([f.key, f.field, f.in_bib, f.in_record, f.source, f.severity])
    return buf.getvalue()
