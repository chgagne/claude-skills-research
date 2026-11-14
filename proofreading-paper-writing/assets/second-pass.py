#!/usr/bin/env python3
"""Second pass by fresh-eyes subagents, one per section.

    python3 second-pass.py split paper.tex --ledger writing-ledger.jsonl [--out pass2]
    python3 second-pass.py merge --ledger writing-ledger.jsonl [--out pass2]

split: cuts the paper into its abstract and top-level sections (subsections stay with their section;
appendix sections count) and writes, per section k, `pass2/sec-kk.tex` (the section's source) and
`pass2/sec-kk.anchors.txt` (the anchors already in the ledger that fall in it), plus `pass2/sections.json`.
Dispatch one subagent per section with `reference/second-pass-prompt.md`; each writes `pass2/sec-kk.jsonl`:
new ledger rows without ids, or one line {"none": "<what was re-read>"}.

merge: refuses until every section has its result file and every `none` says what was read; drops rows
whose anchor is already in the ledger; appends the rest with ids continuing the ledger's numbering (a
`W<n>:` tag in the comment is rewritten to the new id), status `proposed`. Refuses to merge twice.
Stdlib only.
"""
import json
import pathlib
import re
import sys

HEAD = re.compile(r"\\section\*?\{([^}]*)\}")


def sections(tex):
    body = tex.split("\\begin{document}", 1)[-1].split("\\end{document}", 1)[0]
    out = []
    m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", body, re.S)
    if m:
        out.append({"title": "Abstract", "text": m.group(1)})
        body = body[:m.start()] + body[m.end():]
    heads = list(HEAD.finditer(body))
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(body)
        out.append({"title": h.group(1).strip(), "text": body[h.start():end]})
    return out


def norm(s):
    return " ".join((s or "").split())


def load(path):
    p = pathlib.Path(path)
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def split(paper, ledger, out):
    out = pathlib.Path(out); out.mkdir(parents=True, exist_ok=True)
    secs = sections(pathlib.Path(paper).read_text())
    rows = load(ledger)
    meta = []
    for k, s in enumerate(secs, 1):
        (out / f"sec-{k:02d}.tex").write_text(s["text"])
        t = norm(s["text"])
        anchors = [r["anchor"] for r in rows if norm(r.get("anchor")) and norm(r.get("anchor")) in t]
        (out / f"sec-{k:02d}.anchors.txt").write_text("\n".join(anchors) + ("\n" if anchors else ""))
        meta.append({"k": k, "title": s["title"], "file": f"sec-{k:02d}.tex", "result": f"sec-{k:02d}.jsonl",
                     "existing_rows": len(anchors)})
    (out / "sections.json").write_text(json.dumps(meta, indent=1))
    return meta


def merge(ledger, out):
    out = pathlib.Path(out)
    meta = json.loads((out / "sections.json").read_text())
    if (out / "MERGED").exists():
        raise SystemExit("refusing: pass 2 already merged (pass2/MERGED exists)")
    missing, bad, new = [], [], []
    for s in meta:
        f = out / s["result"]
        if not f.exists():
            missing.append(s["result"]); continue
        for x in load(f):
            if "none" in x:
                if len(norm(x["none"])) < 5:
                    bad.append(f"{s['result']}: 'none' must say what was re-read")
            else:
                new.append(x)
    if missing:
        raise SystemExit("refusing: no subagent result for " + ", ".join(missing) +
                         " (dispatch one subagent per section; see reference/second-pass-prompt.md)")
    if bad:
        raise SystemExit("refusing: " + "; ".join(bad))
    rows = load(ledger)
    have = {norm(r.get("anchor")) for r in rows}
    nxt = max([int(r["id"][1:]) for r in rows if str(r.get("id", "")).startswith("W")] + [0]) + 1
    added = 0
    with open(ledger, "a", encoding="utf-8") as fh:
        for x in new:
            if norm(x.get("anchor")) in have:
                continue
            have.add(norm(x.get("anchor")))
            x = dict(x); x["id"] = f"W{nxt}"; x["status"] = "proposed"; x.setdefault("cut_reason", None)
            if x.get("comment"):
                x["comment"] = re.sub(r"^W\d+:\s*", "", x["comment"])
                x["comment"] = f"W{nxt}: " + x["comment"]
            fh.write(json.dumps(x, ensure_ascii=False) + "\n")
            nxt += 1; added += 1
    (out / "MERGED").write_text(str(added))
    return added


def main(argv):
    def opt(name, default=None):
        return argv[argv.index(name) + 1] if name in argv else default
    if len(argv) >= 3 and argv[1] == "split":
        meta = split(argv[2], opt("--ledger", "writing-ledger.jsonl"), opt("--out", "pass2"))
        print(f"{len(meta)} sections -> {opt('--out', 'pass2')}/sec-NN.tex; dispatch one subagent per section")
        for s in meta:
            print(f"  {s['k']:2d}  {s['title'][:50]}  ({s['existing_rows']} rows already)")
        return 0
    if len(argv) >= 2 and argv[1] == "merge":
        n = merge(opt("--ledger", "writing-ledger.jsonl"), opt("--out", "pass2"))
        print(f"OK merged {n} new rows")
        return 0
    sys.stderr.write(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
