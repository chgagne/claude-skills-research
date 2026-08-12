import argparse
import datetime
import os
import re
import sys

from .assemble import build
from .fulltext import Document, fetch, split_sections
from .report import DRAFT, to_json, to_markdown
from .resolve import from_candidates, resolve
from scholarly.latex import read_sources  # noqa: E402

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


def load_draft(paper_dir, main=None):
    path = main or _find_main_tex(paper_dir)
    if not path:
        return None
    return Document(sections=split_sections(read_sources(path)), source="local-latex")


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="compare",
        description="Put a draft and its closest prior work side by side.")
    ap.add_argument("paper_dir")
    ap.add_argument("--against", action="append", default=[], metavar="PAPER",
                    help="title, DOI or arXiv id; repeatable")
    ap.add_argument("--from-candidates", metavar="PATH",
                    help="candidates.json from a gap sweep")
    ap.add_argument("--grade", default="THREAT",
                    help="grade to take from candidates.json (default THREAT)")
    ap.add_argument("--limit", type=int, default=5,
                    help="most papers to compare against (default 5)")
    ap.add_argument("--main", help="main .tex (default: main.tex)")
    ap.add_argument("--out", default="review-assets")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    draft = load_draft(a.paper_dir, a.main)
    if draft is None:
        print(f"no .tex found in {a.paper_dir}", file=sys.stderr)
        return 1

    refs = []
    for q in a.against:
        r = resolve(q)
        if r is None:
            print(f"could not resolve (skipped): {q}", file=sys.stderr)
        else:
            refs.append(r)
    if a.from_candidates:
        refs.extend(from_candidates(a.from_candidates, grades=(a.grade,)))
    refs = refs[:a.limit]

    if not refs:
        print("nothing to compare against; pass --against or --from-candidates",
              file=sys.stderr)
        return 1

    sources = {DRAFT: (draft.source, draft.degraded)}
    docs, named = {}, {}
    for r in refs:
        name = (r.title or "?").split(":")[0][:40]
        if not a.quiet:
            print(f"fetching {name}…", file=sys.stderr)
        doc = fetch(r)
        docs[name] = doc
        named[name] = r
        sources[name] = (doc.source, doc.degraded)

    rows = build(draft, docs)

    os.makedirs(a.out, exist_ok=True)
    stamp = datetime.date.today().strftime("%Y%m%d")
    md_path = os.path.join(a.out, f"paper-comparison-{stamp}.md")
    js_path = os.path.join(a.out, "comparison.json")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(to_markdown(rows, named, sources))
    with open(js_path, "w", encoding="utf-8") as fh:
        fh.write(to_json(rows))

    noted = sum(1 for r in rows if r.note)
    print(f"wrote {md_path} and {js_path}")
    print(f"{len(refs)} paper(s) compared on {len(rows)} axes, {noted} computed note(s)")

    degraded = [n for n, (_s, d) in sources.items() if d]
    if degraded:
        print(f"WARNING: only abstracts were reachable for {', '.join(degraded)} — "
              f"appendix-level axes will read as not found.", file=sys.stderr)
        return 2
    if retrieval.SOURCE_FAILURES:
        print(f"WARNING: source coverage degraded: "
              f"{dict(retrieval.SOURCE_FAILURES)}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
