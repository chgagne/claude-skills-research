#!/usr/bin/env python3
"""List every figure and table of a LaTeX paper, with what cites it, and render the figure files.

    python3 figure-inventory.py [paper-dir] [--out review-assets/figures]

Writes <out>/inventory.md (paste it into review §6 and answer every row) and <out>/inventory.json (read by
check-review-form.py --inventory), and one PNG per image file under <out>/ (PDF figures rendered with mutool or
pdftoppm, rasters copied). Each item: an id (F1.. for figures, T1.. for tables), label, first caption sentence,
image files, and every sentence that references the label (or "never referenced").  Stdlib only.
"""
import json, re, shutil, subprocess, sys, pathlib

IMG = (".pdf", ".png", ".jpg", ".jpeg", ".eps")
REF = r"\\(?:ref|cref|Cref|autoref|subref|figref|tabref)\*?\{([^}]*)\}"


def main_tex(d):
    mains = [t for t in sorted(d.rglob("*.tex")) if re.search(r"^[^%]*\\documentclass", t.read_text(errors="ignore"), re.M)]
    if not mains:
        sys.exit(f"no .tex with \\documentclass under {d}")
    return min(mains, key=lambda t: (t.name not in ("main.tex", "paper.tex"), len(str(t))))


def flatten(t, root, depth=0):
    s = re.sub(r"(?<!\\)%.*", "", t.read_text(errors="ignore"))
    if depth > 6:
        return s
    def rep(m):
        name = m.group(2).strip()
        for base in (t.parent, root):
            f = base / (name if name.endswith(".tex") else name + ".tex")
            if f.is_file():
                return flatten(f, root, depth + 1)
        return m.group(0)
    return re.sub(r"\\(input|include|subfile)\{([^}]+)\}", rep, s)


def braced(s, i):
    """Text of the {...} group starting at s[i] == '{'."""
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "{": depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0: return s[i + 1:j]
    return s[i + 1:]


def caption_of(env):
    ms = list(re.finditer(r"\\caption(?:of\{[^}]*\})?(?:\[[^\]]*\])?\s*\{", env))
    if not ms: return ""
    m = ms[-1]   # with subfigures, the float's own caption comes last
    c = braced(env, m.end() - 1)
    c = re.sub(r"\\label\{[^}]*\}", "", c)
    c = re.sub(r"\s+", " ", c).strip()
    first = re.split(r"(?<=[a-z0-9\)\]])\.\s", c, maxsplit=1)[0]
    return first[:300]


def sentences_citing(text, labels):
    out = []
    plain = re.sub(r"\\begin\{(figure|table|wrapfigure|wraptable)\*?\}.*?\\end\{\1\*?\}", " ", text, flags=re.S)
    for para in re.split(r"\n\s*\n", plain):
        for sent in re.split(r"(?<=[\.\?!])\s+(?=[A-Z\\])", para):
            refs = {r.strip() for g in re.findall(REF, sent) for r in g.split(",")}
            if refs & labels:
                out.append(re.sub(r"\s+", " ", sent).strip()[:400])
    return out


def resolve(name, paths):
    for base in paths:
        for ext in ("",) + IMG:
            f = base / (name + ext)
            if f.is_file(): return f
    return None


def render(src, dst_stem):
    if src.suffix.lower() in (".png", ".jpg", ".jpeg"):
        dst = dst_stem.with_suffix(src.suffix.lower()); shutil.copy(src, dst); return dst
    if src.suffix.lower() == ".pdf":
        dst = dst_stem.with_suffix(".png")
        for cmd in (["mutool", "draw", "-q", "-r", "110", "-o", str(dst), str(src), "1"],
                    ["pdftoppm", "-r", "110", "-png", "-singlefile", "-f", "1", "-l", "1", str(src), str(dst_stem)]):
            try:
                if subprocess.run(cmd, capture_output=True, timeout=120).returncode == 0 and dst.exists(): return dst
            except (OSError, subprocess.TimeoutExpired):
                continue
    return None


def inventory(d, out):
    mt = main_tex(d); root = mt.parent; text = flatten(mt, root)
    gp = re.findall(r"\\graphicspath\{((?:\{[^}]*\})+)\}", text)
    paths = [root] + [root / p for g in gp for p in re.findall(r"\{([^}]*)\}", g)] + [d]
    items, nf, nt = [], 0, 0
    for m in re.finditer(r"\\begin\{(figure|table|wrapfigure|wraptable)(\*?)\}(.*?)\\end\{\1\2\}", text, re.S):
        kind = "table" if m.group(1) in ("table", "wraptable") else "figure"
        env = m.group(3)
        if kind == "figure": nf += 1; iid = f"F{nf}"
        else: nt += 1; iid = f"T{nt}"
        labels = set(re.findall(r"\\label\{([^}]+)\}", env))
        files = []
        for f in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", env):
            p = resolve(f.strip(), paths)
            r = render(p, out / f"{iid}_{len(files) + 1}") if p else None
            files.append({"source": f.strip(), "found": bool(p), "render": str(r) if r else None})
        cites = sentences_citing(text, labels) if labels else []
        items.append({"id": iid, "kind": kind, "labels": sorted(labels), "caption": caption_of(env),
                      "files": files, "cited_by": cites})
    return items


def write_md(items, out):
    L = ["# Figure and table inventory", "",
         "Answer every row in review §6: what it shows (from the render; tables: what the rows/columns hold),",
         "whether it supports the sentence(s) citing it (yes / partly / no / not cited), and the problem if any.", ""]
    for it in items:
        L.append(f"## {it['id']}  ({it['kind']}; {', '.join(it['labels']) or 'no label'})")
        L.append(f"- caption: {it['caption'] or '(none)'}")
        for f in it["files"]:
            L.append(f"- file: {f['source']} -> {'render: ' + f['render'] if f['render'] else ('not rendered' if f['found'] else 'FILE MISSING')}")
        if it["cited_by"]:
            for s in it["cited_by"][:4]: L.append(f"- cited by: \"{s}\"")
            if len(it["cited_by"]) > 4: L.append(f"- cited by: ({len(it['cited_by']) - 4} more)")
        else:
            L.append("- cited by: never referenced in the text")
        L.append("")
    L += ["Row format for §6 (one row per id, none skipped):", "",
          "| id | shows | supports citing claim | problem |", "|---|---|---|---|"]
    L += [f"| {it['id']} | | | |" for it in items]
    (out / "inventory.md").write_text("\n".join(L) + "\n")


def main():
    args = sys.argv[1:]
    out = pathlib.Path("review-assets/figures")
    if "--out" in args:
        i = args.index("--out"); out = pathlib.Path(args[i + 1]); del args[i:i + 2]
    d = pathlib.Path(args[0] if args else ".").resolve()
    out.mkdir(parents=True, exist_ok=True)
    items = inventory(d, out)
    (out / "inventory.json").write_text(json.dumps(items, indent=1))
    write_md(items, out)
    nr = sum(1 for it in items for f in it["files"] if f["render"])
    print(f"{len(items)} items ({sum(i['kind'] == 'figure' for i in items)} figures, {sum(i['kind'] == 'table' for i in items)} tables), "
          f"{nr} images rendered -> {out}/inventory.md. Answer every row in review §6.")


if __name__ == "__main__":
    main()
