"""The writing report: run header, counts, one entry per W-tag, appendix of what was cut."""
from dataclasses import dataclass, field
from .ledger import LEVELS, COMMENT_ONLY

_TITLES = {"mechanics": "Mechanics", "style": "Sentence clarity and style",
           "flow": "Paragraph and argument flow", "framing": "Terminology and framing"}


@dataclass
class RunHeader:
    paper: str
    mode: str
    date: str
    field_profile: str = None
    author_profile: str = None
    run_rules: list = field(default_factory=list)
    dropped_levels: list = field(default_factory=list)
    builds: dict = field(default_factory=dict)


def _pf(ok):
    return "not run" if ok is None else ("passed" if ok else "failed")


def render_report(rows, header):
    out = ["# Writing report", ""]
    out += [f"**Paper:** {header.paper}", f"**Mode:** {header.mode}", f"**Date:** {header.date}",
            f"**Field profile:** {header.field_profile or 'none'}",
            f"**Author profile:** {header.author_profile or 'none'}",
            f"**Markup build:** {_pf(header.builds.get('markup'))}",
            f"**Accept-all build:** {_pf(header.builds.get('final'))}", ""]
    if header.dropped_levels:
        out += [f"**Dropped to make the build pass:** {', '.join(header.dropped_levels)}", ""]
    out += ["## Run rules", ""]
    out += [f"- {r}" for r in header.run_rules] or ["- none"]
    out += ["", "## Counts", "", "| Level | Applied | Degraded | Cut |", "|---|---|---|---|"]
    for lv in LEVELS:
        a = sum(1 for r in rows if r.level == lv and r.status == "applied")
        d = sum(1 for r in rows if r.level == lv and r.status == "degraded")
        c = sum(1 for r in rows if r.level == lv and r.status in ("cut", "unanchored"))
        out.append(f"| {lv} | {a} | {d} | {c} |")
    out.append("")
    for lv in LEVELS:
        live = [r for r in rows if r.level == lv and r.status in ("applied", "degraded")]
        if not live:
            continue
        out += [f"## {_TITLES[lv]}", ""]
        for r in live:
            out += [f"### {r.id} (§{r.section} ¶{r.para}, {r.status}"
                    + (f": {r.cut_reason}" if r.cut_reason else "") + ")", ""]
            out += ["**Before:**", "", "```", r.anchor, "```", ""]
            if r.level not in COMMENT_ONLY and r.replacement is not None:
                out += ["**After:**", "", "```", r.replacement or "(deleted)", "```", ""]
            out += [f"**Why:** {r.rationale}", "", f"**Rule:** {r.rule or 'n/a'} (confidence {r.confidence})", ""]
    gone = [r for r in rows if r.status in ("cut", "unanchored")]
    out += ["## Cut by the noise gate or unanchored", ""]
    if gone:
        out += ["| Id | Level | Reason | Anchor |", "|---|---|---|---|"]
        out += [f"| {r.id} | {r.level} | {r.cut_reason or ''} | {r.anchor[:60]} |" for r in gone]
    else:
        out.append("Nothing was cut.")
    out.append("")
    return "\n".join(out)


def write_report(rows, header, path):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render_report(rows, header))
