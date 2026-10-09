#!/usr/bin/env python3
"""Flag runs whose agent fetched the source paper (PROTOCOL-A.md, Contamination).

Reads run JSONL with traces. Counts only the agent's own requests: WebFetch URLs, WebSearch
queries and Bash commands. The source showing up in tool *results* is not contamination.
"""
import argparse, json, os, pathlib, re, sys
sys.path.insert(0, os.path.expanduser("~/.claude/skills/_shared"))
from scholarly.textnorm import norm_title  # noqa: E402


def requests(trace):
    for line in (trace or "").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") != "assistant":
            continue
        for c in e["message"]["content"]:
            if c.get("type") == "tool_use" and c["name"] in ("WebFetch", "WebSearch", "Bash"):
                inp = c.get("input", {})
                yield c["name"], str(inp.get("url") or inp.get("query") or inp.get("command") or "")


def flags(trace, arxiv_id, doi, title):
    words = set(norm_title(title).split())
    out = []
    for tool, text in requests(trace):
        low = text.lower()
        if arxiv_id and arxiv_id in low:
            out.append(f"{tool}: arXiv id")
        elif doi and doi.lower() in low:
            out.append(f"{tool}: DOI")
        elif tool == "WebSearch" and words:
            q = set(norm_title(text).split())
            if len(q & words) >= 0.6 * len(words):
                out.append(f"WebSearch: title words ({len(q & words)}/{len(words)})")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("runs", nargs="+"); ap.add_argument("--gold", required=True)
    a = ap.parse_args(argv)
    G = json.loads(pathlib.Path(a.gold).read_text())
    for path in a.runs:
        for line in pathlib.Path(path).read_text().splitlines():
            r = json.loads(line)
            me = G["self"][r["case"]]
            f = flags(r.get("trace"), me.get("arxiv"), me.get("doi"), me.get("title", ""))
            if f:
                print(json.dumps({"arm": r["arm"], "case": r["case"], "run": r.get("run"), "flags": f}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
