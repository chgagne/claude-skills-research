#!/usr/bin/env python3
"""Write claude-plugin-eval cases (case.yaml + scaffold.sh + draft/) for surveying-literature.

The drafts and the key file stay outside the repository: the scaffold copies the draft
into the run's working directory and installs the Semantic Scholar key in the run's
isolated HOME, because `claude plugin eval` passes neither files nor secret-looking
variables. Engines are switched off by exporting EVAL_SCHOLARLY_DISABLE before the eval,
which does pass through.

  make_cases.py --drafts private/drafts --out <plugin>/evals --key-file <0600 file> --shared <dir> [ids...]

Bash has no network inside a run unless each host is granted: pass
  --allow-tools "WebFetch(domain:api.semanticscholar.org)" "WebFetch(domain:api.crossref.org)"
                "WebFetch(domain:export.arxiv.org)" "WebFetch(domain:sparql.dblp.org)"
to claude plugin eval, identically for every arm.
"""
import argparse, json, os, pathlib, shutil, sys

PROMPT = """A co-author asks you to check the related work of the paper draft in `./draft`
(LaTeX sources; the main file is `draft/{main}`). The draft is unpublished: do not search
for its title or its text, and do not try to find the draft itself online.

Find published work the draft should cite but does not: the related work a knowledgeable
reviewer would say is missing. Anything already in the draft's bibliography does not count.

End your final message with exactly one fenced `json` block: a list of at most 30
candidates, most important first, each with the title and, when you have them, the first
author, year and DOI or arXiv id:

```json
{{"candidates": [{{"title": "...", "first_author": "...", "year": 2024, "doi": "...", "arxiv": "..."}}]}}
```
"""

SCAFFOLD = """#!/bin/bash
here="$(cd "$(dirname "$0")" && pwd)"
cp -R "$here/draft" ./draft
# the skills import ~/.claude/skills/_shared, which a run's fresh HOME lacks
mkdir -p "$HOME/.claude/skills" && cp -R "{shared}" "$HOME/.claude/skills/_shared"
mkdir -p "$HOME/.config/scholarly"
cp "{key}" "$HOME/.config/scholarly/s2_key" && chmod 600 "$HOME/.config/scholarly/s2_key"
"""

GRADER = """---
type: regex
pattern: "```json[\\\\s\\\\S]*\\"candidates\\""
target: last_message
---
Format check only. Recall is scored offline by score.py.
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--drafts", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--key-file", required=True); ap.add_argument("--originals", required=True)
    ap.add_argument("--shared", required=True, help="frozen copy of _shared to install in each run's HOME")
    ap.add_argument("--runs", type=int, default=3); ap.add_argument("--timeout", type=int, default=2400)
    ap.add_argument("ids", nargs="+")
    a = ap.parse_args(argv)
    O = json.loads(pathlib.Path(a.originals).read_text())
    for pid in a.ids:
        d = pathlib.Path(a.out) / pid
        if d.exists():
            shutil.rmtree(d)
        (d / "graders").mkdir(parents=True)
        shutil.copytree(pathlib.Path(a.drafts) / pid, d / "draft")
        body = PROMPT.format(main="main.tex")   # fix_filenames.py makes the root main.tex everywhere
        yaml = ["schema_version: \"1.1\"", f"name: \"{pid}\"", f"runs: {a.runs}", "execution:",
                "  max_turns: 80", f"  timeout_seconds: {a.timeout}",
                "  allowed_tools: [Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch, Skill]",
                "  prompt: |"] + ["    " + l for l in body.splitlines()] + [
                "context:", "  scaffold_script: scaffold.sh"]
        (d / "case.yaml").write_text("\n".join(yaml) + "\n")
        (d / "scaffold.sh").write_text(SCAFFOLD.format(key=os.path.abspath(a.key_file), shared=os.path.abspath(a.shared)))
        os.chmod(d / "scaffold.sh", 0o755)
        (d / "graders" / "json-block.md").write_text(GRADER)
        print("wrote", d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
