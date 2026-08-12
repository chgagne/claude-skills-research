"""Render a gap sweep. Pure formatting."""
import json

ORDER = ["THREAT", "RELATED", "BACKGROUND"]

BLURB = {
    "THREAT": ("On the contribution *and* reachable from more than one direction "
               "in the citation graph. Each of these needs a response in the "
               "paper: cite and distinguish it, or narrow the novelty claim."),
    "RELATED": ("Topically close, or reached from several directions. Usually a "
                "one-line citation in related work."),
    "BACKGROUND": ("Reached once, no overlap with the contribution. Listed for "
                   "completeness; most of this is noise."),
}


def _cell(v):
    return str(v if v is not None else "").replace("|", "\\|").replace("\n", " ")


def _cites(v):
    """Unknown is not zero: arXiv and DBLP report no counts at all."""
    return "n/r" if v is None else str(v)


def _why(paths, limit=3):
    kinds = []
    for p in paths:
        kind = p.split(":", 1)[0]
        if kind not in kinds:
            kinds.append(kind)
    shown = ", ".join(kinds[:limit])
    return f"{shown} ({len(paths)})"


def to_markdown(ranked, seed, unresolved):
    lines = ["# Related work the draft may have missed", ""]
    if seed.title:
        lines += [f"**Paper:** {seed.title}", ""]
    lines += [f"Seeded from {len(seed.cited_titles)} cited works and "
              f"{len(seed.angles)} topical angles. "
              f"{len(ranked)} candidates after removing everything already cited.", ""]

    if not ranked:
        lines += ["No candidates. Either the draft's citations could not be "
                  "resolved by any index, or every neighbour is already cited — "
                  "check the coverage note below before reading this as a clean bill.",
                  ""]

    for grade in ORDER:
        group = [r for r in ranked if r[2] == grade]
        if not group:
            continue
        lines += [f"## {grade} ({len(group)})", "", BLURB[grade], "",
                  "| Paper | Year | Venue | Why it surfaced | Cites | DOI |",
                  "|---|---|---|---|---|---|"]
        for c, _score, _g in group:
            lines.append(
                f"| {_cell(c.title)} | {_cell(c.year)} | {_cell(c.venue)} "
                f"| {_cell(_why(c.paths))} | {_cites(c.cited_by_count)} | {_cell(c.doi)} |")
        lines.append("")

    lines += ["## Coverage", ""]
    if unresolved:
        lines += [f"{len(unresolved)} cited work(s) could not be resolved by any "
                  f"index, so nothing was explored from them. Anonymous artifacts, "
                  f"blog posts and workshop papers legitimately land here, but the "
                  f"sweep saw less of the graph than the bibliography size suggests:",
                  ""]
        lines += [f"- {_cell(t)}" for t in unresolved]
    else:
        lines.append("Every cited work resolved; the whole bibliography was explored.")
    lines += ["",
              "`n/r` in the Cites column means no engine reported a count "
              "(arXiv and DBLP never do); it does not mean the paper is uncited. "
              "Ranking imputes the median of its peers rather than scoring it zero.",
              "",
              "A gap sweep finds topically adjacent work. It cannot judge whether a "
              "paper actually threatens the claim — that is the reviewer's call."]
    return "\n".join(lines)


def to_json(ranked):
    return json.dumps([
        {"title": c.title, "authors": c.authors, "year": c.year, "venue": c.venue,
         "doi": c.doi, "cited_by_count": c.cited_by_count, "paths": c.paths,
         "score": round(float(s), 4), "grade": g}
        for c, s, g in ranked], indent=2)
