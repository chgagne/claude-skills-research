#!/usr/bin/env python3
"""Extract what a related-work audit needs from a LaTeX draft.

  draft_extract.py DRAFT_DIR_OR_MAIN_TEX --work W [--bib a.bib b.bib]

Finds the main .tex (has \\documentclass and \\begin{document}), inlines \\input/\\include,
strips comments, and writes:
  W/draft.json          title, authors, abstract, per-section cleaned text with [CITE:keys]
                        markers, novelty-claim sentences, prior-work claims lacking a citation,
                        cited keys, parsed .bib entries (title/authors/year/venue/doi/arxiv/cited)
  W/draft_summary.md    human-readable digest (also printed to stdout)
"""
import argparse
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from litlib import clean_doi, find_arxiv_id, tex_to_text, warn, work_file, write_json  # noqa: E402

CITE_RE = re.compile(r"\\[A-Za-z]*cite[A-Za-z]*\*?\s*(?:\[[^\]]*\]\s*){0,2}\{([^}]*)\}")
INPUT_RE = re.compile(r"\\(?:input|include|subfile)\s*\{([^}]+)\}"
                      r"|\\(?:sub)?import\*?\s*\{([^}]*)\}\s*\{([^}]+)\}")
SECTION_RE = re.compile(r"\\(?:chapter|section)\*?(?![A-Za-z])")
NOVELTY_RE = re.compile(
    r"\b(first|novel|to (?:the best of )?our knowledge|we propose|we introduce|we present|"
    r"we develop|unlike (?:prior|previous|existing|most|other)|in contrast to (?:prior|previous|"
    r"existing)|no (?:prior|previous|existing) (?:work|method|approach)|(?:has|have) not been|"
    r"remains? (?:unexplored|open|largely)|our (?:main |key )?contributions?|for the first time|"
    r"new (?:method|approach|framework|paradigm|perspective))\b", re.I)
PRIOR_RE = re.compile(
    r"\b((?:prior|previous|existing|recent|earlier|related|many|several|some) (?:work|works|"
    r"methods|approaches|studies|literature|research|papers|efforts)|(?:has|have) been (?:widely |"
    r"extensively |recently |previously )?(?:studied|explored|shown|proposed|used|investigated|"
    r"demonstrated|observed)|state[- ]of[- ]the[- ]art|well[- ]known|widely[- ]used|"
    r"commonly used|popular|standard (?:approach|practice|benchmark|dataset|technique))\b", re.I)
STYLE_HINT_RE = re.compile(
    r"neurips|nips|icml|iclr|acl|emnlp|naacl|coling|cvpr|iccv|eccv|aaai|ijcai|kdd|sigir|www|"
    r"chi|uist|colm|tmlr|jmlr|ieee|acmart|sig|lncs|llncs|siam|elsarticle|aistats|uai|corl|rss|"
    r"icra|iros|miccai|interspeech|icassp", re.I)


def read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def strip_comments(s):
    s = re.sub(r"\\begin\{comment\}.*?\\end\{comment\}", "", s, flags=re.S)
    lines = []
    for line in s.split("\n"):
        m = re.search(r"(?<!\\)%", line)
        lines.append(line[:m.start()] if m else line)
    s = "\n".join(lines)
    return re.sub(r"\\iffalse\b.*?\\fi\b", "", s, flags=re.S)


def expand(path, root, depth=0, seen=None):
    seen = set() if seen is None else seen
    ap = os.path.abspath(path)
    if depth > 20 or ap in seen:
        return ""
    seen.add(ap)
    s = strip_comments(read(path))
    base = os.path.dirname(path)

    def repl(m):
        if m.group(1):
            name = m.group(1).strip()
            cands = [os.path.join(root, name), os.path.join(base, name)]
        else:
            name = m.group(3).strip()
            d = m.group(2).strip()
            cands = [os.path.join(base, d, name), os.path.join(root, d, name)]
        for c in cands:
            for p in (c, c + ".tex"):
                if os.path.isfile(p):
                    return "\n" + expand(p, root, depth + 1, seen) + "\n"
        warn(f"could not resolve \\input {name!r}")
        return ""

    return INPUT_RE.sub(repl, s)


def find_main(d):
    cands = []
    for p in glob.glob(os.path.join(d, "**", "*.tex"), recursive=True):
        try:
            s = strip_comments(read(p))
        except OSError:
            continue
        if re.search(r"\\documentclass", s) and "\\begin{document}" in s:
            cands.append(p)
    if not cands:
        return None
    pref = [p for p in cands if os.path.basename(p).lower() in ("main.tex", "paper.tex", "ms.tex")]
    pool = pref or cands
    return min(pool, key=lambda p: (os.path.relpath(p, d).count(os.sep), -os.path.getsize(p)))


def braced_arg(s, i):
    """Return (content, end) of the {...} argument at/after i, skipping [optional] args."""
    n = len(s)
    while i < n and s[i] in " \t\n":
        i += 1
    while i < n and s[i] == "[":
        depth = 0
        while i < n:
            if s[i] == "[":
                depth += 1
            elif s[i] == "]":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1
        while i < n and s[i] in " \t\n":
            i += 1
    if i >= n or s[i] != "{":
        return None, i
    depth, start = 0, i
    while i < n:
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[start + 1:i], i + 1
        i += 1
    return s[start + 1:], n


def all_args(s, name):
    for m in re.finditer(r"\\" + name + r"\*?(?![A-Za-z])", s):
        arg, _ = braced_arg(s, m.end())
        if arg is not None:
            yield arg


def first_arg(s, names):
    for name in names:
        for arg in all_args(s, name):
            if arg.strip():
                return arg
    return None


def delatex(s):
    s = CITE_RE.sub(lambda m: " [CITE:" + ",".join(
        k.strip() for k in m.group(1).split(",") if k.strip()) + "]", s)
    s = re.sub(r"\\begin\{(equation|align|gather|multline|eqnarray|displaymath)\*?\}.*?"
               r"\\end\{\1\*?\}", " [EQ] ", s, flags=re.S)
    s = re.sub(r"\\\[.*?\\\]", " [EQ] ", s, flags=re.S)
    s = re.sub(r"\\begin\{(tabular|tabularx|tabular\*|algorithmic|tikzpicture|lstlisting|"
               r"verbatim|minted)\}.*?\\end\{\1\}", " ", s, flags=re.S)
    s = re.sub(r"\\(?:label|ref|eqref|autoref|cref|Cref|pageref|vspace|hspace|includegraphics|"
               r"bibliographystyle|bibliography|addbibresource|url|setlength|addtolength)\*?\s*"
               r"(?:\[[^\]]*\])?\s*\{[^{}]*\}", " ", s)
    s = re.sub(r"\\(?:begin|end)\s*\{[^}]*\}(?:\[[^\]]*\])?", " ", s)
    s = re.sub(r"\\item\b(?:\s*\[[^\]]*\])?", "\n- ", s)
    s = s.replace("\\\\", "\n")
    s = re.sub(r"\\([%&$#_])", r"\1", s)
    s = re.sub(r"\\[A-Za-z@]+\*?", " ", s)
    s = s.replace("~", " ").replace("{", "").replace("}", "")
    s = re.sub(r"[ \t]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n\n", s).strip()


_SENT_SPLIT = re.compile(r"(?<=[.!?])(?<!\bal\.)(?<!e\.g\.)(?<!i\.e\.)(?<!\bcf\.)(?<!\bvs\.)"
                         r"(?<!Fig\.)(?<!Sec\.)(?<!\bEq\.)\s+(?=[A-Z\[(\"`])")


def sentences(text):
    out = []
    for para in re.split(r"\n\s*-\s+|\n\s*\n", text):
        para = " ".join(para.split())
        for s in _SENT_SPLIT.split(para):
            s = s.strip()
            if len(s) > 25:
                out.append(s)
    return out


def split_sections(body):
    marks = []
    for m in SECTION_RE.finditer(body):
        title, end = braced_arg(body, m.end())
        if title is not None:
            marks.append((m.start(), end, tex_to_text(title)))
    app = re.search(r"\\appendix\b|\\begin\{appendices\}", body)
    app_pos = app.start() if app else None
    out = []
    if not marks:
        return [("(body)", body, False)]
    if marks[0][0] > 0:
        out.append(("(front matter)", body[:marks[0][0]], False))
    for i, (st, en, title) in enumerate(marks):
        stop = marks[i + 1][0] if i + 1 < len(marks) else len(body)
        out.append((title, body[en:stop], app_pos is not None and st > app_pos))
    return out


# ---------------------------------------------------------------- bibliography

def parse_fields(s, strings):
    f, i, n = {}, 0, len(s)
    while i < n:
        while i < n and s[i] in " \t\r\n,":
            i += 1
        if i >= n:
            break
        m = re.compile(r"([A-Za-z0-9_\-:.+]+)\s*=\s*").match(s, i)
        if not m:
            j = s.find(",", i)
            if j < 0:
                break
            i = j + 1
            continue
        name = m.group(1).lower()
        i = m.end()
        parts = []
        while i < n:
            while i < n and s[i] in " \t\r\n":
                i += 1
            if i >= n:
                break
            c = s[i]
            if c == "{":
                depth, j = 0, i
                while j < n:
                    if s[j] == "{":
                        depth += 1
                    elif s[j] == "}":
                        depth -= 1
                        if depth == 0:
                            break
                    j += 1
                parts.append(s[i + 1:j])
                i = j + 1
            elif c == '"':
                depth, j = 0, i + 1
                while j < n:
                    if s[j] == "{":
                        depth += 1
                    elif s[j] == "}":
                        depth -= 1
                    elif s[j] == '"' and depth == 0:
                        break
                    j += 1
                parts.append(s[i + 1:j])
                i = j + 1
            else:
                m2 = re.compile(r"[^\s,#]+").match(s, i)
                if not m2:
                    break
                w = m2.group(0)
                parts.append(strings.get(w.lower(), w))
                i = m2.end()
            while i < n and s[i] in " \t\r\n":
                i += 1
            if i < n and s[i] == "#":
                i += 1
                continue
            break
        f[name] = "".join(parts)
    return f


def parse_bib(text):
    entries, strings = [], {}
    head = re.compile(r"@\s*([A-Za-z]+)\s*([{(])")
    i, n = 0, len(text)
    while True:
        m = head.search(text, i)
        if not m:
            break
        typ = m.group(1).lower()
        close = "}" if m.group(2) == "{" else ")"
        j = k = m.end()
        depth = 0
        while k < n:
            c = text[k]
            if c == "{":
                depth += 1
            elif c == "}":
                if depth == 0 and close == "}":
                    break
                depth -= 1
            elif c == ")" and close == ")" and depth == 0:
                break
            k += 1
        body = text[j:k]
        i = k + 1
        if typ in ("comment", "preamble"):
            continue
        if typ == "string":
            for name, val in parse_fields(body, strings).items():
                strings[name.lower()] = val
            continue
        key, _, rest = body.partition(",")
        entries.append({"key": key.strip(), "type": typ, "fields": parse_fields(rest, strings)})
    return entries


def bib_record(e):
    f = e["fields"]
    yr = re.search(r"\d{4}", f.get("year", "") or f.get("date", "") or "")
    eprint = f.get("eprint", "")
    arxiv = find_arxiv_id(eprint, bare_ok=True) if eprint else None
    arxiv = arxiv or find_arxiv_id(" ".join(f.get(k, "") for k in (
        "journal", "journaltitle", "url", "note", "howpublished", "volume", "doi", "booktitle",
        "archiveprefix", "publisher")))
    venue = (f.get("booktitle") or f.get("journal") or f.get("journaltitle")
             or f.get("howpublished") or f.get("publisher") or f.get("school") or "")
    return {"key": e["key"], "type": e["type"], "title": tex_to_text(f.get("title", "")),
            "authors": tex_to_text(f.get("author", "") or f.get("editor", "")),
            "year": int(yr.group(0)) if yr else None, "venue": tex_to_text(venue),
            "doi": clean_doi(f.get("doi")), "arxiv": arxiv, "url": f.get("url")}


def parse_bbl(text):
    out = []
    pat = re.compile(r"\\bibitem\s*(?:\[(?:[^\[\]]|\[[^\]]*\])*\])?\s*\{([^}]+)\}(.*?)"
                     r"(?=\\bibitem|\\end\{thebibliography\}|$)", re.S)
    for m in pat.finditer(text):
        parts = re.split(r"\\newblock", m.group(2))
        title = parts[1] if len(parts) > 1 else parts[0]
        raw = tex_to_text(m.group(2))
        out.append({"key": m.group(1).strip(), "type": "bbl", "title": tex_to_text(title).strip(" ."),
                    "authors": tex_to_text(parts[0]).strip(" ."),
                    "year": int(y.group(0)) if (y := re.search(r"(?:19|20)\d{2}", raw)) else None,
                    "venue": tex_to_text(parts[2]) if len(parts) > 2 else "",
                    "doi": clean_doi(raw), "arxiv": find_arxiv_id(raw), "url": None})
    return out


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", help="draft directory or main .tex file")
    ap.add_argument("--work", required=True, help="audit work directory")
    ap.add_argument("--bib", nargs="*", help="explicit .bib files (default: from \\bibliography)")
    a = ap.parse_args()

    if os.path.isdir(a.src):
        root = a.src
        main_tex = find_main(root)
    else:
        main_tex, root = a.src, os.path.dirname(os.path.abspath(a.src))
    if not main_tex:
        sys.exit("No main .tex with \\documentclass and \\begin{document} found; pass it explicitly.")
    full = expand(main_tex, root)
    m = re.search(r"\\begin\{document\}", full)
    preamble, body = (full[:m.start()], full[m.end():]) if m else ("", full)
    e = re.search(r"\\end\{document\}", body)
    if e:
        body = body[:e.start()]

    title = tex_to_text(first_arg(full, ["title", "icmltitle"]) or "")
    authors = [tex_to_text(x) for name in ("author", "icmlauthor", "name") for x in all_args(full, name)]
    authors_raw = "; ".join(x for x in authors if x)[:800]
    anonymous = (not authors_raw) or bool(re.search(r"anonymous", authors_raw, re.I))
    absm = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", full, re.S)
    abstract = delatex(absm.group(1)) if absm else delatex(first_arg(body, ["abstract"]) or "")
    pkgs = re.findall(r"\\(?:usepackage|documentclass)(?:\[[^\]]*\])?\{([^}]*)\}", preamble)
    style_hints = sorted({p.strip() for ps in pkgs for p in ps.split(",") if STYLE_HINT_RE.search(p)})

    cited, seen = [], set()
    for cm in CITE_RE.finditer(body):
        for k in cm.group(1).split(","):
            k = k.strip()
            if k and k not in seen:
                seen.add(k)
                cited.append(k)

    sections, novelty, uncited = [], [], []
    if abstract:
        for s in sentences(abstract):
            if NOVELTY_RE.search(s):
                novelty.append({"section": "Abstract", "sentence": s})
    for i, (stitle, raw, is_app) in enumerate(split_sections(body)):
        text = delatex(raw)
        keys = []
        for cm in CITE_RE.finditer(raw):
            keys += [k.strip() for k in cm.group(1).split(",") if k.strip()]
        sections.append({"title": stitle, "appendix": is_app, "n_cites": len(keys),
                         "cite_keys": sorted(set(keys)), "words": len(text.split()), "text": text})
        if is_app:
            continue
        early = i <= 3 or re.search(r"intro|related|background|prior|motivation|overview", stitle, re.I)
        for s in sentences(text):
            if NOVELTY_RE.search(s) and len(novelty) < 80:
                novelty.append({"section": stitle, "sentence": s})
            if early and "[CITE:" not in s and PRIOR_RE.search(s) and len(uncited) < 50:
                uncited.append({"section": stitle, "sentence": s})

    # bibliography files
    names = []
    for arg in all_args(full, "bibliography"):
        names += [x.strip() for x in arg.split(",") if x.strip()]
    names += [x.strip() for x in all_args(full, "addbibresource")]
    bib_files = []
    if a.bib:
        bib_files = a.bib
    else:
        for nme in names:
            for base in (root, os.path.dirname(os.path.abspath(main_tex))):
                p = os.path.join(base, nme)
                p = p if p.endswith(".bib") else p + ".bib"
                if os.path.isfile(p) and p not in bib_files:
                    bib_files.append(p)
                    break
            else:
                warn(f"bibliography {nme!r} not found")
        if not bib_files:
            bib_files = sorted(glob.glob(os.path.join(root, "**", "*.bib"), recursive=True))
    bib, keys_seen = [], set()
    for bf in bib_files:
        for ent in parse_bib(read(bf)):
            if ent["key"] in keys_seen:
                continue
            keys_seen.add(ent["key"])
            bib.append(bib_record(ent))
    if not bib:
        bbls = sorted(glob.glob(os.path.join(root, "**", "*.bbl"), recursive=True))
        for bf in bbls:
            bib += parse_bbl(read(bf))
        if bbls:
            warn(f"no .bib entries found; parsed {len(bib)} \\bibitems from {bbls}")
            bib_files = bbls
    cite_all = "*" in seen
    for b in bib:
        b["cited"] = cite_all or b["key"] in seen
    bib_keys = {b["key"] for b in bib}
    missing_keys = [k for k in cited if k != "*" and k not in bib_keys]

    draft = {"main": os.path.abspath(main_tex), "title": title, "authors_raw": authors_raw,
             "anonymous": anonymous, "style_hints": style_hints, "abstract": abstract,
             "sections": sections, "novelty_claims": novelty, "uncited_claims": uncited,
             "cited_keys": cited, "missing_bib_keys": missing_keys,
             "bib_files": [os.path.abspath(x) for x in bib_files], "bib": bib}
    write_json(work_file(a.work, "draft.json"), draft)

    L = [f"# Draft summary\n", f"- Main file: {draft['main']}", f"- Title: {title or '(not found)'}",
         f"- Authors (from source): {authors_raw or '(none)'}{'  [anonymous?]' if anonymous else ''}",
         f"- Style/class hints: {', '.join(style_hints) or '-'}", "", "## Abstract", "", abstract or "(not found)",
         "", "## Sections (citations per section)", ""]
    for s in sections:
        L.append(f"- {s['title']}{' [appendix]' if s['appendix'] else ''}: {s['n_cites']} cites, {s['words']} words")
    L += ["", "## Novelty / contribution sentences (claims to test)", ""]
    L += [f"- [{x['section']}] {x['sentence']}" for x in novelty] or ["- (none detected; read the intro)"]
    L += ["", "## Statements about prior work with no citation in the sentence", ""]
    L += [f"- [{x['section']}] {x['sentence']}" for x in uncited] or ["- (none detected)"]
    uncited_bib = [b["key"] for b in bib if not b["cited"]]
    L += ["", "## Bibliography", "",
          f"- {len(bib)} entries from {len(bib_files)} file(s); {sum(b['cited'] for b in bib)} cited in the text",
          f"- In .bib but never cited ({len(uncited_bib)}): {', '.join(uncited_bib[:40])}"
          + (" ..." if len(uncited_bib) > 40 else ""),
          f"- Cited keys missing from .bib ({len(missing_keys)}): {', '.join(missing_keys[:40])}"]
    summary = "\n".join(L) + "\n"
    with open(work_file(a.work, "draft_summary.md"), "w", encoding="utf-8") as f:
        f.write(summary)
    print(summary)
    print(f"Wrote {work_file(a.work, 'draft.json')} (per-section text under sections[].text)")


if __name__ == "__main__":
    main()
