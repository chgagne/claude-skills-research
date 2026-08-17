"""Render the pairings as a table, coverage first.

Coverage before findings, as in the proof and bibliography reports: "3 of 9
abstract assertions paired" is usually the more important number, because an
unpaired claim means the tool found nothing in the results to compare against,
not that the claim is fine.
"""


def _clip(s, n=90):
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def render(pairings, degraded):
    total = len(pairings)
    paired = sum(1 for p in pairings if p.results)
    lines = ["# Claim strength", ""]

    if degraded:
        lines += ["> **Degraded run.** " + "; ".join(degraded), ""]

    lines += [f"{paired} of {total} abstract assertions paired with a results "
              f"sentence sharing at least 3 content words.", "",
              "Rungs: 1 consistent-with, 2 associated-with, 3 predicts, "
              "4 contributes-to, 5 improves, 6 causes. A hedge demotes one rung.",
              "",
              "| Abstract | Rung | Results | Rung | Diff |",
              "|---|---|---|---|---|"]

    for p in sorted(pairings, key=lambda x: -x.delta):
        if p.results:
            results_cell = _clip(p.results)
            r_label = f"{p.results_rung.label} ({p.results_rung.level})"
            diff = str(p.delta)
        else:
            results_cell = "*no matching results sentence*"
            r_label = "—"
            diff = "—"
        a_label = f"{p.abstract_rung.label} ({p.abstract_rung.level})"
        if p.abstract_rung.hedged:
            a_label += ", hedged"
        lines.append(f"| {_clip(p.abstract)} | {a_label} | {results_cell} "
                     f"| {r_label} | {diff} |")

    lines += ["", "A difference is not a finding. Read both sentences and decide "
                  "whether the abstract is claiming more than the results section "
                  "supports; the tool does not make that judgement."]
    return "\n".join(lines) + "\n"
