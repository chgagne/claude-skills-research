"""Field-map mode: what does this area look like, rather than what did we miss.

Clusters by bibliographic coupling -- two papers that cite the same works are
doing related things, regardless of whether either cites the other. That finds
parallel lines of work, which co-citation misses for anything recent.
"""
import statistics


def _shared(a, b):
    return len(getattr(a, "referenced", set()) & getattr(b, "referenced", set()))


def cluster(candidates, min_shared=3):
    """Union-find over bibliographic coupling. Returns a list of lists."""
    items = list(candidates.values())
    parent = list(range(len(items)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[max(ri, rj)] = min(ri, rj)

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if _shared(items[i], items[j]) >= min_shared:
                union(i, j)

    groups = {}
    for idx, item in enumerate(items):
        groups.setdefault(find(idx), []).append(item)
    return list(groups.values())


def _median_year(group):
    years = [c.year for c in group if c.year]
    return statistics.median(years) if years else float("inf")


def order_clusters(groups):
    """Oldest lineage first, so the map reads as a chronology."""
    return sorted((sorted(g, key=lambda c: (c.year or 9999, c.title))
                   for g in groups), key=_median_year)


def _span(group):
    years = sorted(c.year for c in group if c.year)
    if not years:
        return "undated"
    return f"{years[0]}" if years[0] == years[-1] else f"{years[0]}–{years[-1]}"


def _cell(v):
    return str(v or "").replace("|", "\\|").replace("\n", " ")


def to_markdown(ordered_groups, topic):
    lines = [f"# Field map: {topic}", ""]
    if not ordered_groups:
        lines.append("No clusters. Nothing was retrieved, or no two papers "
                     "shared enough references to couple.")
        return "\n".join(lines)

    lines += [f"{len(ordered_groups)} cluster(s), ordered oldest lineage first. "
              f"Clustering is by bibliographic coupling: papers citing the same "
              f"works, whether or not they cite each other.", ""]
    for n, group in enumerate(ordered_groups, 1):
        lines += [f"## Cluster {n} ({_span(group)}, {len(group)} papers)", "",
                  "| Paper | Year | Venue | Cites |", "|---|---|---|---|"]
        for c in group:
            lines.append(f"| {_cell(c.title)} | {_cell(c.year)} "
                         f"| {_cell(c.venue)} | {c.cited_by_count} |")
        lines.append("")
    lines += ["## Reading this", "",
              "Clusters are lines of work, not a quality judgement. A cluster "
              "with no recent entries is either settled or abandoned; a cluster "
              "that is all recent is where the area is moving. What no cluster "
              "covers is the gap worth naming."]
    return "\n".join(lines)
