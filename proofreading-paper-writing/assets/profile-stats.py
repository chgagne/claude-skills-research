#!/usr/bin/env python3
"""Register statistics for one or more LaTeX papers -> markdown."""
import argparse, os, pathlib, sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE)); sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))
from scholarly.latex import read_sources, split_sections   # noqa: E402
from proofread.stats import profile, to_markdown            # noqa: E402


def load(path):
    p = pathlib.Path(path)
    if p.is_dir():
        p = p / "source.tex"
    return read_sources(str(p))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="+"); ap.add_argument("--out", required=True); ap.add_argument("--title", default="corpus")
    a = ap.parse_args(argv)
    raw = "\n\n".join(load(p) for p in a.paths)
    prof = profile(split_sections(raw), raw)
    parts = [to_markdown(prof, a.title + " (pooled)")]
    if len(a.paths) > 1:
        for p in a.paths:
            t = load(p)
            parts.append(to_markdown(profile(split_sections(t), t), os.path.basename(os.path.normpath(p))))
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write("\n---\n\n".join(parts))
    print(f"wrote {a.out}: {prof['n_sentences']} sentences pooled")
    return 0


if __name__ == "__main__":
    sys.exit(main())
