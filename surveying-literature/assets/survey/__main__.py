import argparse
import datetime
import os
import sys

from . import traverse
from .rank import rank
from .fieldmap import cluster, order_clusters
from .fieldmap import to_markdown as fieldmap_markdown
from .report import to_json, to_markdown
from .seeds import extract, tex_sources

sys.path.insert(0, os.path.expanduser("~/.claude/skills/_shared"))
from scholarly import retrieval  # noqa: E402


def _find_main_tex(paper_dir):
    for name in ("main.tex", "paper.tex", "manuscript.tex"):
        p = os.path.join(paper_dir, name)
        if os.path.exists(p):
            return p
    tex = [os.path.join(paper_dir, f) for f in sorted(os.listdir(paper_dir))
           if f.endswith(".tex")]
    return tex[0] if tex else None


def _find_bib(paper_dir, given):
    if given:
        return given if os.path.isabs(given) else os.path.join(paper_dir, given)
    for f in sorted(os.listdir(paper_dir)):
        if f.endswith(".bib") and "corrected" not in f:
            return os.path.join(paper_dir, f)
    return None


def _field_map(a):
    """Topic in, chronology of coupled clusters out. No draft required."""
    from .seeds import Seed
    seed = Seed(title=a.field_map, angles=[a.field_map])
    candidates = traverse.expand(seed, max_per_seed=a.max_per_seed,
                                 max_angles=a.max_angles)
    groups = order_clusters(cluster(candidates, min_shared=a.min_shared))
    os.makedirs(a.out, exist_ok=True)
    stamp = datetime.date.today().strftime("%Y%m%d")
    path = os.path.join(a.out, f"lit-review-{stamp}.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(fieldmap_markdown(groups, a.field_map))
    print(f"wrote {path}")
    print(f"{len(candidates)} papers in {len(groups)} cluster(s)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="survey", description="Find related work a draft may have missed.")
    ap.add_argument("paper_dir")
    ap.add_argument("--bib", help="bibliography (default: the first .bib found)")
    ap.add_argument("--main", help="main .tex (default: main.tex)")
    ap.add_argument("--out", default=".", help="directory for the report")
    ap.add_argument("--max-per-seed", type=int, default=20)
    ap.add_argument("--max-angles", type=int, default=10)
    ap.add_argument("--field-map", metavar="TOPIC",
                    help="map a field instead of sweeping for gaps")
    ap.add_argument("--min-shared", type=int, default=3,
                    help="references two papers must share to cluster")
    ap.add_argument("--seeds-only", action="store_true",
                    help="print what was extracted from the draft, make no requests")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    if a.field_map:
        return _field_map(a)

    main_tex = a.main or _find_main_tex(a.paper_dir)
    if not main_tex:
        print(f"no .tex found in {a.paper_dir}", file=sys.stderr)
        return 1
    bib = _find_bib(a.paper_dir, a.bib)
    if not bib:
        print(f"no .bib found in {a.paper_dir}", file=sys.stderr)
        return 1

    seed = extract(tex_sources(main_tex), bib)

    if a.seeds_only:
        print(f"title       : {seed.title}")
        print(f"abstract    : {seed.abstract[:160]}")
        print(f"cited keys  : {len(seed.cited_keys)}")
        print(f"cited titles: {len(seed.cited_titles)}")
        print(f"angles      : {traverse._pick_angles(list(seed.angles), a.max_angles)}")
        return 0

    if not a.quiet:
        print(f"{len(seed.cited_titles)} seed works, "
              f"{min(a.max_angles, len(seed.angles))} angles", file=sys.stderr)

    candidates = traverse.expand(seed, max_per_seed=a.max_per_seed,
                                 max_angles=a.max_angles)
    ranked = rank(candidates, seed)

    os.makedirs(a.out, exist_ok=True)
    stamp = datetime.date.today().strftime("%Y%m%d")
    md_path = os.path.join(a.out, f"related-work-gaps-{stamp}.md")
    js_path = os.path.join(a.out, "candidates.json")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(to_markdown(ranked, seed, traverse.UNRESOLVED_SEEDS))
    with open(js_path, "w", encoding="utf-8") as fh:
        fh.write(to_json(ranked))

    threats = sum(1 for _, _, g in ranked if g == "THREAT")
    print(f"wrote {md_path} and {js_path}")
    print(f"{len(ranked)} candidates, {threats} needing a response")

    if retrieval.SOURCE_FAILURES:
        detail = ", ".join(f"{h} ({n})"
                           for h, n in sorted(retrieval.SOURCE_FAILURES.items()))
        print(f"WARNING: source coverage was degraded — {detail}. "
              f"OpenAlex bills each search against a small daily budget that "
              f"resets at midnight UTC; re-run then for full coverage.",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
